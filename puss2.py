from ursina import *
import math
import random

# ==========================================
# 0. CONFIG & MODERN WARM PALETTE (0-255)
# ==========================================
RENDER_DISTANCE = 65.0

C_ORANGE       = color.rgb(235/255, 125/255, 45/255)
C_BLACK        = color.rgb(28/255, 25/255, 23/255)
C_WHITE        = color.rgb(250/255, 246/255, 240/255)
C_BROWN        = color.rgb(140/255, 75/255, 40/255)
C_DARK_BROWN   = color.rgb(70/255, 38/255, 20/255)
C_TAN          = color.rgb(225/255, 185/255, 135/255)
C_TEAL_SWEATER = color.rgb(65/255, 125/255, 135/255)
C_YELLOW       = color.rgb(235/255, 185/255, 45/255)
C_GOLD         = color.rgb(215/255, 165/255, 65/255)
C_DARK_GRAY    = color.rgb(45/255, 42/255, 40/255)
C_GRAY         = color.rgb(125/255, 118/255, 112/255)
C_LIGHT_GRAY   = color.rgb(195/255, 188/255, 180/255)
C_SALMON       = color.rgb(225/255, 125/255, 120/255)
C_LIME         = color.rgb(115/255, 175/255, 75/255)
C_AZURE        = color.rgb(55/255, 110/255, 185/255)
C_CYAN         = color.rgb(75/255, 180/255, 185/255)
C_RED          = color.rgb(205/255, 65/255, 55/255)
C_DARK_RED     = color.rgb(120/255, 30/255, 30/255)
C_PURPLE       = color.rgb(110/255, 45/255, 85/255)
C_PINK_HAIR    = color.rgb(185/255, 70/255, 115/255)
C_PEACH_SKIN   = color.rgb(245/255, 195/255, 165/255)

player = None
active_bots = []
game_started = False
selected_class = None
current_preview = None

# ==========================================
# 1. OPTIMIZED VISUAL BUILDERS (COMBINED MESHES)
# ==========================================
def build_puss_visuals(parent_ent):
    body = Entity(parent=parent_ent)
    Entity(parent=body, model='sphere', color=C_ORANGE, scale=(0.6, 0.8, 0.45), y=0.9)
    Entity(parent=body, model='cube', color=C_BROWN, scale=(0.65, 0.12, 0.5), y=0.65)
    Entity(parent=body, model='cube', color=C_YELLOW, scale=(0.15, 0.15, 0.52), y=0.65)

    for x_off in (-0.18, 0.18):
        Entity(parent=body, model='cube', color=C_ORANGE, scale=(0.18, 0.4, 0.18), y=0.35, x=x_off)
        Entity(parent=body, model='cube', color=C_BLACK, scale=(0.28, 0.15, 0.28), y=0.3, x=x_off)
        Entity(parent=body, model='cube', color=C_BLACK, scale=(0.24, 0.25, 0.35), y=0.12, x=x_off, z=0.05)
    body.combine(auto_destroy=True)

    head = Entity(parent=parent_ent, position=(0.25, 1.55, 0))
    try:
        Entity(parent=head, model='pussface.glb', scale=1.25)
    except:
        Entity(parent=head, model='sphere', color=C_ORANGE, scale=0.55)

    tail = Entity(parent=parent_ent, position=(0, 0.6, -0.25), rotation_x=-30)
    Entity(parent=tail, model='cube', color=C_ORANGE, scale=(0.08, 0.6, 0.08), y=-0.2, rotation_x=-20)
    tail.combine(auto_destroy=True)

    arm_r = Entity(parent=parent_ent, position=(0.35, 0.9, 0.1))
    Entity(parent=arm_r, model='sphere', color=C_ORANGE, scale=0.15)
    Entity(parent=arm_r, model='cube', color=C_BLACK, scale=(0.05, 0.3, 0.05), rotation_x=90)
    Entity(parent=arm_r, model='sphere', color=C_LIGHT_GRAY, scale=(0.25, 0.05, 0.25), z=0.15)
    Entity(parent=arm_r, model='cube', color=C_WHITE, scale=(0.03, 1.4, 0.03), position=(0, 0, 0.85), rotation_x=90)
    arm_r.combine(auto_destroy=True)

    return [arm_r]

