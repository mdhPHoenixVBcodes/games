# =============================================================================
#  PUSS IN BOOTS - 3D Adventure Game
#  Engine: Ursina (Python)
#  3-Panel Character Selection UI with Live 3D Rotating Preview
# =============================================================================

import os
import sys
from pathlib import Path
from ursina import *
import math
import random
import json
import queue
import socket
import threading
import time as system_time

# =============================================================================
# APP INITIALIZATION
# =============================================================================
# GLBs are in the same folder as puss.py
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
application.asset_folder = current_dir
_glb_dir = current_dir

app = Ursina(title="Puss in Boots - 3D Adventure", borderless=False, vsync=True)

# Performance & Render Optimizations
window.fps_counter.enabled      = False
window.entity_counter.enabled   = False
window.collider_counter.enabled = False
window.exit_button.visible      = True

# Camera optimization: Tight clip plane for maximum framerate & zero rendering waste
camera.clip_plane_far  = 75.0
camera.clip_plane_near = 0.2

# =============================================================================
# BACKGROUND BATTLE MUSIC
# =============================================================================
bg_music = None
for _music_name in ['battlesong.mp3', 'battlesong.ogg', 'battlesong.wav']:
    if (current_dir / _music_name).exists() or (current_dir.parent / _music_name).exists():
        try:
            bg_music = Audio(_music_name, loop=True, autoplay=True, volume=0.35, ignore_paused=True)
            break
        except Exception as _e:
            print(f'[audio] Could not load {_music_name}: {_e}')

# =============================================================================
# GLOBAL GAME STATE & STATS
# =============================================================================
game_state          = 'main_menu'
game_mode           = 'pve'
game_over_ui_elems  = []            # Game over UI tracking for clean reset
player              = None          # Active player entity (root pivot)
weapon_arm          = None          # Right arm entity / pivot (or mouth stick pivot)
arm_left            = None          # Left arm entity / pivot (or head pivot)
leg_left            = None          # Left leg pivot (or front-left leg)
leg_right           = None          # Right leg pivot (or front-right leg)
leg_back_l          = None          # Back-left leg pivot (for Perrito quadruped)
leg_back_r          = None          # Back-right leg pivot (for Perrito quadruped)
tail_entity         = None          # Tail pivot (for Perrito wagging)
body_entity         = None          # Torso entity for sprint lean
weapon_entity       = None          # Main weapon mesh

def deep_destroy(ent):
    """Recursively destroys all child entities and shapes to eliminate memory leaks and lag."""
    if not ent:
        return
    try:
        for child in list(ent.children):
            deep_destroy(child)
    except Exception:
        pass
    try:
        destroy(ent)
    except Exception:
        pass

# Combat & Stats
player_hp           = 100.0
player_max_hp       = 100.0
player_damage       = 5.0           # 5% for Puss/Kitty, 15% for Death
is_blocking         = False
is_attacking        = False
walk_time           = 0.0
dash_cooldown       = 0.0
DASH_COOLDOWN       = 1.0
DASH_FORCE          = 12.0          # Snappy, athletic dash
BASE_SPEED          = 7.0           # Increased equally for fast, fluid combat (was 4.0)
SPRINT_MULT         = 2.0
y_velocity          = 0.0
is_grounded         = True
GRAVITY             = 24.0
JUMP_FORCE          = 8.5
camera_pivot        = None
selection_ui        = []
selected_char       = 'puss'

# Pause menu state
is_paused           = False
pause_ui_elems      = []        # holds every entity/text in the pause overlay
kills_count         = 0
menu_ui             = []
menu_camera_pivot   = None
menu_status_text    = None
menu_join_address   = ''
mouse_sensitivity   = 40
CONTROL_DEFAULTS = {
    'forward': 'w',
    'backward': 's',
    'left': 'a',
    'right': 'd',
    'sprint': 'left control',
    'jump': 'space',
    'attack': 'left mouse down',
    'block': 'right mouse down',
    'dash': 'shift',
    'ability': 'e',
    'ult': 'x',
}
controls = CONTROL_DEFAULTS.copy()
control_capture_action = None
control_button_refs = {}
cheat_panel_open = False
cheat_code_input = ''
cheat_panel_status = ''
cheat_input_focused = False
cheat_panel_ui = []
cheat_panel_input_entity = None
cheat_panel_status_entity = None
cheat_panel_submit_callback = None
pending_cheats = set()
match_cheats = set()
training_dummy      = None
network_status_label = None
remote_player       = None
remote_player_data  = None
remote_player_char  = None
remote_player_walk_time = 0.0
remote_hp_bar_fill  = None
remote_name_tag     = None
remote_fear_label    = None
host_start_button   = None
network_role        = None
network_connected   = False
network_server_socket = None
network_connection_socket = None
network_events      = queue.Queue()
network_running     = threading.Event()
network_generation  = 0
network_snapshot_lock = threading.Lock()
network_local_snapshot = {
    'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0, 'attack_seq': 0,
    'char': 'puss', 'moving': False, 'sprinting': False, 'blocking': False, 'hp': 100.0,
}
network_remote_snapshot = None
network_attack_sequence = 0
remote_attack_sequence = 0
join_address_label = None
NETWORK_PORT        = 50007

# Hidden easter egg state
EASTER_EGG_SEQUENCE  = 'nukeyes'
easter_egg_progress  = 0
easter_egg_active    = False
easter_egg_escape_used = False
easter_egg_mouse_unlocked = False
easter_egg_map_ui    = []
easter_egg_player_marker = None
easter_egg_bot_markers = []
easter_egg_cursor    = None

# Bot Spawning
MAX_BOTS            = 4
active_bots         = []
bot_respawn_timer   = 0.0

# Selected character key in menu
selected_preview_key= 'puss'

# =============================================================================
# FLOATING ARENA PLATFORM & LIGHTING
# =============================================================================
PLATFORM_SIZE = 80.0
PLATFORM_HALF = PLATFORM_SIZE / 2.0   # 40.0 units from center to edge

