from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import json
import math
import random
import heapq
import socket
import threading
import os
from direct.interval.IntervalGlobal import Parallel, LerpHprInterval, LerpPosInterval, LerpQuatInterval
from panda3d.core import Quat

# High, unprivileged port so Windows does not require admin rights.
LAN_PORT = 55600
lan_role = None
lan_target_ip = None
lan_server_socket = None
lan_peer_socket = None
network_connected = False
network_send_timer = 0
network_packet_lock = threading.Lock()
latest_network_packet = None
remote_player_state = None
remote_monster_state = None
remote_player_health = 100
remote_player_crouching = False
remote_player_name = "Friend"

current_save_slot = 1
loaded_save_data = None


def safe_entity(model_path, **kwargs):
    try:
        return Entity(model=model_path, **kwargs)
    except Exception as exc:
        print(f"Failed to load model '{model_path}': {exc}")
        return Entity(model='cube', **kwargs)


def animate_node_break(node, pos_delta, hpr_delta, duration=0.18):
    start_pos = node.getPos()
    start_hpr = node.getHpr()
    Parallel(
        LerpPosInterval(node, duration, start_pos + pos_delta, startPos=start_pos),
        LerpHprInterval(node, duration, start_hpr + hpr_delta, startHpr=start_hpr),
    ).start()


def animate_node_quat(node, axis, angle, duration=0.28):
    start_quat = node.getQuat()
    delta = Quat()
    delta.setFromAxisAngle(angle, axis)
    end_quat = start_quat * delta
    LerpQuatInterval(node, duration, end_quat, startQuat=start_quat).start()


def hide_node_later(node, delay):
    invoke(node.hide, delay=delay)


def save_game():
    global current_save_slot
    # We need to access player, player_health, etc. which are initialized later.
    # Ursina globals are accessible once the script reaches that point.
    data = {
        'x': player.x,
        'y': player.y,
        'z': player.z,
        'ry': player.rotation_y,
        'health': player_health,
        'axe_picked_up': axe_picked_up
    }
    filename = f"save_slot{current_save_slot}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
        print(f"Game saved to {filename}")
        save_notification.enabled = True
        save_notification.text = f"SAVED TO SLOT {current_save_slot}"
        invoke(setattr, save_notification, 'enabled', False, delay=2)
    except Exception as e:
        print(f"Failed to save game: {e}")


def load_game_state():
    global player_health, axe_picked_up, loaded_save_data, selected_hotbar_slot
    if not loaded_save_data:
        return

    data = loaded_save_data
    player.position = (data.get('x', player.x), data.get('y', player.y), data.get('z', player.z))
    player.rotation_y = data.get('ry', player.rotation_y)
    player_health = data.get('health', 100)
    axe_picked_up = data.get('axe_picked_up', False)

    if axe_picked_up:
        selected_hotbar_slot = 1
        if axe_world:
            axe_world.enabled = False
            axe_world.collider = None
        axe_hand.enabled = True
        hotbar_labels[0].text = ''
        if hotbar_icons[0]:
            hotbar_icons[0].enabled = True
    update_hud()



# --- TERMINAL STARTUP MENU ---
def get_local_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def start_lan_host():
    global lan_server_socket, lan_peer_socket, network_connected
    lan_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lan_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lan_server_socket.bind(("0.0.0.0", LAN_PORT))
    lan_server_socket.listen(1)

    def wait_for_friend():
        global lan_peer_socket, network_connected
        print(f"LAN host ready on {get_local_ip()}:{LAN_PORT}")
        print("No admin rights needed for this port.")
        print(f"Listening on port {LAN_PORT}...")
        print("Waiting for friend to join...")
        try:
            lan_peer_socket, addr = lan_server_socket.accept()
            network_connected = True
            print(f"Friend connected from {addr[0]}")
            start_network_receiver(lan_peer_socket)
        except OSError as exc:
            print(f"LAN host stopped: {exc}")

    threading.Thread(target=wait_for_friend, daemon=True).start()


def join_lan_game(host_ip):
    global lan_peer_socket, network_connected
    lan_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lan_peer_socket.settimeout(15)
    print(f"Connecting to {host_ip}:{LAN_PORT}...")
    try:
        lan_peer_socket.connect((host_ip, LAN_PORT))
        lan_peer_socket.settimeout(None)
        network_connected = True
        print("Found host -> ", host_ip)
        start_network_receiver(lan_peer_socket)
        print("Connected to host!")
        return True
    except OSError as exc:
        print(f"Could not connect to {host_ip}:{LAN_PORT} ({exc})")
        print("If the IP is correct, check Windows Firewall and make sure both laptops are on the same Wi-Fi/LAN.")
        lan_peer_socket.close()
        lan_peer_socket = None
        return False


def start_network_receiver(sock):
    def receive_loop():
        global network_connected, latest_network_packet
        buffer = ""
        while True:
            try:
                data = sock.recv(4096)
            except OSError:
                break

            if not data:
                break

            buffer += data.decode("utf-8", errors="ignore")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    packet = json.loads(line)
                except json.JSONDecodeError:
                    continue
                with network_packet_lock:
                    latest_network_packet = packet

        network_connected = False

    threading.Thread(target=receive_loop, daemon=True).start()


def send_network_state(payload):
    if not lan_peer_socket or not network_connected:
        return

    try:
        lan_peer_socket.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    except OSError:
        pass


def startup_menu():
    global current_save_slot, loaded_save_data
    print("=== HORROR STARTUP ===")
    username = "Player"

    while True:
        print("Choose mode:")
        print("1) Single Player")
        print("2) LAN")
        try:
            choice = input("Select 1 or 2: ").strip().lower()
        except EOFError:
            choice = "1"

        if choice in ("1", "single", "single player", "singleplayer"):
            while True:
                print("\n--- SINGLE PLAYER SLOTS ---")
                for i in range(1, 4):
                    filename = f"save_slot{i}.json"
                    status = "(Existing Save)" if os.path.exists(filename) else "(Empty)"
                    print(f"{i}) Slot {i} {status}")
                print("b) Back")

                slot_choice = input("Select slot (1-3) or 'b': ").strip().lower()
                if slot_choice == 'b':
                    break
                if slot_choice in ("1", "2", "3"):
                    current_save_slot = int(slot_choice)
                    filename = f"save_slot{current_save_slot}.json"
                    if os.path.exists(filename):
                        try:
                            with open(filename, 'r') as f:
                                loaded_save_data = json.load(f)
                        except:
                            print("Error reading save file.")
                    return username, "single_player", None
            continue

        if choice in ("2", "lan"):
            try:
                username = input("Enter username for LAN: ").strip() or "Player"
            except EOFError:
                username = "Player"

            while True:
                print("LAN mode:")
                print("1) Host")
                print("2) Join")
                try:
                    lan_choice = input("Select 1 or 2: ").strip().lower()
                except EOFError:
                    lan_choice = "1"

                if lan_choice in ("1", "host"):
                    start_lan_host()
                    return username, "lan", "host"

                if lan_choice in ("2", "join"):
                    try:
                        host_ip = input("Enter host IP address: ").strip()
                    except EOFError:
                        host_ip = ""
                    if not host_ip:
                        print("No IP entered. Try again.")
                        continue
                    if join_lan_game(host_ip):
                        return username, "lan", "join"
                    continue

                print("Please enter 1 or 2.")

        print("Please enter 1 or 2.")