def build_kitty_visuals(parent_ent):
    body = Entity(parent=parent_ent)
    Entity(parent=body, model='sphere', color=C_BLACK, scale=(0.55, 0.75, 0.4), y=0.85)
    Entity(parent=body, model='sphere', color=C_WHITE, scale=(0.3, 0.5, 0.41), y=0.88)
    Entity(parent=body, model='cube', color=C_BROWN, scale=(0.58, 0.1, 0.43), y=0.6)

    for x_off in (-0.16, 0.16):
        Entity(parent=body, model='cube', color=C_BLACK, scale=(0.16, 0.45, 0.16), y=0.3, x=x_off)
        Entity(parent=body, model='sphere', color=C_WHITE, scale=(0.2, 0.12, 0.25), y=0.06, x=x_off, z=0.05)
    body.combine(auto_destroy=True)

    head = Entity(parent=parent_ent, position=(0, 1.45, 0))
    Entity(parent=head, model='sphere', color=C_BLACK, scale=0.55)
    Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.48, 0.32, 0.35), position=(0, -0.08, 0.35))
    Entity(parent=head, model='cube', color=C_BLACK, scale=(0.08, 0.06, 0.08), position=(0, -0.02, 0.54))

    for x_off in (-0.14, 0.14):
        Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.16, 0.22, 0.1), position=(x_off, 0.1, 0.44))
        Entity(parent=head, model='sphere', color=C_CYAN, scale=(0.1, 0.15, 0.08), position=(x_off, 0.1, 0.48))
        Entity(parent=head, model='sphere', color=C_BLACK, scale=(0.05, 0.11, 0.07), position=(x_off, 0.1, 0.51))

    for x_off, rot in ((-0.22, 20), (0.22, -20)):
        Entity(parent=head, model='cube', color=C_BLACK, scale=(0.14, 0.32, 0.08), position=(x_off, 0.48, 0), rotation_z=rot)
        Entity(parent=head, model='cube', color=C_WHITE, scale=(0.08, 0.24, 0.06), position=(x_off, 0.48, 0.02), rotation_z=rot)
    head.combine(auto_destroy=True)

    arm_r = Entity(parent=parent_ent, position=(0.32, 0.85, 0.1))
    Entity(parent=arm_r, model='sphere', color=C_WHITE, scale=0.13)
    Entity(parent=arm_r, model='cube', color=C_BROWN, scale=(0.04, 0.25, 0.04), rotation_x=90)
    Entity(parent=arm_r, model='cube', color=C_GRAY, scale=(0.25, 0.04, 0.06), z=0.12)
    Entity(parent=arm_r, model='cube', color=C_LIGHT_GRAY, scale=(0.06, 0.02, 0.9), position=(0, 0, 0.58))
    arm_r.combine(auto_destroy=True)

    return [arm_r]

def build_death_visuals(parent_ent):
    body = Entity(parent=parent_ent)
    Entity(parent=body, model='sphere', color=C_LIGHT_GRAY, scale=(0.7, 1.4, 0.5), y=1.2)
    Entity(parent=body, model='sphere', color=C_DARK_GRAY, scale=(0.85, 1.3, 0.65), y=1.15, z=-0.05)
    body.combine(auto_destroy=True)

    legs = []
    for x_off in (-0.22, 0.22):
        leg_pivot = Entity(parent=parent_ent, position=(x_off, 0.6, 0))
        Entity(parent=leg_pivot, model='cube', color=C_LIGHT_GRAY, scale=(0.2, 0.6, 0.2), y=-0.3)
        Entity(parent=leg_pivot, model='cube', color=C_DARK_GRAY, scale=(0.18, 0.1, 0.3), y=-0.55, z=0.05)
        leg_pivot.combine(auto_destroy=True)
        legs.append(leg_pivot)
    parent_ent.legs = legs 

    hood = Entity(parent=parent_ent, y=2.05)
    Entity(parent=hood, model='quad', color=C_DARK_GRAY, double_sided=True, scale=(1.0, 0.9), position=(0, 0.5, 0.05), rotation_x=90)
    Entity(parent=hood, model='quad', color=C_DARK_GRAY, double_sided=True, scale=(1.0, 1.0), position=(0, 0, -0.42))
    Entity(parent=hood, model='quad', color=C_DARK_GRAY, double_sided=True, scale=(0.9, 1.0), position=(-0.5, 0, 0.05), rotation_y=90)
    Entity(parent=hood, model='quad', color=C_DARK_GRAY, double_sided=True, scale=(0.5, 1.0), position=(0.5, 0, 0.05), rotation_y=-90)
    
    head = Entity(parent=hood, model='sphere', color=C_LIGHT_GRAY, scale=0.55, position=(0, 0.05, 0.05))
    Entity(parent=head, model='cube', color=C_LIGHT_GRAY, scale=(0.38, 0.28, 0.65), position=(0, -0.08, 0.4))
    Entity(parent=head, model='cube', color=C_BLACK, scale=(0.14, 0.12, 0.12), position=(0, 0.02, 0.72))

    for x_off in (-0.16, 0.16):
        Entity(parent=head, model='sphere', color=C_RED, scale=(0.14, 0.18, 0.12), position=(x_off, 0.12, 0.42))
        Entity(parent=head, model='sphere', color=C_DARK_RED, scale=(0.05, 0.14, 0.08), position=(x_off, 0.12, 0.46))

    hood.combine(auto_destroy=True)

    arm_r = Entity(parent=parent_ent, position=(0.5, 1.2, 0.1))
    arm_l = Entity(parent=parent_ent, position=(-0.5, 1.2, 0.1))
    
    for arm in (arm_r, arm_l):
        Entity(parent=arm, model='sphere', color=C_LIGHT_GRAY, scale=0.18)
        Entity(parent=arm, model='cube', color=C_DARK_GRAY, scale=(0.06, 0.4, 0.06), rotation_x=90)
        b1 = Entity(parent=arm, model='cube', color=C_LIGHT_GRAY, scale=(0.04, 0.08, 0.4), position=(0, 0.1, 0.35), rotation_x=25)
        Entity(parent=b1, model='cube', color=C_LIGHT_GRAY, scale=(1, 0.9, 0.8), position=(0, 0.15, 0.25), rotation_x=35)
        arm.combine(auto_destroy=True)

    return [arm_r, arm_l]

