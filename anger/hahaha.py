import pygame
import random

pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()

# ── AUDIO SETUP ─────────────────────────────────────────────────────────────
try:
    crack_sound = pygame.mixer.Sound("crack.wav")
    crack_sound.set_volume(0.5)
except Exception:
    crack_sound = None
    print("💡 Place 'crack.wav' in the same folder for trap sounds!")

# ─── GAME SETUP ──────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trapdoor Rage")
clock = pygame.time.Clock()

class TrapPlatform:
    def __init__(self, x, y, w, h, is_trap=True):
        self.rect = pygame.Rect(x, y, w, h)
        self.is_trap = is_trap
        self.state = "closed"      # closed -> opening -> open
        self.timer = 0
        self.open_delay = 15       # Frames before opening
        self.reset_delay = 45      # Frames before closing again

        self.target_landings = random.randint(2, 7)
        self.current_landings = 0
        self.disabled = False
        self.chain_target = None   # 🔥 For chain traps

    def update(self):
        if self.state == "opening":
            self.timer += 1
            if self.timer >= self.open_delay:
                self.state = "open"
                self.timer = 0
        elif self.state == "open":
            self.timer += 1
            if self.timer >= self.reset_delay:
                self.state = "closed"
                self.timer = 0

    def draw(self, surf):
        if self.state == "open":
            return
        
        r = self.rect
        if self.disabled:
            pygame.draw.rect(surf, (50, 150, 255), r)  # Blue = Safe
        elif self.state == "closed":
            pygame.draw.rect(surf, (80, 180, 80), r)
        else:  # opening
            pygame.draw.rect(surf, (255, 90, 90), r)
            crack_w = min(self.timer * 2, 8)
            pygame.draw.line(surf, (0, 0, 0), 
                           (r.centerx - crack_w, r.top), 
                           (r.centerx + crack_w, r.bottom), 3)
            
            # 🔥 Draw warning arrow if chained
            if self.chain_target and not self.chain_target.disabled:
                pygame.draw.polygon(surf, (255, 255, 0), [
                    (r.right - 10, r.centery - 5),
                    (r.right, r.centery),
                    (r.right - 10, r.centery + 5)
                ])

# ─── PLAYER & PLATFORMS ──────────────────────────────────────────────────────
player = pygame.Rect(100, 500, 30, 30)
vel_y = 0
on_ground = False

platforms = [
    TrapPlatform(50, 550, 700, 20, is_trap=False),    # Ground
    TrapPlatform(300, 480, 150, 20, is_trap=True),    # Trap 1
    TrapPlatform(550, 410, 100, 20, is_trap=True),    # Trap 2
    TrapPlatform(200, 340, 120, 20, is_trap=True)     # Trap 3
]

# 🔥 SETUP CHAINS: Trap 1 → Trap 2 → Trap 3
platforms[1].chain_target = platforms[2]   # Trap at y=480 triggers trap at y=410
platforms[2].chain_target = platforms[3]   # Trap at y=410 triggers trap at y=340

font = pygame.font.SysFont("arial", 20, bold=True)

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  player.x -= 5
    if keys[pygame.K_RIGHT]: player.x += 5
    if keys[pygame.K_SPACE] and on_ground:
        vel_y = -12
        on_ground = False

    # Save position BEFORE applying gravity
    prev_bottom = player.bottom

    vel_y += 0.8
    player.y += vel_y
    on_ground = False

    for p in platforms:
        p.update()

        # Skip ONLY open platforms (disabled ones are still solid!)
        if p.state == "open":
            continue

        # Check rectangle overlap
        if player.colliderect(p.rect):
            # LANDING CHECK: Falling + was above platform last frame
            if vel_y >= 0 and prev_bottom <= p.rect.top + 10:
                player.bottom = p.rect.top
                vel_y = 0
                on_ground = True

                # Only trigger trap if NOT disabled and currently closed
                if p.is_trap and not p.disabled and p.state == "closed":
                    p.state = "opening"
                    p.timer = 0
                    p.current_landings += 1
                    
                    if crack_sound:
                        crack_sound.play()
                    
                    # 🔥 CHAIN TRAP LOGIC: Trigger linked trap immediately
                    if p.chain_target and not p.chain_target.disabled:
                        if p.chain_target.state == "closed":
                            p.chain_target.state = "opening"
                            p.chain_target.timer = 0
                            p.chain_target.current_landings += 1
                            if crack_sound:
                                crack_sound.play()
                    
                    # Disable after required landings
                    if p.current_landings >= p.target_landings:
                        p.disabled = True
                        p.is_trap = False
                        p.state = "closed"

    # Fall off screen = reset
    if player.y > HEIGHT:
        player.topleft = (100, 500)
        vel_y = 0
        for p in platforms:
            p.state = "closed"
            p.timer = 0

    # ─── RENDER ─────────────────────────────────────────────────────────────
    screen.fill((20, 20, 30))
    for p in platforms:
        p.draw(screen)
    pygame.draw.rect(screen, (255, 255, 255), player)

    # Show landing progress
    for p in platforms:
        if p.is_trap and not p.disabled:
            txt = font.render(f"{p.current_landings}/{p.target_landings}", True, (255, 255, 255))
            screen.blit(txt, (p.rect.x + 5, p.rect.y - 22))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()