user_name, game_mode, lan_role = startup_menu()

# Initialize the engine
app = Ursina()
window.icon = 'image.ico'
background_music = Audio('horror.mp3', loop=True, autoplay=True, volume=0.6)
low_health_sound = Audio('lwhealth.mp3', loop=True, autoplay=False, volume=0.8)


# --- RENDER DISTANCE (OPTIMIZATION) ---
camera.clip_plane_far = 30 # <--- Reduced to 20 for maximum performance!

# --- ATMOSPHERE ---
window.color = color.black
# Increased fog density so the 20-unit cutoff is hidden by thick mist
scene.fog_density = 0.10
scene.fog_color = color.black

# --- THE ENVIRONMENT ---
ground = Entity(
    model='cube',  
    scale=(200, 1, 200), 
    color=color.rgb(10/255, 30/255, 10/255), 
    texture='white_cube', 
    texture_scale=(200, 200), 
    collider='box'
)

# --- MAP WALLS ---
map_bounds = 100
wall_thickness = 2
wall_height = 10
wall_color = color.rgb(25/255, 35/255, 25/255)

wall_north = Entity(model='cube', scale=(200, wall_height, wall_thickness), position=(0, wall_height / 2, map_bounds), color=wall_color, collider='box')
wall_south = Entity(model='cube', scale=(200, wall_height, wall_thickness), position=(0, wall_height / 2, -map_bounds), color=wall_color, collider='box')
wall_east = Entity(model='cube', scale=(wall_thickness, wall_height, 200), position=(map_bounds, wall_height / 2, 0), color=wall_color, collider='box')
wall_west = Entity(model='cube', scale=(wall_thickness, wall_height, 200), position=(-map_bounds, wall_height / 2, 0), color=wall_color, collider='box')
world_walls = [wall_north, wall_south, wall_east, wall_west]

# Leave an opening in the north wall for the gate.
GATE_OPENING_WIDTH = 120
wall_north.enabled = False
north_wall_side_width = (200 - GATE_OPENING_WIDTH) / 2
wall_north_left = Entity(
    model='cube',
    scale=(north_wall_side_width, wall_height, wall_thickness),
    position=(-((200 + GATE_OPENING_WIDTH) / 4), wall_height / 2, map_bounds),
    color=wall_color,
    collider='box'
)
wall_north_right = Entity(
    model='cube',
    scale=(north_wall_side_width, wall_height, wall_thickness),
    position=((200 + GATE_OPENING_WIDTH) / 4, wall_height / 2, map_bounds),
    color=wall_color,
    collider='box'
)
world_walls = [wall_north_left, wall_north_right, wall_south, wall_east, wall_west]

gate_model = safe_entity(
    'mdels/gate1.gltf',
    position=(0, wall_height / 2, map_bounds),
    scale=5,
    collider='box',
    texture='mdels/gate1_tex1.png',
    color=color.white
)

# --- LAND MODEL PLACEMENT ---
# Place the stripped land_static.glb structure in a dedicated clearing at (50, 0, 50)
LAND_POS = (50, 0, 50)
LAND_CLEAR_RADIUS = 22  # No trees spawn within this radius

land_model = safe_entity(
    'mdels/land_static.glb',
    position=LAND_POS,
    scale=4,
    color=color.white
)

# Invisible Ursina Entity used only for raycast hit detection
land_collider = Entity(
    position=LAND_POS,
    collider='box',
    scale=(18, 15, 18),
    visible=False
)

door_hit_count = 0
land_animation_enabled = True
land_door_node = None
land_door_base = None
land_door_open = False
land_break_nodes = {}
land_break_base = {}

door_matches = land_model.model.findAllMatches('**/group')
if door_matches.getNumPaths() > 0:
    door_node = door_matches.getPath(0)
    if door_node is not None and not door_node.isEmpty():
        land_door_node = door_node
        land_door_base = (door_node.getPos(), door_node.getHpr())

for anim_name, node_name in (
    ('brke1', 'group9'),
    ('brke2', 'group10'),
    ('brke3', 'group11'),
):
    matches = land_model.model.findAllMatches(f'**/{node_name}')
    if matches.getNumPaths() > 0:
        node = matches.getPath(0)
    else:
        node = None

    if node is not None and not node.isEmpty():
        land_break_nodes[anim_name] = node
        land_break_base[anim_name] = (node.getPos(), node.getHpr())


def play_land_anim(name):
    global land_animation_enabled, land_door_open
    if not land_animation_enabled:
        return
    try:
        if name == 'door' and land_door_node and land_door_base:
            land_door_node.setPos(land_door_base[0])
            land_door_node.setHpr(land_door_base[1])
            animate_node_quat(land_door_node, Vec3(0, 1, 0), -72, duration=0.28)
            land_door_open = True
            invoke(setattr, land_collider, 'collider', None, delay=0.30)
            invoke(setattr, land_collider, 'visible', False, delay=0.30)
            return

        node = land_break_nodes.get(name)
        base = land_break_base.get(name)
        if not node or not base:
            return

        node.setPos(base[0])
        node.setHpr(base[1])
        if name == 'brke1':
            animate_node_break(node, Vec3(-0.08, -0.22, 0.10), Vec3(-8, 16, -18))
            hide_node_later(node, 0.32)
        elif name == 'brke2':
            animate_node_break(node, Vec3(0.00, -0.32, 0.00), Vec3(0, 24, 0))
            hide_node_later(node, 0.32)
        elif name == 'brke3':
            animate_node_break(node, Vec3(0.08, -0.40, -0.10), Vec3(8, 34, 18))
            hide_node_later(node, 0.32)
    except Exception as e:
        print(f'Animation [{name}] error: {e}')
        land_animation_enabled = False