def build_perrito_visuals(parent_ent):
    body = Entity(parent=parent_ent, position=(0, 0.45, 0))
    Entity(parent=body, model='sphere', color=C_TEAL_SWEATER, scale=(0.38, 0.35, 0.65))
    Entity(parent=body, model='sphere', color=C_WHITE, scale=(0.39, 0.36, 0.13), position=(0, 0, 0.26))
    body.combine(auto_destroy=True)

    legs = []
    leg_positions = [(-0.16, 0.25, 0.22), (0.16, 0.25, 0.22), (-0.16, 0.25, -0.22), (0.16, 0.25, -0.22)]
    for pos in leg_positions:
        pivot = Entity(parent=parent_ent, position=pos)
        Entity(parent=pivot, model='cube', color=C_TAN, scale=(0.11, 0.32, 0.11), y=-0.14)
        Entity(parent=pivot, model='sphere', color=C_TAN, scale=(0.14, 0.08, 0.18), position=(0, -0.28, 0.04))
        pivot.combine(auto_destroy=True)
        legs.append(pivot)
    parent_ent.legs = legs

    head = Entity(parent=parent_ent, position=(0, 0.72, 0.38))
    Entity(parent=head, model='sphere', color=C_TAN, scale=0.45)
    Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.35, 0.25, 0.35), position=(0, -0.06, 0.35))
    Entity(parent=head, model='sphere', color=C_BLACK, scale=(0.1, 0.08, 0.1), position=(0, -0.02, 0.52))

    for x_off in (-0.13, 0.13):
        Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.15, 0.18, 0.1), position=(x_off, 0.08, 0.42))
        Entity(parent=head, model='sphere', color=C_DARK_BROWN, scale=(0.1, 0.14, 0.08), position=(x_off, 0.08, 0.46))

    for x_off, rot in ((-0.48, 25), (0.48, -25)):
        Entity(parent=head, model='cube', color=C_DARK_BROWN, scale=(0.22, 0.5, 0.2), position=(x_off, 0.1, -0.05), rotation_z=rot, rotation_x=15)
    head.combine(auto_destroy=True)

    stick_pivot = Entity(parent=parent_ent, position=(0, 0.64, 0.83))
    Entity(parent=stick_pivot, model='cube', color=C_BROWN, scale=(0.05, 0.05, 0.9), position=(0.15, 0, 0.3), rotation_y=35)
    Entity(parent=stick_pivot, model='cube', color=C_DARK_BROWN, scale=(0.07, 0.07, 0.15), position=(0.3, 0, 0.68), rotation_y=35)
    stick_pivot.combine(auto_destroy=True)

    return [stick_pivot]

def build_jack_visuals(parent_ent):
    root = Entity(parent=parent_ent, scale=1.85)

    body = Entity(parent=root)
    Entity(parent=body, model='sphere', color=C_PURPLE, scale=(1.25, 1.1, 0.9), position=(0, 1.05, 0))
    Entity(parent=body, model='sphere', color=C_WHITE, scale=(1.05, 0.95, 0.85), position=(0, 0.95, 0.12))
    Entity(parent=body, model='cube', color=C_BLACK, scale=(0.16, 0.22, 0.05), position=(0, 1.38, 0.48))
    body.combine(auto_destroy=True)

    legs = []
    for x_off in (-0.32, 0.32):
        leg_pivot = Entity(parent=root, position=(x_off, 0.65, 0))
        Entity(parent=leg_pivot, model='cube', color=C_DARK_GRAY, scale=(0.38, 0.38, 0.38), y=-0.15)
        Entity(parent=leg_pivot, model='sphere', color=C_DARK_GRAY, scale=0.39, y=-0.34)
        Entity(parent=leg_pivot, model='cube', color=C_DARK_GRAY, scale=(0.34, 0.38, 0.34), y=-0.52)
        Entity(parent=leg_pivot, model='cube', color=C_BLACK, scale=(0.38, 0.2, 0.52), y=-0.7, z=0.1)
        leg_pivot.combine(auto_destroy=True)
        legs.append(leg_pivot)
    parent_ent.legs = legs

    head = Entity(parent=root, position=(0, 1.82, 0.05))
    Entity(parent=head, model='sphere', color=C_PEACH_SKIN, scale=0.82)
    Entity(parent=head, model='sphere', color=C_PEACH_SKIN, scale=(0.95, 0.5, 0.85), position=(0, -0.3, 0.08))
    Entity(parent=head, model='cube', color=C_PINK_HAIR, scale=(0.85, 0.28, 0.85), position=(0, 0.36, -0.05))
    Entity(parent=head, model='sphere', color=C_PINK_HAIR, scale=(0.42, 0.32, 0.42), position=(0, 0.48, 0.12))

    for x_off in (-0.16, 0.16):
        Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.14, 0.18, 0.1), position=(x_off, 0.08, 0.42))
        Entity(parent=head, model='sphere', color=C_AZURE, scale=(0.08, 0.12, 0.08), position=(x_off, 0.08, 0.46))
    head.combine(auto_destroy=True)

    arm_l = Entity(parent=root, position=(-0.7, 1.35, 0))
    Entity(parent=arm_l, model='cube', color=C_PURPLE, scale=(0.32, 0.6, 0.32), position=(0, -0.25, 0))
    Entity(parent=arm_l, model='sphere', color=C_PEACH_SKIN, scale=0.3, position=(0, -0.6, 0))
    arm_l.combine(auto_destroy=True)

    arm_r = Entity(parent=root, position=(0.7, 1.35, 0))
    Entity(parent=arm_r, model='cube', color=C_PURPLE, scale=(0.32, 0.6, 0.32), position=(0, -0.25, 0))
    Entity(parent=arm_r, model='sphere', color=C_PEACH_SKIN, scale=0.3, position=(0, -0.6, 0))
    
    wand_staff = Entity(parent=arm_r, position=(0, -0.5, 0.2), rotation_x=70)
    Entity(parent=wand_staff, model='cube', color=C_GOLD, scale=(0.07, 0.07, 1.8), position=(0, 0, 0.5))
    Entity(parent=wand_staff, model='sphere', color=C_YELLOW, scale=(0.22, 0.22, 0.28), position=(0, 0, 1.45))
    Entity(parent=wand_staff, model='cone', color=C_GOLD, scale=(0.3, 0.5, 0.3), position=(0, 0, 1.58), rotation_x=-90)
    arm_r.combine(auto_destroy=True)

    return [arm_r, arm_l]

