# =============================================================================
#  PUSS IN BOOTS - 3D Adventure Game
#  Engine: Ursina (Python)
#  3-Panel Character Selection UI with Live 3D Rotating Preview
# =============================================================================

from ursina import *
import math
import random

# =============================================================================
# APP INITIALIZATION
# =============================================================================
app = Ursina(title="Puss in Boots - 3D Adventure", borderless=False)

# Hide debug & entity counters from top-right
window.fps_counter.enabled      = False
window.entity_counter.enabled   = False
window.collider_counter.enabled = False
window.exit_button.visible      = True

# Camera optimization: Set render distance / far clip plane for weak laptops
camera.clip_plane_far  = 90.0
camera.clip_plane_near = 0.1

# =============================================================================
# GLOBAL GAME STATE & STATS
# =============================================================================
game_state          = 'selection'   # 'selection' | 'playing' | 'game_over'
player              = None          # Active player entity (root pivot)
weapon_arm          = None          # Right arm entity / pivot
arm_left            = None          # Left arm entity / pivot
leg_left            = None          # Left leg pivot
leg_right           = None          # Right leg pivot
body_entity         = None          # Torso entity for sprint lean
weapon_entity       = None          # Main weapon mesh

# Combat & Stats
player_hp           = 100.0
player_max_hp       = 100.0
player_damage       = 5.0           # 5% for Puss/Kitty, 15% for Death
is_blocking         = False
is_attacking        = False
walk_time           = 0.0
dash_cooldown       = 0.0
DASH_COOLDOWN       = 1.0
DASH_FORCE          = 8.0
BASE_SPEED          = 4.0           # 4.0 for Puss/Kitty, 8.0 for Death (2x faster)
SPRINT_MULT         = 2.0
y_velocity          = 0.0
is_grounded         = True
GRAVITY             = 22.0
JUMP_FORCE          = 7.5
camera_pivot        = None
selection_ui        = []
selected_char       = 'puss'
kills_count         = 0

# Bot Spawning
MAX_BOTS            = 4
active_bots         = []
bot_respawn_timer   = 0.0

# Selected character key in menu
selected_preview_key= 'puss'

# =============================================================================
# GROUND PLANE & LIGHTING (Optimized for weak PCs)
# =============================================================================
ground = Entity(
    model         = 'plane',
    scale         = (120, 1, 120),
    color         = color.rgb(60/255, 110/255, 50/255),
    texture       = 'white_cube',
    texture_scale = (30, 30),
    collider      = 'box'
)

sky = Sky(color=color.rgb(100/255, 160/255, 220/255))
AmbientLight(color=color.rgba(190/255, 190/255, 190/255, 255/255))
DirectionalLight(shadows=False, rotation=(45, -45, 0))

# =============================================================================
# PROCEDURAL CHARACTER BUILDERS
# =============================================================================

def build_puss(is_enemy=False):
    """Procedurally build Puss in Boots. If is_enemy=True, applies enemy styling."""
    root = Entity()

    body_col   = color.orange if not is_enemy else color.rgb(200/255, 90/255, 30/255)
    eye_col    = color.black if not is_enemy else color.rgb(255/255, 40/255, 40/255)
    hat_col    = color.black if not is_enemy else color.rgb(45/255, 30/255, 30/255)
    feather_col= color.red if not is_enemy else color.rgb(220/255, 180/255, 20/255)

    # --- Body ---
    body = Entity(parent=root, model='cube', color=body_col,
                  scale=(0.7, 0.85, 0.5), position=(0, 0.9, 0))
    Entity(parent=root, model='cube', color=color.white if not is_enemy else color.rgb(210/255, 210/255, 210/255),
           scale=(0.35, 0.45, 0.1), position=(0, 0.95, 0.26))
    Entity(parent=root, model='cube', color=color.black,
           scale=(0.72, 0.08, 0.52), position=(0, 0.72, 0))

    # --- Head ---
    head = Entity(parent=root, model='sphere', color=body_col,
                  scale=(0.6, 0.6, 0.6), position=(0, 1.65, 0))
    Entity(parent=root, model='sphere', color=eye_col,
           scale=(0.1, 0.1, 0.05), position=(-0.12, 1.68, 0.3))
    Entity(parent=root, model='sphere', color=eye_col,
           scale=(0.1, 0.1, 0.05), position=(0.12, 1.68, 0.3))
    Entity(parent=root, model='sphere', color=color.rgb(240/255, 180/255, 120/255),
           scale=(0.22, 0.14, 0.12), position=(0, 1.58, 0.32))
    Entity(parent=root, model='sphere', color=color.rgb(255/255, 100/255, 120/255),
           scale=(0.07, 0.05, 0.05), position=(0, 1.62, 0.36))

    # --- Ears ---
    Entity(parent=root, model='cube', color=body_col,
           scale=(0.12, 0.18, 0.05), position=(-0.2, 1.93, 0), rotation=(0, 0, -20))
    Entity(parent=root, model='cube', color=body_col,
           scale=(0.12, 0.18, 0.05), position=(0.2, 1.93, 0), rotation=(0, 0, 20))

    # --- Hat ---
    Entity(parent=root, model='cube', color=hat_col,
           scale=(0.8, 0.05, 0.8), position=(0, 1.98, 0))
    Entity(parent=root, model='cube', color=hat_col,
           scale=(0.45, 0.3, 0.45), position=(0, 2.12, 0))
    Entity(parent=root, model='cube', color=feather_col,
           scale=(0.04, 0.25, 0.04), position=(0.2, 2.32, 0), rotation=(0, 0, -30))

    # --- Left Leg ---
    leg_l = Entity(parent=root, position=(-0.22, 0.7, 0))
    Entity(parent=leg_l, model='cube', color=body_col,
           scale=(0.28, 0.45, 0.28), position=(0, -0.23, 0))
    Entity(parent=leg_l, model='cube', color=color.black,
           scale=(0.3, 0.35, 0.3), position=(0, -0.5, 0))

    # --- Right Leg ---
    leg_r = Entity(parent=root, position=(0.22, 0.7, 0))
    Entity(parent=leg_r, model='cube', color=body_col,
           scale=(0.28, 0.45, 0.28), position=(0, -0.23, 0))
    Entity(parent=leg_r, model='cube', color=color.black,
           scale=(0.3, 0.35, 0.3), position=(0, -0.5, 0))

    # --- Left Arm ---
    arm_l = Entity(parent=root, position=(-0.48, 1.0, 0))
    Entity(parent=arm_l, model='cube', color=body_col,
           scale=(0.22, 0.5, 0.22), position=(0, 0, 0))

    # --- Right Arm & Rapier ---
    arm_r = Entity(parent=root, position=(0.48, 1.0, 0))
    Entity(parent=arm_r, model='cube', color=body_col,
           scale=(0.22, 0.5, 0.22), position=(0, 0, 0))
    Entity(parent=arm_r, model='sphere', color=body_col,
           scale=(0.2, 0.2, 0.2), position=(0, -0.25, 0.1))

    # Rapier Mesh
    Entity(parent=arm_r, model='cube', color=color.rgb(90/255, 55/255, 20/255),
           scale=(0.06, 0.06, 0.25), position=(0, -0.25, 0.08))
    Entity(parent=arm_r, model='cube', color=color.rgb(245/255, 195/255, 35/255),
           scale=(0.22, 0.22, 0.06), position=(0, -0.25, 0.22))
    Entity(parent=arm_r, model='sphere', color=color.rgb(245/255, 195/255, 35/255),
           scale=(0.1, 0.1, 0.1), position=(0, -0.25, -0.06))
    weapon = Entity(parent=arm_r, model='cube', color=color.rgb(225/255, 235/255, 245/255),
                    scale=(0.04, 0.04, 1.5), position=(0, -0.25, 1.0))
    Entity(parent=arm_r, model='cube', color=color.white,
           scale=(0.025, 0.025, 0.3), position=(0, -0.25, 1.85))

    return {
        'root': root,
        'weapon_arm': arm_r,
        'left_arm': arm_l,
        'leg_l': leg_l,
        'leg_r': leg_r,
        'body': body,
        'weapon': weapon,
    }