# --- DENSE FOREST GENERATION ---
# We will generate hundreds of trees to make it a dense forest
tree_positions = []
for i in range(400):
    tx = random.uniform(-90, 90)
    tz = random.uniform(-90, 90)

    # Leave a small clearing in the middle for the player and monster
    if abs(tx) < 10 and abs(tz) < 15:
        continue

    # Leave a clearing around the land model
    if math.hypot(tx - LAND_POS[0], tz - LAND_POS[2]) < LAND_CLEAR_RADIUS:
        continue

    # Randomize tree sizes to make it look natural
    tree_height = random.uniform(6, 15)
    trunk_thickness = random.uniform(0.5, 1)
    
    # Creepy dark tree trunk
    tree = Entity(
        model='cube',
        color=color.rgb(30/255, 20/255, 15/255),
        scale=(trunk_thickness, tree_height, trunk_thickness),
        position=(tx, tree_height / 2, tz),
        collider='box',
        rotation_y=random.uniform(0, 360)
    )
    tree_positions.append((tx, tz))
    
# Dark, shadowy leaves at the top
    leaves = Entity(
        parent=tree,
        model='sphere',
        color=color.rgb(15/255, 40/255, 15/255), 
        scale=(3, 0.6, 3), # Scale is relative to the parent trunk
        y=0.4 # Positioned near the top
    )

# Pathfinding grid settings.
GRID_SIZE = 4
TREE_RADIUS = 2.8

# Cache blocked path cells so pathfinding doesn't rescan every tree each frame.
blocked_cells = set()

cross_markers = []
LAND_PROP_CLEAR_RADIUS = 34
for gx in range(-90, 91, 10):
    for gz in range(-90, 91, 10):
        if abs(gx) < 10 and abs(gz) < 15:
            continue
        if math.hypot(gx - LAND_POS[0], gz - LAND_POS[2]) < LAND_PROP_CLEAR_RADIUS:
            continue
        if random.random() < 0.30:
            continue
        jitter_x = random.uniform(-4, 4)
        jitter_z = random.uniform(-4, 4)
        stretch_y = random.uniform(2.4, 3.3)
        cross_markers.append(safe_entity(
            'mdels/tmpdwfhail6.glb',
            position=(gx + jitter_x, 0.50, gz + jitter_z),
            scale=(random.uniform(2.1, 2.8), stretch_y, random.uniform(2.1, 2.8)),
            rotation_x=-45,
            collider='box',
            color=color.white
        ))
        rock_grid_x = round(gx / GRID_SIZE)
        rock_grid_z = round(gz / GRID_SIZE)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                blocked_cells.add((rock_grid_x + dx, rock_grid_z + dz))

random_rock_x = random.choice([-1, 1]) * random.uniform(72, 86)
random_rock_z = random.choice([-1, 1]) * random.uniform(72, 86)
if not (abs(random_rock_x) < 10 and abs(random_rock_z) < 15) and math.hypot(random_rock_x - LAND_POS[0], random_rock_z - LAND_POS[2]) >= LAND_PROP_CLEAR_RADIUS:
    axe_world = safe_entity(
        'mdels/tmp4ehe8uj8.glb',
        position=(random_rock_x, 1.15, random_rock_z),
        scale=(3.2, 3.2, 3.2),
        rotation=(0, 0, 90),
        collider='box',
        color=color.white
    )
    random_rock_grid_x = round(random_rock_x / GRID_SIZE)
    random_rock_grid_z = round(random_rock_z / GRID_SIZE)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            blocked_cells.add((random_rock_grid_x + dx, random_rock_grid_z + dz))
else:
    axe_world = None

GRID_PADDING = int(math.ceil(TREE_RADIUS / GRID_SIZE)) + 1
for tx, tz in tree_positions:
    gx = round(tx / GRID_SIZE)
    gz = round(tz / GRID_SIZE)
    for dx in range(-GRID_PADDING, GRID_PADDING + 1):
        for dz in range(-GRID_PADDING, GRID_PADDING + 1):
            blocked_cells.add((gx + dx, gz + dz))

# --- THE MONSTER MODEL ---
monster = Entity(
    position=(0, 2, 0),
    scale=2.4,
    rotation_y=270
)
MONSTER_FACE_OFFSET = 45
MONSTER_TURN_SPEED = 8
MONSTER_RUN_SPEED = 6
monster_run_phase = 0

monster_body = safe_entity(
    'mdels/tmp_k7h6836.glb',
    parent=monster,
    scale=2.0,
    position=(0, 0, 0)
)

# --- THE PLAYER ---
player = FirstPersonController()
player.cursor.color = color.white
player.gravity = 1
player_legs = Entity(parent=player, model='cube', color=color.blue, scale=(0.8, 0.6, 0.4), position=(0, 0.3, 0))
player_torso = Entity(parent=player, model='cube', color=color.red, scale=(1, 0.8, 0.5), position=(0, 1, 0))
player_head = Entity(parent=player, model='cube', color=color.yellow, scale=(0.6, 0.6, 0.6), position=(0, 1.7, 0))
player_name_tag = Text(text=user_name, parent=player, position=(0, 3, 0), scale=10, origin=(0, 0), color=color.white)
remote_player = Entity(position=(0, -1000, 0), enabled=False)
remote_player_legs = Entity(parent=remote_player, model='cube', color=color.blue, scale=(0.8, 0.6, 0.4), position=(0, 0.3, 0))
remote_player_torso = Entity(parent=remote_player, model='cube', color=color.red, scale=(1, 0.8, 0.5), position=(0, 1, 0))
remote_player_head = Entity(parent=remote_player, model='cube', color=color.yellow, scale=(0.6, 0.6, 0.6), position=(0, 1.7, 0))
remote_player_name_tag = Text(text="Friend", parent=remote_player, position=(0, 3, 0), scale=10, origin=(0, 0), color=color.white, enabled=False)
axe_hand = safe_entity(
    'mdels/tmp4ehe8uj8.glb',
    parent=camera,
    position=(0.78, -0.65, 1.10),
    rotation=(0, 90, 0),
    scale=(0.35, 0.35, 0.35),
    enabled=False
)
# Starting position in the small clearing facing the monster
PLAYER_SPAWN_POS = Vec3(-12, 12, -12)
player.position = PLAYER_SPAWN_POS
player_default_height = player.height
player_default_pivot_y = player.camera_pivot.y
player_crouch_height = 1.1
player_crouch_pivot_y = 1.1
player_normal_fov = camera.fov
player_crouch_fov = 75
spawn_protection_timer = 8.0
fly_mode = False
fly_exit_protection_timer = 0.0
fly_speed = 10