# Main 3D Floating Battle Platform
ground = Entity(
    model         = 'cube',
    scale         = (PLATFORM_SIZE, 3, PLATFORM_SIZE),
    position      = (0, -1.5, 0),
    color         = color.rgb(60/255, 110/255, 50/255),
    texture       = 'white_cube',
    texture_scale = (20, 20),
    collider      = 'box'
)
# Rocky cliff underside of the floating battle island
ground_under = Entity(
    parent        = ground,
    model         = 'cube',
    scale         = (0.94, 2.0, 0.94),
    position      = (0, -1.2, 0),
    color         = color.rgb(55/255, 45/255, 40/255),
    texture       = 'white_cube',
    texture_scale = (10, 10),
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

    # --- Body (Torso & Chest Spheres) ---
    body = Entity(parent=root, model='sphere', color=body_col,
                  scale=(0.7, 0.85, 0.55), position=(0, 0.9, 0))
    Entity(parent=root, model='sphere', color=color.white if not is_enemy else color.rgb(210/255, 210/255, 210/255),
           scale=(0.38, 0.48, 0.22), position=(0, 0.95, 0.22))
    Entity(parent=root, model=Cylinder(), color=color.black,
           scale=(0.72, 0.08, 0.55), position=(0, 0.72, 0))

    # --- Head (3D Face Model only — Centered & Straightened) ---
    face = Entity(parent=root, model='pussface.glb',
                  scale=1.15, position=(0.17, 1.65, 0.05), rotation=(0, 0, -10))
    if is_enemy:
        face.color = color.rgb(210/255, 110/255, 60/255)

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

    # --- Body (Torso & Chest Spheres) ---
    body = Entity(parent=root, model='sphere', color=color.black,
                  scale=(0.65, 0.8, 0.52), position=(0, 0.9, 0))
    Entity(parent=root, model='sphere', color=color.white,
           scale=(0.32, 0.45, 0.20), position=(0, 0.96, 0.22))
    Entity(parent=root, model=Cylinder(), color=color.rgb(120/255, 80/255, 40/255),
           scale=(0.67, 0.07, 0.52), position=(0, 0.72, 0))

    # --- Head (3D Face Model only) ---
    face = Entity(parent=root, model='kittyface.glb',
                  scale=0.62, position=(0, 1.44, 0.04))

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
    # TORSO: ABDOMEN & CHEST (Spherical Anatomy)
    # =========================================================================
    # --- Abdomen (Lower Torso Sphere) ---
    abdomen = Entity(parent=root, model='sphere', color=color.rgb(180/255, 180/255, 188/255),
                     scale=(0.86, 0.54, 0.58), position=(0, 1.28, 0))
    # Belt & Buckle
    Entity(parent=root, model=Cylinder(), color=color.rgb(55/255, 42/255, 32/255),
           scale=(0.88, 0.16, 0.58), position=(0, 1.08, 0))
    Entity(parent=root, model='cube', color=color.rgb(210/255, 175/255, 60/255),
           scale=(0.22, 0.18, 0.10), position=(0, 1.08, 0.29))

    # --- Chest (Upper Torso - Muscular & Broad Spheres) ---
    chest = Entity(parent=root, model='sphere', color=color.rgb(215/255, 215/255, 222/255),
                   scale=(1.12, 0.76, 0.70), position=(0, 1.74, 0.02))
    # Pectorals & Sternum Plate
    Entity(parent=root, model='sphere', color=color.rgb(235/255, 235/255, 242/255),
           scale=(0.82, 0.54, 0.25), position=(0, 1.74, 0.30))
    # Side Rib Definition
    Entity(parent=root, model='sphere', color=color.rgb(175/255, 175/255, 182/255),
           scale=(0.35, 0.56, 0.60), position=(-0.46, 1.72, 0.02))
    Entity(parent=root, model='sphere', color=color.rgb(175/255, 175/255, 182/255),
           scale=(0.35, 0.56, 0.60), position=(0.46, 1.72, 0.02))

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
    Entity(parent=root, model='sphere', color=color.rgb(205/255, 205/255, 212/255),
           scale=(0.54, 0.42, 0.54), position=(0, 2.18, 0))

    # Head (3D Face Model only — larger and straightened)
    face = Entity(parent=root, model='deathface.glb',
                  scale=1.30, position=(-0.06, 2.49, 0.06), rotation=(0, -30, 0))

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


def build_perrito():
    """
    Procedurally build Perrito (The Therapy Dog from The Last Wish).
    Quadruped dog on all fours wearing his knitted blue/teal sweater, floppy ears,
    expressive eyes, wagging tail, and holding a wooden stick sword in his mouth.
    """
    root = Entity()
    root.scale = Vec3(0.95, 0.95, 0.95)

    C_TAN          = color.rgb(225/255, 185/255, 135/255)
    C_WHITE        = color.rgb(250/255, 246/255, 240/255)
    C_TEAL_SWEATER = color.rgb(55/255, 140/255, 150/255)
    C_DARK_BROWN   = color.rgb(85/255, 48/255, 25/255)
    C_BLACK        = color.rgb(25/255, 25/255, 28/255)
    C_STICK        = color.rgb(130/255, 75/255, 35/255)

    # --- Torso (Quadruped Dog Body with Hand-Knit Sweater) ---
    body = Entity(parent=root, position=(0, 0.45, 0))
    # Sweater body (horizontal rounded oval sphere)
    Entity(parent=body, model='sphere', color=C_TEAL_SWEATER, scale=(0.44, 0.40, 0.72))
    # White collar at front of sweater
    Entity(parent=body, model='sphere', color=C_WHITE, scale=(0.40, 0.38, 0.16), position=(0, 0.08, 0.32))
    # Sweater ribbing hem
    Entity(parent=body, model=Cylinder(), color=color.rgb(45/255, 120/255, 130/255), scale=(0.46, 0.05, 0.70), position=(0, -0.02, 0))

    # --- Tail (Happy Wagging Tail at rear) ---
    tail_pivot = Entity(parent=root, position=(0, 0.52, -0.36), rotation=(35, 0, 0))
    Entity(parent=tail_pivot, model='cube', color=C_TAN, scale=(0.07, 0.28, 0.07), position=(0, 0.12, 0), rotation=(15, 0, 0))
    Entity(parent=tail_pivot, model='sphere', color=C_WHITE, scale=(0.10, 0.10, 0.10), position=(0, 0.26, 0.04))

    # --- 4 Legs on Pivots (Quadruped Walking Dog) ---
    # Front Left
    leg_fl = Entity(parent=root, position=(-0.16, 0.32, 0.24))
    Entity(parent=leg_fl, model='cube', color=C_TEAL_SWEATER, scale=(0.12, 0.16, 0.12), position=(0, -0.06, 0))
    Entity(parent=leg_fl, model='cube', color=C_TAN, scale=(0.10, 0.22, 0.10), position=(0, -0.22, 0))
    Entity(parent=leg_fl, model='sphere', color=C_WHITE, scale=(0.12, 0.08, 0.14), position=(0, -0.32, 0.03))

    # Front Right
    leg_fr = Entity(parent=root, position=(0.16, 0.32, 0.24))
    Entity(parent=leg_fr, model='cube', color=C_TEAL_SWEATER, scale=(0.12, 0.16, 0.12), position=(0, -0.06, 0))
    Entity(parent=leg_fr, model='cube', color=C_TAN, scale=(0.10, 0.22, 0.10), position=(0, -0.22, 0))
    Entity(parent=leg_fr, model='sphere', color=C_WHITE, scale=(0.12, 0.08, 0.14), position=(0, -0.32, 0.03))

    # Back Left
    leg_bl = Entity(parent=root, position=(-0.16, 0.32, -0.24))
    Entity(parent=leg_bl, model='cube', color=C_TAN, scale=(0.11, 0.28, 0.11), position=(0, -0.14, 0))
    Entity(parent=leg_bl, model='sphere', color=C_WHITE, scale=(0.12, 0.08, 0.14), position=(0, -0.28, 0.03))

    # Back Right
    leg_br = Entity(parent=root, position=(0.16, 0.32, -0.24))
    Entity(parent=leg_br, model='cube', color=C_TAN, scale=(0.11, 0.28, 0.11), position=(0, -0.14, 0))
    Entity(parent=leg_br, model='sphere', color=C_WHITE, scale=(0.12, 0.08, 0.14), position=(0, -0.28, 0.03))

    # --- Head (3D Face Model only) & Floppy Ears ---
    head = Entity(parent=root, position=(0, 0.65, 0.28))
    face = Entity(parent=head, model='perritoface.glb',
                  scale=0.62, position=(0.08, 0, 0.04), rotation=(0, 0, -5))

    # --- Wooden Stick Sword Held Horizontally Across Muzzle ---
    # Clamped crosswise in teeth across his muzzle (left-to-right along X-axis), NOT sticking out forward!
    stick_pivot = Entity(parent=head, position=(0, -0.09, 0.32), rotation=(0, 0, 0))
    # Main stick branch running horizontally across the mouth (X-axis)
    stick = Entity(parent=stick_pivot, model='cube', color=C_STICK,
                   scale=(1.18, 0.055, 0.055), position=(0.06, 0, 0))
    # Whittled wooden sword blade on right side
    Entity(parent=stick_pivot, model='cube', color=color.rgb(175/255, 110/255, 55/255),
           scale=(0.28, 0.045, 0.045), position=(0.58, 0, 0))
    # Small branch knot / twig crossguard on the left side near cheek
    Entity(parent=stick_pivot, model='cube', color=color.rgb(90/255, 50/255, 22/255),
           scale=(0.065, 0.16, 0.065), position=(-0.24, 0, 0), rotation=(0, 0, 15))
    # Bark wrapped grip on left end
    Entity(parent=stick_pivot, model='cube', color=color.rgb(80/255, 45/255, 20/255),
           scale=(0.20, 0.068, 0.068), position=(-0.36, 0, 0))

    return {
        'root': root,
        'weapon_arm': stick_pivot,    # drives stick attack swing
        'left_arm': head,             # head pivot
        'leg_l': leg_fl,              # front left
        'leg_r': leg_fr,              # front right
        'leg_bl': leg_bl,             # back left
        'leg_br': leg_br,             # back right
        'tail': tail_pivot,           # wagging tail
        'body': body,
        'weapon': stick,
    }


# =============================================================================
# COMBAT FX: FORTNITE-STYLE DAMAGE NUMBERS
# =============================================================================

def spawn_damage_number(target_pos, amount, is_crit=False):
    """Fortnite-style Pop-up Damage Numbers (Yellow for regular, Red with ! for Crits)."""
    txt_str = f"{int(amount)}!" if is_crit else f"{int(amount)}"
    txt_col = color.rgb(255/255, 40/255, 40/255) if is_crit else color.rgb(255/255, 220/255, 30/255)
    base_scale = 2.4 if is_crit else 1.6

    offset = Vec3(random.uniform(-0.35, 0.35), 2.2 + random.uniform(0.0, 0.35), random.uniform(-0.35, 0.35))
    dmg_txt = Text(
        text=txt_str,
        position=target_pos + offset,
        color=txt_col,
        scale=base_scale,
        billboard=True,
        origin=(0, 0)
    )
    dmg_txt.animate_scale(base_scale * 1.35, duration=0.10, curve=curve.out_back)
    dmg_txt.animate_position(dmg_txt.position + Vec3(random.uniform(-0.25, 0.25), 0.95, 0), duration=0.45, curve=curve.out_quad)
    dmg_txt.fade_out(duration=0.35, delay=0.14)
    destroy(dmg_txt, delay=0.50)


# =============================================================================
# ENEMY BOT CLASS (Puss Bots)
# =============================================================================

class PussBot:
    def __init__(self, position, training_dummy=False):
        self.data       = build_puss(is_enemy=True)
        self.root       = self.data['root']
        self.weapon_arm = self.data['weapon_arm']
        self.leg_l      = self.data['leg_l']
        self.leg_r      = self.data['leg_r']
        self.root.position = position

        self.hp         = 100.0
        self.max_hp     = 100.0
        self.speed      = 5.6           # Increased bot speed for faster, dynamic battle
        self.attack_range = 2.4
        self.attack_cooldown = 1.3
        self.cooldown_timer = random.uniform(0.2, 0.8)
        self.is_attacking = False
        self.walk_time  = random.uniform(0.0, 3.0)
        self.is_dead    = False
        self.training_dummy = training_dummy

        # Floating 3D Health Bar
        self.hp_bar_bg = Entity(parent=self.root, model='cube', color=color.black,
                                scale=(1.2, 0.12, 0.04), position=(0, 2.5, 0), billboard=True)
        self.hp_bar_fill = Entity(parent=self.hp_bar_bg, model='cube', color=color.red,
                                  scale=(0.96, 0.7, 1.0), position=(0, 0, -0.05))

    def update_ai(self, dt, target_pos):
        if self.is_dead or not self.root or self.training_dummy:
            return

        # Fall-off platform detection for bots!
        bot_on_platform = (abs(self.root.x) <= PLATFORM_HALF and abs(self.root.z) <= PLATFORM_HALF)
        if not bot_on_platform or self.root.y < -0.2:
            self.root.y -= GRAVITY * 0.9 * dt
            if self.root.y < -20.0:
                self.die()
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

            self.walk_time += dt * 13.0
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

        if self.weapon_arm and self.root:
            self.weapon_arm.animate_rotation(Vec3(-35, -20, 10), duration=0.1, curve=curve.linear)
            self.weapon_arm.animate_position(Vec3(self.weapon_arm.x, self.weapon_arm.y, 0.35), duration=0.1)

        invoke(self.hit_check, delay=0.12)
        invoke(self.reset_attack, delay=0.25)

    def reset_attack(self):
        if self.weapon_arm and not self.is_dead and self.root:
            self.weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            self.weapon_arm.animate_position(Vec3(self.weapon_arm.x, self.weapon_arm.y, 0.0), duration=0.12)
        self.is_attacking = False

    def hit_check(self):
        global player_hp
        if self.is_dead or not self.root or player is None or game_state != 'playing':
            return

        diff = player.position - self.root.position
        diff.y = 0
        if diff.length() <= (self.attack_range + 0.6):
            apply_damage_to_player(5.0)

    def take_damage(self, amount, is_crit=False):
        if self.is_dead or not self.root:
            return
        if self.training_dummy:
            for child in self.root.children:
                if hasattr(child, 'color'):
                    child.blink(color.yellow, duration=0.12)
            return
        self.hp -= amount

        # Flash red on hit
        for child in self.root.children:
            if hasattr(child, 'color'):
                child.blink(color.red, duration=0.12)

        pct = max(0.0, self.hp / self.max_hp)
        if hasattr(self, 'hp_bar_fill') and self.hp_bar_fill:
            self.hp_bar_fill.scale_x = max(0.01, pct * 0.96)
            self.hp_bar_fill.x = -(1.0 - pct) * 0.48

        # Fortnite-style Pop-up Damage Numbers (Yellow for regular, Red with ! for Crits)
        spawn_damage_number(self.root.position, amount, is_crit=is_crit)

        if self.hp <= 0:
            self.die()

    def die(self):
        global kills_count
        self.is_dead = True
        kills_count += 1
        update_hud()

        if self.root:
            self.root.animate_scale(Vec3(0.01, 0.01, 0.01), duration=0.3, curve=curve.linear)
            destroy(self.root, delay=0.35)


def spawn_bot():
    """Spawn a Puss Bot at a safe perimeter around player strictly within platform bounds at ground height y=0."""
    if player is None:
        return
    for _ in range(12):
        angle = random.uniform(0, math.pi * 2)
        dist  = random.uniform(14.0, 22.0)
        spawn_pos = Vec3(player.position.x + math.cos(angle) * dist, 0.0, player.position.z + math.sin(angle) * dist)
        if abs(spawn_pos.x) < (PLATFORM_HALF - 5.0) and abs(spawn_pos.z) < (PLATFORM_HALF - 5.0):
            bot = PussBot(spawn_pos)
            active_bots.append(bot)
            return
    rx = random.uniform(-PLATFORM_HALF + 8.0, PLATFORM_HALF - 8.0)
    rz = random.uniform(-PLATFORM_HALF + 8.0, PLATFORM_HALF - 8.0)
    bot = PussBot(Vec3(rx, 0.0, rz))
    active_bots.append(bot)


# =============================================================================
# MAIN MENU & MULTIPLAYER
# =============================================================================

def clear_menu_ui():
    global menu_status_text, join_address_label
    for elem in menu_ui:
        deep_destroy(elem)
    menu_ui.clear()
    menu_status_text = None
    join_address_label = None


def _begin_menu_page(title, subtitle):
    global menu_camera_pivot
    clear_menu_ui()
    camera.parent = scene
    if menu_camera_pivot:
        deep_destroy(menu_camera_pivot)
    menu_camera_pivot = Entity(position=(0, 0, 0))
    camera.clip_plane_far = 200
    camera.fov = 55
    camera.parent = menu_camera_pivot
    camera.position = (0, 56, -100)
    camera.rotation = (math.degrees(math.atan2(56, 100)), 0, 0)
    mouse.locked = False
    mouse.visible = True
    title_text = Text(
        parent=camera.ui, text=title, origin=(0, 0), scale=2.3,
        position=(0, 0.34), color=color.rgb(255/255, 205/255, 75/255),
    )
    subtitle_text = Text(
        parent=camera.ui, text=subtitle, origin=(0, 0), scale=0.95,
        position=(0, 0.27), color=color.rgb(220/255, 220/255, 230/255),
    )
    menu_ui.extend([title_text, subtitle_text])


def _menu_button(label, y_pos, callback, fill=None):
    btn = Button(
        parent=camera.ui, text=label,
        color=fill or color.rgb(105/255, 35/255, 38/255),
        highlight_color=color.rgb(190/255, 75/255, 55/255),
        text_color=color.white, scale=(0.34, 0.075), position=(0, y_pos),
        text_size=1.1,
    )
    btn.on_click = callback
    menu_ui.append(btn)
    return btn


def show_main_menu():
    global game_state
    game_state = 'main_menu'
    _clear_cheat_panel()
    _begin_menu_page('PUSS IN BOOTS', '3D BATTLE ARENA')
    _menu_button('PLAY', 0.10, show_play_menu, color.rgb(125/255, 42/255, 38/255))
    _menu_button('SETTINGS', -0.01, show_settings_menu, color.rgb(55/255, 72/255, 100/255))
    _menu_button('QUIT', -0.12, application.quit, color.rgb(75/255, 35/255, 40/255))
    secret_button = Button(
        parent=camera.ui, text='', color=color.rgb(0/255, 70/255, 25/255),
        highlight_color=color.rgb(0/255, 90/255, 30/255),
        scale=(0.045, 0.045), position=(0.82, -0.44),
    )
    secret_button.on_click = show_cheat_panel
    menu_ui.append(secret_button)


def show_play_menu():
    global game_state
    game_state = 'play_menu'
    _begin_menu_page('PLAY', 'Choose how you want to play')
    _menu_button('SINGLEPLAYER', 0.10, show_singleplayer_menu)
    _menu_button('MULTIPLAYER', -0.02, show_multiplayer_menu, color.rgb(45/255, 85/255, 115/255))
    _menu_button('BACK', -0.17, show_main_menu, color.rgb(55/255, 55/255, 65/255))


def show_singleplayer_menu():
    global game_state
    game_state = 'singleplayer_menu'
    _begin_menu_page('SINGLEPLAYER', 'Choose a game mode')
    _menu_button('TRAINING GROUNDS', 0.10, lambda: begin_character_selection('training'))
    _menu_button('PVE - FIGHT ENEMIES', -0.02, lambda: begin_character_selection('pve'))
    _menu_button('BACK', -0.17, show_play_menu, color.rgb(55/255, 55/255, 65/255))


def show_multiplayer_menu():
    global game_state
    game_state = 'multiplayer_menu'
    _begin_menu_page('MULTIPLAYER', 'Play over a local network (TCP port 50007)')
    _menu_button('HOST GAME', 0.10, show_host_menu)
    _menu_button('JOIN GAME', -0.02, show_join_menu, color.rgb(45/255, 85/255, 115/255))
    _menu_button('BACK', -0.17, show_play_menu, color.rgb(55/255, 55/255, 65/255))


def show_settings_menu():
    global game_state, control_capture_action, control_button_refs
    game_state = 'settings_menu'
    control_capture_action = None
    control_button_refs = {}
    _begin_menu_page('SETTINGS', 'Adjust mouse look and review controls')
    sensitivity_text = Text(
        parent=camera.ui, text='', origin=(0, 0), scale=1.0,
        position=(0, 0.12), color=color.white,
    )
    menu_ui.append(sensitivity_text)

    def refresh_sensitivity():
        sensitivity_text.text = f'Mouse sensitivity: {mouse_sensitivity}'

    def adjust_sensitivity(amount):
        global mouse_sensitivity
        mouse_sensitivity = clamp(mouse_sensitivity + amount, 10, 100)
        refresh_sensitivity()

    lower = _menu_button('-', -0.01, lambda: adjust_sensitivity(-5), color.rgb(55/255, 72/255, 100/255))
    higher = _menu_button('+', -0.01, lambda: adjust_sensitivity(5), color.rgb(55/255, 72/255, 100/255))
    lower.x = -0.12
    higher.x = 0.12
    lower.scale = (0.12, 0.07)
    higher.scale = (0.12, 0.07)
    controls_hint = Text(
        parent=camera.ui, text='Click a binding, press a key (Esc cancels). Resets when game closes.',
        origin=(0, 0), scale=0.7, position=(0, -0.075),
        color=color.rgb(210/255, 210/255, 220/255),
    )
    menu_ui.append(controls_hint)
    control_rows = (
        ('forward', 'Move forward'), ('backward', 'Move backward'),
        ('left', 'Move left'), ('right', 'Move right'),
        ('sprint', 'Sprint'), ('jump', 'Jump'), ('attack', 'Attack'),
        ('block', 'Block'), ('dash', 'Dash'),
        ('ability', 'Whistle (Death)'),
        ('ult', 'Ring of Fire Ult (Death)'),
    )
    for index, (action, label) in enumerate(control_rows):
        y_pos = -0.12 - index * 0.040
        action_label = Text(
            parent=camera.ui, text=label, origin=(-0.5, 0), scale=0.58,
            position=(-0.29, y_pos), color=color.white,
        )
        menu_ui.append(action_label)
        binding_btn = Button(
            parent=camera.ui, text='', color=color.rgb(55/255, 72/255, 100/255),
            highlight_color=color.rgb(90/255, 115/255, 150/255),
            text_color=color.white, scale=(0.22, 0.035), position=(0.24, y_pos),
            text_size=0.70,
        )
        binding_btn.on_click = lambda action=action: _begin_control_remap(action)
        control_button_refs[action] = binding_btn
        menu_ui.append(binding_btn)
    _refresh_control_buttons()
    refresh_sensitivity()
    back_button = _menu_button('BACK', 0.43, show_main_menu, color.rgb(55/255, 55/255, 65/255))
    back_button.x = 0.79
    back_button.scale = (0.18, 0.06)


def _format_control_binding(binding):
    return {
        'left mouse down': 'Mouse 1',
        'right mouse down': 'Mouse 2',
        'left control': 'Left Ctrl',
        'right control': 'Right Ctrl',
        'left shift': 'Left Shift',
        'right shift': 'Right Shift',
    }.get(binding, binding.upper())


def _refresh_control_buttons():
    for action, button in control_button_refs.items():
        if action == control_capture_action:
            button.text = 'PRESS A KEY...'
        else:
            button.text = _format_control_binding(controls[action])


def _begin_control_remap(action):
    global control_capture_action
    control_capture_action = action
    _refresh_control_buttons()


def _finish_control_remap(key):
    global control_capture_action
    if key == 'escape':
        control_capture_action = None
        _refresh_control_buttons()
        return
    if key.endswith(' up'):
        return
    binding = key.lower()
    if binding in controls.values():
        other_action = next(
            (action for action, value in controls.items()
             if value == binding and action != control_capture_action),
            None,
        )
        if other_action:
            controls[other_action] = controls[control_capture_action]
    controls[control_capture_action] = binding
    control_capture_action = None
    _refresh_control_buttons()


def _clear_cheat_panel():
    global cheat_panel_open, cheat_panel_input_entity, cheat_panel_status_entity
    global cheat_panel_submit_callback, cheat_input_focused
    was_open = cheat_panel_open
    for elem in cheat_panel_ui:
        deep_destroy(elem)
    cheat_panel_ui.clear()
    cheat_panel_open = False
    cheat_panel_input_entity = None
    cheat_panel_status_entity = None
    cheat_panel_submit_callback = None
    cheat_input_focused = False
    if was_open:
        show_main_menu()


def show_cheat_panel():
    global cheat_panel_open, cheat_code_input, cheat_panel_status
    global cheat_panel_input_entity, cheat_panel_status_entity
    global cheat_panel_submit_callback, cheat_input_focused
    if cheat_panel_open or game_state != 'main_menu':
        return
    cheat_panel_open = True
    clear_menu_ui()
    cheat_code_input = ''
    cheat_input_focused = False
    cheat_panel_status = 'Cheats apply to your next match.'

    backdrop = Entity(
        parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 190/255),
        scale=(2, 2), z=0.08,
    )
    panel = Entity(
        parent=camera.ui, model='quad',
        color=color.rgb(20/255, 24/255, 32/255),
        scale=(0.62, 0.46), position=(0, 0), z=0.07,
    )
    title = Text(
        parent=camera.ui, text='ADMIN PANEL', origin=(0, 0), scale=1.5,
        position=(0, 0.14), color=color.rgb(255/255, 205/255, 75/255), z=-0.1,
    )
    entry_hint = Text(
        parent=camera.ui, text='Enter access code', origin=(0, 0), scale=0.72,
        position=(0, 0.055), color=color.rgb(190/255, 195/255, 205/255), z=-0.1,
    )
    input_box = Button(
        parent=camera.ui, text='', color=color.rgb(45/255, 52/255, 65/255),
        highlight_color=color.rgb(60/255, 70/255, 88/255),
        text_color=color.white,
        scale=(0.48, 0.075), position=(0, -0.025), z=0.06,
    )
    input_box.on_click = focus_cheat_input
    input_text = Text(
        parent=camera.ui, text='', origin=(-0.5, 0), scale=0.85,
        position=(-0.22, -0.025), color=color.white, z=-0.1,
    )
    status_text = Text(
        parent=camera.ui, text=cheat_panel_status, origin=(0, 0), scale=0.68,
        position=(0, -0.105), color=color.rgb(130/255, 220/255, 150/255), z=-0.1,
    )
    cheat_panel_input_entity = input_text
    cheat_panel_status_entity = status_text

    def submit_cheat():
        global cheat_panel_status
        code = cheat_code_input.strip().lower()
        cheat_names = {
            'fearmeifudare': 'damage',
            'seehastalamurite': 'ultimate',
            'overrideactivatedsonicspeed': 'speed',
            'immoratility': 'immortal',
        }
        effect = cheat_names.get(code)
        if not effect:
            cheat_panel_status = 'Unknown cheat code.'
            status_text.color = color.rgb(255/255, 120/255, 100/255)
        elif effect == 'ultimate':
            pending_cheats.add(effect)
            cheat_panel_status = 'Saved for the future ultimate ability.'
        else:
            pending_cheats.add(effect)
            cheat_panel_status = 'Cheat activated for your next match.'
        input_text.text = ''
        status_text.text = cheat_panel_status
        cheat_panel_status_entity.color = (
            color.rgb(255/255, 120/255, 100/255)
            if not effect else color.rgb(130/255, 220/255, 150/255)
        )

    cheat_code_input = ''

    submit_button = Button(
        parent=camera.ui, text='ACTIVATE', color=color.rgb(115/255, 45/255, 40/255),
        highlight_color=color.rgb(175/255, 70/255, 55/255),
        text_color=color.white, scale=(0.19, 0.065), position=(-0.13, -0.19), z=0.05,
    )
    submit_button.on_click = submit_cheat
    cheat_panel_submit_callback = submit_cheat
    close_button = Button(
        parent=camera.ui, text='CLOSE', color=color.rgb(55/255, 65/255, 80/255),
        highlight_color=color.rgb(85/255, 100/255, 125/255),
        text_color=color.white, scale=(0.19, 0.065), position=(0.13, -0.19), z=0.05,
    )
    close_button.on_click = _clear_cheat_panel
    cheat_panel_ui.extend([
        backdrop, panel, title, entry_hint, input_box, input_text, status_text,
        submit_button, close_button,
    ])
    input_text.text = cheat_code_input + '_'


