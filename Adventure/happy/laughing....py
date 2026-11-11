import pygame
import random
import math
import time

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

# 🔥 GAME START TIME
game_start_time = time.time()

# 🔥 RANDOM CONTROL INVERSION
INVERT_EVERY_FRAMES = 300
invert_active = False
invert_timer = 0

# 🔥 JUMP LOCKOUT SETTINGS
jump_lockout_active = False
jump_lockout_end_time = 0
next_jump_lockout_time = pygame.time.get_ticks() + random.randint(15000, 20000)

# 🔥 DEATH COUNTER & QUOTES
death_count = 0
DEATH_QUOTES = [
    "Skill issue.", "Try pressing space?", "Your mouse is broken.",
    "Maybe try walking?", "Gravity is hard.", "I believe in you! (not really)",
    "Rage quit yet?", "That looked painful.", "Almost... nope.",
    "Git gud.", "Did you forget how to jump?", "The floor misses you.",
    "L + Ratio.", "Emotional damage.", "Have you tried uninstalling?",
    "My grandma plays better.", "Was that a speedrun?", "Imagine being good at this.",
    "Are you even trying?", "GG EZ.", "Maybe play something easier?",
    "I've seen better from a bot.", "Touch grass.", "That's gotta hurt.",
    "Uninstall confirmed.", "Were you lagging?", "Nice fail.",
    "0/10 would not watch again.", "Are you okay?", "Call an ambulance."
]
current_death_quote = ""
death_quote_timer = 0
ui_font = pygame.font.Font(None, 28)

# 🔥 FALL MESSAGE SYSTEM
FALL_MESSAGES = [
    "You can do this.", "Almost there!", "So close...", "Keep trying!",
    "Just one more!", "You got this!", "Don't give up!", "Rage yet?",
    "Try jumping earlier!", "Maybe next time!",
    "Oops.", "Watch your step.", "The floor is lava.", "Did you mean to do that?",
    "Gravity: 1, You: 0.", "Nice try, though.", "It's a trap!", 
    "Falling is just flying with style... downwards.", "Look down.",
    "Hold my hand.", "Uh oh.", "Spaghetti time!", "Hold onto your butts.",
    "Yikes.", "That wasn't supposed to happen.", "Surprise!",
    "I meant to do that.", "Calculated risk.", "Trust the process."
]
fall_message = ""
fall_message_timer = 0
msg_font = pygame.font.Font(None, 50)
win_font = pygame.font.Font(None, 52)
win_text_active = False
win_text_timer = 0

# 🔥 LEVEL PROGRESSION
current_level = 1
flag_touch_count = 0
LEVELS_TO_ADVANCE = 3
level_transition_active = False
level_transition_timer = 0
flag_touched_this_round = False
flag_touch_cooldown = 0

# 🔥 LEVEL 2 TIMERS & OBSTACLES
level2_entry_time = 0
hallucination_spawned = False
hallucination_flag_active = False
hallucination_flag_pos = (0, 0)
hallucination_approach_count = 0

#  MID-JUMP TRAP WALL
mid_jump_wall = None
wall_spawned_this_jump = False

# ── PLAYER ───────────────────────────────────────────────────────────────
player = pygame.Rect(100, 500, 30, 30)
vel_y = 0
on_ground = False

# ─ LEVEL 1 & 3 OBJECTS ─────────────────────────────────────────────────────
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
        self.killed = False

    def activate(self, spawn_x):
        self.active = True
        self.killed = False
        self.rect.x = spawn_x
        self.rect.y = 0

    def update(self):
        if self.active:
            self.rect.x -= self.speed
            if self.rect.right < -50:
                self.active = False

    def draw(self, surf, camera_x=0):
        if not self.active or self.killed: return
        r = self.rect.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (220, 50, 50), r)
        for i in range(0, r.height, 30):
            pygame.draw.line(surf, (255, 100, 100),
                             (r.left, r.top + i), (r.right, r.bottom - i), 4)

# ── LEVEL 2: INFINITE GROUND + HOLES ──────────────────────────────────────
GROUND_Y = 500
camera_x = 0
level2_platforms = []
level2_next_x = 0