player_health = 100
player_stamina = 100
player_max_stamina = 100
player_attack_cooldown = 0
stamina_rest_timer = 0
stamina_flash_timer = 0
game_over = False
spawn_protection_timer = 8.0
STAMINA_DRAIN_RATE = 3
WALK_STAMINA_DRAIN_RATE = 1
STAMINA_REGEN_RATE = 20
STAMINA_REST_DELAY = 2
STAMINA_FLASH_TIME = 0.22

HUD_BAR_WIDTH = 0.34
HUD_BAR_HEIGHT = 0.025
HUD_RIGHT_X = 0.30

health_label = Text(
    text='HEALTH',
    parent=camera.ui,
    origin=(0, 0),
    scale=0.9,
    position=(0.44, 0.46),
    color=color.white
)

health_bar_fill = Entity(
    parent=camera.ui,
    model='quad',
    color=color.rgb(106/255, 111/255, 63/255),
    scale=(HUD_BAR_WIDTH, HUD_BAR_HEIGHT),
    position=(HUD_RIGHT_X, 0.40),
    origin=(-0.5, 0),
)

stamina_label = Text(
    text='STAMINA',
    parent=camera.ui,
    origin=(0, 0),
    scale=0.9,
    position=(0.437, 0.355),
    color=color.white
)


stamina_bar_fill = Entity(
    parent=camera.ui,
    model='quad',
    color=color.rgb(139/255, 145/255, 173/255),
    scale=(HUD_BAR_WIDTH, HUD_BAR_HEIGHT),
    position=(HUD_RIGHT_X, 0.29),
    origin=(-0.5, 0),
)

stamina_value_text = Text(
    text='100%',
    parent=camera.ui,
    origin=(0, 0),
    scale=0.9,
    position=(0.70, 0.29),
    color=color.white
)

selected_hotbar_slot = 1
axe_picked_up = False
hotbar_slots = []
hotbar_labels = []
hotbar_icons = []
hotbar_base_colors = [
    color.rgb(36, 36, 36),
    color.rgb(36, 36, 36),
    color.rgb(36, 36, 36),
    color.rgb(36, 36, 36),
]
hotbar_selected_color = color.rgb(160, 110, 30)
hotbar_xs = [-0.18, -0.06, 0.06, 0.18]
for i in range(4):
    slot = Entity(
        parent=camera.ui,
        model='quad',
        scale=(0.085, 0.085),
        position=(hotbar_xs[i], -0.46),
        color=hotbar_base_colors[i],
        origin=(0, 0),
        z=1
    )
    slot.alpha = 0.35
    label = Text(
        text=str(i + 1),
        parent=slot,
        origin=(0, 0),
        scale=1.0,
        position=(0, 0),
        color=color.rgba(255, 255, 255, 200)
    )
    hotbar_slots.append(slot)
    hotbar_labels.append(label)
    icon = None
    if i == 0:
        icon = safe_entity(
            'mdels/tmp4ehe8uj8.glb',
            parent=slot,
            position=(0, 0, -0.01),
            rotation=(0, 90, 0),
            scale=(0.22, 0.22, 0.22),
            enabled=False
        )
    hotbar_icons.append(icon)

door_prompt = Text(
    text='PRESS [F] TO OPEN DOOR',
    parent=camera.ui,
    origin=(0, 0),
    scale=1.0,
    position=(0, -0.28),
    color=color.white,
    enabled=False
)

axe_prompt = Text(
    text='PRESS [F] TO PICKUP AXE',
    parent=camera.ui,
    origin=(0, 0),
    scale=1.0,
    position=(0, -0.28),
    color=color.white,
    enabled=False
)

inventory_open = False
inventory_panel = Entity(
    parent=camera.ui,
    model='quad',
    color=color.rgba(10, 10, 10, 180),
    scale=(0.78, 0.48),
    position=(0, 0.05),
    enabled=False
)
inventory_title = Text(
    text='INVENTORY',
    parent=camera.ui,
    origin=(0, 0),
    scale=1.2,
    position=(0, 0.24),
    color=color.white,
    enabled=False
)
inventory_slots = []
inventory_labels = []
inventory_cols = 5
inventory_rows = 3
inventory_spacing_x = 0.105
inventory_spacing_y = 0.11
inventory_start_x = -0.21
inventory_start_y = 0.11
for row in range(inventory_rows):
    for col in range(inventory_cols):
        index = row * inventory_cols + col + 1
        slot = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(40, 40, 40, 170),
            scale=(0.09, 0.09),
            position=(inventory_start_x + col * inventory_spacing_x, inventory_start_y - row * inventory_spacing_y),
            enabled=False
        )
        slot.alpha = 0.4
        label = Text(
            text=str(index),
            parent=slot,
            origin=(0, 0),
            scale=0.9,
            position=(0, 0),
            color=color.rgba(255, 255, 255, 180),
            enabled=False
        )
        inventory_slots.append(slot)
        inventory_labels.append(label)

vignette_top = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(2.2, 0.18), position=(0, 0.52), z=1)
vignette_bottom = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(2.2, 0.18), position=(0, -0.52), z=1)
vignette_left = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(0.18, 1.2), position=(-1.02, 0), z=1)
vignette_right = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(0.18, 1.2), position=(1.02, 0), z=1)
jumpscare_overlay = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(2.6, 1.6), z=-10)
jumpscare_text = Text(
    text='GET OUT',
    parent=camera.ui,
    origin=(0, 0),
    scale=3.2,
    position=(0, 0.02),
    color=color.rgba(255, 255, 255, 0)
)

save_notification = Text(
    text='GAME SAVED',
    parent=camera.ui,
    origin=(0, 0),
    scale=1.5,
    position=(0, 0.35),
    color=color.green,
    enabled=False
)

save_button = Button(
    text='SAVE GAME',
    parent=camera.ui,
    scale=(0.25, 0.08),
    position=(0, -0.42),
    color=color.azure,
    enabled=False
)
save_button.on_click = save_game