def focus_cheat_input():
    global cheat_input_focused
    cheat_input_focused = True
    if cheat_panel_input_entity:
        cheat_panel_input_entity.text = cheat_code_input + '_'


def show_host_menu():
    global game_state, menu_status_text, host_start_button
    game_state = 'host_menu'
    _begin_menu_page('HOST GAME', 'Host a game for another player on your network')
    menu_status_text = Text(
        parent=camera.ui, text='Select Start Hosting to open a game on port 50007.',
        origin=(0, 0), scale=0.8, position=(0, 0.12), color=color.white,
    )
    menu_ui.append(menu_status_text)
    host_start_button = _menu_button('START HOSTING', -0.01, start_host_session)
    _menu_button('BACK', -0.17, leave_host_menu, color.rgb(55/255, 55/255, 65/255))


def show_join_menu():
    global game_state, menu_status_text, join_address_label, menu_join_address
    game_state = 'join_menu'
    _begin_menu_page('JOIN GAME', 'Enter the host computer IP address, then press Join')
    join_address_label = Text(
        parent=camera.ui, text='', origin=(0, 0), scale=1.05,
        position=(0, 0.12), color=color.rgb(255/255, 220/255, 120/255),
    )
    menu_ui.append(join_address_label)
    menu_status_text = Text(
        parent=camera.ui, text='For internet play, the host may need port forwarding.',
        origin=(0, 0), scale=0.72, position=(0, 0.055), color=color.white,
    )
    menu_ui.append(menu_status_text)
    _menu_button('JOIN', -0.04, connect_to_host, color.rgb(45/255, 85/255, 115/255))
    _menu_button('BACK', -0.17, leave_join_menu, color.rgb(55/255, 55/255, 65/255))
    _refresh_join_address()


def leave_host_menu():
    stop_network_session()
    show_multiplayer_menu()


def leave_join_menu():
    stop_network_session()
    show_multiplayer_menu()


def _refresh_join_address():
    if join_address_label:
        join_address_label.text = f'Host IP: {menu_join_address}_'


def begin_character_selection(mode):
    global game_mode, game_state
    game_mode = mode
    clear_menu_ui()
    game_state = 'selection'
    setup_selection_menu()


def _local_ip_address():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(('8.8.8.8', 80))
        return probe.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        probe.close()


def stop_network_session():
    global network_server_socket, network_connection_socket
    global network_role, network_connected, network_remote_snapshot
    global network_attack_sequence, remote_attack_sequence, network_generation
    network_running.clear()
    network_generation += 1
    for active_socket in (network_connection_socket, network_server_socket):
        if active_socket:
            try:
                active_socket.close()
            except OSError:
                pass
    network_connection_socket = None
    network_server_socket = None
    network_role = None
    network_connected = False
    network_remote_snapshot = None
    network_attack_sequence = 0
    remote_attack_sequence = 0
    while True:
        try:
            network_events.get_nowait()
        except queue.Empty:
            break


def start_host_session():
    global network_server_socket, network_role, game_mode, menu_status_text
    stop_network_session()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', NETWORK_PORT))
        server.listen(1)
        server.settimeout(0.5)
    except OSError as error:
        server.close()
        if menu_status_text:
            menu_status_text.text = f'Could not host: {error}'
        return

    network_server_socket = server
    network_role = 'host'
    game_mode = 'multiplayer'
    network_running.set()
    generation = network_generation
    threading.Thread(
        target=_host_network_worker, args=(server, generation), daemon=True,
    ).start()
    if menu_status_text:
        menu_status_text.text = (
            f'Share {_local_ip_address()}:{NETWORK_PORT} with your friend.\n'
            'Choose character to enter the arena.'
        )
    if host_start_button:
        host_start_button.text = 'CHOOSE CHARACTER'
        host_start_button.on_click = lambda: begin_character_selection('multiplayer')


def connect_to_host():
    global network_role, game_mode, menu_status_text
    address = menu_join_address.strip()
    if not address or any(char.isspace() for char in address):
        if menu_status_text:
            menu_status_text.text = 'Enter a valid host IP address.'
        return
    stop_network_session()
    network_role = 'client'
    game_mode = 'multiplayer'
    network_running.set()
    generation = network_generation
    if menu_status_text:
        menu_status_text.text = f'Connecting to {address}:{NETWORK_PORT}...'
    threading.Thread(
        target=_client_network_worker, args=(address, generation), daemon=True,
    ).start()


def _network_session_active(generation):
    return network_running.is_set() and generation == network_generation


def _host_network_worker(server, generation):
    global network_connection_socket
    while _network_session_active(generation):
        try:
            connection, address = server.accept()
        except socket.timeout:
            continue
        except OSError as error:
            if _network_session_active(generation):
                network_events.put(('error', str(error)))
            return
        if not _network_session_active(generation):
            connection.close()
            return
        network_connection_socket = connection
        network_events.put(('connected', address[0]))
        _network_exchange(connection, generation)


def _client_network_worker(address, generation):
    try:
        connection = socket.create_connection((address, NETWORK_PORT), timeout=5.0)
    except OSError as error:
        if _network_session_active(generation):
            network_events.put(('error', str(error)))
        return
    if not _network_session_active(generation):
        connection.close()
        return
    network_events.put(('connected', address))
    _network_exchange(connection, generation)


def _network_exchange(connection, generation):
    global network_connection_socket
    buffer = ''
    last_send = 0.0
    network_connection_socket = connection
    try:
        connection.settimeout(0.02)
        while _network_session_active(generation):
            now = system_time.monotonic()
            if now - last_send >= 0.05:
                with network_snapshot_lock:
                    snapshot = network_local_snapshot.copy()
                connection.sendall((json.dumps(snapshot) + '\n').encode('utf-8'))
                last_send = now
            try:
                chunk = connection.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                break
            buffer += chunk.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                packet = json.loads(line)
                required = ('x', 'y', 'z', 'yaw', 'attack_seq')
                if (
                    not isinstance(packet, dict)
                    or any(type(packet.get(key)) not in (int, float) for key in required[:4])
                    or type(packet.get('attack_seq')) is not int
                    or not all(math.isfinite(packet[key]) for key in required[:4])
                ):
                    if _network_session_active(generation):
                        network_events.put(('error', 'Received an invalid player update.'))
                    return
                if not _network_session_active(generation):
                    return
                network_events.put(('snapshot', packet))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        if _network_session_active(generation):
            network_events.put(('error', str(error)))
    finally:
        connection.close()
        if network_connection_socket is connection:
            network_connection_socket = None
        if _network_session_active(generation):
            network_events.put(('disconnected', 'The other player disconnected.'))


def process_network_events():
    global network_connected, network_remote_snapshot, network_status_label
    global remote_player, remote_attack_sequence
    while True:
        try:
            event, payload = network_events.get_nowait()
        except queue.Empty:
            break
        if event == 'connected':
            network_connected = True
            if game_state == 'join_menu':
                begin_character_selection('multiplayer')
            elif game_state == 'playing':
                _create_remote_player(network_remote_snapshot.get('char', 'puss') if network_remote_snapshot else 'puss')
            if menu_status_text:
                menu_status_text.text = f'Connected to {payload}.'
            if network_status_label:
                network_status_label.text = 'PLAYER CONNECTED'
        elif event == 'snapshot':
            network_remote_snapshot = payload
            if payload['attack_seq'] != remote_attack_sequence:
                remote_attack_sequence = payload['attack_seq']
                trigger_remote_player_attack()
                _check_remote_attack(payload)
        elif event == 'disconnected':
            network_connected = False
            network_remote_snapshot = None
            if remote_player:
                deep_destroy(remote_player)
                remote_player = None
            remote_player_data = None
            remote_player_char = None
            remote_hp_bar_fill = None
            remote_name_tag = None
            if menu_status_text:
                menu_status_text.text = payload
            if network_status_label:
                network_status_label.text = 'PLAYER DISCONNECTED'
        elif event == 'error':
            if menu_status_text:
                menu_status_text.text = f'Network error: {payload}'
            if network_status_label:
                network_status_label.text = f'NETWORK ERROR: {payload}'


def _create_remote_player(char_key='puss'):
    global remote_player, remote_player_data, remote_player_char
    global remote_player_walk_time, remote_hp_bar_fill, remote_name_tag

    if not network_connected or game_state != 'playing':
        return

    # If already built with this character, keep it
    if remote_player and remote_player_char == char_key:
        return

    # Destroy previous remote model if character changed
    if remote_player:
        deep_destroy(remote_player)
        remote_player = None
        remote_player_data = None
        remote_hp_bar_fill = None
        remote_name_tag = None

    builders = {'puss': build_puss, 'kitty': build_kitty, 'death': build_death, 'perrito': build_perrito}
    builder = builders.get(char_key, build_puss)
    if char_key == 'puss':
        data = builder(is_enemy=True)
    else:
        data = builder()

    remote_player_data = data
    remote_player = data['root']
    remote_player_char = char_key
    remote_player_walk_time = 0.0

    # PROPER SCALE: Do NOT shrink to 0.72! Set natural full scale 1.0!
    if char_key == 'perrito':
        remote_player.scale = Vec3(0.95, 0.95, 0.95)
    else:
        remote_player.scale = Vec3(1.0, 1.0, 1.0)

    # 3D Overhead Floating Health Bar & Name Tag
    char_display_names = {
        'puss': 'PUSS (P2)',
        'kitty': 'KITTY (P2)',
        'death': 'DEATH (P2)',
        'perrito': 'PERRITO (P2)',
    }
    y_bar = 2.8 if char_key == 'death' else (1.4 if char_key == 'perrito' else 2.3)
    hp_bg = Entity(parent=remote_player, model='cube', color=color.black,
                   scale=(1.2, 0.12, 0.04), position=(0, y_bar, 0), billboard=True)
    remote_hp_bar_fill = Entity(parent=hp_bg, model='cube', color=color.cyan,
                                scale=(0.96, 0.7, 1.0), position=(0, 0, -0.05))
    remote_name_tag = Text(
        parent=remote_player,
        text=char_display_names.get(char_key, 'PLAYER 2'),
        position=(0, y_bar + 0.22, 0),
        origin=(0, 0),
        scale=1.2,
        color=color.rgb(255/255, 215/255, 60/255),
        billboard=True,
    )

    if network_remote_snapshot:
        _apply_remote_snapshot(1.0)