def build_goldi_visuals(parent_ent):
    root = Entity(parent=parent_ent, scale=1.35)

    body = Entity(parent=root)
    Entity(parent=body, model='sphere', color=C_TEAL_SWEATER, scale=(0.55, 0.75, 0.45), y=0.85)

    for i in range(8):
        Entity(parent=body, model='sphere', color=C_LIGHT_GRAY, scale=0.15, position=(-0.4 + i*0.11, 0.3 - i*0.08, -0.45 + i*0.03))
        Entity(parent=body, model='sphere', color=C_LIGHT_GRAY, scale=0.15, position=(-0.4 + i*0.11, 0.3 - i*0.08, 0.45 - i*0.03))
    body.combine(auto_destroy=True)

    legs = []
    for x_off in (-0.18, 0.18):
        leg_pivot = Entity(parent=root, position=(x_off, 0.55, 0))
        Entity(parent=leg_pivot, model='cube', color=C_PEACH_SKIN, scale=(0.14, 0.3, 0.14), y=-0.15)
        Entity(parent=leg_pivot, model='sphere', color=C_PEACH_SKIN, scale=0.18, y=-0.3)
        Entity(parent=leg_pivot, model='cube', color=C_PEACH_SKIN, scale=(0.12, 0.25, 0.12), y=-0.45)
        Entity(parent=leg_pivot, model='cube', color=C_BROWN, scale=(0.18, 0.15, 0.28), y=-0.58, z=0.05)
        leg_pivot.combine(auto_destroy=True)
        legs.append(leg_pivot)
    parent_ent.legs = legs

    head = Entity(parent=root, position=(0, 1.4, 0))
    Entity(parent=head, model='sphere', color=C_PEACH_SKIN, scale=0.55)
    Entity(parent=head, model='sphere', color=C_YELLOW, scale=(0.65, 0.65, 0.65), position=(-0.45, 0.2, 0))
    Entity(parent=head, model='sphere', color=C_YELLOW, scale=(0.65, 0.65, 0.65), position=(0.45, 0.2, 0))
    Entity(parent=head, model='sphere', color=C_YELLOW, scale=(0.8, 0.3, 0.75), position=(0, 0.4, -0.05))

    for x_off in (-0.16, 0.16):
        Entity(parent=head, model='sphere', color=C_WHITE, scale=(0.16, 0.2, 0.1), position=(x_off, 0.05, 0.45))
        Entity(parent=head, model='sphere', color=C_AZURE, scale=(0.08, 0.12, 0.08), position=(x_off, 0.05, 0.48))
    head.combine(auto_destroy=True)

    arm_l = Entity(parent=root, position=(-0.4, 1.1, 0))
    Entity(parent=arm_l, model='cube', color=C_TEAL_SWEATER, scale=(0.12, 0.4, 0.12), position=(0, -0.2, 0))
    Entity(parent=arm_l, model='sphere', color=C_PEACH_SKIN, scale=0.15, position=(0, -0.45, 0))
    arm_l.combine(auto_destroy=True)

    arm_r = Entity(parent=root, position=(0.4, 1.1, 0))
    Entity(parent=arm_r, model='cube', color=C_TEAL_SWEATER, scale=(0.12, 0.4, 0.12), position=(0, -0.2, 0))
    Entity(parent=arm_r, model='sphere', color=C_PEACH_SKIN, scale=0.15, position=(0, -0.45, 0))
    staff = Entity(parent=arm_r, position=(0, -0.45, 0.2), rotation_x=75)
    Entity(parent=staff, model='cube', color=C_DARK_BROWN, scale=(0.06, 0.06, 1.6), position=(0, 0, 0.5))
    u_base = Entity(parent=staff, position=(0, 0, 1.3))
    Entity(parent=u_base, model='cube', color=C_DARK_BROWN, scale=(0.35, 0.06, 0.06), position=(0,0,0))
    Entity(parent=u_base, model='cube', color=C_DARK_BROWN, scale=(0.06, 0.06, 0.35), position=(-0.145, 0, 0.145))
    Entity(parent=u_base, model='cube', color=C_DARK_BROWN, scale=(0.06, 0.06, 0.35), position=(0.145, 0, 0.145))
    arm_r.combine(auto_destroy=True)

    return [arm_r, arm_l]