respawn_overlay = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(2.6, 1.6), z=5, enabled=False)
respawn_title = Text(
    text='YOU DIED',
    parent=camera.ui,
    origin=(0, 0),
    scale=2.4,
    position=(0, 0.12),
    color=color.white,
    z=20,
    enabled=False
)
respawn_button = Button(
    text='RESPAWN',
    parent=camera.ui,
    scale=(0.24, 0.09),
    position=(0, -0.03),
    color=color.rgb(110, 20, 20),
    highlight_color=color.rgb(160, 40, 40),
    pressed_color=color.rgb(70, 10, 10),
    text_color=color.white,
    z=20,
    enabled=False
)

# --- MONSTER PATHFINDING ---
WORLD_MIN = -96
WORLD_MAX = 96
monster_path = []
path_repath_timer = 0
path_repath_interval = 0.35
monster_fog_stop_distance = 24
monster_detection_range = 60
monster_crouch_detection_range = 10
monster_attack_range = 2.3
monster_attack_damage = 25
monster_attack_interval = 0.8
jumpscare_trigger_distance = 4.5
jumpscare_reset_distance = 7.0
jumpscare_duration = 0.85
jumpscare_timer = 0
jumpscare_active = False
jumpscare_armed = True
monster_search_mode = False
monster_search_timer = 0
monster_search_duration = 8.0
monster_search_repath_timer = 0
monster_last_seen_pos = Vec3(0, 2, 0)
monster_search_target = Vec3(0, 2, 0)
monster_search_radius = 12.0
monster_search_radius_max = 48.0
monster_search_radius_growth = 7


def clamp_world_pos(pos):
    return Vec3(
        clamp(pos.x, WORLD_MIN * GRID_SIZE, WORLD_MAX * GRID_SIZE),
        pos.y,
        clamp(pos.z, WORLD_MIN * GRID_SIZE, WORLD_MAX * GRID_SIZE),
    )


def pick_search_target(center_world, radius):
    offset_x = random.uniform(-radius, radius)
    offset_z = random.uniform(-radius, radius)
    target = Vec3(center_world.x + offset_x, monster.y, center_world.z + offset_z)
    return clamp_world_pos(target)


def world_to_grid(x, z):
    return (round(x / GRID_SIZE), round(z / GRID_SIZE))


def grid_to_world(cell):
    return Vec3(cell[0] * GRID_SIZE, monster.y, cell[1] * GRID_SIZE)


def is_blocked(cell):
    x = int(cell[0])
    z = int(cell[1])
    if x < WORLD_MIN or x > WORLD_MAX or z < WORLD_MIN or z > WORLD_MAX:
        return True
    return (x, z) in blocked_cells


def get_neighbors(cell):
    x, z = cell
    neighbors = [
        (x + 1, z),
        (x - 1, z),
        (x, z + 1),
        (x, z - 1),
    ]

    diagonals = [
        (x + 1, z + 1),
        (x + 1, z - 1),
        (x - 1, z + 1),
        (x - 1, z - 1),
    ]

    for neighbor in diagonals:
        dx = neighbor[0] - x
        dz = neighbor[1] - z
        if not is_blocked(neighbor) and not is_blocked((x + dx, z)) and not is_blocked((x, z + dz)):
            neighbors.append(neighbor)

    return neighbors


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def build_path(start_world, goal_world):
    start = world_to_grid(start_world.x, start_world.z)
    goal = world_to_grid(goal_world.x, goal_world.z)

    open_heap = []
    heapq.heappush(open_heap, (0, start))
    came_from = {}
    g_score = {start: 0}
    closed = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        if current in closed:
            continue
        closed.add(current)

        for neighbor in get_neighbors(current):
            if neighbor in closed or is_blocked(neighbor):
                continue

            step_cost = 1.4 if neighbor[0] != current[0] and neighbor[1] != current[1] else 1.0
            tentative_g = g_score[current] + step_cost

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f_score, neighbor))

    return []


def face_target(target):
    dx = target.x - monster.x
    dz = target.z - monster.z
    if dx == 0 and dz == 0:
        return

    desired_yaw = math.degrees(math.atan2(dx, dz)) + MONSTER_FACE_OFFSET
    monster.rotation_y = lerp_angle(monster.rotation_y, desired_yaw, time.dt * MONSTER_TURN_SPEED)


def set_crouch_state(active):
    if active:
        player.height = player_crouch_height
        player.camera_pivot.y = player_crouch_pivot_y
        camera.fov = player_crouch_fov
    else:
        player.height = player_default_height
        player.camera_pivot.y = player_default_pivot_y
        camera.fov = player_normal_fov


def get_host_monster_target():
    target_entity = player
    target_crouching = getattr(player, 'is_crouching', False)
    target_is_remote = False

    if game_mode == 'lan' and lan_role == 'host' and network_connected and remote_player.enabled:
        local_distance = math.hypot(monster.x - player.x, monster.z - player.z)
        remote_distance = math.hypot(monster.x - remote_player.x, monster.z - remote_player.z)
        if remote_distance < local_distance:
            target_entity = remote_player
            target_crouching = remote_player_crouching
            target_is_remote = True

    return target_entity, target_crouching, target_is_remote


def apply_network_packet():
    global latest_network_packet, remote_player_state, remote_monster_state
    global remote_player_health, remote_player_crouching, remote_player_name, player_health

    with network_packet_lock:
        packet = latest_network_packet
        latest_network_packet = None

    if not packet or packet.get('type') != 'state':
        return

    remote_player_name = packet.get('name', 'Friend')
    remote_player.enabled = True
    remote_player_name_tag.enabled = True
    remote_player_name_tag.text = remote_player_name

    remote_player_state = {
        'x': packet.get('x', 0),
        'y': packet.get('y', 0),
        'z': packet.get('z', 0),
        'ry': packet.get('ry', 0),
        'crouch': bool(packet.get('crouch', False)),
    }

    remote_player_crouching = remote_player_state['crouch']
    remote_player.position = (
        remote_player_state['x'],
        remote_player_state['y'] - (0.45 if remote_player_crouching else 0),
        remote_player_state['z']
    )
    remote_player.rotation_y = remote_player_state['ry']
    remote_player.scale_y = 0.78 if remote_player_crouching else 1.0

    remote_player_health = int(packet.get('health', remote_player_health))

    if lan_role == 'join':
        remote_monster_state = {
            'x': packet.get('monster_x', monster.x),
            'y': packet.get('monster_y', monster.y),
            'z': packet.get('monster_z', monster.z),
            'ry': packet.get('monster_ry', monster.rotation_y),
            'moving': bool(packet.get('monster_moving', False)),
        }
        monster.position = (remote_monster_state['x'], remote_monster_state['y'], remote_monster_state['z'])
        monster.rotation_y = remote_monster_state['ry']
        player_health = remote_player_health
        if player_health <= 0 and not game_over:
            trigger_game_over()