def trigger_remote_player_attack():
    """Animate attack weapon swings on the remote player character."""
    if not remote_player or not remote_player_data:
        return
    remote_player._is_animating_attack = True
    arm_l = remote_player_data.get('left_arm')
    arm_r = remote_player_data.get('weapon_arm')

    if remote_player_char == 'death':
        if arm_l:
            arm_l.animate_rotation(Vec3(-35, 30, -20), duration=0.09, curve=curve.linear)
            arm_l.animate_position(Vec3(-0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
        if arm_r:
            arm_r.animate_rotation(Vec3(-35, -30, 20), duration=0.09, curve=curve.linear)
            arm_r.animate_position(Vec3(0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
    elif remote_player_char == 'perrito':
        if arm_r:
            arm_r.animate_rotation(Vec3(0, -60, 12), duration=0.07, curve=curve.linear)
        if arm_l:
            arm_l.animate_rotation(Vec3(4, -40, 8), duration=0.07, curve=curve.linear)
    else:
        if arm_r:
            arm_r.animate_rotation(Vec3(-25, -20, 10), duration=0.09, curve=curve.linear)
            arm_r.animate_position(Vec3(arm_r.x, arm_r.y, 0.35), duration=0.09, curve=curve.linear)

    def _reset_remote_attack():
        if not remote_player or not remote_player_data:
            return
        al = remote_player_data.get('left_arm')
        ar = remote_player_data.get('weapon_arm')
        if remote_player_char == 'death':
            if al:
                al.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
                al.animate_position(Vec3(-0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
            if ar:
                ar.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
                ar.animate_position(Vec3(0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
        elif remote_player_char == 'perrito':
            if ar: ar.animate_rotation(Vec3(0, 0, 0), duration=0.10, curve=curve.linear)
            if al: al.animate_rotation(Vec3(0, 0, 0), duration=0.10, curve=curve.linear)
        else:
            if ar:
                ar.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
                ar.animate_position(Vec3(ar.x, ar.y, 0.0), duration=0.12, curve=curve.linear)
        remote_player._is_animating_attack = False

    invoke(_reset_remote_attack, delay=0.18)


def _apply_remote_snapshot(dt):
    global remote_player, remote_player_data, remote_player_char
    global remote_player_walk_time, remote_hp_bar_fill

    if not remote_player or not network_remote_snapshot:
        return

    snapshot = network_remote_snapshot

    # Check if remote player changed their character
    snap_char = snapshot.get('char')
    if snap_char and snap_char in ('puss', 'kitty', 'death', 'perrito') and snap_char != remote_player_char:
        _create_remote_player(snap_char)
        return

    # Position & Rotation interpolation
    target = Vec3(snapshot['x'], snapshot['y'], snapshot['z'])
    dist_moved = (target - remote_player.position).length()
    remote_player.position = lerp(remote_player.position, target, min(1.0, dt * 14.0))
    angle_diff = (snapshot['yaw'] - remote_player.rotation_y + 180) % 360 - 180
    remote_player.rotation_y += angle_diff * min(1.0, 14.0 * dt)

    # Health bar update
    if remote_hp_bar_fill and 'hp' in snapshot:
        pct = clamp(snapshot['hp'] / 100.0, 0.0, 1.0)
        remote_hp_bar_fill.scale_x = max(0.01, pct * 0.96)
        remote_hp_bar_fill.x = -(1.0 - pct) * 0.48

    # Movement and Walk Animations
    is_moving = snapshot.get('moving', dist_moved > 0.02)
    is_sprint = snapshot.get('sprinting', False)
    is_blocking = snapshot.get('blocking', False)

    if remote_player_data:
        leg_l = remote_player_data.get('leg_l')
        leg_r = remote_player_data.get('leg_r')
        leg_bl = remote_player_data.get('leg_bl')
        leg_br = remote_player_data.get('leg_br')
        tail = remote_player_data.get('tail')
        arm_l = remote_player_data.get('left_arm')
        arm_r = remote_player_data.get('weapon_arm')

        if is_moving:
            anim_speed = 22.0 if is_sprint else 13.0
            swing_amp = 36.0 if is_sprint else 22.0
            remote_player_walk_time += dt * anim_speed

            if remote_player_char == 'perrito':
                if leg_l: leg_l.rotation_x = math.sin(remote_player_walk_time) * swing_amp
                if leg_br: leg_br.rotation_x = math.sin(remote_player_walk_time) * swing_amp
                if leg_r: leg_r.rotation_x = -math.sin(remote_player_walk_time) * swing_amp
                if leg_bl: leg_bl.rotation_x = -math.sin(remote_player_walk_time) * swing_amp
                if tail: tail.rotation_y = math.sin(remote_player_walk_time * 2.2) * 35.0
            else:
                if leg_l: leg_l.rotation_x = math.sin(remote_player_walk_time) * swing_amp
                if leg_r: leg_r.rotation_x = -math.sin(remote_player_walk_time) * swing_amp
                if not getattr(remote_player, '_is_animating_attack', False) and not is_blocking:
                    if arm_l: arm_l.rotation_x = math.sin(remote_player_walk_time) * 14.0
                    if arm_r: arm_r.rotation_x = -math.sin(remote_player_walk_time) * 14.0
        else:
            if leg_l: leg_l.rotation_x = lerp(leg_l.rotation_x, 0, dt * 10)
            if leg_r: leg_r.rotation_x = lerp(leg_r.rotation_x, 0, dt * 10)
            if leg_bl: leg_bl.rotation_x = lerp(leg_bl.rotation_x, 0, dt * 10)
            if leg_br: leg_br.rotation_x = lerp(leg_br.rotation_x, 0, dt * 10)
            if not getattr(remote_player, '_is_animating_attack', False) and not is_blocking:
                if arm_l: arm_l.rotation = Vec3(0, 0, 0)
                if arm_r: arm_r.rotation = Vec3(0, 0, 0)

        # Defense / Block stance
        if is_blocking:
            if remote_player_char == 'death':
                if arm_l: arm_l.rotation = Vec3(25, 45, -20)
                if arm_r: arm_r.rotation = Vec3(25, -45, 20)
            elif remote_player_char == 'perrito':
                if arm_r: arm_r.rotation = Vec3(10, -45, 30)
            else:
                if arm_r: arm_r.rotation = Vec3(25, -45, 20)


def _check_remote_attack(snapshot):
    if not player or game_state != 'playing' or is_paused:
        return
    remote_pos = Vec3(snapshot['x'], snapshot['y'], snapshot['z'])
    direction = Vec3(
        math.sin(math.radians(snapshot['yaw'])), 0,
        math.cos(math.radians(snapshot['yaw'])),
    )
    offset = player.position - remote_pos
    offset.y = 0
    r_char = snapshot.get('char', 'puss')
    hit_range = 4.2 if r_char == 'death' else (3.3 if r_char == 'perrito' else 2.8)
    if offset.length() <= hit_range and offset.length() > 0.01:
        if direction.dot(offset.normalized()) > 0.15:
            base_dmg = 15.0 if r_char == 'death' else (7.0 if r_char == 'perrito' else 5.0)
            apply_damage_to_player(base_dmg)
            spawn_damage_number(player.position, base_dmg, is_crit=False)


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
    global game_state, menu_camera_pivot, preview_model

    for elem in list(selection_ui):
        deep_destroy(elem)
    selection_ui.clear()
    card_buttons.clear()
    if preview_model:
        deep_destroy(preview_model)
        preview_model = None
    if preview_pivot:
        deep_destroy(preview_pivot)
        preview_pivot = None

    game_state = 'selection'
    # Set selection camera
    camera.parent = scene
    if menu_camera_pivot:
        deep_destroy(menu_camera_pivot)
        menu_camera_pivot = None
    camera.clip_plane_far = 75.0
    camera.fov = 50
    camera.position = (0, 1.2, -6.0)
    camera.rotation = (0, 0, 0)
    mouse.locked  = False
    mouse.visible = True

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

    # --- Character Cards: 2x2 Modern Grid with Outlines ---
    chars = [
        ('puss',    'Puss in Boots',  -0.095,  0.14, color.rgb(180/255, 90/255, 20/255),   color.rgb(255/255, 165/255, 50/255)),
        ('kitty',   'Kitty Softpaws',  0.095,  0.14, color.rgb(35/255, 45/255, 55/255),    color.rgb(80/255, 200/255, 220/255)),
        ('death',   'Death',          -0.095, -0.02, color.rgb(110/255, 18/255, 22/255),   color.rgb(220/255, 50/255, 60/255)),
        ('perrito', 'Perrito',         0.095, -0.02, color.rgb(35/255, 115/255, 125/255),  color.rgb(65/255, 215/255, 230/255)),
    ]

    for char_key, label_txt, x_pos, y_pos, btn_col, border_col in chars:
        card_border = Entity(parent=camera.ui, model='quad',
                             color=border_col,
                             scale=(0.178, 0.138), position=(x_pos, y_pos), z=0.02)
        card = Button(
            text            = label_txt,
            color           = btn_col,
            highlight_color = color.rgba(border_col[0], border_col[1], border_col[2], 0.7),
            text_color      = color.white,
            scale           = (0.165, 0.125),
            x               = x_pos,
            y               = y_pos,
            z               = 0.0,
            text_size       = 0.95,
        )
        card.on_click = lambda c=char_key: select_preview_character(c)
        selection_ui.extend([card_border, card])
        card_buttons[char_key] = (card_border, card)

    # CHOOSE CHARACTER button (Modern red gradient with border)
    choose_border = Entity(parent=camera.ui, model='quad',
                           color=color.rgb(255/255, 80/255, 80/255),
                           scale=(0.36, 0.088), position=(0.0, -0.22), z=0.02)
    btn_choose = Button(
        text            = "CHOOSE CHARACTER",
        color           = color.rgb(200/255, 30/255, 30/255),
        highlight_color = color.rgb(255/255, 80/255, 80/255),
        text_color      = color.white,
        scale           = (0.345, 0.074),
        position        = (0.0, -0.22),
        z               = 0.0,
        text_size       = 1.15,
    )
    btn_choose.on_click = confirm_and_start_game
    selection_ui.extend([choose_border, btn_choose])

    btn_back = Button(
        text='BACK', color=color.rgb(55/255, 55/255, 65/255),
        highlight_color=color.rgb(90/255, 90/255, 105/255),
        text_color=color.white, scale=(0.20, 0.06),
        position=(0.0, -0.34), text_size=0.9,
    )
    btn_back.on_click = return_from_character_selection
    selection_ui.append(btn_back)

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
    """Switch the 3D rotating preview model and update selection indicators, destroying old shapes cleanly."""
    global preview_model, selected_preview_key

    selected_preview_key = char_key

    # Completely destroy previous 3D preview model shapes
    if preview_model:
        deep_destroy(preview_model)
        preview_model = None

    # Build 3D character on turntable
    builders = {'puss': build_puss, 'kitty': build_kitty, 'death': build_death, 'perrito': build_perrito}
    result = builders[char_key]()
    preview_model = result['root']
    preview_model.parent = preview_pivot
    preview_model.position = Vec3(0, 0, 0)
    if char_key == 'death':
        preview_model.scale = Vec3(0.68, 0.68, 0.68)
    elif char_key == 'perrito':
        preview_model.scale = Vec3(0.85, 0.85, 0.85)
    else:
        preview_model.scale = Vec3(0.72, 0.72, 0.72)

    names = {
        'puss':    'Puss in Boots',
        'kitty':   'Kitty Softpaws',
        'death':   'Death',
        'perrito': 'Perrito',
    }
    name_cols = {
        'puss':    color.orange,
        'kitty':   color.cyan,
        'death':   color.rgb(255/255, 80/255, 80/255),
        'perrito': color.rgb(65/255, 215/255, 230/255),
    }

    if preview_char_name:
        preview_char_name.text  = names[char_key]
        preview_char_name.color = name_cols[char_key]

    if player1_char_text:
        player1_char_text.text  = names[char_key]

    # Highlight active card border
    highlight_cols = {
        'puss':    color.rgb(255/255, 200/255, 80/255),
        'kitty':   color.rgb(80/255, 220/255, 240/255),
        'death':   color.rgb(255/255, 80/255, 80/255),
        'perrito': color.rgb(80/255, 240/255, 255/255),
    }
    dim_col = color.rgb(50/255, 50/255, 60/255)
    for k, (border_ent, btn_ent) in card_buttons.items():
        if k == char_key:
            border_ent.color = highlight_cols[k]
            border_ent.scale = (0.188, 0.148)
            btn_ent.scale    = (0.165, 0.125)
        else:
            border_ent.color = dim_col
            border_ent.scale = (0.178, 0.138)
            btn_ent.scale    = (0.165, 0.125)


def confirm_and_start_game():
    """Triggered when clicking CHOOSE CHARACTER."""
    start_game(selected_preview_key)


def return_from_character_selection():
    global preview_model, preview_pivot
    for elem in selection_ui:
        deep_destroy(elem)
    selection_ui.clear()
    if preview_model:
        deep_destroy(preview_model)
        preview_model = None
    if preview_pivot:
        deep_destroy(preview_pivot)
        preview_pivot = None
    if game_mode == 'multiplayer':
        stop_network_session()
        show_multiplayer_menu()
    else:
        show_singleplayer_menu()


# =============================================================================
# GAME START
# =============================================================================

CAMERA_CONFIG = {
    'puss':    {'pivot_height': 1.05, 'cam_pos': Vec3(0, 0.35, -4.5), 'cam_rot': Vec3(4, 0, 0), 'fov': 50},
    'kitty':   {'pivot_height': 0.90, 'cam_pos': Vec3(0, 0.30, -4.2), 'cam_rot': Vec3(3, 0, 0), 'fov': 50},
    'death':   {'pivot_height': 2.10, 'cam_pos': Vec3(0, 1.00, -8.2), 'cam_rot': Vec3(5, 0, 0), 'fov': 55},
    'perrito': {'pivot_height': 0.65, 'cam_pos': Vec3(0, 0.40, -3.8), 'cam_rot': Vec3(6, 0, 0), 'fov': 52},
}
current_pivot_height = 1.05

# Dynamic Camera Zoom & FOV Scroll State
cam_base_z     = -4.5
cam_base_fov   = 50.0
cam_zoom_delta = 0.0
cam_fov_delta  = 0.0

def start_game(char_key):
    global player, weapon_arm, arm_left, leg_left, leg_right, body_entity, weapon_entity
    global leg_back_l, leg_back_r, tail_entity
    global game_state, selected_char, camera_pivot, current_pivot_height
    global BASE_SPEED, player_damage, player_hp, kills_count, active_bots
    global preview_pivot, preview_model, camera_yaw, camera_pitch
    global training_dummy, network_status_label, remote_player
    global match_cheats
    global easter_egg_progress, easter_egg_active, easter_egg_escape_used
    global easter_egg_mouse_unlocked
    global cam_base_z, cam_base_fov, cam_zoom_delta, cam_fov_delta

    camera_yaw   = 0.0
    camera_pitch = 3.0
    easter_egg_progress = 0
    easter_egg_active = False
    easter_egg_escape_used = False
    easter_egg_mouse_unlocked = False

    selected_char = char_key
    match_cheats = pending_cheats.copy()
    pending_cheats.clear()
    camera.clip_plane_far = 75.0
    cam_cfg = CAMERA_CONFIG.get(char_key, CAMERA_CONFIG['puss'])
    current_pivot_height = cam_cfg['pivot_height']

    # Set Character Stats
    player_hp = 100.0
    kills_count = 0
    if selected_char == 'death':
        BASE_SPEED    = 12.0   # Fast, menacing pace
        player_damage = 15.0   # 15% damage per hit
    elif selected_char == 'perrito':
        BASE_SPEED    = 9.5    # Fast, nimble dog trot
        player_damage = 7.0    # 7% damage per stick strike
    else:
        BASE_SPEED    = 7.0    # Puss / Kitty snappy agile pace
        player_damage = 5.0    # 5% damage per hit

    # Destroy menu UI & preview turntable cleanly (removes all shapes)
    for elem in selection_ui:
        deep_destroy(elem)
    selection_ui.clear()

    if preview_model:
        deep_destroy(preview_model)
        preview_model = None
    if preview_pivot:
        deep_destroy(preview_pivot)
        preview_pivot = None

    # Build ONLY the chosen champion in world (no other character shapes exist!)
    builders = {'puss': build_puss, 'kitty': build_kitty, 'death': build_death, 'perrito': build_perrito}
    result    = builders[char_key]()

    player        = result['root']
    weapon_arm    = result['weapon_arm']
    arm_left      = result['left_arm']
    leg_left      = result['leg_l']
    leg_right     = result['leg_r']
    leg_back_l    = result.get('leg_bl', None)
    leg_back_r    = result.get('leg_br', None)
    tail_entity   = result.get('tail', None)
    body_entity   = result['body']
    weapon_entity = result['weapon']

    if game_mode == 'training':
        player.position = Vec3(0, 0, -8)
    elif game_mode == 'multiplayer':
        player.position = Vec3(0, 0, -6 if network_role == 'host' else 6)
        player.rotation_y = 0 if network_role == 'host' else 180
    else:
        player.position = Vec3(0, 0, 0)

    # Attach TPP Camera with character-specific pivot height, distance, and field of view
    camera_pivot = Entity(position=player.position + Vec3(0, current_pivot_height, 0))
    camera.parent   = camera_pivot
    camera.position = cam_cfg['cam_pos']
    camera.rotation = cam_cfg['cam_rot']
    camera.fov      = cam_cfg.get('fov', 50)
    cam_base_z     = cam_cfg['cam_pos'].z
    cam_base_fov   = float(cam_cfg.get('fov', 50))
    cam_zoom_delta = 0.0
    cam_fov_delta  = 0.0

    teardown_ring_of_fire()

    mouse.locked = True
    game_state = 'playing'

    # Clear any leftover bots and spawn up to MAX_BOTS
    for bot in active_bots:
        deep_destroy(bot.root)
    active_bots.clear()

    training_dummy = None
    if game_mode == 'pve':
        for _ in range(MAX_BOTS):
            spawn_bot()
    elif game_mode == 'training':
        training_dummy = PussBot(Vec3(0, 0, 0), training_dummy=True)
        active_bots.append(training_dummy)

    build_hud()
    if game_mode == 'training':
        network_status_label = Text(
            parent=camera.ui, text='TRAINING DUMMY: IMMORTAL',
            origin=(0, 0), scale=1.0, position=(0, 0.43),
            color=color.rgb(255/255, 220/255, 90/255),
        )
    elif game_mode == 'multiplayer':
        network_status_label = Text(
            parent=camera.ui,
            text='PLAYER CONNECTED' if network_connected else 'WAITING FOR PLAYER',
            origin=(0, 0), scale=0.85, position=(0, 0.43),
            color=color.rgb(130/255, 230/255, 150/255),
        )
        if network_connected:
            _create_remote_player(network_remote_snapshot.get('char', 'puss') if network_remote_snapshot else 'puss')


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
hud_whistle_icon    = None
hud_whistle_cooldown = None
WHISTLE_ICON_SIZE   = 0.15
hud_ult_icon        = None
hud_ult_cooldown    = None
ULT_ICON_SIZE       = 0.16
HUD_FONT = next(
    (font_name for font_name in ('GoogleSansPro-Regular.ttf', 'GoogleSans-Regular.ttf')
     if (current_dir / font_name).is_file()),
    'OpenSans-Regular.ttf',
)
block_indicator     = None
autoblock_banner    = None

def build_hud():
    global hud_char_name, hud_hp_bar_bg, hud_hp_bar_fill, hud_hp_text, hud_dash_text
    global hud_kills_text, hud_special_perk, hud_controls, block_indicator, autoblock_banner
    global hud_whistle_icon, hud_whistle_cooldown, hud_ult_icon, hud_ult_cooldown

    names = {
        'puss':    'Puss in Boots',
        'kitty':   'Kitty Softpaws',
        'death':   'Death (The Wolf)',
        'perrito': 'Perrito (The Therapy Dog)',
    }

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
        text   = f"DASH [{_format_control_binding(controls['dash'])}]: Ready",
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

    # (Perk text banner removed per request)

    hud_controls = Text(
        text   = (
            f"{_format_control_binding(controls['forward'])}/"
            f"{_format_control_binding(controls['backward'])}/"
            f"{_format_control_binding(controls['left'])}/"
            f"{_format_control_binding(controls['right'])}: Move | "
            f"{_format_control_binding(controls['jump'])}: Jump | "
            f"{_format_control_binding(controls['sprint'])}: Sprint | "
            f"{_format_control_binding(controls['dash'])}: Dash | "
            f"{_format_control_binding(controls['block'])}: Block | "
            f"{_format_control_binding(controls['attack'])}: Attack | "
            f"Scroll: Zoom/FOV"
            + (
                f" | {_format_control_binding(controls['ability'])}: Whistle"
                f" | {_format_control_binding(controls.get('ult', 'x'))}: Ring of Fire"
                if selected_char == 'death' else ''
            )
        ),
        origin = (0, -0.5),
        scale  = 0.85,
        y      = -0.47,
        color  = color.rgb(200/255, 200/255, 200/255),
        font   = HUD_FONT,
    )

    if selected_char == 'death':
        # Whistle Icon (E)
        icon_x, icon_y = 0.63, -0.36
        hud_whistle_icon = Entity(
            parent   = camera.ui,
            model    = 'quad',
            texture  = 'whistle.png',
            color    = color.white,
            scale    = (WHISTLE_ICON_SIZE, WHISTLE_ICON_SIZE),
            position = (icon_x, icon_y),
            z        = 0,
        )
        hud_whistle_cooldown = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.black,
            scale    = (WHISTLE_ICON_SIZE, 0.001),
            origin   = (0, 0.5),
            position = (icon_x, icon_y + WHISTLE_ICON_SIZE / 2),
            z        = -0.01,
            visible  = False,
        )
        update_whistle_hud()

        # Ultimate Icon: Ring of Fire (X)
        ult_x, ult_y = 0.80, -0.36
        hud_ult_icon = Entity(
            parent   = camera.ui,
            model    = 'quad',
            texture  = 'ringfire.png',
            color    = color.white,
            scale    = (ULT_ICON_SIZE, ULT_ICON_SIZE),
            position = (ult_x, ult_y),
            z        = 0,
        )
        hud_ult_cooldown = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.black,
            scale    = (ULT_ICON_SIZE, 0.001),
            origin   = (0, 0.5),
            position = (ult_x, ult_y + ULT_ICON_SIZE / 2),
            z        = -0.01,
            visible  = False,
        )
        update_ult_hud()


def activate_easter_egg():
    """Create the radar and cursor effects after the hidden key sequence."""
    global easter_egg_active, easter_egg_map_ui
    global easter_egg_player_marker, easter_egg_bot_markers
    global easter_egg_cursor

    easter_egg_active = True
    radar_border = Entity(
        parent=camera.ui, model='quad',
        color=color.rgb(35/255, 190/255, 210/255),
        scale=(0.35, 0.35), position=(-0.78, 0.69, 0.03),
    )
    radar_panel = Entity(
        parent=camera.ui, model='quad',
        color=color.rgba(8/255, 15/255, 24/255, 225/255),
        scale=(0.34, 0.34), position=(-0.78, 0.69, 0.02),
    )
    arena_field = Entity(
        parent=camera.ui, model='quad',
        color=color.rgba(25/255, 55/255, 58/255, 220/255),
        scale=(0.27, 0.20), position=(-0.78, 0.675, 0.01),
    )
    radar_title = Text(
        parent=camera.ui, text='NUKEYES // RADAR',
        origin=(0, 0), scale=0.72, color=color.cyan,
        position=(-0.78, 0.815, -0.03),
    )
    horizontal_grid = Entity(
        parent=camera.ui, model='quad',
        color=color.rgba(110/255, 160/255, 160/255, 100/255),
        scale=(0.25, 0.002), position=(-0.78, 0.675, 0),
    )
    vertical_grid = Entity(
        parent=camera.ui, model='quad',
        color=color.rgba(110/255, 160/255, 160/255, 100/255),
        scale=(0.002, 0.18), position=(-0.78, 0.675, 0),
    )
    mode_banner = Entity(
        parent=camera.ui, model='quad',
        color=color.rgba(8/255, 15/255, 24/255, 230/255),
        scale=(0.62, 0.13), position=(0, 0.85, 0.03),
    )
    mode_title = Text(
        parent=camera.ui, text='NUKE MODE ACTIVATED',
        origin=(0, 0), scale=1.25, color=color.lime,
        position=(0, 0.87, -0.03),
    )
    mode_instructions = Text(
        parent=camera.ui, text='ESC: UNLOCK MOUSE  |  CLICK: DETONATE',
        origin=(0, 0), scale=0.72, color=color.white,
        position=(0, 0.81, -0.03),
    )
    easter_egg_map_ui = [
        radar_border, radar_panel, arena_field, radar_title,
        horizontal_grid, vertical_grid, mode_banner, mode_title,
        mode_instructions,
    ]

    easter_egg_player_marker = Entity(
        parent=camera.ui, model='circle',
        color=color.lime, scale=(0.022, 0.022), z=-0.02,
    )
    easter_egg_map_ui.append(easter_egg_player_marker)
    easter_egg_bot_markers = []
    for _ in range(MAX_BOTS):
        marker = Entity(
            parent=camera.ui, model='circle',
            color=color.rgb(255/255, 75/255, 55/255),
            scale=(0.016, 0.016), visible=False, z=-0.02,
        )
        easter_egg_bot_markers.append(marker)
        easter_egg_map_ui.append(marker)

    easter_egg_cursor = Entity(
        parent=camera.ui, model='circle',
        color=color.rgba(255/255, 75/255, 35/255, 90/255),
        scale=(0.22, 0.22), position=(0, 0, -0.08), visible=False,
    )
    update_easter_egg_map()


def update_easter_egg_map():
    if not easter_egg_active or not easter_egg_player_marker or not player:
        return

    map_x, map_y = -0.78, 0.675

    def marker_position(world_x, world_z):
        x = map_x + clamp(world_x / PLATFORM_HALF, -1, 1) * 0.12
        y = map_y + clamp(world_z / PLATFORM_HALF, -1, 1) * 0.085
        return (x, y, 0.01)

    easter_egg_player_marker.position = marker_position(player.x, player.z)

    living_bots = [bot for bot in active_bots if not bot.is_dead and bot.root]
    for marker, bot in zip(easter_egg_bot_markers, living_bots):
        marker.position = marker_position(bot.root.x, bot.root.z)
        marker.visible = True

    for marker in easter_egg_bot_markers[len(living_bots):]:
        marker.visible = False


def advance_easter_egg_sequence(key):
    global easter_egg_progress

    if not isinstance(key, str) or easter_egg_active or len(key) != 1 or not key.isalpha():
        return

    key = key.lower()
    if key == EASTER_EGG_SEQUENCE[easter_egg_progress]:
        easter_egg_progress += 1
        if easter_egg_progress == len(EASTER_EGG_SEQUENCE):
            easter_egg_progress = 0
            activate_easter_egg()
    else:
        easter_egg_progress = int(key == EASTER_EGG_SEQUENCE[0])


def trigger_easter_egg_blast():
    """Explode every living bot while leaving the player unharmed."""
    if not easter_egg_active or game_state != 'playing':
        return

    blast_flash = Entity(
        parent=camera.ui, model='circle',
        color=color.rgba(255/255, 85/255, 25/255, 150/255),
        scale=(0.08, 0.08), position=(mouse.position[0], mouse.position[1], -0.08),
    )
    blast_flash.animate_scale((0.42, 0.42), duration=0.22, curve=curve.out_quad)
    blast_flash.fade_out(duration=0.22)
    destroy(blast_flash, delay=0.24)

    for bot in list(active_bots):
        if bot.is_dead or not bot.root:
            continue
        explosion = Entity(
            model='sphere', color=color.orange, unlit=True,
            scale=0.15, position=bot.root.position + Vec3(0, 1, 0),
        )
        explosion.animate_scale(Vec3(4, 4, 4), duration=0.3, curve=curve.out_quad)
        explosion.fade_out(duration=0.3)
        destroy(explosion, delay=0.32)
        bot.die()


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

    if game_state != 'playing' or player_hp <= 0 or 'immortal' in match_cheats:
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
        invoke(lambda: arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.1) if arm_left else None, delay=0.15)
    if weapon_arm:
        weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.08)
        invoke(lambda: weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1) if weapon_arm else None, delay=0.15)


def hide_autoblock_banner():
    if autoblock_banner:
        autoblock_banner.visible = False


def show_block_spark():
    """Visual indicator for manual parry."""
    if block_indicator:
        block_indicator.color = color.yellow
        invoke(lambda: setattr(block_indicator, 'color', color.azure) if block_indicator else None, delay=0.15)


def trigger_game_over():
    """Display Game Over screen and unlock mouse for clean interaction."""
    global game_state, game_over_ui_elems, _whistle_remaining, _whistle_bgm_paused
    game_state = 'game_over'
    mouse.locked  = False
    mouse.visible = True
    if easter_egg_cursor:
        easter_egg_cursor.visible = False

    if _whistle_audio:
        try:
            _whistle_audio.stop()
        except Exception:
            pass
    _whistle_remaining = 0.0
    if bg_music and _whistle_bgm_paused:
        try:
            bg_music.resume()
        except Exception:
            pass
        _whistle_bgm_paused = False

    t1 = Text(
        text   = "YOU FELL IN BATTLE!",
        origin = (0, 0),
        scale  = 3,
        y      = 0.1,
        color  = color.red,
    )
    t2 = Text(
        text   = f"Total Bots Defeated: {kills_count}\nPress [R] to Restart",
        origin = (0, 0),
        scale  = 1.5,
        y      = -0.05,
        color  = color.white,
    )
    game_over_ui_elems.extend([t1, t2])


def respawn_player():
    """Instantly respawn player back onto the platform center after falling off the edge."""
    global y_velocity, is_grounded, is_blocking, is_attacking
    if player is None or game_state != 'playing':
        return
    player.position = Vec3(0, 0.1, 0)
    player.rotation = Vec3(0, 0, 0)
    y_velocity = 0.0
    is_grounded = True
    is_blocking = False
    is_attacking = False
    if camera_pivot:
        camera_pivot.position = player.position + Vec3(0, current_pivot_height, 0)

    # Clean instant respawn notification banner
    respawn_txt = Text(
        text     = "RESPAWNED!",
        origin   = (0, 0),
        scale    = 2.2,
        y        = 0.2,
        color    = color.rgb(80/255, 230/255, 120/255),
    )
    respawn_txt.fade_out(duration=0.5)
    destroy(respawn_txt, delay=0.55)


# =============================================================================
# PLAYER ATTACK & HIT DETECTION
# =============================================================================

def trigger_attack():
    """Animate weapons and detect melee hits against active Puss Bots."""
    global is_attacking, network_attack_sequence
    if is_attacking:
        return
    is_attacking = True
    network_attack_sequence += 1

    if selected_char == 'death':
        # Death's dual scissor cleave with BOTH arms
        if arm_left:
            arm_left.animate_rotation(Vec3(-35, 30, -20), duration=0.09, curve=curve.linear)
            arm_left.animate_position(Vec3(-0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(-35, -30, 20), duration=0.09, curve=curve.linear)
            weapon_arm.animate_position(Vec3(0.70, 1.82, 0.45), duration=0.09, curve=curve.linear)
    elif selected_char == 'perrito':
        # Perrito swings his wooden stick sword in his mouth with a snappy horizontal bite-slash!
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, -60, 12), duration=0.07, curve=curve.linear)
        if arm_left: # Head turns with the swing
            arm_left.animate_rotation(Vec3(4, -40, 8), duration=0.07, curve=curve.linear)
    else:
        # Puss / Kitty single rapier/sword thrust
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(-25, -20, 10), duration=0.09, curve=curve.linear)
            weapon_arm.animate_position(Vec3(weapon_arm.x, weapon_arm.y, 0.35), duration=0.09, curve=curve.linear)

    invoke(check_player_attack_hits, delay=0.08)
    invoke(reset_attack_arm, delay=0.15)


def reset_attack_arm():
    global is_attacking
    if selected_char == 'death':
        if arm_left:
            arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            arm_left.animate_position(Vec3(-0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            weapon_arm.animate_position(Vec3(0.70, 1.82, 0.0), duration=0.12, curve=curve.linear)
    elif selected_char == 'perrito':
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.10, curve=curve.linear)
        if arm_left:
            arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.10, curve=curve.linear)
    else:
        if weapon_arm:
            weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.12, curve=curve.linear)
            weapon_arm.animate_position(Vec3(weapon_arm.x, weapon_arm.y, 0.0), duration=0.12, curve=curve.linear)
    is_attacking = False