def build_kitty():
    """Procedurally build Kitty Softpaws from primitives."""
    root = Entity()

    # --- Body ---
    body = Entity(parent=root, model='cube', color=color.black,
                  scale=(0.65, 0.8, 0.48), position=(0, 0.9, 0))
    Entity(parent=root, model='cube', color=color.white,
           scale=(0.28, 0.42, 0.08), position=(0, 0.96, 0.25))
    Entity(parent=root, model='cube', color=color.rgb(120/255, 80/255, 40/255),
           scale=(0.67, 0.07, 0.5), position=(0, 0.72, 0))

    # --- Head ---
    head = Entity(parent=root, model='sphere', color=color.black,
                  scale=(0.55, 0.55, 0.55), position=(0, 1.6, 0))
    Entity(parent=root, model='sphere', color=color.white,
           scale=(0.22, 0.14, 0.14), position=(0, 1.51, 0.22))
    Entity(parent=root, model='sphere', color=color.rgb(255/255, 120/255, 150/255),
           scale=(0.06, 0.05, 0.05), position=(0, 1.56, 0.28))
    Entity(parent=root, model='sphere', color=color.white,
           scale=(0.07, 0.12, 0.04), position=(0, 1.76, 0.24))
    Entity(parent=root, model='sphere', color=color.white,
           scale=(0.07, 0.06, 0.04), position=(-0.16, 1.54, 0.21))
    Entity(parent=root, model='sphere', color=color.white,
           scale=(0.07, 0.06, 0.04), position=(0.16, 1.54, 0.21))

    # --- Eyes ---
    Entity(parent=root, model='sphere', color=color.rgb(30/255, 210/255, 110/255),
           scale=(0.11, 0.11, 0.06), position=(-0.11, 1.65, 0.24))
    Entity(parent=root, model='sphere', color=color.black,
           scale=(0.04, 0.08, 0.04), position=(-0.11, 1.65, 0.27))
    Entity(parent=root, model='sphere', color=color.rgb(30/255, 210/255, 110/255),
           scale=(0.11, 0.11, 0.06), position=(0.11, 1.65, 0.24))
    Entity(parent=root, model='sphere', color=color.black,
           scale=(0.04, 0.08, 0.04), position=(0.11, 1.65, 0.27))

    # --- Ears ---
    Entity(parent=root, model='cube', color=color.black,
           scale=(0.11, 0.16, 0.04), position=(-0.18, 1.88, 0), rotation=(0, 0, -15))
    Entity(parent=root, model='cube', color=color.rgb(255/255, 160/255, 180/255),
           scale=(0.06, 0.1, 0.03), position=(-0.18, 1.88, 0.02), rotation=(0, 0, -15))
    Entity(parent=root, model='cube', color=color.black,
           scale=(0.11, 0.16, 0.04), position=(0.18, 1.88, 0), rotation=(0, 0, 15))
    Entity(parent=root, model='cube', color=color.rgb(255/255, 160/255, 180/255),
           scale=(0.06, 0.1, 0.03), position=(0.18, 1.88, 0.02), rotation=(0, 0, 15))

    # --- Tail ---
    Entity(parent=root, model='cube', color=color.dark_gray,
           scale=(0.1, 0.6, 0.1), position=(0, 0.8, -0.35), rotation=(40, 0, 0))

    # --- Legs ---
    leg_l = Entity(parent=root, position=(-0.2, 0.65, 0))
    Entity(parent=leg_l, model='cube', color=color.black,
           scale=(0.25, 0.42, 0.25), position=(0, -0.21, 0))
    Entity(parent=leg_l, model='sphere', color=color.white,
           scale=(0.22, 0.1, 0.22), position=(0, -0.43, 0))

    leg_r = Entity(parent=root, position=(0.2, 0.65, 0))
    Entity(parent=leg_r, model='cube', color=color.black,
           scale=(0.25, 0.42, 0.25), position=(0, -0.21, 0))
    Entity(parent=leg_r, model='sphere', color=color.white,
           scale=(0.22, 0.1, 0.22), position=(0, -0.43, 0))

    # --- Arms ---
    arm_l = Entity(parent=root, position=(-0.44, 1.0, 0))
    Entity(parent=arm_l, model='cube', color=color.black,
           scale=(0.2, 0.45, 0.2), position=(0, 0, 0))

    arm_r = Entity(parent=root, position=(0.44, 1.0, 0))
    Entity(parent=arm_r, model='cube', color=color.black,
           scale=(0.2, 0.45, 0.2), position=(0, 0, 0))
    Entity(parent=arm_r, model='sphere', color=color.white,
           scale=(0.18, 0.18, 0.18), position=(0, -0.22, 0.1))

    # --- Sword ---
    Entity(parent=arm_r, model='cube', color=color.rgb(80/255, 50/255, 20/255),
           scale=(0.05, 0.05, 0.22), position=(0, -0.22, 0.08))
    Entity(parent=arm_r, model='cube', color=color.rgb(180/255, 180/255, 190/255),
           scale=(0.2, 0.04, 0.04), position=(0, -0.22, 0.2))
    weapon = Entity(parent=arm_r, model='cube', color=color.rgb(215/255, 220/255, 230/255),
                    scale=(0.035, 0.035, 1.3), position=(0, -0.22, 0.88))
    Entity(parent=arm_r, model='cube', color=color.white,
           scale=(0.02, 0.02, 0.25), position=(0, -0.22, 1.6))

    return {
        'root': root,
        'weapon_arm': arm_r,
        'left_arm': arm_l,
        'leg_l': leg_l,
        'leg_r': leg_r,
        'body': body,
        'weapon': weapon,
    }