def broadcast_network_state(is_moving):
    if game_mode != 'lan' or not network_connected:
        return

    payload = {
        'type': 'state',
        'name': user_name,
        'x': player.x,
        'y': player.y,
        'z': player.z,
        'ry': player.rotation_y,
        'crouch': getattr(player, 'is_crouching', False),
        'health': player_health if lan_role == 'join' else remote_player_health,
    }

    if lan_role == 'host':
        payload.update({
            'monster_x': monster.x,
            'monster_y': monster.y,
            'monster_z': monster.z,
            'monster_ry': monster.rotation_y,
            'monster_moving': is_moving,
        })

    send_network_state(payload)


def update_hud():
    health_ratio = clamp(player_health / 100, 0, 1)
    stamina_ratio = clamp(player_stamina / player_max_stamina, 0, 1)

    health_bar_fill.scale_x = HUD_BAR_WIDTH * health_ratio
    health_bar_fill.x = HUD_RIGHT_X

    stamina_bar_fill.scale_x = HUD_BAR_WIDTH * stamina_ratio
    stamina_bar_fill.x = HUD_RIGHT_X
    stamina_value_text.text = f'{int(stamina_ratio * 100)}%'
    if stamina_flash_timer > 0:
        flash_amount = clamp(stamina_flash_timer / STAMINA_FLASH_TIME, 0, 1)
        stamina_bar_fill.color = color.rgb(255, int(60 + 120 * flash_amount), int(60 + 30 * flash_amount))
    else:
        stamina_bar_fill.color = color.rgb(60, 200, 180)

    vignette_alpha = 85 if player.is_crouching else 0

    vignette_color = color.rgba(0, 0, 0, vignette_alpha)
    vignette_top.color = vignette_color
    vignette_bottom.color = vignette_color
    vignette_left.color = vignette_color
    vignette_right.color = vignette_color

    for index, slot in enumerate(hotbar_slots, start=1):
        if index == selected_hotbar_slot:
            slot.color = hotbar_selected_color
            slot.scale = (0.092, 0.092)
            slot.alpha = 0.5
        else:
            slot.color = hotbar_base_colors[index - 1]
            slot.scale = (0.085, 0.085)
            slot.alpha = 0.35

    axe_hand.enabled = axe_picked_up and selected_hotbar_slot == 1


def set_gameplay_ui_enabled(enabled):
    health_label.enabled = enabled
    health_bar_fill.enabled = enabled
    stamina_label.enabled = enabled
    stamina_bar_fill.enabled = enabled
    stamina_value_text.enabled = enabled
    vignette_top.enabled = enabled
    vignette_bottom.enabled = enabled
    vignette_left.enabled = enabled
    vignette_right.enabled = enabled
    for slot in hotbar_slots:
        slot.enabled = enabled
        for child in slot.children:
            child.enabled = enabled


def show_inventory():
    global inventory_open
    inventory_open = True
    inventory_panel.enabled = True
    inventory_title.enabled = True
    for slot in inventory_slots:
        slot.enabled = True
    for label in inventory_labels:
        label.enabled = True
    mouse.locked = False
    mouse.visible = True


def hide_inventory():
    global inventory_open
    inventory_open = False
    inventory_panel.enabled = False
    inventory_title.enabled = False
    for slot in inventory_slots:
        slot.enabled = False
    for label in inventory_labels:
        label.enabled = False


def show_respawn_menu():
    respawn_title.enabled = True
    respawn_button.enabled = True
    set_gameplay_ui_enabled(False)
    mouse.locked = False
    mouse.visible = True


def hide_respawn_menu():
    respawn_title.enabled = False
    respawn_button.enabled = False


def respawn_player():
    global player_health, player_stamina, player_attack_cooldown, stamina_rest_timer, stamina_flash_timer
    global game_over, jumpscare_active, jumpscare_timer, jumpscare_armed, monster_path, path_repath_timer, spawn_protection_timer
    global monster_search_mode, monster_search_timer, monster_search_repath_timer, monster_search_target, monster_last_seen_pos, monster_search_radius

    game_over = False
    jumpscare_active = False
    jumpscare_timer = 0
    jumpscare_armed = True
    monster_path = []
    path_repath_timer = 0
    monster_search_mode = False
    monster_search_timer = 0
    monster_search_repath_timer = 0
    monster_last_seen_pos = Vec3(player.position.x, monster.y, player.position.z)
    monster_search_target = monster_last_seen_pos
    monster_search_radius = 12.0

    player.position = PLAYER_SPAWN_POS
    player.rotation = (0, 0, 0)
    player.rotation_y = 0
    player.height = player_default_height
    player.camera_pivot.y = player_default_pivot_y
    camera.fov = player_normal_fov
    if hasattr(player, 'velocity'):
        player.velocity = Vec3(0, 0, 0)

    player_health = 100
    player_stamina = 100
    player_attack_cooldown = 0
    stamina_rest_timer = 0
    stamina_flash_timer = 0
    spawn_protection_timer = 8.0

    jumpscare_overlay.color = color.rgba(0, 0, 0, 0)
    jumpscare_text.color = color.rgba(255, 255, 255, 0)
    hide_inventory()
    hide_respawn_menu()
    set_gameplay_ui_enabled(True)
    mouse.locked = True
    mouse.visible = False
    update_hud()


def trigger_game_over():
    global game_over, jumpscare_active, jumpscare_timer
    if game_over:
        return
    game_over = True
    jumpscare_active = False
    jumpscare_timer = 0
    jumpscare_overlay.color = color.rgba(0, 0, 0, 0)
    jumpscare_text.color = color.rgba(255, 255, 255, 0)
    hide_inventory()
    hide_respawn_menu()
    show_respawn_menu()


respawn_button.on_click = respawn_player

# --- AXE SWING & DOOR BREAK ---
axe_swinging = False

def swing_axe():
    global axe_swinging
    if axe_swinging:
        return
    axe_swinging = True
    # Animate the hand axe forward (swing)
    axe_hand.animate('rotation_x', -55, duration=0.12, curve=curve.linear)
    invoke(reset_axe_swing, delay=0.22)