def check_player_attack_hits():
    """Detect bots within melee strike range in front of the player."""
    if player is None or game_state != 'playing':
        return

    hit_range = 4.2 if selected_char == 'death' else (3.3 if selected_char == 'perrito' else 2.8)

    # Detect if attack is executed while airborne/jumping for jumping critical strike!
    is_airborne = (not is_grounded) or (player and player.y > 0.05)

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
                # Critical hit system: jumping attacks guarantee a crit with +15% extra crit damage!
                is_crit = is_airborne or (random.random() < 0.30) or (facing_dot > 0.90)
                damage = player_damage * (1.1 if 'damage' in match_cheats else 1.0)
                if is_crit:
                    # +15% extra crit damage on jump attacks
                    crit_mult = 1.8 * (1.15 if is_airborne else 1.0)
                    final_damage = damage * crit_mult
                else:
                    final_damage = damage
                bot.take_damage(final_damage, is_crit=is_crit)
                if dist > 0.01:
                    knockback = 0.95 if is_airborne else (0.75 if is_crit else 0.5)
                    bot.root.position += diff.normalized() * knockback

    # Hit check against remote player in multiplayer!
    if remote_player and network_connected:
        diff = remote_player.position - player.position
        diff.y = 0
        dist = diff.length()
        if dist <= hit_range:
            facing_dot = player.forward.normalized().dot(diff.normalized()) if dist > 0.01 else 1.0
            if facing_dot > 0.15:
                is_crit = is_airborne or (random.random() < 0.30) or (facing_dot > 0.90)
                damage = player_damage * (1.1 if 'damage' in match_cheats else 1.0)
                if is_crit:
                    crit_mult = 1.8 * (1.15 if is_airborne else 1.0)
                    final_damage = damage * crit_mult
                else:
                    final_damage = damage
                spawn_damage_number(remote_player.position, final_damage, is_crit=is_crit)
                for child in remote_player.children:
                    if hasattr(child, 'color'):
                        child.blink(color.red, duration=0.12)
                if dist > 0.01:
                    knockback = 0.95 if is_airborne else (0.75 if is_crit else 0.5)
                    remote_player.position += diff.normalized() * knockback