# ==========================================
# 2. PLAYER CLASSES
# ==========================================
class BaseCharacter(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hp = 100
        self.max_hp = 100
        self.base_speed = 6
        self.attack_damage = 5
        self.is_blocking = False
        self.is_attacking = False
        self.dash_cooldown = 0
        
        self.vertical_velocity = 0
        self.gravity = 28
        self.jump_force = 11
        self.is_grounded = True
        
        self.weapon_arms = []
        self.default_arm_rots = []

        self.camera_pivot = Entity(position=self.position + Vec3(0, 1.1, 0))
        camera.parent = self.camera_pivot
        camera.position = (0, 0.2, -6.5)
        camera.look_at(self.camera_pivot)
        camera.clip_plane_far = RENDER_DISTANCE

    def setup_arms(self):
        self.default_arm_rots = [arm.rotation for arm in self.weapon_arms]

    def apply_block_pose(self):
        for i, arm in enumerate(self.weapon_arms):
            arm.rotation = self.default_arm_rots[i] + Vec3(-45, 20, 35)

    def take_damage(self, amount):
        if self.is_blocking:
            return 
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0

    def on_destroy(self):
        if hasattr(self, 'camera_pivot') and self.camera_pivot:
            destroy(self.camera_pivot)

    def update(self):
        if self.hp <= 0: return
        if self.dash_cooldown > 0: self.dash_cooldown -= time.dt

        self.camera_pivot.position = self.position + Vec3(0, getattr(self, 'cam_offset_y', 1.1), 0)
        self.camera_pivot.rotation_y += mouse.velocity[0] * 120
        self.camera_pivot.rotation_x -= mouse.velocity[1] * 120
        self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -30, 35)

        if not self.is_grounded:
            self.vertical_velocity -= self.gravity * time.dt
            self.y += self.vertical_velocity * time.dt
            if self.y <= 0:
                self.y = 0
                self.vertical_velocity = 0
                self.is_grounded = True

        self.is_blocking = held_keys['right mouse']
        if self.is_blocking:
            self.rotation_z = -6
            self.apply_block_pose()
            return 

        self.rotation_z = 0
        if not self.is_attacking:
            for i, arm in enumerate(self.weapon_arms):
                arm.rotation = self.default_arm_rots[i]

        current_speed = self.base_speed * 1.85 if held_keys['control'] else self.base_speed
        cam_forward = Vec3(self.camera_pivot.forward.x, 0, self.camera_pivot.forward.z).normalized()
        cam_right = Vec3(self.camera_pivot.right.x, 0, self.camera_pivot.right.z).normalized()
        move_dir = (cam_forward * (held_keys['w'] - held_keys['s']) + cam_right * (held_keys['d'] - held_keys['a']))

        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalized()
            self.rotation_y = math.degrees(math.atan2(move_dir.x, move_dir.z))
            self.position += move_dir * current_speed * time.dt

    def perform_attack(self):
        for bot in list(active_bots):
            if bot.enabled and (bot.position - self.position).length() <= 3.2:
                bot.take_damage(self.attack_damage)

    def input(self, key):
        if key == 'space' and self.is_grounded and not self.is_blocking:
            self.vertical_velocity = self.jump_force
            self.is_grounded = False

        if key == 'shift' and not self.is_blocking and self.dash_cooldown <= 0:
            self.animate_position(self.position + self.forward * 5.5, duration=0.15, curve=curve.out_expo)
            self.dash_cooldown = 1.2

        if key == 'left mouse down' and not self.is_blocking and not self.is_attacking:
            self.is_attacking = True
            for i, arm in enumerate(self.weapon_arms):
                arm.animate_rotation(self.default_arm_rots[i] + Vec3(90, -30, -40), duration=0.08)
            
            self.perform_attack()
                
            def reset_attack():
                if self and self.hp > 0:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.animate_rotation(self.default_arm_rots[i], duration=0.18)
                    self.is_attacking = False
            invoke(reset_attack, delay=0.12)