def build_death():
    """Procedurally build Death (The Wolf) - Large, tall, menacing boss anatomy with torso, chest, abdomen, thighs, and legs."""
    root = Entity()

    # =========================================================================
    # TORSO: ABDOMEN & CHEST
    # =========================================================================
    # --- Abdomen (Lower Torso) ---
    abdomen = Entity(parent=root, model='cube', color=color.rgb(180/255, 180/255, 188/255),
                     scale=(0.82, 0.46, 0.54), position=(0, 1.28, 0))
    # Belt & Buckle
    Entity(parent=root, model='cube', color=color.rgb(55/255, 42/255, 32/255),
           scale=(0.88, 0.16, 0.58), position=(0, 1.08, 0))
    Entity(parent=root, model='cube', color=color.rgb(210/255, 175/255, 60/255),
           scale=(0.22, 0.18, 0.10), position=(0, 1.08, 0.29))

    # --- Chest (Upper Torso - Muscular & Broad) ---
    chest = Entity(parent=root, model='cube', color=color.rgb(215/255, 215/255, 222/255),
                   scale=(1.08, 0.68, 0.66), position=(0, 1.74, 0.02))
    # Pectorals & Sternum Plate
    Entity(parent=root, model='cube', color=color.rgb(235/255, 235/255, 242/255),
           scale=(0.78, 0.50, 0.14), position=(0, 1.74, 0.34))
    # Side Rib Definition
    Entity(parent=root, model='cube', color=color.rgb(175/255, 175/255, 182/255),
           scale=(0.12, 0.52, 0.60), position=(-0.52, 1.72, 0.02))
    Entity(parent=root, model='cube', color=color.rgb(175/255, 175/255, 182/255),
           scale=(0.12, 0.52, 0.60), position=(0.52, 1.72, 0.02))

    # --- Tattered Shroud / Cloak ---
    Entity(parent=root, model='cube', color=color.rgb(26/255, 26/255, 32/255),
           scale=(1.18, 1.60, 0.12), position=(0, 1.45, -0.36))
    Entity(parent=root, model='cube', color=color.rgb(26/255, 26/255, 32/255),
           scale=(0.12, 1.50, 0.72), position=(-0.60, 1.45, 0))
    Entity(parent=root, model='cube', color=color.rgb(26/255, 26/255, 32/255),
           scale=(0.12, 1.50, 0.72), position=(0.60, 1.45, 0))

    # =========================================================================
    # HEAD, SNOUT & HOOD
    # =========================================================================
    # Muscular Wolf Neck
    Entity(parent=root, model='cube', color=color.rgb(205/255, 205/255, 212/255),
           scale=(0.50, 0.38, 0.50), position=(0, 2.18, 0))

    # Head
    head = Entity(parent=root, model='sphere', color=color.rgb(228/255, 228/255, 235/255),
                  scale=(0.76, 0.82, 0.76), position=(0, 2.54, 0))
    # Snout / Muzzle
    Entity(parent=root, model='cube', color=color.rgb(200/255, 200/255, 208/255),
           scale=(0.36, 0.26, 0.52), position=(0, 2.44, 0.48))
    # Black Nose
    Entity(parent=root, model='sphere', color=color.black,
           scale=(0.13, 0.11, 0.11), position=(0, 2.49, 0.74))

    # Glowing Red Eyes
    Entity(parent=root, model='sphere', color=color.red,
           scale=(0.16, 0.16, 0.10), position=(-0.16, 2.62, 0.38))
    Entity(parent=root, model='sphere', color=color.red,
           scale=(0.16, 0.16, 0.10), position=(0.16, 2.62, 0.38))

    # Wolf Ears
    Entity(parent=root, model='cube', color=color.rgb(220/255, 220/255, 228/255),
           scale=(0.16, 0.34, 0.08), position=(-0.28, 2.94, 0), rotation=(0, 0, -12))
    Entity(parent=root, model='cube', color=color.rgb(220/255, 220/255, 228/255),
           scale=(0.16, 0.34, 0.08), position=(0.28, 2.94, 0), rotation=(0, 0, 12))

    # Plane Hood
    Entity(parent=root, model='plane', color=color.rgb(35/255, 35/255, 42/255),
           scale=(1.18, 1, 1.18), position=(0, 3.02, -0.05), rotation=(15, 0, 0), double_sided=True)
    Entity(parent=root, model='plane', color=color.rgb(40/255, 40/255, 48/255),
           scale=(1.08, 1, 0.58), position=(0, 2.99, 0.28), rotation=(-30, 0, 0), double_sided=True)
    Entity(parent=root, model='plane', color=color.rgb(32/255, 32/255, 38/255),
           scale=(1.08, 1, 0.94), position=(-0.54, 2.54, -0.05), rotation=(0, 0, -75), double_sided=True)
    Entity(parent=root, model='plane', color=color.rgb(32/255, 32/255, 38/255),
           scale=(1.08, 1, 0.94), position=(0.54, 2.54, -0.05), rotation=(0, 0, 75), double_sided=True)
    Entity(parent=root, model='plane', color=color.rgb(28/255, 28/255, 34/255),
           scale=(1.12, 1, 1.08), position=(0, 2.54, -0.54), rotation=(80, 0, 0), double_sided=True)

    # =========================================================================
    # LEGS: THIGHS, CALVES, PAWS & CLAWS
    # =========================================================================
    # --- Left Leg Pivot ---
    leg_l = Entity(parent=root, position=(-0.28, 1.05, 0))
    # Thigh (Upper Leg)
    Entity(parent=leg_l, model='cube', color=color.rgb(42/255, 42/255, 48/255),
           scale=(0.34, 0.52, 0.36), position=(0, -0.24, 0.02))
    Entity(parent=leg_l, model='cube', color=color.rgb(65/255, 65/255, 72/255),
           scale=(0.30, 0.44, 0.12), position=(0, -0.24, 0.18))
    # Calf / Shin (Lower Leg)
    Entity(parent=leg_l, model='cube', color=color.rgb(32/255, 32/255, 38/255),
           scale=(0.28, 0.48, 0.30), position=(0, -0.68, -0.04))
    # Wolf Paw
    Entity(parent=leg_l, model='cube', color=color.rgb(20/255, 20/255, 25/255),
           scale=(0.32, 0.14, 0.46), position=(0, -0.96, 0.08))
    # Claws
    Entity(parent=leg_l, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.14), position=(-0.09, -0.98, 0.35))
    Entity(parent=leg_l, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.16), position=(0, -0.98, 0.37))
    Entity(parent=leg_l, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.14), position=(0.09, -0.98, 0.35))

    # --- Right Leg Pivot ---
    leg_r = Entity(parent=root, position=(0.28, 1.05, 0))
    # Thigh (Upper Leg)
    Entity(parent=leg_r, model='cube', color=color.rgb(42/255, 42/255, 48/255),
           scale=(0.34, 0.52, 0.36), position=(0, -0.24, 0.02))
    Entity(parent=leg_r, model='cube', color=color.rgb(65/255, 65/255, 72/255),
           scale=(0.30, 0.44, 0.12), position=(0, -0.24, 0.18))
    # Calf / Shin (Lower Leg)
    Entity(parent=leg_r, model='cube', color=color.rgb(32/255, 32/255, 38/255),
           scale=(0.28, 0.48, 0.30), position=(0, -0.68, -0.04))
    # Wolf Paw
    Entity(parent=leg_r, model='cube', color=color.rgb(20/255, 20/255, 25/255),
           scale=(0.32, 0.14, 0.46), position=(0, -0.96, 0.08))
    # Claws
    Entity(parent=leg_r, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.14), position=(-0.09, -0.98, 0.35))
    Entity(parent=leg_r, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.16), position=(0, -0.98, 0.37))
    Entity(parent=leg_r, model='cube', color=color.rgb(230/255, 230/255, 230/255),
           scale=(0.05, 0.06, 0.14), position=(0.09, -0.98, 0.35))

    # =========================================================================
    # ARMS & DUAL SICKLES
    # =========================================================================
    # --- Left Arm ---
    arm_l = Entity(parent=root, position=(-0.70, 1.82, 0))
    # Upper Arm / Shoulder
    Entity(parent=arm_l, model='cube', color=color.rgb(215/255, 215/255, 222/255),
           scale=(0.26, 0.55, 0.26), position=(0, -0.22, 0))
    # Forearm
    Entity(parent=arm_l, model='cube', color=color.rgb(195/255, 195/255, 202/255),
           scale=(0.24, 0.48, 0.24), position=(0, -0.62, 0.04))
    # Hand
    Entity(parent=arm_l, model='sphere', color=color.rgb(180/255, 180/255, 188/255),
           scale=(0.22, 0.22, 0.22), position=(0, -0.88, 0.1))
    # Sickle Handle
    Entity(parent=arm_l, model='cube', color=color.rgb(80/255, 50/255, 25/255),
           scale=(0.07, 0.42, 0.07), position=(0, -0.88, 0.1))
    Entity(parent=arm_l, model='cube', color=color.rgb(160/255, 160/255, 170/255),
           scale=(0.09, 0.06, 0.09), position=(0, -0.69, 0.1))
    # Curved Sickle Blade
    Entity(parent=arm_l, model='cube', color=color.rgb(190/255, 195/255, 205/255),
           scale=(0.05, 0.05, 0.40), position=(0, -0.67, 0.28), rotation=(20, 0, 0))
    Entity(parent=arm_l, model='cube', color=color.rgb(210/255, 215/255, 230/255),
           scale=(0.045, 0.045, 0.52), position=(0, -0.48, 0.48), rotation=(-40, 25, 0))
    Entity(parent=arm_l, model='cube', color=color.rgb(225/255, 230/255, 245/255),
           scale=(0.04, 0.04, 0.48), position=(0.12, -0.25, 0.55), rotation=(-75, 55, 0))
    Entity(parent=arm_l, model='cube', color=color.white,
           scale=(0.03, 0.03, 0.40), position=(0.26, -0.06, 0.42), rotation=(-120, 80, 0))

    # --- Right Arm ---
    arm_r = Entity(parent=root, position=(0.70, 1.82, 0))
    # Upper Arm / Shoulder
    Entity(parent=arm_r, model='cube', color=color.rgb(215/255, 215/255, 222/255),
           scale=(0.26, 0.55, 0.26), position=(0, -0.22, 0))
    # Forearm
    Entity(parent=arm_r, model='cube', color=color.rgb(195/255, 195/255, 202/255),
           scale=(0.24, 0.48, 0.24), position=(0, -0.62, 0.04))
    # Hand
    Entity(parent=arm_r, model='sphere', color=color.rgb(180/255, 180/255, 188/255),
           scale=(0.22, 0.22, 0.22), position=(0, -0.88, 0.1))
    # Sickle Handle
    Entity(parent=arm_r, model='cube', color=color.rgb(80/255, 50/255, 25/255),
           scale=(0.07, 0.42, 0.07), position=(0, -0.88, 0.1))
    Entity(parent=arm_r, model='cube', color=color.rgb(160/255, 160/255, 170/255),
           scale=(0.09, 0.06, 0.09), position=(0, -0.69, 0.1))
    # Curved Sickle Blade
    Entity(parent=arm_r, model='cube', color=color.rgb(190/255, 195/255, 205/255),
           scale=(0.05, 0.05, 0.40), position=(0, -0.67, 0.28), rotation=(20, 0, 0))
    weapon = Entity(parent=arm_r, model='cube', color=color.rgb(210/255, 215/255, 230/255),
                    scale=(0.045, 0.045, 0.52), position=(0, -0.48, 0.48), rotation=(-40, -25, 0))
    Entity(parent=arm_r, model='cube', color=color.rgb(225/255, 230/255, 245/255),
           scale=(0.04, 0.04, 0.48), position=(-0.12, -0.25, 0.55), rotation=(-75, -55, 0))
    Entity(parent=arm_r, model='cube', color=color.white,
           scale=(0.03, 0.03, 0.40), position=(-0.26, -0.06, 0.42), rotation=(-120, -80, 0))

    # Death is 1.45x-1.5x taller and broader than Puss
    root.scale = Vec3(1.35, 1.45, 1.35)

    return {
        'root': root,
        'weapon_arm': arm_r,
        'left_arm': arm_l,
        'leg_l': leg_l,
        'leg_r': leg_r,
        'body': chest,
        'weapon': weapon,
    }