# =============================================================================
# PAUSE MENU SYSTEM (Modern Colors, Crisp Outlines, Full /255 Fix)
# =============================================================================

def show_pause_menu():
    """Freeze the game and show the modern outlined 3-button pause overlay."""
    global is_paused, pause_ui_elems

    if is_paused:
        return
    is_paused = True
    application.paused = True
    mouse.locked  = False
    mouse.visible = True
    if easter_egg_cursor:
        easter_egg_cursor.visible = False

    # ── Semi-transparent dark backdrop ───────────────────────────────────────
    overlay = Entity(
        parent        = camera.ui,
        model         = 'quad',
        color         = color.rgba(12/255, 12/255, 18/255, 200/255),
        scale         = (3, 3),
        z             = 0.05,
        ignore_paused = True,
    )

    # ── Outer Panel Glow & Inner Card ─────────────────────────────────────────
    border = Entity(
        parent        = camera.ui,
        model         = 'quad',
        color         = color.rgb(220/255, 45/255, 55/255),
        scale         = (0.45, 0.63),
        position      = (0, 0.01),
        z             = 0.04,
        ignore_paused = True,
    )
    panel = Entity(
        parent        = camera.ui,
        model         = 'quad',
        color         = color.rgb(18/255, 18/255, 24/255),
        scale         = (0.43, 0.61),
        position      = (0, 0.01),
        z             = 0.03,
        ignore_paused = True,
    )

    # ── Title & Subtitle ─────────────────────────────────────────────────────
    title = Text(
        text          = 'PAUSED',
        origin        = (0, 0),
        position      = (0, 0.22),
        scale         = 2.8,
        color         = color.rgb(255/255, 215/255, 60/255),
        ignore_paused = True,
    )
    sub = Text(
        text          = 'Game Paused',
        origin        = (0, 0),
        position      = (0, 0.165),
        scale         = 1.1,
        color         = color.rgb(160/255, 165/255, 180/255),
        ignore_paused = True,
    )

    # ── Modern Outlined Buttons Helper ───────────────────────────────────────
    def make_pause_btn(label, ypos, fill_col, border_col, hover_col, on_click_fn):
        bdr = Entity(
            parent        = camera.ui,
            model         = 'quad',
            color         = border_col,
            scale         = (0.34, 0.072),
            position      = (0, ypos),
            z             = 0.02,
            ignore_paused = True,
        )
        btn = Button(
            text            = label,
            color           = fill_col,
            highlight_color = hover_col,
            text_color      = color.white,
            scale           = (0.326, 0.060),
            position        = (0, ypos),
            z               = 0.01,
            text_size       = 1.05,
            ignore_paused   = True,
        )
        btn.on_click = on_click_fn
        pause_ui_elems.extend([bdr, btn])
        return btn

    # Modern Emerald Green Resume
    make_pause_btn(
        'RESUME', 0.08,
        color.rgb(25/255, 130/255, 70/255),
        color.rgb(50/255, 220/255, 115/255),
        color.rgb(45/255, 175/255, 95/255),
        hide_pause_menu
    )

    # Modern Amber / Golden Orange Change Character
    make_pause_btn(
        'CHANGE CHARACTER', 0.00,
        color.rgb(180/255, 90/255, 20/255),
        color.rgb(255/255, 170/255, 50/255),
        color.rgb(225/255, 125/255, 30/255),
        go_to_character_select
    )

    # Modern Sapphire Blue Main Menu
    make_pause_btn(
        'MAIN MENU', -0.08,
        color.rgb(30/255, 85/255, 170/255),
        color.rgb(75/255, 170/255, 255/255),
        color.rgb(50/255, 120/255, 215/255),
        go_to_main_menu
    )

    # Modern Crimson Red Quit
    make_pause_btn(
        'QUIT', -0.16,
        color.rgb(165/255, 28/255, 38/255),
        color.rgb(250/255, 70/255, 80/255),
        color.rgb(210/255, 45/255, 55/255),
        application.quit
    )

    pause_ui_elems.extend([overlay, border, panel, title, sub])


def hide_pause_menu():
    """Resume gameplay and cleanly destroy all pause overlay entities."""
    global is_paused, pause_ui_elems

    for elem in pause_ui_elems:
        deep_destroy(elem)
    pause_ui_elems.clear()

    is_paused = False
    application.paused = False
    mouse.locked  = not (easter_egg_active and easter_egg_mouse_unlocked)
    mouse.visible = not mouse.locked
    if easter_egg_cursor:
        easter_egg_cursor.visible = easter_egg_mouse_unlocked


def teardown_gameplay():
    """
    Tear down the current gameplay session completely and clean up all entities,
    HUD elements, bots, and overlays.
    """
    global player, weapon_arm, arm_left, leg_left, leg_right, body_entity
    global leg_back_l, leg_back_r, tail_entity
    global weapon_entity, camera_pivot, game_state, active_bots, is_paused
    global pause_ui_elems, is_blocking, is_attacking, walk_time
    global hud_char_name, hud_hp_bar_bg, hud_hp_bar_fill, hud_hp_text
    global hud_dash_text, hud_kills_text, hud_special_perk, hud_controls
    global hud_whistle_icon, hud_whistle_cooldown, hud_ult_icon, hud_ult_cooldown
    global block_indicator, autoblock_banner, game_over_ui_elems
    global camera_yaw, camera_pitch
    global easter_egg_progress, easter_egg_active, easter_egg_escape_used
    global easter_egg_mouse_unlocked, easter_egg_map_ui
    global easter_egg_player_marker, easter_egg_bot_markers, easter_egg_cursor
    global training_dummy, network_status_label, remote_player
    global remote_player_data, remote_player_char, remote_hp_bar_fill, remote_name_tag
    global _whistle_remaining, _whistle_bgm_paused
    global cam_zoom_delta, cam_fov_delta

    cam_zoom_delta = 0.0
    cam_fov_delta  = 0.0

    teardown_ring_of_fire()

    if _whistle_audio:
        try:
            _whistle_audio.stop()
        except Exception:
            pass
    _whistle_remaining = 0.0
    if bg_music and _whistle_bgm_paused:
        try:
            bg_music.resume()
        except Exception:
            pass
        _whistle_bgm_paused = False

    # 1. Clear game over overlay if present
    for elem in game_over_ui_elems:
        deep_destroy(elem)
    game_over_ui_elems.clear()

    # 2. Clear pause overlay
    for elem in pause_ui_elems:
        deep_destroy(elem)
    pause_ui_elems.clear()
    is_paused = False
    application.paused = False

    # 3. Destroy all active bots and their shapes
    for bot in list(active_bots):
        if hasattr(bot, 'root') and bot.root:
            deep_destroy(bot.root)
    active_bots.clear()
    training_dummy = None

    if remote_player:
        deep_destroy(remote_player)
        remote_player = None
    remote_player_data = None
    remote_player_char = None
    remote_hp_bar_fill = None
    remote_name_tag = None
    stop_network_session()

    # 4. Destroy active player model and all attached parts
    if player:
        deep_destroy(player)
        player = None

    weapon_arm  = None
    arm_left    = None
    leg_left    = None
    leg_right   = None
    leg_back_l  = None
    leg_back_r  = None
    tail_entity = None
    body_entity = None
    weapon_entity = None

    # 5. Destroy camera pivot
    if camera_pivot:
        deep_destroy(camera_pivot)
        camera_pivot = None

    # 6. Destroy HUD elements
    for hud_elem in [hud_char_name, hud_hp_bar_bg, hud_hp_bar_fill, hud_hp_text,
                     hud_dash_text, hud_kills_text, hud_controls,
                     hud_whistle_icon, hud_whistle_cooldown,
                     block_indicator, autoblock_banner]:
        if hud_elem:
            deep_destroy(hud_elem)

    hud_char_name = hud_hp_bar_bg = hud_hp_bar_fill = hud_hp_text = None
    hud_dash_text = hud_kills_text = hud_controls = None
    hud_whistle_icon = hud_whistle_cooldown = None
    block_indicator = autoblock_banner = None
    if network_status_label:
        deep_destroy(network_status_label)
        network_status_label = None

    for egg_elem in easter_egg_map_ui:
        if egg_elem:
            deep_destroy(egg_elem)
    easter_egg_map_ui.clear()
    if easter_egg_cursor:
        deep_destroy(easter_egg_cursor)
    easter_egg_player_marker = None
    easter_egg_bot_markers = []
    easter_egg_cursor = None
    easter_egg_progress = 0
    easter_egg_active = False
    easter_egg_escape_used = False
    easter_egg_mouse_unlocked = False

    # 7. Reset combat state and camera rotation
    is_blocking  = False
    is_attacking = False
    walk_time    = 0.0
    camera_yaw   = 0.0
    camera_pitch = 3.0

    # 8. Reset camera to menu position
    camera.parent   = scene
    camera.position = (0, 1.2, -6.0)
    camera.rotation = (0, 0, 0)
    mouse.locked    = False
    mouse.visible   = True


def go_to_character_select():
    """
    Tear down gameplay and return directly to the character selection screen.
    """
    teardown_gameplay()
    game_state = 'selection'
    setup_selection_menu()


def go_to_main_menu():
    """
    Tear down gameplay and return to the main title menu.
    """
    teardown_gameplay()
    show_main_menu()


# =============================================================================
# DEATH'S WHISTLE ABILITY
# =============================================================================
_whistle_cooldown = 0.0
_WHISTLE_COOLDOWN = 15.0          # seconds between whistles
_whistle_label    = None          # on-screen flash text
_whistle_remaining = 0.0          # time left in the whistle animation
_whistle_bgm_paused = False       # whether battlesong is paused for the whistle

# Load whistle with Ursina's audio system
_whistle_audio = Audio('whistle.mp3', loop=False, autoplay=False)


def play_death_whistle():
    """Play the whistle MP3 sound + show a flash label (Death only, E key)."""
    global _whistle_cooldown, _whistle_label, _whistle_remaining, _whistle_bgm_paused
    if _whistle_cooldown > 0 or _whistle_remaining > 0:
        return
    _whistle_cooldown = _WHISTLE_COOLDOWN
    _whistle_remaining = max(0.1, getattr(_whistle_audio, 'length', 3.0))

    # Pause battlesong background music while whistle plays
    if bg_music and not _whistle_bgm_paused:
        try:
            bg_music.pause()
            _whistle_bgm_paused = True
        except Exception:
            pass

    # Play audio when triggered with F
    _whistle_audio.stop()
    _whistle_audio.play()
    # Death keeps both hands lowered while whistling.
    if arm_left:
        arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.15)
    if weapon_arm:
        weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.15)
    update_whistle_hud()


def update_whistle_hud():
    if not hud_whistle_icon or not hud_whistle_cooldown:
        return

    cooldown_ratio = clamp(_whistle_cooldown / _WHISTLE_COOLDOWN, 0.0, 1.0)
    hud_whistle_cooldown.visible = cooldown_ratio > 0
    hud_whistle_cooldown.scale_y = max(0.001, WHISTLE_ICON_SIZE * cooldown_ratio)


# =============================================================================
# DEATH'S ULTIMATE ABILITY: RING OF FIRE (Climax 1v1 Arena from The Last Wish)
# =============================================================================
_ult_cooldown           = 0.0
_ULT_COOLDOWN           = 32.0          # cooldown in seconds
_ring_of_fire_active    = False
_ring_of_fire_center    = Vec3(0, 0, 0)
_ring_of_fire_radius    = 8.5           # circular duel arena radius
_ring_of_fire_remaining = 0.0
_RING_OF_FIRE_DURATION  = 16.0          # duration of the fiery cage
_ring_of_fire_target    = None          # target locked in the 1v1
_ring_of_fire_entities  = []            # all 3D flame quads, decals, and embers
_ring_of_fire_embers    = []            # floating spark particle definitions


def update_ult_hud():
    if not hud_ult_icon or not hud_ult_cooldown:
        return
    cooldown_ratio = clamp(_ult_cooldown / _ULT_COOLDOWN, 0.0, 1.0)
    hud_ult_cooldown.visible = cooldown_ratio > 0
    hud_ult_cooldown.scale_y = max(0.001, ULT_ICON_SIZE * cooldown_ratio)


def cast_death_ult():
    """
    Death's Ultimate: Ring of Fire (Puss in Boots: The Last Wish).
    Death clashes his two sickles producing intense sparks, then summons a towering,
    multi-colored ring of blazing magical fire around himself and his opponent,
    locking them into an inescapable 1v1 duel to the death.
    """
    global _ult_cooldown, _ring_of_fire_active, _ring_of_fire_center, _ring_of_fire_remaining
    global _ring_of_fire_target, _ring_of_fire_entities, _ring_of_fire_embers

    if _ult_cooldown > 0 or _ring_of_fire_active or player is None or game_state != 'playing':
        return

    _ult_cooldown = _ULT_COOLDOWN
    _ring_of_fire_active = True
    _ring_of_fire_remaining = _RING_OF_FIRE_DURATION

    # Identify duel target (closest active bot or multiplayer remote player)
    closest_enemy = None
    closest_dist = 999.0
    for bot in active_bots:
        if not bot.is_dead and hasattr(bot, 'root') and bot.root:
            d = (bot.root.position - player.position).length()
            if d < closest_dist:
                closest_dist = d
                closest_enemy = bot

    if remote_player and network_connected:
        rd = (remote_player.position - player.position).length()
        if rd < closest_dist:
            closest_dist = rd
            closest_enemy = remote_player

    _ring_of_fire_target = closest_enemy

    # Position arena center between Death and his duel opponent if close, else around Death
    if closest_enemy and closest_dist < 13.0:
        target_pos = closest_enemy.root.position if hasattr(closest_enemy, 'root') else closest_enemy.position
        _ring_of_fire_center = Vec3(
            (player.x + target_pos.x) * 0.5,
            0.0,
            (player.z + target_pos.z) * 0.5
        )
    else:
        _ring_of_fire_center = Vec3(player.x, 0.0, player.z)

    # 1. Death Sickle Clash Friction Animation
    if arm_left:
        arm_left.animate_rotation(Vec3(25, 45, -20), duration=0.12)
        arm_left.animate_position(Vec3(-0.35, 1.82, 0.40), duration=0.12)
    if weapon_arm:
        weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.12)
        weapon_arm.animate_position(Vec3(0.35, 1.82, 0.40), duration=0.12)

    # 2. Burst of Friction Sparks from sickles
    clash_point = player.position + Vec3(0, 1.82, 0.45)
    for _ in range(16):
        spark = Entity(
            model='quad',
            texture='flame_ember.png',
            color=color.rgb(255/255, random.uniform(200, 255)/255, random.uniform(80, 140)/255),
            scale=random.uniform(0.12, 0.26),
            position=clash_point,
            double_sided=True
        )
        s_dir = Vec3(random.uniform(-1, 1), random.uniform(-0.3, 1), random.uniform(-1, 1)).normalized()
        spark.animate_position(spark.position + s_dir * random.uniform(1.2, 2.8), duration=0.35, curve=curve.out_quad)
        spark.fade_out(duration=0.30, delay=0.08)
        destroy(spark, delay=0.45)

    update_ult_hud()

    # 3. Ignite Ring of Fire after sickle friction clash
    invoke(_ignite_ring_of_fire, delay=0.15)


