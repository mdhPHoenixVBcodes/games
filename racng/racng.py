import pygame
import random
import math

pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()

# ── AUDIO SETUP ─────────────────────────────────────────────────────────────
try:
    crack_sound = pygame.mixer.Sound("crack.wav")
    crack_sound.set_volume(0.5)
except Exception:
    crack_sound = None

# ── GAME SETUP ──────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trapdoor Rage")
clock = pygame.time.Clock()

# 🔥 RANDOM CONTROL INVERSION
INVERT_EVERY_FRAMES = 300
invert_active = False
invert_timer = 0

# 🔥 DEATH COUNTER & QUOTES
death_count = 0
DEATH_QUOTES = [
    "Skill issue.", "Try pressing space?", "Your mouse is broken.",
    "Maybe try walking?", "Gravity is hard.", "I believe in you! (not really)",
    "Rage quit yet?", "That looked painful.", "Almost... nope.",
    "Git gud.", "Did you forget how to jump?", "The floor misses you."
]
current_death_quote = ""
death_quote_timer = 0
ui_font = pygame.font.Font(None, 28)

# 🔥 FALL MESSAGE SYSTEM
FALL_MESSAGES = [
    "You can do this.", "Almost there!", "So close...", "Keep trying!",
    "Just one more!", "You got this!", "Don't give up!", "Rage yet?",
    "Try jumping earlier!", "Maybe next time!"
]
fall_message = ""
fall_message_timer = 0
msg_font = pygame.font.Font(None, 50)
win_font = pygame.font.Font(None, 52)
win_text_active = False
win_text_timer = 0

#  LEVEL PROGRESSION
current_level = 1
flag_touch_count = 0
LEVELS_TO_ADVANCE = 3
level_transition_active = False
level_transition_timer = 0
flag_touched_this_round = False

# ── PLAYER ──────────────────────────────────────────────────────────────────
player = pygame.Rect(100, 500, 30, 30)
vel_y = 0
on_ground = False

# ── LEVEL 1 OBJECTS ─────────────────────────────────────────────────────────
class TrapPlatform:
    def __init__(self, x, y, w, h, is_trap=True, is_invisible=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.is_trap = is_trap
        self.state = "closed"
        self.timer = 0
        self.open_delay = 15
        self.close_delay = 45
        self.target_landings = random.randint(2, 7)
        self.current_landings = 0
        self.disabled = False
        self.is_invisible = is_invisible
        self.reactivate_timer = 0
        self.reactivate_delay = random.randint(600, 1200)

    def update(self):
        if self.disabled:
            self.reactivate_timer += 1
            if self.reactivate_timer >= self.reactivate_delay:
                self.disabled = False
                self.is_trap = True
                self.current_landings = 0
                self.target_landings = random.randint(2, 7)
                self.state = "closed"
                self.timer = 0
                self.reactivate_timer = 0
                self.reactivate_delay = random.randint(600, 1200)
            return
        if self.state == "opening":
            self.timer += 1
            if self.timer >= self.open_delay:
                self.state = "open"
                self.timer = 0
        elif self.state == "open":
            self.timer += 1
            if self.timer >= self.close_delay:
                self.state = "closed"
                self.timer = 0

    def draw(self, surf, camera_x=0):
        if self.is_invisible or self.state == "open":
            return
        r = self.rect.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (80, 180, 80), r)
        if self.state == "opening":
            crack_w = min(self.timer * 2, 8)
            pygame.draw.line(surf, (0, 0, 0),
                           (r.centerx - crack_w, r.top),
                           (r.centerx + crack_w, r.bottom), 3)

class Flag:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 10, 50)
        self.active = True
        self.touched = False

    def draw(self, surf, camera_x=0):
        if not self.active: return
        r = self.rect.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (200, 200, 200), r)
        if not self.touched:
            pygame.draw.polygon(surf, (255, 215, 0), [
                (r.right, r.top), (r.right + 30, r.top + 15), (r.right, r.top + 30)
            ])

class SideWall:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 40, HEIGHT)
        self.active = False
        self.speed = 7.5

    def activate(self, spawn_x):
        self.active = True
        self.rect.x = spawn_x
        self.rect.y = 0

    def update(self):
        if self.active:
            self.rect.x -= self.speed
            if self.rect.right < -50:
                self.active = False

    def draw(self, surf, camera_x=0):
        if not self.active: return
        r = self.rect.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (220, 50, 50), r)
        for i in range(0, r.height, 30):
            pygame.draw.line(surf, (255, 100, 100),
                             (r.left, r.top + i), (r.right, r.bottom - i), 4)