# =============================================================================
# ENEMY BOT CLASS (Puss Bots)
# =============================================================================

class PussBot:
    def __init__(self, position):
        self.data       = build_puss(is_enemy=True)
        self.root       = self.data['root']
        self.weapon_arm = self.data['weapon_arm']
        self.leg_l      = self.data['leg_l']
        self.leg_r      = self.data['leg_r']
        self.root.position = position

        self.hp         = 100.0
        self.max_hp     = 100.0
        self.speed      = 3.2
        self.attack_range = 2.4
        self.attack_cooldown = 1.3
        self.cooldown_timer = random.uniform(0.2, 0.8)
        self.is_attacking = False
        self.walk_time  = random.uniform(0.0, 3.0)
        self.is_dead    = False

        # Floating 3D Health Bar
        self.hp_bar_bg = Entity(parent=self.root, model='cube', color=color.black,
                                scale=(1.2, 0.12, 0.04), position=(0, 2.5, 0), billboard=True)
        self.hp_bar_fill = Entity(parent=self.hp_bar_bg, model='cube', color=color.red,
                                  scale=(0.96, 0.7, 1.0), position=(0, 0, -0.05))

    def update_ai(self, dt, target_pos):
        if self.is_dead:
            return

        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt

        diff = target_pos - self.root.position
        diff.y = 0
        dist = diff.length()

        if dist > 0.01:
            target_rot_y = math.degrees(math.atan2(diff.x, diff.z))
            angle_diff = (target_rot_y - self.root.rotation_y + 180) % 360 - 180
            self.root.rotation_y += angle_diff * min(1.0, 10.0 * dt)

        if dist > self.attack_range:
            move_dir = diff.normalized()
            self.root.position += move_dir * self.speed * dt

            self.walk_time += dt * 8.0
            swing = math.sin(self.walk_time) * 22.0
            if self.leg_l: self.leg_l.rotation_x = swing
            if self.leg_r: self.leg_r.rotation_x = -swing
        else:
            if self.leg_l: self.leg_l.rotation_x = lerp(self.leg_l.rotation_x, 0, dt * 10)
            if self.leg_r: self.leg_r.rotation_x = lerp(self.leg_r.rotation_x, 0, dt * 10)

            if self.cooldown_timer <= 0 and not self.is_attacking:
                self.attack()

    def attack(self):
        self.is_attacking = True
        self.cooldown_timer = self.attack_cooldown

        if self.weapon_arm:
            self.weapon_arm.animate_rotation(Vec3(-35, -20, 10), duration=0.1, curve=curve.linear)
            self.weapon_arm.animate_position(Vec3(self.weapon_arm.x, self.weapon_arm.y, 0.35), duration=0.1)

        invoke(self.hit_check, delay=0.12)
        invoke(self.reset_attack, delay=0.25)

    def reset_attack(self):
        if self.weapon_arm and not self.is_dead:
            self.weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            self.weapon_arm.animate_position(Vec3(self.weapon_arm.x, self.weapon_arm.y, 0.0), duration=0.12)
        self.is_attacking = False

    def hit_check(self):
        global player_hp
        if self.is_dead or player is None or game_state != 'playing':
            return

        diff = player.position - self.root.position
        diff.y = 0
        if diff.length() <= (self.attack_range + 0.6):
            apply_damage_to_player(5.0)

    def take_damage(self, amount):
        if self.is_dead:
            return
        self.hp -= amount

        for child in self.root.children:
            if hasattr(child, 'color'):
                child.blink(color.red, duration=0.15)

        pct = max(0.0, self.hp / self.max_hp)
        self.hp_bar_fill.scale_x = max(0.01, pct * 0.96)
        self.hp_bar_fill.x = -(1.0 - pct) * 0.48

        dmg_txt = Text(text=f"-{int(amount)}%", position=self.root.position + Vec3(0, 2.7, 0),
                       color=color.yellow, scale=1.5, billboard=True)
        dmg_txt.animate_position(dmg_txt.position + Vec3(0, 0.8, 0), duration=0.4)
        dmg_txt.fade_out(duration=0.4)
        destroy(dmg_txt, delay=0.45)

        if self.hp <= 0:
            self.die()

    def die(self):
        global kills_count
        self.is_dead = True
        kills_count += 1
        update_hud()

        self.root.animate_scale(Vec3(0.01, 0.01, 0.01), duration=0.3, curve=curve.linear)
        destroy(self.root, delay=0.35)


def spawn_bot():
    """Spawn a Puss Bot at a safe perimeter around player."""
    if player is None:
        return
    angle = random.uniform(0, math.pi * 2)
    dist  = random.uniform(16.0, 26.0)
    spawn_pos = player.position + Vec3(math.cos(angle) * dist, 0, math.sin(angle) * dist)
    bot = PussBot(spawn_pos)
    active_bots.append(bot)