def reset_axe_swing():
    global axe_swinging
    axe_hand.animate('rotation_x', 0, duration=0.12, curve=curve.linear)
    axe_swinging = False


def check_door_hit():
    global door_hit_count
    hit = raycast(camera.world_position, camera.forward, distance=5, ignore=[player])
    if hit.hit and hit.entity == land_collider:
        return True
    return False

# --- THE MASTER GAME LOOP ---
def update():
    global monster_path, path_repath_timer, monster_run_phase, stamina_rest_timer, stamina_flash_timer, spawn_protection_timer
    global player_stamina, player_health, player_attack_cooldown, jumpscare_timer, jumpscare_active, jumpscare_armed, remote_player_health
    global monster_search_mode, monster_search_timer, monster_search_repath_timer, monster_search_target, monster_last_seen_pos, monster_search_radius
    global fly_mode, fly_exit_protection_timer

    if game_over:
        return

    spawn_protection_timer = max(0, spawn_protection_timer - time.dt)
    fly_exit_protection_timer = max(0, fly_exit_protection_timer - time.dt)

    player_name_tag.look_at(camera, Vec3.back)
    if remote_player.enabled:
        remote_player_name_tag.look_at(camera, Vec3.back)

    near_door = land_collider and distance(player.position, land_collider.position) < 10
    door_prompt.enabled = bool(near_door and not game_over and not inventory_open)
    near_axe = axe_world and not axe_picked_up and distance(player.position, axe_world.position) < 6
    axe_prompt.enabled = bool(near_axe and not game_over and not inventory_open)

    # If the player falls out of the map, treat it as death.
    if not fly_mode and fly_exit_protection_timer <= 0 and spawn_protection_timer <= 0 and player.y < -20:
        player_health = 0
        trigger_game_over()
        return

    # 1. Monster Breathing / Idle Animation
    monster.scale = 2 + math.sin(time.time() * 3) * 0.04

    # 2. Player movement states
    is_crouching = held_keys['shift']
    movement_now = getattr(player, 'direction', Vec3(0, 0, 0)).length() > 0.05
    is_sprinting = (held_keys['control'] or held_keys['left control'] or held_keys['right control']) and movement_now and not is_crouching
    player.is_crouching = is_crouching
    set_crouch_state(is_crouching)

    if is_crouching:
        player.speed = 2.25
        stamina_rest_timer = STAMINA_REST_DELAY
    elif movement_now and player_stamina > 0:
        stamina_rest_timer = STAMINA_REST_DELAY
        if is_sprinting:
            player.speed = 9
            player_stamina = max(0, player_stamina - STAMINA_DRAIN_RATE * time.dt)
            stamina_flash_timer = STAMINA_FLASH_TIME
        else:
            player.speed = 5
            player_stamina = max(0, player_stamina - WALK_STAMINA_DRAIN_RATE * time.dt)
            stamina_flash_timer = max(stamina_flash_timer, STAMINA_FLASH_TIME * 0.5)
    else:
        player.speed = 5
        stamina_rest_timer = max(0, stamina_rest_timer - time.dt)
        if stamina_rest_timer <= 0 and player_stamina < player_max_stamina:
            player_stamina = min(player_max_stamina, player_stamina + STAMINA_REGEN_RATE * time.dt)

    if fly_mode:
        player.gravity = 0
        if hasattr(player, 'velocity'):
            player.velocity = Vec3(0, 0, 0)
        player.speed = max(player.speed, 7)
        if held_keys['space']:
            player.y += fly_speed * time.dt
        if held_keys['left control'] or held_keys['right control']:
            player.y -= fly_speed * time.dt
    else:
        player.gravity = 1

    stamina_flash_timer = max(0, stamina_flash_timer - time.dt)

    apply_network_packet()
    is_network_join = game_mode == 'lan' and lan_role == 'join'
    is_moving = False

    # 3. Monster chase / network sync
    if is_network_join:
        if remote_monster_state:
            monster.position = (remote_monster_state['x'], remote_monster_state['y'], remote_monster_state['z'])
            monster.rotation_y = remote_monster_state['ry']
            is_moving = remote_monster_state['moving']
    else:
        target_entity, target_crouching, target_is_remote = get_host_monster_target()
        monster_distance = math.hypot(monster.x - target_entity.x, monster.z - target_entity.z)
        can_see_player = monster_distance <= monster_fog_stop_distance
        can_detect_player = monster_distance <= (monster_crouch_detection_range if target_crouching else monster_detection_range)
        should_chase = can_see_player and can_detect_player

        if spawn_protection_timer > 0:
            monster_path = []
            face_target(Vec3(target_entity.x, monster.y, target_entity.z))
            broadcast_network_state(False)
            update_hud()
            return

        if can_detect_player:
            monster_search_mode = False
            monster_search_timer = 0
            monster_search_repath_timer = 0
            monster_last_seen_pos = Vec3(target_entity.x, monster.y, target_entity.z)
            monster_search_radius = 12.0
        else:
            if not monster_search_mode:
                monster_search_mode = True
                monster_search_timer = monster_search_duration
                monster_search_repath_timer = 0
                monster_last_seen_pos = Vec3(target_entity.x, monster.y, target_entity.z)
                monster_search_radius = 12.0
                monster_search_target = Vec3(monster_last_seen_pos.x, monster.y, monster_last_seen_pos.z)

            monster_search_timer = max(0, monster_search_timer - time.dt)
            monster_search_radius = min(
                monster_search_radius_max,
                12.0 + (monster_search_duration - monster_search_timer) * monster_search_radius_growth
            )

            if (monster.position - monster_search_target).length() < 1.0:
                monster_search_target = pick_search_target(monster_last_seen_pos, monster_search_radius)
                monster_search_repath_timer = 1.5
            elif monster_search_repath_timer <= 0:
                monster_search_target = pick_search_target(monster_last_seen_pos, monster_search_radius)
                monster_search_repath_timer = 1.5

            monster_search_repath_timer = max(0, monster_search_repath_timer - time.dt)

        if not jumpscare_active and monster_distance > jumpscare_reset_distance:
            jumpscare_armed = True

        if jumpscare_armed and not jumpscare_active and monster_distance <= jumpscare_trigger_distance:
            jumpscare_active = True
            jumpscare_armed = False
            jumpscare_timer = jumpscare_duration
            monster_path = []
            if spawn_protection_timer <= 0 and target_is_remote:
                remote_player_health = max(0, remote_player_health - monster_attack_damage * 2)
            elif spawn_protection_timer <= 0:
                player_health = max(0, player_health - monster_attack_damage * 2)
            if not target_is_remote and player_health <= 0:
                trigger_game_over()
                return

        if jumpscare_active:
            jumpscare_timer -= time.dt
            scare_strength = clamp(jumpscare_timer / jumpscare_duration, 0, 1)
            jumpscare_overlay.color = color.rgba(160, 0, 0, int(220 * scare_strength))
            jumpscare_text.color = color.rgba(255, 255, 255, int(255 * scare_strength))
            camera.fov = lerp(camera.fov, player_normal_fov + 8, time.dt * 12)
            if jumpscare_timer <= 0:
                jumpscare_active = False
                jumpscare_overlay.color = color.rgba(0, 0, 0, 0)
                jumpscare_text.color = color.rgba(255, 255, 255, 0)
            update_hud()
            broadcast_network_state(False)
            return

        if not should_chase:
            monster_path = []

        path_repath_timer -= time.dt
        if should_chase:
            target_goal = target_entity.position
        else:
            target_goal = monster_search_target

        if path_repath_timer <= 0 or not monster_path:
            monster_path = build_path(monster.position, target_goal)
            path_repath_timer = path_repath_interval

        if monster_path:
            while len(monster_path) > 1:
                next_cell = monster_path[1]
                target = grid_to_world(next_cell)
                move_vector = Vec3(target.x - monster.x, 0, target.z - monster.z)
                if move_vector.length() < 0.5:
                    monster_path.pop(0)
                    continue
                monster.position += move_vector.normalized() * MONSTER_RUN_SPEED * time.dt
                face_target(Vec3(target.x, monster.y, target.z))
                is_moving = True
                break
        elif should_chase:
            fallback_vector = Vec3(target_entity.x - monster.x, 0, target_entity.z - monster.z)
            if fallback_vector.length() > 0.1:
                monster.position += fallback_vector.normalized() * (MONSTER_RUN_SPEED * 0.6) * time.dt
                face_target(Vec3(target_entity.x, monster.y, target_entity.z))
                is_moving = True
        else:
            search_vector = Vec3(target_goal.x - monster.x, 0, target_goal.z - monster.z)
            if search_vector.length() > 0.15:
                search_speed = MONSTER_RUN_SPEED * 0.45
                monster.position += search_vector.normalized() * search_speed * time.dt
                face_target(Vec3(target_goal.x, monster.y, target_goal.z))
                is_moving = True
            else:
                face_target(Vec3(target_goal.x, monster.y, target_goal.z))
                monster_path = []
                if monster_search_mode and monster_search_timer <= 0:
                    monster_search_mode = False

        if is_moving:
            monster_run_phase += time.dt * 12
            body_bob = math.sin(monster_run_phase * 0.5) * 0.05
            body_sway = math.sin(monster_run_phase) * 4
            monster_body.y = lerp(monster_body.y, body_bob, time.dt * 8)
            monster_body.rotation_x = lerp(monster_body.rotation_x, -4, time.dt * 8)
            monster_body.rotation_z = lerp(monster_body.rotation_z, body_sway, time.dt * 6)
        else:
            monster_body.y = lerp(monster_body.y, 0, time.dt * 8)
            monster_body.rotation_x = lerp(monster_body.rotation_x, 0, time.dt * 8)
            monster_body.rotation_z = lerp(monster_body.rotation_z, 0, time.dt * 8)
        player_attack_cooldown = max(0, player_attack_cooldown - time.dt)
        if should_chase and spawn_protection_timer <= 0 and monster_distance <= monster_attack_range and player_attack_cooldown <= 0:
            if not target_crouching or monster_distance <= monster_crouch_detection_range:
                if target_is_remote:
                    remote_player_health = max(0, remote_player_health - monster_attack_damage)
                else:
                    player_health = max(0, player_health - monster_attack_damage)
                    if player_health <= 0:
                        trigger_game_over()
                        return
                player_attack_cooldown = monster_attack_interval

    # 5. Continuous Jumping Logic
    if not fly_mode and held_keys['space'] and player.grounded:
        player.jump()

    if player_health <= 30 and not low_health_sound.playing:
        low_health_sound.play()
    elif player_health > 30 and low_health_sound.playing:
        low_health_sound.stop()

    broadcast_network_state(is_moving)
    update_hud()