def _ignite_ring_of_fire():
    """Erupt the multi-chromatic 3D flame wall around the duel arena."""
    global _ring_of_fire_entities, _ring_of_fire_embers

    if not _ring_of_fire_active or player is None:
        return

    # Death outward dual-sickle flare animation
    if arm_left:
        arm_left.animate_rotation(Vec3(-20, -50, 20), duration=0.25)
        arm_left.animate_position(Vec3(-0.70, 1.82, 0.0), duration=0.25)
    if weapon_arm:
        weapon_arm.animate_rotation(Vec3(-20, 50, -20), duration=0.25)
        weapon_arm.animate_position(Vec3(0.70, 1.82, 0.0), duration=0.25)
    invoke(reset_attack_arm, delay=0.45)

    # A) Fiery floor scorch and glowing ground rune decals
    decal_size = _ring_of_fire_radius * 2.18
    floor_ring = Entity(
        model='quad',
        texture='flame_ring_decal.png',
        position=_ring_of_fire_center + Vec3(0, 0.03, 0),
        rotation_x=90,
        scale=(decal_size, decal_size),
        color=color.rgb(255/255, 90/255, 20/255),
        double_sided=True
    )
    _ring_of_fire_entities.append(floor_ring)

    inner_glow = Entity(
        model='quad',
        texture='flame_ring_decal.png',
        position=_ring_of_fire_center + Vec3(0, 0.04, 0),
        rotation_x=90,
        scale=(_ring_of_fire_radius * 2.06, _ring_of_fire_radius * 2.06),
        color=color.rgb(255/255, 220/255, 50/255),
        double_sided=True
    )
    _ring_of_fire_entities.append(inner_glow)

    # B) Detailed multi-layered flame wall pillars (36 clusters around circle)
    NUM_PILLARS = 36
    for i in range(NUM_PILLARS):
        angle = i * (2.0 * math.pi / NUM_PILLARS)
        dir_vec = Vec3(math.cos(angle), 0, math.sin(angle))
        pillar_pos = _ring_of_fire_center + dir_vec * _ring_of_fire_radius
        tangent_yaw = -math.degrees(angle) + 90.0

        # Layer 1: Outer Mystical Crimson & Magenta Flame Tips (Iconic Wishing Star edges)
        scale_y_1 = random.uniform(3.8, 5.0)
        c_layer1 = color.rgb(
            random.uniform(205, 230) / 255,
            random.uniform(20, 35) / 255,
            random.uniform(70, 125) / 255
        )
        f1 = Entity(
            model='quad',
            texture='flame_tongue.png',
            color=c_layer1,
            scale=(1.45, scale_y_1),
            position=pillar_pos + Vec3(0, scale_y_1 * 0.48, 0),
            rotation=(0, tangent_yaw + random.uniform(-10, 10), random.uniform(-4, 4)),
            double_sided=True
        )
        f1.base_scale_y = scale_y_1
        f1.base_rot_z = f1.rotation_z
        f1.flicker_phase = angle * 2.5
        _ring_of_fire_entities.append(f1)

        # Layer 2: Mid Blazing Scarlet & Fiery Orange Flames
        scale_y_2 = random.uniform(3.0, 4.0)
        c_layer2 = color.rgb(
            255 / 255,
            random.uniform(75, 125) / 255,
            random.uniform(10, 25) / 255
        )
        f2 = Entity(
            model='quad',
            texture='flame_tongue.png',
            color=c_layer2,
            scale=(1.25, scale_y_2),
            position=pillar_pos + Vec3(0, scale_y_2 * 0.48, 0),
            rotation=(0, tangent_yaw + random.uniform(-25, 25), 0),
            double_sided=True
        )
        f2.base_scale_y = scale_y_2
        f2.base_rot_z = 0.0
        f2.flicker_phase = angle * 2.5 + 1.2
        _ring_of_fire_entities.append(f2)

        # Layer 3: Inner Golden Sun Incandescent Core Flames
        scale_y_3 = random.uniform(2.0, 2.9)
        c_layer3 = color.rgb(
            255 / 255,
            random.uniform(215, 245) / 255,
            random.uniform(40, 90) / 255
        )
        f3 = Entity(
            model='quad',
            texture='flame_tongue.png',
            color=c_layer3,
            scale=(0.95, scale_y_3),
            position=pillar_pos + Vec3(0, scale_y_3 * 0.48, 0),
            rotation=(0, tangent_yaw + random.uniform(-15, 15), 0),
            double_sided=True
        )
        f3.base_scale_y = scale_y_3
        f3.base_rot_z = 0.0
        f3.flicker_phase = angle * 2.5 + 2.4
        _ring_of_fire_entities.append(f3)

        # Layer 4: Volumetric Radial Cross-Quad (perpendicular for full 3D depth)
        scale_y_4 = random.uniform(2.8, 3.8)
        f4 = Entity(
            model='quad',
            texture='flame_tongue.png',
            color=color.rgb(255/255, 105/255, 18/255),
            scale=(1.15, scale_y_4),
            position=pillar_pos + Vec3(0, scale_y_4 * 0.48, 0),
            rotation=(0, tangent_yaw + 90.0, 0),
            double_sided=True
        )
        f4.base_scale_y = scale_y_4
        f4.base_rot_z = 0.0
        f4.flicker_phase = angle * 2.5 + 0.6
        _ring_of_fire_entities.append(f4)

    # C) Floating Rising Ember Particles along the circle
    _ring_of_fire_embers.clear()
    for _ in range(28):
        ember_angle = random.uniform(0, 2 * math.pi)
        e_pos = _ring_of_fire_center + Vec3(
            math.cos(ember_angle) * (_ring_of_fire_radius + random.uniform(-0.35, 0.35)),
            random.uniform(0.2, 4.0),
            math.sin(ember_angle) * (_ring_of_fire_radius + random.uniform(-0.35, 0.35))
        )
        ember = Entity(
            model='quad',
            texture='flame_ember.png',
            color=color.rgb(255/255, random.uniform(150, 240)/255, 45/255),
            scale=random.uniform(0.12, 0.22),
            position=e_pos,
            double_sided=True
        )
        _ring_of_fire_embers.append({
            'entity': ember,
            'base_angle': ember_angle,
            'speed': random.uniform(2.6, 4.4),
            'sway_freq': random.uniform(3.5, 7.0),
            'sway_amp': random.uniform(0.12, 0.28)
        })
        _ring_of_fire_entities.append(ember)

    # D) Dramatic On-Screen Fiery Duel Announcement
    banner_title = Text(
        text="RING OF FIRE",
        origin=(0, 0),
        position=(0, 0.25),
        scale=2.7,
        color=color.rgb(255/255, 140/255, 20/255),
        font=HUD_FONT,
        parent=camera.ui
    )
    banner_sub = Text(
        text="1v1 LOCKED DUEL",
        origin=(0, 0),
        position=(0, 0.17),
        scale=1.35,
        color=color.rgb(255/255, 40/255, 60/255),
        font=HUD_FONT,
        parent=camera.ui
    )
    banner_title.animate_scale(3.3, duration=0.25, curve=curve.out_back)
    banner_title.fade_out(duration=0.6, delay=1.8)
    banner_sub.fade_out(duration=0.6, delay=1.8)
    destroy(banner_title, delay=2.5)
    destroy(banner_sub, delay=2.5)


def update_ring_of_fire(dt):
    """
    Tick ultimate timer, flicker the multi-colored flames, drift the sparks,
    and enforce the 1v1 containment boundary with burn damage.
    """
    global _ult_cooldown, _ring_of_fire_active, _ring_of_fire_remaining
    global _ring_of_fire_target, _ring_of_fire_entities, _ring_of_fire_embers

    if _ult_cooldown > 0:
        _ult_cooldown = max(0.0, _ult_cooldown - dt)
        update_ult_hud()

    if not _ring_of_fire_active:
        return

    _ring_of_fire_remaining -= dt

    # Check expiration or target death
    if _ring_of_fire_remaining <= 0 or (
        _ring_of_fire_target and hasattr(_ring_of_fire_target, 'is_dead') and _ring_of_fire_target.is_dead
    ):
        extinguish_ring_of_fire()
        return

    t = time.time()

    # 1. Animate multi-chromatic flame flickers and wind sway
    for ent in _ring_of_fire_entities:
        if hasattr(ent, 'base_scale_y'):
            flicker = math.sin(t * 14.0 + ent.flicker_phase)
            ent.scale_y = ent.base_scale_y * (1.0 + 0.16 * flicker)
            if hasattr(ent, 'base_rot_z'):
                ent.rotation_z = ent.base_rot_z + 3.8 * math.sin(t * 9.0 + ent.flicker_phase)

    # 2. Animate floating rising embers
    for item in _ring_of_fire_embers:
        ember = item['entity']
        if ember and ember.enabled:
            ember.y += item['speed'] * dt
            sway = math.sin(t * item['sway_freq'] + item['base_angle']) * item['sway_amp']
            ang = item['base_angle']
            ember.x = _ring_of_fire_center.x + math.cos(ang) * (_ring_of_fire_radius + sway)
            ember.z = _ring_of_fire_center.z + math.sin(ang) * (_ring_of_fire_radius + sway)
            if ember.y > 4.8:
                ember.y = random.uniform(0.1, 0.4)
                item['base_angle'] = random.uniform(0, 2 * math.pi)

    # 3. 1v1 Arena Containment & Burn Barrier
    # Player (Death) stays inside the ring of fire
    if player:
        p_diff = player.position - _ring_of_fire_center
        p_diff.y = 0
        p_dist = p_diff.length()
        if p_dist > _ring_of_fire_radius - 0.4 and p_dist > 0.01:
            player.position = _ring_of_fire_center + p_diff.normalized() * (_ring_of_fire_radius - 0.4)

    # Bots: Target trapped inside; outsiders repelled outside
    for bot in list(active_bots):
        if bot.is_dead or not hasattr(bot, 'root') or not bot.root:
            continue
        b_diff = bot.root.position - _ring_of_fire_center
        b_diff.y = 0
        b_dist = b_diff.length()

        is_duel_target = (bot == _ring_of_fire_target)
        if is_duel_target or b_dist < _ring_of_fire_radius:
            # Trapped inside
            if b_dist > _ring_of_fire_radius - 0.6 and b_dist > 0.01:
                bot.root.position = _ring_of_fire_center + b_diff.normalized() * (_ring_of_fire_radius - 0.7)
                bot.take_damage(28.0 * dt, is_crit=True)
                for child in bot.root.children:
                    if hasattr(child, 'color'):
                        child.blink(color.rgb(255/255, 60/255, 10/255), duration=0.1)
        else:
            # Outsider bot: cannot enter the 1v1 ring
            if b_dist < _ring_of_fire_radius + 0.8 and b_dist > 0.01:
                bot.root.position = _ring_of_fire_center + b_diff.normalized() * (_ring_of_fire_radius + 1.1)
                bot.take_damage(28.0 * dt, is_crit=True)

    # Remote player in multiplayer
    if remote_player and network_connected:
        r_diff = remote_player.position - _ring_of_fire_center
        r_diff.y = 0
        r_dist = r_diff.length()
        if r_dist < _ring_of_fire_radius:
            if r_dist > _ring_of_fire_radius - 0.6 and r_dist > 0.01:
                remote_player.position = _ring_of_fire_center + r_diff.normalized() * (_ring_of_fire_radius - 0.7)
                spawn_damage_number(remote_player.position, 28.0 * dt, is_crit=True)
        else:
            if r_dist < _ring_of_fire_radius + 0.8 and r_dist > 0.01:
                remote_player.position = _ring_of_fire_center + r_diff.normalized() * (_ring_of_fire_radius + 1.1)
                spawn_damage_number(remote_player.position, 28.0 * dt, is_crit=True)


def extinguish_ring_of_fire():
    """Dissolve the ring of fire into fading embers at the end of the duel."""
    global _ring_of_fire_active, _ring_of_fire_entities, _ring_of_fire_embers
    _ring_of_fire_active = False
    for ent in list(_ring_of_fire_entities):
        if ent and hasattr(ent, 'fade_out'):
            try:
                ent.fade_out(duration=0.5)
                destroy(ent, delay=0.55)
            except Exception:
                deep_destroy(ent)
        elif ent:
            deep_destroy(ent)
    _ring_of_fire_entities.clear()
    _ring_of_fire_embers.clear()


def teardown_ring_of_fire():
    """Immediately clean up all entities and HUD elements."""
    global _ring_of_fire_active, _ring_of_fire_entities, _ring_of_fire_embers
    global _ring_of_fire_remaining, _ring_of_fire_target, _ult_cooldown
    global hud_ult_icon, hud_ult_cooldown
    _ring_of_fire_active = False
    _ring_of_fire_remaining = 0.0
    _ring_of_fire_target = None
    for ent in list(_ring_of_fire_entities):
        deep_destroy(ent)
    _ring_of_fire_entities.clear()
    _ring_of_fire_embers.clear()
    if hud_ult_icon:
        deep_destroy(hud_ult_icon)
    if hud_ult_cooldown:
        deep_destroy(hud_ult_cooldown)
    hud_ult_icon = None
    hud_ult_cooldown = None


# =============================================================================
# INPUT HANDLER
# =============================================================================