# ─ LEVEL 2: INFINITE GROUND + HOLES + GAP WALLS ───────────────────────────
GROUND_Y = 500
camera_x = 0
level2_platforms = []
level2_next_x = 0
level2_gap_walls = []  # 🔥 NEW: Stores walls in gaps

def init_level2():
    global level2_platforms, level2_next_x, camera_x, level2_gap_walls
    level2_platforms = []
    level2_next_x = 0
    camera_x = 0
    level2_gap_walls = []
    for _ in range(5):
        add_level2_segment(safe_start=True)

def add_level2_segment(safe_start=False):
    global level2_next_x
    plat_w = random.randint(120, 250)
    hole_w = random.randint(90, 150)
        
    level2_platforms.append(pygame.Rect(level2_next_x, GROUND_Y, plat_w, 20))
    
    # 🔥 GAP WALL LOGIC: 40% chance to spawn a wall in the gap
    if not safe_start and random.random() < 0.4:
        wall_x = level2_next_x + plat_w + (hole_w // 2) - 5
        # Wall sits in middle of gap, 40px tall (requires precise jump to clear)
        level2_gap_walls.append(pygame.Rect(wall_x, GROUND_Y - 40, 10, 40))
        
    level2_next_x += plat_w + hole_w

def update_level2():
    while level2_next_x < camera_x + WIDTH + 500:
        add_level2_segment()
    level2_platforms[:] = [p for p in level2_platforms if p.right > camera_x - 200]
    level2_gap_walls[:] = [w for w in level2_gap_walls if w.right > camera_x - 200]

def draw_level2(surf):
    for plat in level2_platforms:
        r = plat.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (80, 180, 80), r)
        
    # 🔥 DRAW GAP WALLS
    for wall in level2_gap_walls:
        r = wall.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (160, 30, 30), r)  # Dark red (visible but easy to miss)
        pygame.draw.rect(surf, (200, 60, 60), r, 1)  # Thin outline

# ── INITIAL SETUP ───────────────────────────────────────────────────────────
def setup_level1():
    traps = [
        TrapPlatform(50, 550, 700, 20, is_trap=False),
        TrapPlatform(300, 480, 150, 20, is_trap=True),
        TrapPlatform(550, 410, 100, 20, is_trap=True),
        TrapPlatform(200, 340, 120, 20, is_trap=True),
        TrapPlatform(420, 375, 80, 20, is_trap=False, is_invisible=True)
    ]
    traps[3].open_delay = 40
    return traps

platforms = setup_level1()
flag = Flag(250, 300)
side_wall = SideWall()