# =============================================================================
# 3-PANEL CHARACTER SELECTION UI (Players | Selection | Preview)
# =============================================================================

# UI Tracking references
card_buttons        = {}
player1_char_text   = None
preview_char_name   = None
preview_pivot       = None
preview_model       = None

def setup_selection_menu():
    global player1_char_text, preview_char_name, preview_pivot

    # Set selection camera
    camera.position = (0, 1.2, -6.0)
    camera.rotation = (0, 0, 0)

    # 3D Rotating Turntable Pivot — perfectly centered inside the right preview frame
    preview_pivot = Entity(position=(1.28, 0.60, -2.0), scale=(0.58, 0.58, 0.58))
    # Pedestal platform under the character
    Entity(parent=preview_pivot, model='cube', color=color.rgb(30/255, 30/255, 40/255),
           scale=(1.2, 0.10, 1.2), position=(0, -0.05, 0))
    Entity(parent=preview_pivot, model='cube', color=color.rgb(220/255, 50/255, 50/255),
           scale=(1.24, 0.03, 1.24), position=(0, 0.01, 0))

    # Top Banner Header
    top_title = Text(
        text   = "PUSS IN BOOTS : 3D BATTLE ARENA",
        origin = (0, 0),
        scale  = 1.8,
        y      = 0.45,
        z      = -0.05,
        color  = color.rgb(255/255, 200/255, 60/255),
    )
    selection_ui.append(top_title)

    # =========================================================================
    # HELPER: creates a bordered solid panel
    # =========================================================================
    def make_panel(bx, by, bw, bh, border_col, fill_col):
        border = Entity(parent=camera.ui, model='quad', color=border_col,
                        scale=(bw, bh), position=(bx, by), z=0.05)
        fill   = Entity(parent=camera.ui, model='quad',
                        color=color.rgb(fill_col[0]/255, fill_col[1]/255, fill_col[2]/255),
                        scale=(bw - 0.024, bh - 0.024), position=(bx, by), z=0.04)
        selection_ui.extend([border, fill])

    # =========================================================================
    # LEFT PANEL: PLAYERS  (Red border, dark fill)
    # =========================================================================
    make_panel(-0.44, -0.02, 0.36, 0.78,
               color.rgb(220/255, 40/255, 40/255),
               (18, 16, 22))

    lbl_players = Text(
        text='PLAYERS', origin=(0, 0), scale=1.5,
        x=-0.44, y=0.32, z=-0.02, color=color.rgb(255/255, 80/255, 80/255),
    )
    selection_ui.append(lbl_players)

    div1 = Entity(parent=camera.ui, model='quad',
                  color=color.rgb(220/255, 40/255, 40/255),
                  scale=(0.30, 0.005), position=(-0.44, 0.28), z=0.02)
    selection_ui.append(div1)

    def make_player_slot(idx, name, char_name, status, status_col, y_top):
        av_border = Entity(parent=camera.ui, model='circle',
                           color=color.rgb(220/255, 40/255, 40/255) if idx == 0 else color.rgb(70/255, 70/255, 80/255),
                           scale=(0.060, 0.060), position=(-0.56, y_top + 0.005), z=0.02)
        av_fill = Entity(parent=camera.ui, model='circle',
                         color=color.rgb(255/255, 140/255, 40/255) if idx == 0 else color.rgb(50/255, 50/255, 60/255),
                         scale=(0.050, 0.050), position=(-0.56, y_top + 0.005), z=0.01)
        av_num = Text(text=str(idx+1), origin=(0, 0), scale=0.85,
                      x=-0.56, y=y_top + 0.005, z=-0.01,
                      color=color.white if idx == 0 else color.gray)
        n_text  = Text(text=name, origin=(-0.5, 0), scale=1.0,
                       x=-0.51, y=y_top + 0.015, z=-0.01,
                       color=color.white if idx == 0 else color.gray)
        c_text  = Text(text=char_name, origin=(-0.5, 0), scale=0.85,
                       x=-0.51, y=y_top - 0.022, z=-0.01,
                       color=color.rgb(255/255, 215/255, 0/255) if idx == 0 else color.rgb(100/255, 100/255, 110/255))
        s_text  = Text(text=status, origin=(-0.5, 0), scale=0.75,
                       x=-0.51, y=y_top - 0.052, z=-0.01,
                       color=status_col)
        selection_ui.extend([av_border, av_fill, av_num, n_text, c_text, s_text])
        return c_text

    player1_char_text = make_player_slot(0, "Player 1 (Host)", "Puss in Boots",
                                         "[ READY ]",  color.rgb(50/255, 230/255, 80/255),  0.19)
    make_player_slot(1, "Player 2", "---", "[ Waiting... ]", color.rgb(140/255, 140/255, 150/255), 0.01)
    make_player_slot(2, "Player 3", "---", "[ Open Slot ]",  color.rgb(100/255, 100/255, 110/255), -0.15)
    make_player_slot(3, "Player 4", "---", "[ Open Slot ]",  color.rgb(100/255, 100/255, 110/255), -0.31)

    # =========================================================================
    # MIDDLE PANEL: CHARACTER SELECTION  (Grey border, dark fill)
    # =========================================================================
    make_panel(0.0, -0.02, 0.44, 0.78,
               color.rgb(80/255, 80/255, 100/255),
               (14, 14, 18))

    lbl_char_select = Text(
        text='CHARACTER SELECTION', origin=(0, 0), scale=1.45,
        x=0.0, y=0.32, z=-0.02, color=color.white,
    )
    selection_ui.append(lbl_char_select)

    div2 = Entity(parent=camera.ui, model='quad',
                  color=color.rgb(80/255, 80/255, 100/255),
                  scale=(0.40, 0.005), position=(0.0, 0.28), z=0.02)
    selection_ui.append(div2)

    # --- Character Cards: Name only ---
    chars = [
        ('puss',  'Puss in Boots',  -0.13, color.rgb(180/255, 90/255, 20/255),  color.rgb(255/255, 165/255, 50/255)),
        ('kitty', 'Kitty Softpaws',  0.0,   color.rgb(35/255, 45/255, 55/255),   color.rgb(80/255, 200/255, 220/255)),
        ('death', 'Death',           0.13,  color.rgb(110/255, 18/255, 22/255),  color.rgb(220/255, 50/255, 60/255)),
    ]

    for char_key, label_txt, x_pos, btn_col, border_col in chars:
        card_border = Entity(parent=camera.ui, model='quad',
                             color=border_col,
                             scale=(0.125, 0.38), position=(x_pos, 0.08), z=0.02)
        card = Button(
            text            = label_txt,
            color           = btn_col,
            highlight_color = color.rgba(border_col[0], border_col[1], border_col[2], 0.7),
            scale           = (0.112, 0.36),
            x               = x_pos,
            y               = 0.08,
            z               = 0.0,
            text_size       = 0.95,
        )
        card.on_click = lambda c=char_key: select_preview_character(c)
        selection_ui.extend([card_border, card])
        card_buttons[char_key] = (card_border, card)

    # CHOOSE CHARACTER button
    choose_border = Entity(parent=camera.ui, model='quad',
                           color=color.rgb(255/255, 80/255, 80/255),
                           scale=(0.36, 0.095), position=(0.0, -0.27), z=0.02)
    btn_choose = Button(
        text            = "CHOOSE CHARACTER",
        color           = color.rgb(200/255, 30/255, 30/255),
        highlight_color = color.rgb(255/255, 80/255, 80/255),
        scale           = (0.34, 0.080),
        x               = 0.0,
        y               = -0.27,
        z               = 0.0,
        text_size       = 1.2,
    )
    btn_choose.on_click = confirm_and_start_game
    selection_ui.extend([choose_border, btn_choose])

    # =========================================================================
    # RIGHT PANEL: CHARACTER PREVIEW  (Red Border Outline ONLY - No Opaque Fill)
    # =========================================================================
    px, py, pw, ph = 0.44, -0.02, 0.36, 0.78
    half_w, half_h = pw / 2, ph / 2
    bthick = 0.018
    rc = color.rgb(220/255, 40/255, 40/255)

    top_edge   = Entity(parent=camera.ui, model='quad', color=rc,
                        scale=(pw + bthick, bthick), position=(px, py + half_h), z=0.01)
    bot_edge   = Entity(parent=camera.ui, model='quad', color=rc,
                        scale=(pw + bthick, bthick), position=(px, py - half_h), z=0.01)
    left_edge  = Entity(parent=camera.ui, model='quad', color=rc,
                        scale=(bthick, ph), position=(px - half_w, py), z=0.01)
    right_edge = Entity(parent=camera.ui, model='quad', color=rc,
                        scale=(bthick, ph), position=(px + half_w, py), z=0.01)
    selection_ui.extend([top_edge, bot_edge, left_edge, right_edge])

    lbl_preview = Text(
        text='CHARACTER PREVIEW', origin=(0, 0), scale=1.4,
        x=px, y=0.32, z=-0.02, color=color.rgb(255/255, 80/255, 80/255),
    )
    preview_char_name = Text(
        text='Puss in Boots', origin=(0, 0), scale=1.4,
        x=px, y=-0.32, z=-0.02, color=color.orange,
    )
    selection_ui.extend([lbl_preview, preview_char_name])

    # Initial 3D preview model
    select_preview_character('puss')