def init_level2():
    global level2_platforms, level2_next_x, camera_x
    level2_platforms = []
    level2_next_x = 0
    camera_x = 0
    for _ in range(5):
        add_level2_segment(safe_start=True)

def add_level2_segment(safe_start=False):
    global level2_next_x
    plat_w = random.randint(120, 250)
    hole_w = random.randint(90, 150)
    level2_platforms.append(pygame.Rect(level2_next_x, GROUND_Y, plat_w, 20))
    level2_next_x += plat_w + hole_w

def update_level2():
    while level2_next_x < camera_x + WIDTH + 500:
        add_level2_segment()
    level2_platforms[:] = [p for p in level2_platforms if p.right > camera_x - 200]

def draw_level2(surf):
    for plat in level2_platforms:
        r = plat.copy()
        r.x -= camera_x
        pygame.draw.rect(surf, (80, 180, 80), r)

# ── LEVEL 3 SETUP ─────────────────────────────────────────────────────────
level3_platforms = []
level3_flag = None
level3_side_wall = None

def setup_level3():
    global level3_platforms, level3_flag, level3_side_wall
    level3_platforms = [
        TrapPlatform(50, 550, 700, 20, is_trap=False),
        TrapPlatform(250, 470, 140, 20, is_trap=True),
        TrapPlatform(480, 390, 110, 20, is_trap=True),
        TrapPlatform(180, 310, 130, 20, is_trap=True),
        TrapPlatform(350, 360, 90, 20, is_trap=False, is_invisible=True)
    ]
    level3_platforms[3].open_delay = 40
    level3_flag = Flag(230, 260)
    level3_side_wall = SideWall()

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

# Initialize
platforms = setup_level1()
flag = Flag(250, 300)
side_wall = SideWall()