# ─── MAIN LOOP ──────────────────────────────────────────────────────────────
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 🔥 INVERSION LOGIC
    invert_timer += 1
    if invert_timer >= INVERT_EVERY_FRAMES:
        invert_active = not invert_active
        invert_timer = 0

    keys = pygame.key.get_pressed()
    left, right, jump = keys[pygame.K_LEFT], keys[pygame.K_RIGHT], keys[pygame.K_SPACE]
    if invert_active: left, right = right, left

    if left: player.x -= 5
    if right: player.x += 5
    if jump and on_ground:
        vel_y = -12
        on_ground = False

    # Physics
    prev_bottom = player.bottom
    vel_y += 0.8
    player.y += vel_y
    on_ground = False

    #  TIMERS
    if win_text_timer > 0:
        win_text_timer -= 1
        if win_text_timer <= 0: win_text_active = False
            
    if fall_message_timer > 0:
        fall_message_timer -= 1
        if fall_message_timer == 0: fall_message = ""
            
    if level_transition_timer > 0:
        level_transition_timer -= 1
        if level_transition_timer <= 0: level_transition_active = False
            
    if death_quote_timer > 0:
        death_quote_timer -= 1
        if death_quote_timer == 0: current_death_quote = ""

    # 🔥 FLAG COLLISION
    if flag.active and player.colliderect(flag.rect) and not level_transition_active:
        flag.active = False
        flag.touched = True
        flag_touched_this_round = True
        flag_touch_count += 1

        if flag_touch_count >= LEVELS_TO_ADVANCE:
            current_level = 2
            level_transition_active = True
            level_transition_timer = 150
            init_level2()
            player.topleft = (100, 450)
            vel_y = 0
            fall_message = ""
            fall_message_timer = 0
            win_text_active = False
            win_text_timer = 0
            side_wall.active = False
        else:
            side_wall.activate(flag.rect.x + 100)
            win_text_active = True
            win_text_timer = 120

    # 🔥 WALL UPDATE
    side_wall.update()
    if side_wall.active and player.colliderect(side_wall.rect):
        player.right = side_wall.rect.left - 2
        vel_y = 6
        player.x -= 8
        on_ground = False

    # 🔥 CAMERA & COLLISION LOGIC
    if current_level == 2:
        target_cam = player.x - 300
        camera_x = max(0, target_cam)
        update_level2()
        
        # Platform collision
        for plat in level2_platforms:
            if player.colliderect(plat):
                if vel_y >= 0 and prev_bottom <= plat.top and player.bottom >= plat.top:
                    player.bottom = plat.top
                    vel_y = 0
                    on_ground = True
                    
        #  GAP WALL COLLISION (NEW)
        for wall in level2_gap_walls:
            if player.colliderect(wall):
                # If hitting mid-air, smash into wall and force fall
                player.right = wall.left - 2
                player.x -= 4
                vel_y = 10  # Hard downward force
                on_ground = False
                # Small screen shake effect could be added here
    else:
        for p in platforms:
            p.update()
            if p.state == "open": continue
            if player.colliderect(p.rect):
                if vel_y >= 0 and prev_bottom <= p.rect.top + 10:
                    player.bottom = p.rect.top
                    vel_y = 0
                    on_ground = True
                    if p.is_trap and not p.disabled and p.state == "closed":
                        p.state = "opening"
                        p.timer = 0
                        p.current_landings += 1
                        if crack_sound: crack_sound.play()
                        if fall_message_timer <= 0:
                            fall_message = random.choice(FALL_MESSAGES)
                            fall_message_timer = 180
                        if p.current_landings >= p.target_landings:
                            p.disabled = True
                            p.is_trap = False
                            p.state = "closed"

    #  DEATH RESET + COUNTER + QUOTES
    if player.y > HEIGHT and not level_transition_active:
        death_count += 1
        current_death_quote = random.choice(DEATH_QUOTES)
        death_quote_timer = 180
        
        if not flag_touched_this_round:
            flag_touch_count = 0
        
        current_level = 1
        camera_x = 0
        player.topleft = (100, 500)
        vel_y = 0
        
        level2_platforms = []
        level2_next_x = 0
        level2_gap_walls = []
        
        platforms = setup_level1()
        flag = Flag(250, 300)
        side_wall.active = False
        win_text_active = False
        win_text_timer = 0
        fall_message = ""
        fall_message_timer = 0
        invert_active = False
        invert_timer = 0
        flag_touched_this_round = False

    # ── RENDER ──────────────────────────────────────────────────────────
    screen.fill((20, 20, 30))
    
    if level_transition_active:
        screen.fill((255, 255, 255))
        txt = win_font.render(f"LEVEL {current_level}", True, (0, 0, 0))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
    else:
        if current_level == 1:
            for p in platforms: p.draw(screen)
            flag.draw(screen)
            side_wall.draw(screen)
        else:
            draw_level2(screen)
            
        screen_player_rect = pygame.Rect(player.x - camera_x, player.y, player.width, player.height)
        pygame.draw.rect(screen, (255, 255, 255), screen_player_rect)

        #  DEATH COUNTER
        death_txt = ui_font.render(f"Deaths: {death_count}", True, (255, 100, 100))
        screen.blit(death_txt, (WIDTH - death_txt.get_width() - 20, 20))

        # 🔥 DEATH QUOTE
        if death_quote_timer > 0 and current_death_quote:
            quote_surf = msg_font.render(current_death_quote, True, (255, 120, 120))
            screen.blit(quote_surf, (WIDTH//2 - quote_surf.get_width()//2, HEIGHT - 100))

        if win_text_active and win_text_timer > 0:
            win_txt = win_font.render("YOU WIN!", True, (255, 255, 0))
            screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, HEIGHT - 60))
            
        if fall_message_timer > 0 and fall_message:
            msg_surf = msg_font.render(fall_message, True, (255, 255, 255))
            screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, HEIGHT - 60))
            
        if invert_active:
            pygame.draw.rect(screen, (255, 50, 50), (10, 10, 20, 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()