def select_preview_character(char_key):
    """Switch the 3D rotating preview model and update selection indicators."""
    global preview_model, selected_preview_key

    selected_preview_key = char_key

    # Destroy previous 3D preview model
    if preview_model:
        destroy(preview_model)
        preview_model = None

    # Build 3D character on turntable
    builders = {'puss': build_puss, 'kitty': build_kitty, 'death': build_death}
    result = builders[char_key]()
    preview_model = result['root']
    preview_model.parent = preview_pivot
    preview_model.position = Vec3(0, 0, 0)
    preview_model.scale = Vec3(0.58, 0.58, 0.58) if char_key == 'death' else Vec3(0.72, 0.72, 0.72)

    names = {
        'puss':  'Puss in Boots',
        'kitty': 'Kitty Softpaws',
        'death': 'Death',
    }
    name_cols = {
        'puss':  color.orange,
        'kitty': color.cyan,
        'death': color.rgb(255/255, 80/255, 80/255),
    }

    if preview_char_name:
        preview_char_name.text  = names[char_key]
        preview_char_name.color = name_cols[char_key]

    if player1_char_text:
        player1_char_text.text  = names[char_key]

    # Highlight active card border
    highlight_cols = {
        'puss':  color.rgb(255/255, 200/255, 80/255),
        'kitty': color.rgb(80/255, 220/255, 240/255),
        'death': color.rgb(255/255, 80/255, 80/255),
    }
    dim_col = color.rgb(50/255, 50/255, 60/255)
    for k, (border_ent, btn_ent) in card_buttons.items():
        if k == char_key:
            border_ent.color = highlight_cols[k]
            border_ent.scale = (0.135, 0.395)
            btn_ent.scale    = (0.112, 0.36)
        else:
            border_ent.color = dim_col
            border_ent.scale = (0.125, 0.38)
            btn_ent.scale    = (0.112, 0.36)


def confirm_and_start_game():
    """Triggered when clicking CHOOSE CHARACTER."""
    start_game(selected_preview_key)


# =============================================================================
# GAME START
# =============================================================================

CAMERA_CONFIG = {
    'puss':  {'pivot_height': 1.05, 'cam_pos': Vec3(0, 0.35, -4.5), 'cam_rot': Vec3(4, 0, 0), 'fov': 50},
    'kitty': {'pivot_height': 0.90, 'cam_pos': Vec3(0, 0.30, -4.2), 'cam_rot': Vec3(3, 0, 0), 'fov': 50},
    'death': {'pivot_height': 2.10, 'cam_pos': Vec3(0, 1.00, -8.2), 'cam_rot': Vec3(5, 0, 0), 'fov': 55},
}
current_pivot_height = 1.05

def start_game(char_key):
    global player, weapon_arm, arm_left, leg_left, leg_right, body_entity, weapon_entity
    global game_state, selected_char, camera_pivot, current_pivot_height
    global BASE_SPEED, player_damage, player_hp, kills_count, active_bots
    global preview_pivot, preview_model

    selected_char = char_key
    cam_cfg = CAMERA_CONFIG.get(char_key, CAMERA_CONFIG['puss'])
    current_pivot_height = cam_cfg['pivot_height']

    # Set Character Stats
    player_hp = 100.0
    kills_count = 0
    if selected_char == 'death':
        BASE_SPEED    = 8.0    # 2 times faster!
        player_damage = 15.0   # 15% damage per hit
    else:
        BASE_SPEED    = 4.0
        player_damage = 5.0    # 5% damage per hit

    # Destroy menu UI & preview turntable
    for elem in selection_ui:
        destroy(elem)
    selection_ui.clear()

    if preview_model:
        destroy(preview_model)
        preview_model = None
    if preview_pivot:
        destroy(preview_pivot)
        preview_pivot = None

    # Build chosen champion in world
    builders = {'puss': build_puss, 'kitty': build_kitty, 'death': build_death}
    result    = builders[char_key]()

    player        = result['root']
    weapon_arm    = result['weapon_arm']
    arm_left      = result['left_arm']
    leg_left      = result['leg_l']
    leg_right     = result['leg_r']
    body_entity   = result['body']
    weapon_entity = result['weapon']

    player.position = Vec3(0, 0, 0)

    # Attach TPP Camera with character-specific pivot height, distance, and field of view
    camera_pivot = Entity(position=player.position + Vec3(0, current_pivot_height, 0))
    camera.parent   = camera_pivot
    camera.position = cam_cfg['cam_pos']
    camera.rotation = cam_cfg['cam_rot']
    camera.fov      = cam_cfg.get('fov', 50)

    mouse.locked = True
    game_state = 'playing'

    # Clear any leftover bots and spawn up to MAX_BOTS
    for bot in active_bots:
        destroy(bot.root)
    active_bots.clear()

    for _ in range(MAX_BOTS):
        spawn_bot()

    build_hud()


# =============================================================================
# HUD & COMBAT UI
# =============================================================================
hud_char_name       = None
hud_hp_bar_bg       = None
hud_hp_bar_fill     = None
hud_hp_text         = None
hud_dash_text       = None
hud_kills_text      = None
hud_special_perk    = None
hud_controls        = None
block_indicator     = None
autoblock_banner    = None