# ─── MAIN LOOP ──────────────────────────────────────────────────────────────
running = True
while running:
    current_time = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 🔥 INVERSION LOGIC
    invert_timer += 1
    if invert_timer >= INVERT_EVERY_FRAMES:
        invert_active = not invert_active
        invert_timer = 0

    # 🔥 JUMP LOCKOUT TIMER LOGIC
    if not jump_lockout_active and current_time >= next_jump_lockout_time:
        jump_lockout_active = True
        jump_lockout_end_time = current_time + 3000  # 3 seconds
        next_jump_lockout_time = current_time + random.randint(15000, 20000) # Next in 15-20s

    if jump_lockout_active and current_time >= jump_lockout_end_time:
        jump_lockout_active = False

    #  MOUSE & KEYBOARD INPUT HANDLING
    keys = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_x, mouse_y = pygame.mouse.get_pos()

    kb_left = keys[pygame.K_LEFT]
    kb_right = keys[pygame.K_RIGHT]
    kb_jump = keys[pygame.K_SPACE]

    mouse_move_left = False
    mouse_move_right = False
    mouse_jump = False

    if mouse_buttons[0]:
        if mouse_x < WIDTH // 2:
            mouse_move_left = True
        else:
            mouse_move_right = True

    if mouse_buttons[2]:
        mouse_jump = True

    left = kb_left or mouse_move_left
    right = kb_right or mouse_move_right
    jump = kb_jump or mouse_jump

    # 🔥 DISABLE JUMP IF LOCKED OUT
    if jump_lockout_active:
        jump = False

    if invert_active: left, right = right, left

    # 🔥 TRANSITION LOCK
    if level_transition_active:
        player.topleft = (100, 450)
        vel_y = 0
        on_ground = True
    else:
        if left: player.x -= 5
        if right: player.x += 5
            
        if jump and on_ground:
            vel_y = -12
            on_ground = False

    # Physics
    if not level_transition_active:
        prev_bottom = player.bottom
        vel_y += 0.8
        player.y += vel_y
        on_ground = False

    # 🔥 TIMERS
    if win_text_timer > 0: win_text_timer -= 1; win_text_active = win_text_timer > 0
    if fall_message_timer > 0: fall_message_timer -= 1; fall_message = fall_message if fall_message_timer > 0 else ""
    if level_transition_timer > 0: 
        level_transition_timer -= 1
        if level_transition_timer <= 0: level_transition_active = False
    if death_quote_timer > 0: death_quote_timer -= 1; current_death_quote = current_death_quote if death_quote_timer > 0 else ""
    if flag_touch_cooldown > 0: flag_touch_cooldown -= 1

    # ─ LEVEL 2 SPECIFIC LOGIC ────────────────────────────────────────────
    if current_level == 2 and not level_transition_active:
        time_in_l2 = current_time - level2_entry_time
        target_cam = player.x - 300
        camera_x = max(0, target_cam)
        update_level2()

        prev_plat = None
        next_plat = None
        for plat in level2_platforms:
            if plat.right <= player.left + 5:
                if prev_plat is None or plat.right > prev_plat.right:
                    prev_plat = plat
            elif plat.left >= player.right - 5:
                if next_plat is None or plat.left < next_plat.left:
                    next_plat = plat

        for plat in level2_platforms:
            if player.colliderect(plat):
                if vel_y >= 0 and prev_bottom <= plat.top and player.bottom >= plat.top:
                    player.bottom = plat.top
                    vel_y = 0
                    on_ground = True

        #  MID-JUMP TRAP WALL LOGIC
        if on_ground:
            wall_spawned_this_jump = False
            mid_jump_wall = None
        elif not on_ground and prev_plat and next_plat:
            gap_midpoint = (prev_plat.right + next_plat.left) // 2
            if player.x >= gap_midpoint and not wall_spawned_this_jump:
                mid_jump_wall = pygame.Rect(gap_midpoint - 5, GROUND_Y - 40, 10, 40)
                wall_spawned_this_jump = True

        if mid_jump_wall and player.colliderect(mid_jump_wall):
            player.right = mid_jump_wall.left - 1
            vel_y = 10
            on_ground = False

        #  HALLUCINATION FLAG
        if time_in_l2 >= 30000 and not hallucination_spawned:
            hallucination_flag_active = True
            hallucination_flag_pos = (player.x + 250, GROUND_Y - 50)
            hallucination_spawned = True

        if hallucination_flag_active:
            if abs(player.centerx - hallucination_flag_pos[0]) < 70:
                hallucination_flag_active = False
                current_death_quote = "yr hallucinating"
                death_quote_timer = 180
                hallucination_approach_count += 1
                
                if hallucination_approach_count >= 3:
                    current_level = 3
                    level_transition_active = True
                    level_transition_timer = 150
                    setup_level3()
                    player.topleft = (100, 500)
                    vel_y = 0
                    camera_x = 0
                    hallucination_approach_count = 0
                    hallucination_flag_active = False

    # ── LEVEL 1 & 3 LOGIC ─────────────────────────────────────────────────
    if current_level in [1, 3] and not level_transition_active and flag_touch_cooldown == 0:
        active_flag = flag if current_level == 1 else level3_flag
        active_wall = side_wall if current_level == 1 else level3_side_wall
        
        if active_flag.active and player.colliderect(active_flag.rect):
            active_flag.active = False
            flag_touch_count += 1
            flag_touched_this_round = True
            flag_touch_cooldown = 60
            
            if flag_touch_count >= LEVELS_TO_ADVANCE:
                side_wall.killed = True
                side_wall.active = False
                side_wall.rect.x = -999
                
                if current_level == 1:
                    current_level = 2
                    init_level2()
                    player.topleft = (100, 450)
                    level2_entry_time = current_time
                    hallucination_spawned = False
                else:
                    current_level = 1
                    platforms = setup_level1()
                    flag = Flag(250, 300)
                    player.topleft = (100, 500)
                    
                level_transition_active = True
                level_transition_timer = 150
                vel_y = 0
                win_text_active = False
            else:
                active_wall.activate(active_flag.rect.x + 100)
                win_text_active = True
                win_text_timer = 120

    active_wall = side_wall if current_level == 1 else level3_side_wall
    if active_wall and active_wall.active and not active_wall.killed and not level_transition_active:
        active_wall.update()
        if player.colliderect(active_wall.rect):
            player.right = active_wall.rect.left - 2
            vel_y = 12
            player.x -= 8
            on_ground = False

    if current_level != 2 and not level_transition_active:
        lvl_platforms = platforms if current_level == 1 else level3_platforms
        for p in lvl_platforms:
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

    # 🔥 DEATH RESET
    if player.y > HEIGHT and not level_transition_active:
        death_count += 1
        if not current_death_quote: current_death_quote = random.choice(DEATH_QUOTES)
        death_quote_timer = 180
        if not flag_touched_this_round: flag_touch_count = 0
        
        current_level = 1
        camera_x = 0
        player.topleft = (100, 500)
        vel_y = 0
        flag_touched_this_round = False
        flag_touch_cooldown = 0
        
        level2_platforms = []
        level2_next_x = 0
        hallucination_spawned = False
        
        platforms = setup_level1()
        flag = Flag(250, 300)
        side_wall.killed = False
        side_wall.active = False
        side_wall.rect.x = -200
        if level3_side_wall: level3_side_wall.active = False
        win_text_active = False
        fall_message = ""
        invert_active = False
        invert_timer = 0
        
        # Reset jump lockout timer on death
        jump_lockout_active = False
        next_jump_lockout_time = current_time + random.randint(15000, 20000)

    # ── RENDER ───────────────────────────────────────────────────────────
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
        elif current_level == 2:
            draw_level2(screen)
            if hallucination_flag_active:
                hx, hy = hallucination_flag_pos
                hx -= camera_x
                pygame.draw.rect(screen, (200, 200, 200), (hx, hy, 10, 50))
                pygame.draw.polygon(screen, (255, 215, 0), [
                    (hx + 10, hy), (hx + 40, hy + 15), (hx + 10, hy + 30)
                ])
            if mid_jump_wall:
                bx = mid_jump_wall.x - camera_x
                pygame.draw.rect(screen, (255, 40, 40), (bx, GROUND_Y - 40, 10, 40))
                pygame.draw.rect(screen, (255, 150, 150), (bx, GROUND_Y - 40, 10, 40), 1)
        else:
            for p in level3_platforms: p.draw(screen)
            level3_flag.draw(screen)
            level3_side_wall.draw(screen)
            
        screen_player_rect = pygame.Rect(player.x - camera_x, player.y, player.width, player.height)
        pygame.draw.rect(screen, (255, 255, 255), screen_player_rect)

        # 🔥 PLAYTIME TIMER
        elapsed_time = int(time.time() - game_start_time)
        hours = elapsed_time // 3600
        minutes = (elapsed_time % 3600) // 60
        seconds = elapsed_time % 60
        if hours > 0:
            time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes}:{seconds:02d}"
        time_txt = ui_font.render(f"Time: {time_str}", True, (200, 200, 200))
        screen.blit(time_txt, (20, 50))

        # UI Elements
        death_txt = ui_font.render(f"Deaths: {death_count}", True, (255, 100, 100))
        screen.blit(death_txt, (WIDTH - death_txt.get_width() - 20, 20))
        
        if current_level in [1, 3]:
            prog_txt = ui_font.render(f"Flag: {flag_touch_count}/{LEVELS_TO_ADVANCE}", True, (255, 255, 100))
            screen.blit(prog_txt, (20, 20))

        if death_quote_timer > 0 and current_death_quote:
            quote_surf = msg_font.render(current_death_quote, True, (255, 120, 120))
            screen.blit(quote_surf, (WIDTH//2 - quote_surf.get_width()//2, HEIGHT - 100))
        if win_text_active and win_text_timer > 0:
            win_txt = win_font.render("YOU WIN!", True, (255, 255, 0))
            screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, HEIGHT - 60))
        if fall_message_timer > 0 and fall_message:
            msg_surf = msg_font.render(fall_message, True, (255, 255, 255))
            screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, HEIGHT - 60))
            
        # 🔥 INDICATOR BOXES (Top Left)
        if invert_active:
            pygame.draw.rect(screen, (255, 50, 50), (10, 10, 20, 20))  # Red box for inversion
            
        if jump_lockout_active:
            pygame.draw.rect(screen, (50, 100, 255), (35, 10, 20, 20))  # Blue box for jump lockout

    pygame.display.flip()
    clock.tick(60)

pygame.quit()