class Puss(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cam_offset_y = 1.1
        self.weapon_arms = build_puss_visuals(self)
        self.setup_arms()

class Kitty(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cam_offset_y = 1.1
        self.weapon_arms = build_kitty_visuals(self)
        self.setup_arms()

class Death(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_speed = 12.0
        self.attack_damage = 15
        self.cam_offset_y = 1.8
        self.weapon_arms = build_death_visuals(self)
        self.setup_arms()

    def take_damage(self, amount):
        if random.random() < 0.5:
            self.apply_block_pose()
            def reset_auto_block():
                if self and self.hp > 0 and not self.is_blocking:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.rotation = self.default_arm_rots[i]
            invoke(reset_auto_block, delay=0.25)
            return 
        super().take_damage(amount)

    def apply_block_pose(self):
        self.weapon_arms[0].rotation = self.default_arm_rots[0] + Vec3(-35, -45, 40)
        self.weapon_arms[1].rotation = self.default_arm_rots[1] + Vec3(-35, 45, -40)

    def update(self):
        super().update()
        if self.hp <= 0: return

        cam_forward = Vec3(self.camera_pivot.forward.x, 0, self.camera_pivot.forward.z).normalized()
        cam_right = Vec3(self.camera_pivot.right.x, 0, self.camera_pivot.right.z).normalized()
        move_dir = (cam_forward * (held_keys['w'] - held_keys['s']) + cam_right * (held_keys['d'] - held_keys['a']))
        is_moving = move_dir.length_squared() > 0
        is_sprinting = is_moving and held_keys['control']

        if is_moving and self.is_grounded and hasattr(self, 'legs'):
            freq = 18 if is_sprinting else 10
            amp = 38 if is_sprinting else 22
            self.legs[0].rotation_x = math.sin(time.time() * freq) * amp
            self.legs[1].rotation_x = -math.sin(time.time() * freq) * amp

        if is_sprinting and not self.is_attacking and not self.is_blocking:
            self.weapon_arms[0].rotation = self.default_arm_rots[0] + Vec3(-50, 25, -20)
            self.weapon_arms[1].rotation = self.default_arm_rots[1] + Vec3(-50, -25, 20)

    def input(self, key):
        if key == 'left mouse down' and not self.is_blocking and not self.is_attacking:
            self.is_attacking = True
            self.weapon_arms[0].animate_rotation(self.default_arm_rots[0] + Vec3(85, -50, -45), duration=0.08)
            self.weapon_arms[1].animate_rotation(self.default_arm_rots[1] + Vec3(85, 50, 45), duration=0.08)
            self.perform_attack()

            def reset_attack():
                if self and self.hp > 0:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.animate_rotation(self.default_arm_rots[i], duration=0.18)
                    self.is_attacking = False
            invoke(reset_attack, delay=0.15)
        else:
            super().input(key)

class Perrito(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_speed = 9.0
        self.jump_force = 15.0
        self.attack_damage = 7
        self.cam_offset_y = 0.7
        self.weapon_arms = build_perrito_visuals(self)
        self.setup_arms()

    def update(self):
        super().update()
        if self.hp <= 0: return

        cam_forward = Vec3(self.camera_pivot.forward.x, 0, self.camera_pivot.forward.z).normalized()
        cam_right = Vec3(self.camera_pivot.right.x, 0, self.camera_pivot.right.z).normalized()
        move_dir = (cam_forward * (held_keys['w'] - held_keys['s']) + cam_right * (held_keys['d'] - held_keys['a']))
        is_moving = move_dir.length_squared() > 0

        if is_moving and self.is_grounded and hasattr(self, 'legs'):
            freq = 18
            amp = 25
            t = time.time() * freq
            self.legs[0].rotation_x = math.sin(t) * amp
            self.legs[1].rotation_x = -math.sin(t) * amp
            self.legs[2].rotation_x = -math.sin(t) * amp
            self.legs[3].rotation_x = math.sin(t) * amp

    def input(self, key):
        if key == 'left mouse down' and not self.is_blocking and not self.is_attacking:
            self.is_attacking = True
            for i, arm in enumerate(self.weapon_arms):
                arm.animate_rotation(self.default_arm_rots[i] + Vec3(0, -90, 20), duration=0.04)

            self.perform_attack()

            def reset_attack():
                if self and self.hp > 0:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.animate_rotation(self.default_arm_rots[i], duration=0.06)
                    self.is_attacking = False
            invoke(reset_attack, delay=0.06)
        else:
            super().input(key)

class Jack(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hp = 140
        self.max_hp = 140
        self.base_speed = 7.5
        self.attack_damage = 12
        self.cam_offset_y = 3.2
        self.weapon_arms = build_jack_visuals(self)
        self.setup_arms()

    def update(self):
        super().update()
        if self.hp <= 0: return

        cam_forward = Vec3(self.camera_pivot.forward.x, 0, self.camera_pivot.forward.z).normalized()
        cam_right = Vec3(self.camera_pivot.right.x, 0, self.camera_pivot.right.z).normalized()
        move_dir = (cam_forward * (held_keys['w'] - held_keys['s']) + cam_right * (held_keys['d'] - held_keys['a']))
        is_moving = move_dir.length_squared() > 0

        if is_moving and self.is_grounded and hasattr(self, 'legs'):
            freq = 12
            amp = 26
            t = time.time() * freq
            self.legs[0].rotation_x = math.sin(t) * amp
            self.legs[1].rotation_x = -math.sin(t) * amp

    def input(self, key):
        if key == 'left mouse down' and not self.is_blocking and not self.is_attacking:
            self.is_attacking = True
            self.weapon_arms[0].animate_rotation(self.default_arm_rots[0] + Vec3(80, -20, -30), duration=0.08)
            self.weapon_arms[1].animate_rotation(self.default_arm_rots[1] + Vec3(30, 20, 0), duration=0.08)
            self.perform_attack()

            def reset_attack():
                if self and self.hp > 0:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.animate_rotation(self.default_arm_rots[i], duration=0.18)
                    self.is_attacking = False
            invoke(reset_attack, delay=0.15)
        else:
            super().input(key)

class Goldi(BaseCharacter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hp = 110
        self.max_hp = 110
        self.base_speed = 8.5
        self.attack_damage = 9
        self.cam_offset_y = 1.9
        self.weapon_arms = build_goldi_visuals(self)
        self.setup_arms()

    def update(self):
        super().update()
        if self.hp <= 0: return

        cam_forward = Vec3(self.camera_pivot.forward.x, 0, self.camera_pivot.forward.z).normalized()
        cam_right = Vec3(self.camera_pivot.right.x, 0, self.camera_pivot.right.z).normalized()
        move_dir = (cam_forward * (held_keys['w'] - held_keys['s']) + cam_right * (held_keys['d'] - held_keys['a']))
        is_moving = move_dir.length_squared() > 0

        if is_moving and self.is_grounded and hasattr(self, 'legs'):
            freq = 15
            amp = 25
            t = time.time() * freq
            self.legs[0].rotation_x = math.sin(t) * amp
            self.legs[1].rotation_x = -math.sin(t) * amp

    def input(self, key):
        if key == 'left mouse down' and not self.is_blocking and not self.is_attacking:
            self.is_attacking = True
            self.weapon_arms[0].animate_rotation(self.default_arm_rots[0] + Vec3(20, -80, -45), duration=0.08)
            self.perform_attack()

            def reset_attack():
                if self and self.hp > 0:
                    for i, arm in enumerate(self.weapon_arms):
                        arm.animate_rotation(self.default_arm_rots[i], duration=0.18)
                    self.is_attacking = False
            invoke(reset_attack, delay=0.15)
        else:
            super().input(key)


# ==========================================
# 3. ENEMY AI
# ==========================================
class PussBot(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hp = 100
        self.max_hp = 100
        self.attack_cooldown = 0
        
        self.weapon_arms = build_puss_visuals(self)
        self.arm_r = self.weapon_arms[0]
        
        self.hp_container = Entity(parent=self, position=(0, 2.2, 0))
        self.hp_bar_bg = Entity(parent=self.hp_container, model='quad', color=C_DARK_GRAY, scale=(1.0, 0.14))
        self.hp_bar = Entity(parent=self.hp_container, model='quad', color=C_RED, scale=(1.0, 0.12), position=(-0.5, 0, -0.01), origin=(-0.5, 0))

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            if self in active_bots:
                active_bots.remove(self)
            destroy(self)
        else:
            self.hp_bar.scale_x = max(0.0, (self.hp / self.max_hp))

    def update(self):
        global player
        if not player or player.hp <= 0 or not self.enabled: return

        if camera:
            self.hp_container.world_rotation = camera.world_rotation

        dist = (player.position - self.position).length()
        self.look_at(player.position)
        self.rotation_x = 0
        self.rotation_z = 0

        if dist > 2.0:
            self.position += self.forward * 4.5 * time.dt
        else:
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 1.2
                self.arm_r.animate_rotation(Vec3(60, -20, 0), duration=0.1)
                player.take_damage(5)
                
                def reset_bot_arm():
                    if self and self.hp > 0:
                        self.arm_r.animate_rotation(Vec3(0, 0, 0), duration=0.15)
                invoke(reset_bot_arm, delay=0.15)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt


# ==========================================
# 4. GAME SYSTEM & UI
# ==========================================
app = Ursina()

window.fps_counter.enabled = False
window.entity_counter.enabled = False

ground = Entity(model='plane', scale=200, texture='white_cube', texture_scale=(100, 100), color=C_LIGHT_GRAY, collider='box')

menu_ui = Entity(parent=camera.ui)

left_panel_border = Entity(parent=menu_ui, model='quad', color=C_RED, scale=(0.415, 0.715), position=(-0.55, 0), z=0.01)
left_panel = Entity(parent=menu_ui, model='quad', color=C_BLACK, scale=(0.4, 0.7), position=(-0.55, 0), z=0)
Text("players", parent=left_panel, y=0.4, origin=(0, 0), scale=2, color=C_RED)
Text("1. You (Selecting...)", parent=left_panel, y=0.2, x=-0.4, scale=1.3, color=C_WHITE)
Text("2. Waiting for player...", parent=left_panel, y=0.05, x=-0.4, scale=1.3, color=C_GRAY)
Text("3. Waiting for player...", parent=left_panel, y=-0.1, x=-0.4, scale=1.3, color=C_GRAY)

mid_panel_border = Entity(parent=menu_ui, model='quad', color=C_BLACK, scale=(0.615, 0.715), position=(0, 0), z=0.01)
mid_panel = Entity(parent=menu_ui, model='quad', color=C_WHITE, scale=(0.6, 0.7), position=(0, 0), z=0)
Text("character selection", parent=mid_panel, y=0.4, origin=(0, 0), scale=2, color=C_BLACK)

right_panel_border = Entity(parent=menu_ui, model='quad', color=C_RED, scale=(0.415, 0.715), position=(0.55, 0), z=0.01)
right_panel = Entity(parent=menu_ui, model='quad', color=C_BLACK, scale=(0.4, 0.7), position=(0.55, 0), z=0)
Text("character preview", parent=right_panel, y=0.4, origin=(0, 0), scale=2, color=C_RED)

def make_outlined_button(text, position, scale, bg_color=C_WHITE, text_color=C_BLACK, border_color=C_GRAY, on_click=lambda: None, parent=mid_panel, ignore_paused=False):
    Entity(parent=parent, model='quad', color=border_color, position=position, scale=(scale[0] + 0.012, scale[1] + 0.012), z=0.005, ignore_paused=ignore_paused)
    return Button(text=text, color=bg_color, text_color=text_color, parent=parent, position=position, scale=scale, z=-0.01, on_click=on_click, ignore_paused=ignore_paused)

def set_character(char_cls):
    global selected_class, current_preview
    selected_class = char_cls
    if current_preview:
        destroy(current_preview)
    
    current_preview = Entity(parent=camera.ui, position=(0.55, -0.05, -2), scale=0.11)
    if char_cls == Puss:
        build_puss_visuals(current_preview)
    elif char_cls == Kitty:
        build_kitty_visuals(current_preview)
    elif char_cls == Death:
        build_death_visuals(current_preview)
    elif char_cls == Perrito:
        build_perrito_visuals(current_preview)
    elif char_cls == Jack:
        build_jack_visuals(current_preview)
    elif char_cls == Goldi:
        build_goldi_visuals(current_preview)

make_outlined_button('puss in\nboots', position=(-0.25, 0.2), scale=(0.18, 0.13), border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Puss))
make_outlined_button('kitty\nsoftpaws', position=(0.0, 0.2), scale=(0.18, 0.13), border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Kitty))
make_outlined_button('death', position=(0.25, 0.2), scale=(0.18, 0.13), border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Death))

make_outlined_button('perrito', position=(-0.25, 0.02), scale=(0.18, 0.13), text_color=C_BLACK, border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Perrito))
make_outlined_button('big jack', position=(0.0, 0.02), scale=(0.18, 0.13), text_color=C_BLACK, border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Jack))
make_outlined_button('goldi', position=(0.25, 0.02), scale=(0.18, 0.13), text_color=C_BLACK, border_color=C_LIGHT_GRAY, on_click=lambda: set_character(Goldi))

def start_game():
    global player, game_started, current_preview
    if not selected_class:
        return
    game_started = True
    
    menu_ui.enabled = False
    if current_preview:
        destroy(current_preview)
        current_preview = None
    
    hud_ui.enabled = True
    mouse.locked = True
    
    player = selected_class(position=(0, 0, 0))

choose_btn_border = Entity(parent=menu_ui, model='quad', color=C_WHITE, position=(0.55, -0.28), scale=(0.335, 0.095), z=-0.01)
choose_btn = Button(
    text='CHOOSE CHARACTER', 
    color=C_RED, 
    text_color=C_WHITE, 
    parent=menu_ui, 
    position=(0.55, -0.28), 
    scale=(0.32, 0.08), 
    z=-0.02,
    on_click=start_game
)

set_character(Puss)

# HUD UI
hud_ui = Entity(parent=camera.ui, enabled=False)
hp_bar_border = Entity(parent=hud_ui, model='quad', color=C_BLACK, origin=(-0.5, 0.5), position=(-0.855, 0.455), scale=(0.51, 0.05), z=0.01)
hp_bar_bg = Entity(parent=hud_ui, model='quad', color=C_DARK_GRAY, origin=(-0.5, 0.5), position=(-0.85, 0.45), scale=(0.5, 0.04))
hp_bar = Entity(parent=hud_ui, model='quad', color=C_LIME, origin=(-0.5, 0.5), position=(-0.85, 0.45), scale=(0.5, 0.04), z=-0.01)
hp_text = Text(parent=hud_ui, text="HP: 100%", position=(-0.85, 0.48), scale=1.2, color=C_WHITE)


# ==========================================
# 5. PAUSE MENU
# ==========================================
pause_ui = Entity(parent=camera.ui, enabled=False, ignore_paused=True)

pause_panel_border = Entity(parent=pause_ui, model='quad', color=C_RED, scale=(0.42, 0.52), position=(0, 0), z=0.01, ignore_paused=True)
pause_panel = Entity(parent=pause_ui, model='quad', color=C_BLACK, scale=(0.4, 0.5), position=(0, 0), z=0, ignore_paused=True)
Text("PAUSED", parent=pause_panel, y=0.38, origin=(0, 0), scale=2.2, color=C_WHITE, ignore_paused=True)

def resume_game():
    pause_ui.enabled = False
    application.paused = False
    mouse.locked = True

def change_character_action():
    global player, game_started, active_bots
    resume_game()
    game_started = False
    hud_ui.enabled = False
    mouse.locked = False

    if player:
        destroy(player)
        player = None

    for bot in list(active_bots):
        destroy(bot)
    active_bots.clear()

    menu_ui.enabled = True
    set_character(selected_class if selected_class else Puss)

def quit_game():
    application.quit()

make_outlined_button('RESUME', position=(0, 0.1), scale=(0.3, 0.08), bg_color=C_WHITE, text_color=C_BLACK, parent=pause_ui, ignore_paused=True, on_click=resume_game)
make_outlined_button('CHANGE CHARACTER', position=(0, -0.04), scale=(0.3, 0.08), bg_color=C_WHITE, text_color=C_BLACK, parent=pause_ui, ignore_paused=True, on_click=change_character_action)
make_outlined_button('QUIT', position=(0, -0.18), scale=(0.3, 0.08), bg_color=C_RED, text_color=C_WHITE, border_color=C_DARK_RED, parent=pause_ui, ignore_paused=True, on_click=quit_game)


# ==========================================
# 6. UPDATE LOOP
# ==========================================
def update():
    global player, game_started, current_preview

    if not game_started:
        if current_preview:
            current_preview.rotation_y += 45 * time.dt
        return

    if player and player.hp > 0:
        if len(active_bots) < 3:
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(12, 20)
            spawn_pos = player.position + Vec3(math.cos(angle) * dist, 0, math.sin(angle) * dist)
            bot = PussBot(position=spawn_pos)
            active_bots.append(bot)

        for bot in active_bots:
            d = (bot.position - player.position).length()
            bot.enabled = (d <= RENDER_DISTANCE)

        hp_pct = max(0, player.hp / player.max_hp)
        hp_bar.scale_x = hp_pct * 0.5
        hp_text.text = f"HP: {int(player.hp)}%"
        
        if player.hp <= 0:
            hp_text.text = "YOU DIED"
            hp_text.color = C_RED

def input(key):
    if key == 'escape':
        if game_started:
            if pause_ui.enabled:
                resume_game()
            else:
                pause_ui.enabled = True
                application.paused = True
                mouse.locked = False

app.run()