def build_hud():
    global hud_char_name, hud_hp_bar_bg, hud_hp_bar_fill, hud_hp_text, hud_dash_text
    global hud_kills_text, hud_special_perk, hud_controls, block_indicator, autoblock_banner

    names = {'puss': 'Puss in Boots', 'kitty': 'Kitty Softpaws', 'death': 'Death (The Wolf)'}

    # Character Name Header
    hud_char_name = Text(
        text   = f"Hero: {names[selected_char]}",
        origin = (-0.5, 0.5),
        scale  = 1.15,
        x      = -0.85,
        y      = 0.47,
        color  = color.rgb(255/255, 215/255, 0/255),
    )

    # Health Bar Background
    hud_hp_bar_bg = Entity(
        parent = camera.ui,
        model  = 'quad',
        color  = color.rgb(40/255, 20/255, 20/255),
        scale  = (0.32, 0.038),
        origin = (-0.5, 0.5),
        x      = -0.85,
        y      = 0.42,
    )
    # Health Bar Fill
    hud_hp_bar_fill = Entity(
        parent = camera.ui,
        model  = 'quad',
        color  = color.rgb(50/255, 220/255, 70/255),
        scale  = (0.316, 0.034),
        origin = (-0.5, 0.5),
        x      = -0.848,
        y      = 0.418,
    )
    hud_hp_text = Text(
        text   = "HP: 100 / 100 (100%)",
        origin = (-0.5, 0.5),
        scale  = 0.95,
        x      = -0.51,
        y      = 0.418,
        color  = color.white,
    )

    # Dash Status
    hud_dash_text = Text(
        text   = "DASH [Shift]: Ready",
        origin = (-0.5, 0.5),
        scale  = 1.05,
        x      = -0.85,
        y      = 0.36,
        color  = color.cyan,
    )

    # Kills Counter
    hud_kills_text = Text(
        text   = "BOTS DEFEATED: 0",
        origin = (0.5, 0.5),
        scale  = 1.2,
        x      = 0.85,
        y      = 0.47,
        color  = color.rgb(255/255, 140/255, 40/255),
    )

    # Death Special Perk Banner in gameplay HUD
    if selected_char == 'death':
        hud_special_perk = Text(
            text   = "★ DEATH PERKS: 2x Speed | 15% Dmg | 50% Auto-Block Active!",
            origin = (-0.5, 0.5),
            scale  = 1.0,
            x      = -0.85,
            y      = 0.31,
            color  = color.rgb(255/255, 80/255, 80/255),
        )

    hud_controls = Text(
        text   = "WASD: Move | Space: Jump | Ctrl: Sprint | Shift: Dash | RMB: Block | LMB: Attack",
        origin = (0, -0.5),
        scale  = 0.85,
        y      = -0.47,
        color  = color.rgb(200/255, 200/255, 200/255),
    )

    block_indicator = Text(
        text   = "[ SHIELD BLOCKING ]",
        origin = (0, 0),
        scale  = 2.2,
        y      = 0.15,
        color  = color.azure,
        visible= False,
    )

    autoblock_banner = Text(
        text   = "[ ★ 50% AUTO-BLOCKED! ★ ]",
        origin = (0, 0),
        scale  = 2.2,
        y      = 0.22,
        color  = color.rgb(255/255, 220/255, 50/255),
        visible= False,
    )


def update_hud():
    """Refresh the health bar, HP text, and kill counter."""
    global hud_hp_bar_fill, hud_hp_text, hud_kills_text

    if hud_hp_bar_fill and hud_hp_text:
        pct = max(0.0, player_hp / player_max_hp)
        hud_hp_bar_fill.scale_x = max(0.001, pct * 0.316)

        if pct > 0.5:
            hud_hp_bar_fill.color = color.rgb(50/255, 220/255, 70/255)
        elif pct > 0.25:
            hud_hp_bar_fill.color = color.rgb(240/255, 200/255, 40/255)
        else:
            hud_hp_bar_fill.color = color.rgb(240/255, 40/255, 40/255)

        hud_hp_text.text = f"HP: {int(player_hp)} / {int(player_max_hp)} ({int(pct*100)}%)"

    if hud_kills_text:
        hud_kills_text.text = f"BOTS DEFEATED: {kills_count}"


def apply_damage_to_player(amount):
    """Handle damage taken by the player, checking manual block and Death's 50% autoblock."""
    global player_hp, game_state

    if game_state != 'playing' or player_hp <= 0:
        return

    # 1. Manual Block Check (RMB held)
    if is_blocking:
        show_block_spark()
        return

    # 2. Death's Passive: 50% Auto-Block Chance!
    if selected_char == 'death' and random.random() < 0.50:
        trigger_autoblock_effect()
        return

    # 3. Take Damage
    player_hp -= amount
    update_hud()

    for child in player.children:
        if hasattr(child, 'color'):
            child.blink(color.red, duration=0.15)

    if player_hp <= 0:
        player_hp = 0
        update_hud()
        trigger_game_over()


def trigger_autoblock_effect():
    """Visual feedback when Death's 50% autoblock negates a hit."""
    global autoblock_banner
    if autoblock_banner:
        autoblock_banner.visible = True
        invoke(hide_autoblock_banner, delay=0.5)

    if arm_left:
        arm_left.animate_rotation(Vec3(25, 45, -20), duration=0.08)
        invoke(lambda: arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.1), delay=0.15)
    if weapon_arm:
        weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.08)
        invoke(lambda: weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1), delay=0.15)


def hide_autoblock_banner():
    if autoblock_banner:
        autoblock_banner.visible = False


def show_block_spark():
    """Visual indicator for manual parry."""
    if block_indicator:
        block_indicator.color = color.yellow
        invoke(lambda: setattr(block_indicator, 'color', color.azure), delay=0.15)


def trigger_game_over():
    """Display Game Over screen."""
    global game_state
    game_state = 'game_over'

    Text(
        text   = "YOU FELL IN BATTLE!",
        origin = (0, 0),
        scale  = 3,
        y      = 0.1,
        color  = color.red,
    )
    Text(
        text   = f"Total Bots Defeated: {kills_count}\nPress [R] to Restart",
        origin = (0, 0),
        scale  = 1.5,
        y      = -0.05,
        color  = color.white,
    )


# =============================================================================
# PLAYER ATTACK & HIT DETECTION
# =============================================================================