def input(key):
    global is_blocking, game_state, y_velocity, is_grounded
    global easter_egg_escape_used, easter_egg_mouse_unlocked, easter_egg_cursor

    if control_capture_action:
        _finish_control_remap(key)
        return

    if cheat_panel_open:
        global cheat_code_input
        if key == 'escape':
            _clear_cheat_panel()
        elif not cheat_input_focused:
            return
        elif key == 'backspace':
            cheat_code_input = cheat_code_input[:-1]
            if cheat_panel_input_entity:
                cheat_panel_input_entity.text = cheat_code_input + '_'
        elif key in ('enter', 'return'):
            if cheat_panel_submit_callback:
                cheat_panel_submit_callback()
        elif len(key) == 1 and (key.isalnum() or key in '-_'):
            cheat_code_input += key.lower()
            if cheat_panel_input_entity:
                cheat_panel_input_entity.text = cheat_code_input + '_'
        return

    # ── Restart after game-over ───────────────────────────────────────────────
    if game_state == 'game_over' and key == 'r':
        go_to_character_select()
        return

    # ── ESC: toggle pause in gameplay, ignore in other states ─────────────────
    if key == 'escape':
        if game_state == 'playing':
            if easter_egg_active and not easter_egg_escape_used:
                easter_egg_escape_used = True
                easter_egg_mouse_unlocked = True
                mouse.locked = False
                mouse.visible = True
                if easter_egg_cursor:
                    easter_egg_cursor.visible = True
                return
            if is_paused:
                hide_pause_menu()
            else:
                show_pause_menu()
        elif game_state == 'join_menu':
            stop_network_session()
            show_multiplayer_menu()
        elif game_state == 'host_menu':
            stop_network_session()
            show_multiplayer_menu()
        elif game_state == 'settings_menu':
            show_main_menu()
        elif game_state == 'singleplayer_menu':
            show_play_menu()
        elif game_state == 'multiplayer_menu':
            show_play_menu()
        elif game_state == 'play_menu':
            show_main_menu()
        elif game_state == 'selection':
            return_from_character_selection()
        return          # don't fall through to gameplay keys

    if game_state == 'join_menu':
        global menu_join_address
        if key == 'backspace':
            menu_join_address = menu_join_address[:-1]
            _refresh_join_address()
        elif key in ('enter', 'return'):
            connect_to_host()
        elif len(key) == 1 and (key.isalnum() or key in '.-:'):
            menu_join_address += key
            _refresh_join_address()
        return

    # ── While paused or not in gameplay, ignore everything else ───────────────
    if game_state != 'playing' or is_paused:
        return

    if easter_egg_active and easter_egg_mouse_unlocked and key == 'left mouse down':
        trigger_easter_egg_blast()
        return

    advance_easter_egg_sequence(key)

    # --- Block (hold RMB) ---
    if key == controls['block']:
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
        elif selected_char == 'perrito':
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(10, -45, 30), duration=0.1)
            if arm_left:
                arm_left.animate_rotation(Vec3(-10, 0, 0), duration=0.1)
        else:
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(25, -45, 20), duration=0.1)
        if block_indicator:
            block_indicator.visible = True

    block_release = (
        controls['block'][:-4] + 'up'
        if controls['block'].endswith('down')
        else f"{controls['block']} up"
    )
    if key == block_release:
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
        elif selected_char == 'perrito':
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1)
            if arm_left:
                arm_left.animate_rotation(Vec3(0, 0, 0), duration=0.1)
        else:
            if weapon_arm:
                weapon_arm.animate_rotation(Vec3(0, 0, 0), duration=0.1)
        if block_indicator:
            block_indicator.visible = False

    # --- Attack (LMB) ---
    if key == controls['attack'] and not is_blocking:
        trigger_attack()

    # --- Dash (Shift) ---
    if key == controls['dash'] and not is_blocking:
        do_dash()

    # --- Jump (Space) ---
    if key == controls['jump'] and is_grounded and not is_blocking:
        y_velocity = JUMP_FORCE
        is_grounded = False

    # --- Death's Whistle (E) ---
    if key == controls['ability'] and selected_char == 'death':
        play_death_whistle()

    # --- Death's Ultimate: Ring of Fire (X) ---
    if (key == controls.get('ult', 'x') or key == 'x') and selected_char == 'death':
        cast_death_ult()

    # --- Camera Zoom & FOV Scroll Controls ---
    global cam_zoom_delta, cam_fov_delta
    if key == 'scroll up':
        # Zoom in on character: increases zoomness / character size on screen
        cam_zoom_delta = clamp(cam_zoom_delta + 0.6, -7.0, 2.8)
        cam_fov_delta  = clamp(cam_fov_delta - 3.5, -24.0, 36.0)
        camera.z   = cam_base_z + cam_zoom_delta
        camera.fov = cam_base_fov + cam_fov_delta
    elif key == 'scroll down':
        # Increase FOV and pull back camera for wide-angle battlefield perspective
        cam_zoom_delta = clamp(cam_zoom_delta - 0.6, -7.0, 2.8)
        cam_fov_delta  = clamp(cam_fov_delta + 3.5, -24.0, 36.0)
        camera.z   = cam_base_z + cam_zoom_delta
        camera.fov = cam_base_fov + cam_fov_delta
    elif key == 'middle mouse down':
        # Reset camera zoom and FOV to character preset default
        cam_zoom_delta = 0.0
        cam_fov_delta  = 0.0
        camera.z   = cam_base_z
        camera.fov = cam_base_fov


# =============================================================================
# DASH MECHANIC
# =============================================================================

def do_dash():
    global dash_cooldown
    if dash_cooldown > 0:
        return

    dash_cooldown = DASH_COOLDOWN
    forward = player.forward
    dash_multiplier = 1.3 if 'speed' in match_cheats else 1.0
    player.position += forward * DASH_FORCE * dash_multiplier


# =============================================================================
# COLLISION SYSTEM (Player vs Bots, Bot vs Bot, Player vs Player)
# =============================================================================

def resolve_collisions():
    """
    Push apart characters on the XZ plane so players and bots cannot walk through each other.
    Handles:
    - Player vs Active Bots
    - Bot vs Bot
    - Player vs Remote Player
    - Remote Player vs Bots
    """
    if game_state != 'playing' or not player:
        return

    player_radius = 0.75 if selected_char == 'death' else 0.50

    # 1. Player vs Active Bots
    for bot in active_bots:
        if bot.is_dead or not bot.root:
            continue
        diff = player.position - bot.root.position
        diff.y = 0
        dist = diff.length()
        min_dist = player_radius + 0.50
        if 0.0001 < dist < min_dist:
            push = (min_dist - dist)
            norm = diff.normalized()
            player.position += norm * (push * 0.55)
            bot.root.position -= norm * (push * 0.45)

    # 2. Bot vs Bot (prevent overlapping into a single spot)
    num_bots = len(active_bots)
    for i in range(num_bots):
        b1 = active_bots[i]
        if b1.is_dead or not b1.root:
            continue
        for j in range(i + 1, num_bots):
            b2 = active_bots[j]
            if b2.is_dead or not b2.root:
                continue
            diff = b1.root.position - b2.root.position
            diff.y = 0
            dist = diff.length()
            min_dist = 1.05
            if 0.0001 < dist < min_dist:
                push = (min_dist - dist) * 0.5
                norm = diff.normalized()
                b1.root.position += norm * push
                b2.root.position -= norm * push

    # 3. Player vs Remote Player (Multiplayer)
    if remote_player and network_connected:
        r_rad = 0.75 if remote_player_char == 'death' else 0.50
        diff = player.position - remote_player.position
        diff.y = 0
        dist = diff.length()
        min_dist = player_radius + r_rad
        if 0.0001 < dist < min_dist:
            push = (min_dist - dist) * 0.5
            norm = diff.normalized()
            player.position += norm * push
            remote_player.position -= norm * push

    # 4. Remote Player vs Bots (Multiplayer)
    if remote_player and network_connected:
        r_rad = 0.75 if remote_player_char == 'death' else 0.50
        for bot in active_bots:
            if bot.is_dead or not bot.root:
                continue
            diff = remote_player.position - bot.root.position
            diff.y = 0
            dist = diff.length()
            min_dist = r_rad + 0.50
            if 0.0001 < dist < min_dist:
                push = (min_dist - dist) * 0.5
                norm = diff.normalized()
                remote_player.position += norm * push
                bot.root.position -= norm * push


# =============================================================================
# MAIN UPDATE LOOP
# =============================================================================
camera_yaw   = 0.0
camera_pitch = 3.0

def update():
    global dash_cooldown, camera_yaw, camera_pitch, y_velocity, is_grounded, walk_time
    global bot_respawn_timer, _whistle_cooldown, _whistle_remaining, _whistle_bgm_paused
    global network_local_snapshot

    dt = time.dt
    process_network_events()

    if game_state in (
        'main_menu', 'play_menu', 'singleplayer_menu', 'multiplayer_menu',
        'settings_menu', 'host_menu', 'join_menu',
    ):
        panorama_angle = (time.time() * 0.035) % (2 * math.pi)
        if menu_camera_pivot:
            menu_camera_pivot.rotation_y = -math.degrees(panorama_angle)
        return

    # Tick whistle cooldown
    if _whistle_cooldown > 0:
        _whistle_cooldown = max(0.0, _whistle_cooldown - dt)
        update_whistle_hud()
    if _whistle_remaining > 0:
        _whistle_remaining = max(0.0, _whistle_remaining - dt)
        if _whistle_remaining <= 0 and _whistle_bgm_paused:
            if bg_music:
                try:
                    bg_music.resume()
                except Exception:
                    pass
            _whistle_bgm_paused = False

    # Tick Death's Ultimate: Ring of Fire
    update_ring_of_fire(dt)

    # 3D Turntable continuous rotation in selection menu
    if game_state == 'selection' and preview_pivot:
        preview_pivot.rotation_y += dt * 45.0
        return

    if game_state != 'playing' or player is None:
        return

    if network_connected:
        if not remote_player:
            _create_remote_player(network_remote_snapshot.get('char', 'puss') if network_remote_snapshot else 'puss')
        _apply_remote_snapshot(dt)

    # -------------------------------------------------------
    # CAMERA PIVOT FOLLOWS PLAYER
    # -------------------------------------------------------
    camera_pivot.position = player.position + Vec3(0, current_pivot_height, 0)
    update_easter_egg_map()
    if easter_egg_mouse_unlocked and easter_egg_cursor:
        easter_egg_cursor.position = (mouse.position[0], mouse.position[1], -0.08)

    # -------------------------------------------------------
    # CAMERA ORBIT — mouse look remains available while blocking
    # -------------------------------------------------------
    if mouse.locked and camera_pivot:
        sensitivity  = mouse_sensitivity
        camera_yaw  += mouse.velocity[0] * sensitivity
        camera_pitch -= mouse.velocity[1] * sensitivity
        camera_pitch  = clamp(camera_pitch, -20, 50)

        camera_pivot.rotation_y = camera_yaw
        camera_pivot.rotation_x = camera_pitch

    # -------------------------------------------------------
    # DASH COOLDOWN TIMER
    # -------------------------------------------------------
    if dash_cooldown > 0:
        dash_cooldown -= dt
        if dash_cooldown <= 0:
            dash_cooldown = 0
            if hud_dash_text:
                hud_dash_text.text  = f"DASH [{_format_control_binding(controls['dash'])}]: Ready"
                hud_dash_text.color = color.cyan
        else:
            if hud_dash_text:
                hud_dash_text.text  = f"DASH: {dash_cooldown:.1f}s"
                hud_dash_text.color = color.orange

    # -------------------------------------------------------
    # JUMP & GRAVITY PHYSICS & PLATFORM FALL-OFF DETECTION
    # -------------------------------------------------------
    on_platform = (abs(player.x) <= PLATFORM_HALF and abs(player.z) <= PLATFORM_HALF)

    if on_platform and player.y >= -0.3:
        # On the solid platform: regular jumping & grounded physics
        if not is_grounded or player.y > 0 or y_velocity != 0:
            y_velocity -= GRAVITY * dt
            player.y += y_velocity * dt

        if player.y <= 0:
            player.y = 0
            y_velocity = 0.0
            is_grounded = True
    else:
        # OFF THE EDGE! Falling down into the abyss from the platform!
        is_grounded = False
        y_velocity -= GRAVITY * dt
        player.y += y_velocity * dt

        # Instantly respawn back on the platform center after falling below!
        if player.y < -12.0:
            respawn_player()

    # -------------------------------------------------------
    # BOT SPAWNING & AI LOOP (Maintain up to 4 bots)
    # -------------------------------------------------------
    for bot in list(active_bots):
        if bot.is_dead and bot.root not in scene.entities:
            active_bots.remove(bot)

    if game_mode == 'pve' and len(active_bots) < MAX_BOTS:
        bot_respawn_timer -= dt
        if bot_respawn_timer <= 0:
            spawn_bot()
            bot_respawn_timer = 1.2

    for bot in list(active_bots):
        if not bot.is_dead and bot.root:
            bot.update_ai(dt, player.position)

    # -------------------------------------------------------
    # BLOCK — disable horizontal movement
    # -------------------------------------------------------
    if is_blocking:
        if leg_left:   leg_left.rotation_x = 0
        if leg_right:  leg_right.rotation_x = 0
        if leg_back_l: leg_back_l.rotation_x = 0
        if leg_back_r: leg_back_r.rotation_x = 0
        return

    # -------------------------------------------------------
    # MOVEMENT & INPUT
    # -------------------------------------------------------
    speed = BASE_SPEED * (1.3 if 'speed' in match_cheats else 1.0)
    sprint_binding = controls['sprint']
    is_sprinting = held_keys[sprint_binding]
    if is_sprinting:
        speed *= SPRINT_MULT
    if selected_char == 'death' and _whistle_remaining > 0:
        speed *= 0.25

    cam_forward = camera_pivot.forward
    cam_forward.y = 0
    if cam_forward.length() > 0:
        cam_forward = cam_forward.normalized()

    cam_right = camera_pivot.right
    cam_right.y = 0
    if cam_right.length() > 0:
        cam_right = cam_right.normalized()

    move_dir = Vec3(0, 0, 0)
    if held_keys[controls['forward']]: move_dir += cam_forward
    if held_keys[controls['backward']]: move_dir -= cam_forward
    if held_keys[controls['left']]: move_dir -= cam_right
    if held_keys[controls['right']]: move_dir += cam_right

    move_dir.y = 0
    is_moving = move_dir.length() > 0

    if is_moving:
        move_dir = move_dir.normalized()
        player.position += move_dir * speed * dt

        target_rot_y = math.degrees(math.atan2(move_dir.x, move_dir.z))
        angle_diff = (target_rot_y - player.rotation_y + 180) % 360 - 180
        player.rotation_y += angle_diff * min(1.0, 15.0 * dt)

        if selected_char == 'perrito':
            # Quadruped natural dog trot: diagonal pairs swing together!
            dog_freq = 24.0 if is_sprinting else 15.0
            dog_amp  = 32.0 if is_sprinting else 22.0
            walk_time += dt * dog_freq

            if leg_left:   leg_left.rotation_x = math.sin(walk_time) * dog_amp
            if leg_back_r: leg_back_r.rotation_x = math.sin(walk_time) * dog_amp
            if leg_right:  leg_right.rotation_x = -math.sin(walk_time) * dog_amp
            if leg_back_l: leg_back_l.rotation_x = -math.sin(walk_time) * dog_amp

            # Happy wagging tail while trotting
            if tail_entity:
                tail_entity.rotation_y = math.sin(walk_time * 2.2) * 35.0
            # Head bobbing
            if arm_left:
                arm_left.rotation_x = math.sin(walk_time * 2.0) * 8.0
        else:
            anim_speed = 20.0 if is_sprinting else 12.0
            walk_time += dt * anim_speed
            swing_amp = 38.0 if is_sprinting else 22.0

            if leg_left:  leg_left.rotation_x = math.sin(walk_time) * swing_amp
            if leg_right: leg_right.rotation_x = -math.sin(walk_time) * swing_amp

            if not is_attacking and not is_blocking and _whistle_remaining <= 0:
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
        if selected_char == 'perrito':
            if leg_left:   leg_left.rotation_x = lerp(leg_left.rotation_x, 0, dt * 10)
            if leg_right:  leg_right.rotation_x = lerp(leg_right.rotation_x, 0, dt * 10)
            if leg_back_l: leg_back_l.rotation_x = lerp(leg_back_l.rotation_x, 0, dt * 10)
            if leg_back_r: leg_back_r.rotation_x = lerp(leg_back_r.rotation_x, 0, dt * 10)
            if tail_entity:
                tail_entity.rotation_y = math.sin(time.time() * 5.0) * 20.0
            if arm_left:
                arm_left.rotation = Vec3(0, 0, 0)
            if weapon_arm and not is_attacking and not is_blocking:
                weapon_arm.rotation = Vec3(0, 0, 0)
        else:
            if leg_left:  leg_left.rotation_x = lerp(leg_left.rotation_x, 0, dt * 10)
            if leg_right: leg_right.rotation_x = lerp(leg_right.rotation_x, 0, dt * 10)

            if not is_attacking and not is_blocking and _whistle_remaining <= 0:
                if arm_left:   arm_left.rotation = Vec3(0, 0, 0)
                if weapon_arm: weapon_arm.rotation = Vec3(0, 0, 0)

    # -------------------------------------------------------
    # CHARACTER COLLISIONS (Push apart players & bots)
    # -------------------------------------------------------
    resolve_collisions()

    # -------------------------------------------------------
    # MULTIPLAYER SNAPSHOT UPDATE (Full movement & combat state sync)
    # -------------------------------------------------------
    if network_role and player:
        with network_snapshot_lock:
            network_local_snapshot = {
                'x': float(player.x),
                'y': float(player.y),
                'z': float(player.z),
                'yaw': float(player.rotation_y),
                'attack_seq': int(network_attack_sequence),
                'char': str(selected_char),
                'moving': bool(is_moving) if 'is_moving' in locals() else False,
                'sprinting': bool(is_sprinting) if 'is_sprinting' in locals() else False,
                'blocking': bool(is_blocking),
                'attacking': bool(is_attacking),
                'hp': float(player_hp),
            }


if __name__ == '__main__':
    # Initialize the main menu and its slowly orbiting arena panorama.
    show_main_menu()

    # =============================================================================
    # RUN
    # =============================================================================
    app.run()