# --- INPUT HANDLING ---
def input(key):
    # Unlocks the mouse cursor so you can close the window easily
    global fly_mode, axe_picked_up, selected_hotbar_slot
    if key == 'escape':
        if inventory_open:
            hide_inventory()
            mouse.locked = True
        else:
            mouse.locked = not mouse.locked
            mouse.visible = not mouse.locked
            if game_mode == 'single_player':
                save_button.enabled = mouse.visible
    elif key in ('\\', 'backslash'):
        fly_mode = not fly_mode
        if fly_mode:
            player.gravity = 0
            if hasattr(player, 'velocity'):
                player.velocity = Vec3(0, 0, 0)
            if player.y < 5:
                player.y = 5
            mouse.locked = True
            mouse.visible = False
        else:
            player.gravity = 1
            fly_exit_protection_timer = 2.5
            if hasattr(player, 'velocity'):
                player.velocity = Vec3(0, 0, 0)
            if player.y < 5:
                player.y = 5
    elif key == 'f':
        if axe_world and not axe_picked_up and distance(player.position, axe_world.position) < 6:
            axe_picked_up = True
            selected_hotbar_slot = 1
            hotbar_labels[0].text = ''
            if hotbar_icons[0]:
                hotbar_icons[0].enabled = True
            axe_world.enabled = False
            axe_world.collider = None
            axe_hand.enabled = True
            axe_prompt.enabled = False
        elif land_collider and distance(player.position, land_collider.position) < 10:
            play_land_anim('door')
    elif key == 'e' and not game_over:
        if inventory_open:
            hide_inventory()
            mouse.locked = True
            mouse.visible = False
        else:
            show_inventory()
    elif key in ('1', '2', '3', '4'):
        selected_hotbar_slot = int(key)
    elif key == 'left mouse down' and axe_picked_up and not game_over and not inventory_open:
        swing_axe()

# Run the game!
invoke(load_game_state, delay=0.1)
app.run()