def trigger_attack():
    """Animate weapons and detect melee hits against active Puss Bots."""
    global is_attacking
    if is_attacking:
        return
    is_attacking = True

    if selected_char == 'death':
        # Death's dual scissor cleave with BOTH arms
        if arm_left:
            arm_left.animate_rotation(Vec3(-35, 30, -20), duration=0.09, curve=curve.linear)
            arm_left.animate_position(Vec3(-0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(-35, -30, 20), duration=0.09, curve=curve.linear)
            weapon_arm.animate_position(Vec3(0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
    else:
        # Puss / Kitty single rapier/sword thrust
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(-25, -20, 10), duration=0.09, curve=curve.linear)
            weapon_arm.animate_position(Vec3(weapon_arm.x, weapon_arm.y, 0.35), duration=0.09, curve=curve.linear)

    invoke(check_player_attack_hits, delay=0.09)
    invoke(reset_attack_arm, delay=0.16)


def reset_attack_arm():
    global is_attacking
    if selected_char == 'death':
        if arm_left:
            arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            arm_left.animate_position(Vec3(-0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            weapon_arm.animate_position(Vec3(0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
    else:
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            weapon_arm.animate_position(Vec3(weapon_arm.x, weapon_arm.y, 0.0), duration=0.12, curve=curve.linear)
    is_attacking = False


def check_player_attack_hits():
    """Detect bots within melee strike range in front of the player."""
    if player is None or game_state != 'playing':
        return

    hit_range = 4.2 if selected_char == 'death' else 2.8

    for bot in list(active_bots):
        if bot.is_dead:
            continue
        diff = bot.root.position - player.position
        diff.y = 0
        dist = diff.length()

        if dist <= hit_range:
            if dist > 0.01:
                facing_dot = player.forward.normalized().dot(diff.normalized())
            else:
                facing_dot = 1.0

            if facing_dot > 0.15:  # within forward strike cone
                bot.take_damage(player_damage)
                if dist > 0.01:
                    bot.root.position += diff.normalized() * 0.5


# =============================================================================
# INPUT HANDLER
# =============================================================================

def input(key):
    global is_blocking, game_state, y_velocity, is_grounded

    if game_state == 'game_over' and key == 'r':
        import sys, os
        os.execv(sys.executable, ['python'] + sys.argv)
        return

    if game_state != 'playing':
        return

    # --- Block (hold RMB) ---
    if key == 'right mouse down':
        is_blocking = True
        if player:
            player.animate_rotation(Vec3(-6, player.rotation_y, player.rotation_z), duration=0.1)
        if selected_char == 'death':
            if arm_left:
                arm_left.animate_rotation(Vec3(25, 45, -20), duration=0.1)
                arm_left.animate_position(Vec3(-0.42, 1.82, 0.40), duration=0.1)
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.1)
                weapon_arm.animate_position(Vec3(0.42, 1.82, 0.40), duration=0.1)
        else:
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.1)
        if block_indicator:
            block_indicator.visible = True

    if key == 'right mouse up':
        is_blocking = False
        if player:
            player.animate_rotation(Vec3(0, player.rotation_y, player.rotation_z), duration=0.1)
        if selected_char == 'death':
            if arm_left:
                arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.1)
                arm_left.animate_position(Vec3(-0.70, 1.82, 0.0), duration=0.1)
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1)
                weapon_arm.animate_position(Vec3(0.70, 1.82, 0.0), duration=0.1)
        else:
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1)
        if block_indicator:
            block_indicator.visible = False

    # --- Attack (LMB) ---
    if key == 'left mouse down' and not is_blocking:
        trigger_attack()

    # --- Dash (Shift) ---
    if key == 'shift' and not is_blocking:
        do_dash()

    # --- Jump (Space) ---
    if key == 'space' and is_grounded and not is_blocking:
        y_velocity = JUMP_FORCE
        is_grounded = False

    # --- ESC → toggle mouse lock ---
    if key == 'escape':
        mouse.locked = not mouse.locked


# =============================================================================
# DASH MECHANIC
# =============================================================================

def do_dash():
    global dash_cooldown
    if dash_cooldown > 0:
        return

    dash_cooldown = DASH_COOLDOWN
    forward = player.forward
    player.position += forward * DASH_FORCE


# =============================================================================
# MAIN UPDATE LOOP
# =============================================================================
camera_yaw   = 0.0
camera_pitch = 3.0

def update():
    global dash_cooldown, camera_yaw, camera_pitch, y_velocity, is_grounded, walk_time
    global bot_respawn_timer

    dt = time.dt

    # 3D Turntable continuous rotation in selection menu
    if game_state == 'selection' and preview_pivot:
        preview_pivot.rotation_y += dt * 45.0
        return

    if game_state != 'playing' or player is None:
        return

    # -------------------------------------------------------
    # CAMERA PIVOT FOLLOWS PLAYER
    # -------------------------------------------------------
    camera_pivot.position = player.position + Vec3(0, current_pivot_height, 0)

    # -------------------------------------------------------
    # DASH COOLDOWN TIMER
    # -------------------------------------------------------
    if dash_cooldown > 0:
        dash_cooldown -= dt
        if dash_cooldown <= 0:
            dash_cooldown = 0
            if hud_dash_text:
                hud_dash_text.text  = "DASH [Shift]: Ready"
                hud_dash_text.color = color.cyan
        else:
            if hud_dash_text:
                hud_dash_text.text  = f"DASH: {dash_cooldown:.1f}s"
                hud_dash_text.color = color.orange

    # -------------------------------------------------------
    # JUMP & GRAVITY PHYSICS
    # -------------------------------------------------------
    if not is_grounded or player.y > 0 or y_velocity != 0:
        y_velocity -= GRAVITY * dt
        player.y += y_velocity * dt

    if player.y <= 0:
        player.y = 0
        y_velocity = 0.0
        is_grounded = True

    # -------------------------------------------------------
    # BOT SPAWNING & AI LOOP (Maintain up to 4 bots)
    # -------------------------------------------------------
    for bot in list(active_bots):
        if bot.is_dead and bot.root not in scene.entities:
            active_bots.remove(bot)

    if len(active_bots) < MAX_BOTS:
        bot_respawn_timer -= dt
        if bot_respawn_timer <= 0:
            spawn_bot()
            bot_respawn_timer = 1.2

    for bot in active_bots:
        bot.update_ai(dt, player.position)

    # -------------------------------------------------------
    # BLOCK — disable horizontal movement
    # -------------------------------------------------------
    if is_blocking:
        if leg_left: leg_left.rotation_x = 0
        if leg_right: leg_right.rotation_x = 0
        return

    # -------------------------------------------------------
    # CAMERA ORBIT — mouse look
    # -------------------------------------------------------
    if mouse.locked:
        sensitivity  = 40
        camera_yaw  += mouse.velocity[0] * sensitivity
        camera_pitch -= mouse.velocity[1] * sensitivity
        camera_pitch  = clamp(camera_pitch, -20, 50)

        camera_pivot.rotation_y = camera_yaw
        camera_pivot.rotation_x = camera_pitch

    # -------------------------------------------------------
    # MOVEMENT & INPUT
    # -------------------------------------------------------
    speed = BASE_SPEED
    is_sprinting = held_keys['control']
    if is_sprinting:
        speed *= SPRINT_MULT

    cam_forward = camera_pivot.forward
    cam_forward.y = 0
    if cam_forward.length() > 0:
        cam_forward = cam_forward.normalized()

    cam_right = camera_pivot.right
    cam_right.y = 0
    if cam_right.length() > 0:
        cam_right = cam_right.normalized()

    move_dir = Vec3(0, 0, 0)
    if held_keys['w']: move_dir += cam_forward
    if held_keys['s']: move_dir -= cam_forward
    if held_keys['a']: move_dir -= cam_right
    if held_keys['d']: move_dir += cam_right

    move_dir.y = 0
    is_moving = move_dir.length() > 0

    if is_moving:
        move_dir = move_dir.normalized()
        player.position += move_dir * speed * dt

        target_rot_y = math.degrees(math.atan2(move_dir.x, move_dir.z))
        angle_diff = (target_rot_y - player.rotation_y + 180) % 360 - 180
        player.rotation_y += angle_diff * min(1.0, 15.0 * dt)

        anim_speed = 14.0 if is_sprinting else 8.0
        walk_time += dt * anim_speed
        swing_amp = 38.0 if is_sprinting else 22.0

        if leg_left:  leg_left.rotation_x = math.sin(walk_time) * swing_amp
        if leg_right: leg_right.rotation_x = -math.sin(walk_time) * swing_amp

        if not is_attacking and not is_blocking:
            if selected_char == 'death':
                if is_sprinting:
                    if arm_left:   arm_left.rotation = Vec3(35, 20, -15)
                    if weapon_arm: weapon_arm.rotation = Vec3(35, -20, 15)
                else:
                    arm_swing = math.sin(walk_time) * 14.0
                    if arm_left:   arm_left.rotation_x = arm_swing
                    if weapon_arm: weapon_arm.rotation_x = -arm_swing
            else:
                arm_swing = math.sin(walk_time) * (26.0 if is_sprinting else 16.0)
                if arm_left:   arm_left.rotation_x = arm_swing
                if weapon_arm: weapon_arm.rotation_x = -arm_swing * 0.4
    else:
        if leg_left:  leg_left.rotation_x = lerp(leg_left.rotation_x, 0, dt * 10)
        if leg_right: leg_right.rotation_x = lerp(leg_right.rotation_x, 0, dt * 10)

        if not is_attacking and not is_blocking:
            if arm_left:   arm_left.rotation = Vec3(0, 0, 0)
            if weapon_arm: weapon_arm.rotation = Vec3(0, 0, 0)


# Initialize 3-Panel Selection Screen
setup_selection_menu()

# =============================================================================
# RUN
# =============================================================================
app.run()
