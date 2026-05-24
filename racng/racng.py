import socket
import threading
import json
import os
import time
import math

# ==============================================================================
# --- 1. INTERNAL SERVER LOGIC (Runs inside a background thread if hosting) ---
# ==============================================================================
srv_game_state = {"players": {}, "blocks": [], "driving_vehicles": {}}
srv_clients = []
srv_lock = threading.Lock()

def srv_broadcast(message, exclude_conn=None):
    data = json.dumps(message).encode('utf-8') + b'\n'
    with srv_lock:
        for client in srv_clients:
            if client != exclude_conn:
                try:
                    client.sendall(data)
                except:
                    if client in srv_clients:
                        srv_clients.remove(client)

def srv_handle_client(conn, addr):
    client_id = f"{addr[0]}:{addr[1]}"
    with srv_lock:
        srv_clients.append(conn)
        conn.sendall(json.dumps({
            "type": "init", 
            "id": client_id, 
            "blocks": srv_game_state["blocks"],
            "driving_vehicles": srv_game_state["driving_vehicles"]
        }).encode('utf-8') + b'\n')

    buffer = ""
    try:
        while True:
            data = conn.recv(4096).decode('utf-8')
            if not data: break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                msg = json.loads(line)
                
                if msg["type"] == "move":
                    with srv_lock: srv_game_state["players"][client_id] = msg["data"]
                    srv_broadcast({"type": "sync_players", "players": srv_game_state["players"]}, exclude_conn=conn)
                elif msg["type"] == "place":
                    with srv_lock: srv_game_state["blocks"].append(msg["data"])
                    srv_broadcast({"type": "place", "data": msg["data"]}, exclude_conn=conn)
                elif msg["type"] == "break":
                    pos_to_remove = msg["data"]["pos"]
                    with srv_lock: srv_game_state["blocks"] = [b for b in srv_game_state["blocks"] if b["pos"] != pos_to_remove]
                    srv_broadcast({"type": "break", "data": msg["data"]}, exclude_conn=conn)
                elif msg["type"] == "drive_start":
                    with srv_lock: srv_game_state["driving_vehicles"][client_id] = msg["data"]["blocks"]
                    srv_broadcast({"type": "drive_start", "id": client_id, "blocks": msg["data"]["blocks"]}, exclude_conn=conn)
                elif msg["type"] == "drive_stop":
                    with srv_lock:
                        if client_id in srv_game_state["driving_vehicles"]:
                            del srv_game_state["driving_vehicles"][client_id]
                    srv_broadcast({"type": "drive_stop", "id": client_id}, exclude_conn=conn)
    except:
        pass
    finally:
        with srv_lock:
            if conn in srv_clients: srv_clients.remove(conn)
            if client_id in srv_game_state["players"]: del srv_game_state["players"][client_id]
            if client_id in srv_game_state["driving_vehicles"]: del srv_game_state["driving_vehicles"][client_id]
        conn.close()
        srv_broadcast({"type": "player_left", "id": client_id})

def launch_internal_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', 5555))
        server.listen()
        while True:
            conn, addr = server.accept()
            threading.Thread(target=srv_handle_client, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"[SERVER ERROR] Could not start background server: {e}")

# ==============================================================================
# --- 2. MULTI-STAGE TERMINAL STARTUP MENU ---
# ==============================================================================
print("\n" + "="*40)
print("     PHOENIX VEHICLE BUILDER & RACER     ")
print("="*40)
print("[1] Singleplayer (Offline Mode)")
print("[2] Multiplayer (LAN Setup)")
choice = input("\nSelect game mode (1 or 2): ").strip()

is_multiplayer = False
is_hosting = False
username = "LocalDriver"
SERVER_IP = '192.168.0.191'
PORT = 5555
unlimited_parts = False

if choice.lower() == 'haha':
    unlimited_parts = True
elif choice == '2' or choice == '676767':
    is_multiplayer = True
    if choice == '676767':
        unlimited_parts = True
        print("\n[CHEAT CODE] Unlimited Parts Multiplayer Activated! 676767!")
    print("\n" + "-"*30)
    print("       MULTIPLAYER OPTIONS")
    print("-"*30)
    print("[1] Host a Server")
    print("[2] Join a Server")
    mp_choice = input("\nSelect option (1 or 2): ").strip()
    
    username = input("Enter your username: ").strip() or "Player"
    
    if mp_choice == '1':
        is_hosting = True
        SERVER_IP = '127.0.0.1'  # Host loops back to their own internal server thread
        print("\n[HOST] Launching background game server engine...")
        threading.Thread(target=launch_internal_server, daemon=True).start()
        time.sleep(0.5)  # Let server bind cleanly before connecting
    else:
        ip_input = input("Enter Host IP Address (Leave blank for Localhost): ").strip()
        if ip_input:
            SERVER_IP = ip_input
        print(f"\n[CLIENT] Attempting connection to remote terminal at {SERVER_IP}...")
else:
    if unlimited_parts:
        print("\n[EASTER EGG] Unlimited Parts Singleplayer Activated! Haha!")
    else:
        print("\n[LAUNCHING] Starting Offline Singleplayer Sandbox...")

# ==============================================================================
# --- 3. GAME ENGINE INITIALIZATION ---
# ==============================================================================
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()
application.development_mode = False 

# --- Network Tracking Tables ---
client_socket = None
my_id = username
remote_players = {}  
remote_blocks = {}   
remote_vehicles = {}  # Track parented blocks for remote driving players
net_queue = []       
queue_lock = threading.Lock()
save_plates = []
load_plates = []
rotating_symbols = []
player_last_on_save = False
player_last_on_load = False

# --- Physics Constants ---
selected_block_type = 1
is_driving = False
current_speed = 0.0
max_speed = 0.0
acceleration = 0.0
mouse_accelerate = False
mouse_brake = False
deceleration = 0.0
vehicle_y_velocity = 0.0  
lowest_y_offset = 0.0     
car_weight = 0
base_engine_power = 120 
car_parts = []
car_velocity = Vec3(0, 0, 0) 
max_fuel = 0.0
current_fuel = 0.0
fuel_timer = 0.0
is_drifting = False
skid_timer = 0.0

PART_DATA = {
    1: {'name': 'Base Block', 'color': color.white, 'weight': 5, 'inventory': 10, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
    2: {'name': 'Wheel', 'color': color.black, 'weight': 4, 'inventory': 4, 'model': 'cube', 'scale': (0.8, 0.8, 0.3), 'rot': (0, 0, 0)}, 
    3: {'name': 'Suspension', 'color': color.green, 'weight': 3, 'inventory': 4, 'model': 'cube', 'scale': (0.3, 0.3, 1), 'rot': (0, 0, 0)}, 
    4: {'name': 'Engine', 'color': color.red, 'weight': 15, 'inventory': 1, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
    5: {'name': 'Driver Seat', 'color': color.azure, 'weight': 4, 'inventory': 1, 'model': 'cube', 'scale': (1, 0.5, 1), 'rot': (0, 0, 0)}, 
    6: {'name': 'Fuel Tank', 'color': color.orange, 'weight': 10, 'inventory': 2, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
    7: {'name': 'Thruster', 'color': color.magenta, 'weight': 6, 'inventory': 0, 'model': 'cube', 'scale': (0.8, 0.8, 0.8), 'rot': (0, 0, 0)},
}

garage_centers = [
    Vec3(-50, 0, -60), Vec3(-50, 0, 0), Vec3(-50, 0, 60),
    Vec3(80, 0, -60),  Vec3(80, 0, 0),  Vec3(80, 0, 60)
]

# Environment Architecture
ground = Entity(model='plane', scale=(200, 1, 200), color=color.dark_gray, collider='box')
track = Entity(model='cube', scale=(20, 0.1, 150), position=(20, 0.01, 0), color=color.black, collider='box')
for center in garage_centers:
    Entity(model='cube', scale=(30, 0.11, 30), position=(center.x, 0.015, center.z), color=color.blue, collider='box')
    # --- Save Pressure Plate (green) ---
    _sp = Entity(model='cube', scale=(3, 0.08, 3), position=(center.x - 12, 0.04, center.z - 12), color=color.green)
    save_plates.append(_sp)
    _sp_sym = Entity(model='cube', scale=(0.5, 0.5, 0.5), position=(center.x - 12, 1.2, center.z - 12), color=color.green)
    rotating_symbols.append(_sp_sym)
    # --- Load Pressure Plate (yellow/gold) ---
    _lp = Entity(model='cube', scale=(3, 0.08, 3), position=(center.x + 12, 0.04, center.z - 12), color=color.yellow)
    load_plates.append(_lp)
    _lp_sym = Entity(model='cube', scale=(0.5, 0.5, 0.5), position=(center.x + 12, 1.2, center.z - 12), color=color.yellow)
    rotating_symbols.append(_lp_sym)

# Bridge to new area
bridge = Entity(model='cube', scale=(20, 0.1, 200), position=(20, 0.01, 160), color=color.gray, collider='box')

# Oval race track (very big) - positioned far away
oval_track_center = Vec3(20, 0.01, 380)
oval_scale_x = 150  # Major axis
oval_scale_z = 80   # Minor axis
oval_track_outer = Entity(model='cube', scale=(oval_scale_x * 2, 0.1, oval_scale_z * 2), position=oval_track_center, color=color.black, collider='box')
oval_track_inner = Entity(model='cube', scale=(oval_scale_x * 1.6, 0.08, oval_scale_z * 1.6), position=(oval_track_center.x, 0.05, oval_track_center.z), color=color.dark_gray, collider='box')

# Extended ground plane for race track area
race_ground = Entity(model='plane', scale=(400, 1, 300), position=(20, -0.5, 380), color=color.dark_gray, collider='box')

sky = Sky(color=color.rgb(135/255, 206/255, 250/255))

player = FirstPersonController(position=(-50, 2, -10))

# --- Additional structures: mirrored bridge, long test road, U-turn and return road
# Mirror of the existing bridge on the other side of the map (removed)

# Long straight road to test top speeds
long_road_length = 1500
long_road_start_z = oval_track_center.z + oval_scale_z * 2 + 20
long_road = Entity(model='cube', scale=(20, 0.1, long_road_length), position=(oval_track_center.x, 0.01, long_road_start_z + long_road_length / 2), color=color.black, collider='box')

# U-turn pad at the end of the long road and a return parallel road
u_turn_pad = Entity(model='cube', scale=(60, 0.1, 60), position=(oval_track_center.x, 0.01, long_road_start_z + long_road_length + 30), color=color.gray, collider='box')
return_road = Entity(model='cube', scale=(20, 0.1, long_road_length), position=(oval_track_center.x, 0.01, long_road_start_z + long_road_length + 60 + long_road_length / 2), color=color.black, collider='box')

# --- New bridge + winding hairpin test road (for brakes and drifting)
# Bridge leading to the hairpin zone
# Bridge leading to the hairpin zone — place it adjacent to the main bridge so it's reachable
hairpin_bridge_x = bridge.x + 120
hairpin_bridge_z = bridge.z + (bridge.scale_z / 2) + 10
hairpin_bridge = Entity(model='cube', scale=(30, 0.2, 30), position=(hairpin_bridge_x, 0.01, hairpin_bridge_z), color=color.brown, collider='box')

# Create a sequence of hairpin segments that zig-zag back and forth
hairpin_segments = []
# Make segments longer and use alternating lateral offsets so pieces connect
seg_len = 60
seg_width = 20
num_hairpins = 12
lateral_base = 14
lateral_step = 2
start_x = hairpin_bridge.x + 20
start_z = hairpin_bridge.z + 20
hairpin_segment_entities = []
for i in range(num_hairpins):
    side = -1 if i % 2 == 0 else 1
    lateral = side * (lateral_base + (i // 2) * lateral_step)
    seg_x = start_x + lateral
    # place each segment so its end slightly overlaps the previous segment
    seg_z = start_z + i * (seg_len - 8)
    # compute yaw so the segment points toward the next lateral offset (makes a true zig-zag)
    next_side = -1 if (i+1) % 2 == 0 else 1
    next_lateral = next_side * (lateral_base + ((i+1) // 2) * lateral_step)
    dx = (start_x + next_lateral) - seg_x
    dz = (seg_len - 8)
    yaw = math.degrees(math.atan2(dx, dz))
    seg = Entity(model='cube', scale=(seg_width, 0.12, seg_len), position=(seg_x, 0.01, seg_z), rotation=(0, yaw, 0), color=color.black, collider='box')
    hairpin_segments.append(seg)
    # Add a small connector pad parented to the segment so it follows the rotation
    pad = Entity(parent=seg, model='cube', scale=(seg_width + 6, 0.12, 8), position=(0, 0.01, seg_len/2 - 4), color=color.gray, collider='box')
    hairpin_segments.append(pad)
    hairpin_segment_entities.append(seg)

# Create connectors between consecutive segments to make a continuous road
for idx in range(len(hairpin_segment_entities) - 1):
    a = hairpin_segment_entities[idx]
    b = hairpin_segment_entities[idx + 1]
    # compute forward vectors from rotation_y (Ursina uses rotation_y in degrees)
    rad_a = math.radians(a.rotation_y)
    rad_b = math.radians(b.rotation_y)
    forward_a = Vec3(math.sin(rad_a), 0, math.cos(rad_a))
    forward_b = Vec3(math.sin(rad_b), 0, math.cos(rad_b))
    # end point of a and start point of b (approx)
    end_a = a.position + forward_a * (seg_len / 2)
    start_b = b.position - forward_b * (seg_len / 2)
    mid = (end_a + start_b) / 2
    dist = distance(end_a, start_b)
    if dist < 0.1:
        continue
    # connector oriented from a to b
    conn_yaw = math.degrees(math.atan2((start_b.x - end_a.x), (start_b.z - end_a.z)))
    connector = Entity(model='cube', scale=(seg_width, 0.12, dist + 2), position=(mid.x, 0.01, mid.z), rotation=(0, conn_yaw, 0), color=color.black, collider='box')
    hairpin_segments.append(connector)

# A larger U-turn pad at the end of the hairpins and a small return connector
hairpin_u_turn = Entity(model='cube', scale=(80, 0.2, 80), position=(start_x, 0.01, start_z + num_hairpins * (seg_len - 8) + 40), color=color.gray, collider='box')
hairpin_return = Entity(model='cube', scale=(20, 0.1, 300), position=(start_x + 140, 0.01, hairpin_u_turn.z + 160), color=color.black, collider='box')

# ==============================================================================
# --- RACE PORTAL (standing arch) ---
# ==============================================================================
# Place the portal in front of the right-hand garage cluster
portal_pos = Vec3(garage_centers[3].x + 20, 0, garage_centers[3].z)

# Left pillar
_pl = Entity(model='cube', scale=(1.2, 8, 1.2),
             position=(portal_pos.x, 4, portal_pos.z - 3.5),
             color=color.magenta, collider=None)
# Right pillar
_pr = Entity(model='cube', scale=(1.2, 8, 1.2),
             position=(portal_pos.x, 4, portal_pos.z + 3.5),
             color=color.magenta, collider=None)
# Top crossbar
_pt = Entity(model='cube', scale=(1.2, 1.2, 9),
             position=(portal_pos.x, 8.6, portal_pos.z),
             color=color.magenta, collider=None)
# Glowing fill (semi-transparent, pulsates)
portal_fill = Entity(model='cube', scale=(0.3, 7, 7),
                     position=(portal_pos.x, 4.3, portal_pos.z),
                     color=color.rgba(180, 0, 255, 160), collider=None)
# Sign board above arch (3D world-space)
_psign = Entity(model='cube', scale=(0.25, 1.8, 7),
                position=(portal_pos.x - 0.9, 10.2, portal_pos.z),
                color=color.black, collider=None)
# 3D text parented to scene so it appears above the arch, not on screen
portal_label = Text(
    text='ENTER TO RACE',
    parent=scene,
    position=Vec3(portal_pos.x - 0.6, 10.2, portal_pos.z),
    rotation=(0, 90, 0),
    world_scale=4,
    color=color.cyan,
    origin=(0, 0)
)

# --- Race arena at z=1200 ---
race_center = Vec3(20, 0, 1200)
# Large flat ground for the race area
Entity(model='cube', scale=(400, 0.15, 600),
       position=(race_center.x, -0.08, race_center.z),
       color=color.dark_gray, collider='box')
# Outer oval track surface
Entity(model='cube', scale=(220, 0.12, 320),
       position=(race_center.x, 0, race_center.z),
       color=color.black, collider='box')
# Inner infield (grass-like)
Entity(model='cube', scale=(160, 0.1, 230),
       position=(race_center.x, 0.01, race_center.z),
       color=color.dark_gray, collider='box')
# Start/finish line
Entity(model='cube', scale=(60, 0.13, 4),
       position=(race_center.x, 0.02, race_center.z - 110),
       color=color.white, collider='box')
# Barrier walls around the outside
Entity(model='cube', scale=(225, 2, 4), position=(race_center.x, 1, race_center.z - 163), color=color.red, collider='box')
Entity(model='cube', scale=(225, 2, 4), position=(race_center.x, 1, race_center.z + 163), color=color.red, collider='box')
Entity(model='cube', scale=(4, 2, 328), position=(race_center.x - 113, 1, race_center.z), color=color.red, collider='box')
Entity(model='cube', scale=(4, 2, 328), position=(race_center.x + 113, 1, race_center.z), color=color.red, collider='box')

# Return portal inside the race arena (cyan arch)
return_portal_pos = Vec3(race_center.x, 0, race_center.z - 140)
_rpl = Entity(model='cube', scale=(1.2, 8, 1.2), position=(return_portal_pos.x, 4, return_portal_pos.z - 3.5), color=color.cyan, collider=None)
_rpr = Entity(model='cube', scale=(1.2, 8, 1.2), position=(return_portal_pos.x, 4, return_portal_pos.z + 3.5), color=color.cyan, collider=None)
_rpt = Entity(model='cube', scale=(1.2, 1.2, 9),  position=(return_portal_pos.x, 8.6, return_portal_pos.z), color=color.cyan, collider=None)
return_fill = Entity(model='cube', scale=(0.3, 7, 7), position=(return_portal_pos.x - 0.8, 4.3, return_portal_pos.z), color=color.rgba(0, 220, 255, 160), collider=None)
# Sign board above return arch
_rsign = Entity(model='cube', scale=(0.25, 1.8, 6),
                position=(return_portal_pos.x - 0.9, 10.2, return_portal_pos.z),
                color=color.black, collider=None)
# 3D world-space text above return arch
_return_label = Text(
    text='EXIT RACE',
    parent=scene,
    position=Vec3(return_portal_pos.x - 0.6, 10.2, return_portal_pos.z),
    rotation=(0, 90, 0),
    world_scale=4,
    color=color.magenta,
    origin=(0, 0)
)

# Teleport cooldown
portal_cooldown = 2.0
_last_portal_time = -999.0

# Display UI Surfaces
hotbar_text = Text(text="Loading...", position=(-0.85, 0.45), scale=1.2, color=color.yellow, background=True)
warning_text = Text(text="", position=(0, 0.2), scale=2, color=color.red, origin=(0,0))
fuel_text = Text(text="", position=(0, -0.32), scale=2, color=color.orange, origin=(0,0))
speedometer = Text(text="", position=(0, -0.4), scale=2, color=color.yellow, origin=(0,0))
shop = Button(text="SHOP", position=(-0.85, -0.45), scale=0.05, color=color.yellow, highlight_color=color.orange, pressed_color=color.white, text_color=color.black)

def update_shop():
    if shop.pressed:
        shopui = Text(text="Welcome to the Shop!", position=(0, 0), scale=1, color=color.white, text_color=color.black)
        bttn1 = Button(text="Buy Fuel Tank [x2] ($100)", position=(0, -0.5), scale=0.05, color=color.green, highlight_color=color.lime, pressed_color=color.white, text_color=color.black)
        bttn2 = Button(text="Buy Engine [x1] ($200)", position=(0, -1), scale=0.05, color=color.green, highlight_color=color.lime, pressed_color=color.white, text_color=color.black)
        bttn3 = Button(text="Buy Thruster [x1] ($1500)", position=(0, -1.5), scale=0.05, color=color.green, highlight_color=color.lime, pressed_color=color.white, text_color=color.black)



def update_hotbar_ui():
    if is_multiplayer:
        role = "[HOST]" if is_hosting else "[CLIENT]"
        display_name = f"{username} {role} (ID: {my_id})"
    else:
        display_name = f"{username} [OFFLINE]"
        
    if unlimited_parts:
        display_name += " [UNLIMITED PARTS]"
        
    ui_string = f"PLAYER: {display_name}\nHOTBAR:\n"
    for key, data in PART_DATA.items():
        if key == 7 and not unlimited_parts:
            continue
        prefix = "> " if key == selected_block_type else "  "
        count_str = "∞" if unlimited_parts else str(data['inventory'])
        ui_string += f"{prefix}[{key}] {data['name']} (x{count_str})\n"
    hotbar_text.text = ui_string

def in_build_zone(pos):
    for center in garage_centers:
        if abs(pos.x - center.x) <= 15 and abs(pos.z - center.z) <= 15:
            return True
    return False

def get_nearest_garage(pos):
    nearest = garage_centers[0]
    min_dist = distance(pos, nearest)
    for g in garage_centers[1:]:
        d = distance(pos, g)
        if d < min_dist: min_dist = d; nearest = g
    return nearest

vehicle_parent = Entity(position=(0,0,0))

hologram = Entity(model='cube', color=color.white, alpha=0.5, collider=None, add_to_scene_entities=False, texture='white_cube')

def send_net_msg(msg_type, data):
    if is_multiplayer and client_socket:
        try:
            packet = json.dumps({"type": msg_type, "data": data}).encode('utf-8') + b'\n'
            client_socket.sendall(packet)
        except:
            pass

def receive_loop():
    global my_id
    buffer = ""
    try:
        while True:
            data = client_socket.recv(4096).decode('utf-8')
            if not data: break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                msg = json.loads(line)
                with queue_lock:
                    net_queue.append(msg)
    except:
        pass

def connect_to_lan():
    global client_socket, is_multiplayer
    if not is_multiplayer: return
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_IP, PORT))
        threading.Thread(target=receive_loop, daemon=True).start()
    except Exception as e:
        print(f"Could not reach target network runtime: {e}")
        is_multiplayer = False

def get_build_pos_rot():
    snapped_rot_y = round(player.rotation_y / 90) * 90
    custom_rotation = (0, snapped_rot_y, 0)
    local_scale = PART_DATA[selected_block_type]['scale']
    part_height = local_scale[1] / 2

    if mouse.hovered_entity:
        target = mouse.hovered_entity
        normal = mouse.normal
        if normal is None:
            return None, custom_rotation, False

        if hasattr(target, 'part_id'):
            h_thickness = target.scale_y if abs(normal.y) > 0.5 else target.scale_x
            build_pos = target.position + normal * ((h_thickness / 2) + part_height)
        else:
            build_pos = mouse.world_point + normal * part_height
    else:
        ray = raycast(camera.world_position, camera.forward, distance=500)
        if not ray.hit:
            return None, custom_rotation, False
        build_pos = ray.world_point + ray.normal * part_height

    build_pos.x = round(build_pos.x)
    build_pos.z = round(build_pos.z)
    build_pos.y = round(build_pos.y)

    is_valid = in_build_zone(build_pos) and distance(build_pos, player.position) > 0.8 and (unlimited_parts or PART_DATA[selected_block_type]['inventory'] > 0)
    return build_pos, custom_rotation, is_valid

class VehiclePart(Entity):
    def __init__(self, position=(0,0,0), part_id=1, custom_rot=(0,0,0), local_build=True):
        super().__init__(
            parent=scene, position=position, model=PART_DATA[part_id]['model'],
            scale=PART_DATA[part_id]['scale'], rotation=custom_rot, origin_y=0,
            color=PART_DATA[part_id]['color'], collider='box',
            texture='white_cube'
        )
        self.part_id = part_id
        self.weight = PART_DATA[part_id]['weight']
        
        if local_build:
            car_parts.append(self)
        else:
            coord_key = (round(position[0],2), round(position[1],2), round(position[2],2))
            remote_blocks[coord_key] = self

def input(key):
    global selected_block_type, is_driving, mouse_accelerate, mouse_brake

    if key == 'escape':
        mouse.locked = not mouse.locked
        return

    if key.isdigit() and int(key) in PART_DATA:
        val = int(key)
        if val == 7 and not unlimited_parts:
            return  # Hide thrusters outside of Unlimited Mode
        selected_block_type = val
        warning_text.text = ""  # Clear any active inventory warning on tool switch
        update_hotbar_ui()
        
    if is_driving:
        if key == 'right mouse down':
            mouse_accelerate = True
        if key == 'right mouse up':
            mouse_accelerate = False
        if key == 'left mouse down':
            mouse_brake = True
        if key == 'left mouse up':
            mouse_brake = False
    elif not is_driving and mouse.locked: 
        if key == 'right mouse down' and mouse.hovered_entity:
            if hasattr(mouse.hovered_entity, 'part_id') and mouse.hovered_entity.part_id == 5:
                enter_vehicle(mouse.hovered_entity)
                return 

            build_pos, custom_rotation, is_valid = get_build_pos_rot()
            if build_pos:
                if not unlimited_parts and PART_DATA[selected_block_type]['inventory'] <= 0:
                    warning_text.text = f"OUT OF {PART_DATA[selected_block_type]['name'].upper()}!"
                elif not in_build_zone(build_pos):
                    warning_text.text = "CANNOT BUILD OUTSIDE GARAGE!"
                elif is_valid:
                    VehiclePart(position=build_pos, part_id=selected_block_type, custom_rot=custom_rotation, local_build=True)
                    if not unlimited_parts:
                        PART_DATA[selected_block_type]['inventory'] -= 1
                    update_hotbar_ui()
                    warning_text.text = ""  # Clear warning on successful place
                    send_net_msg("place", {"pos": [build_pos.x, build_pos.y, build_pos.z], "rot": list(custom_rotation), "part_id": selected_block_type})
                
        if key == 'left mouse down' and mouse.hovered_entity:
            if hasattr(mouse.hovered_entity, 'part_id'):
                pos = mouse.hovered_entity.position
                coord_key = (round(pos.x,2), round(pos.y,2), round(pos.z,2))
                
                send_net_msg("break", {"pos": [pos.x, pos.y, pos.z]})
                if mouse.hovered_entity in car_parts:
                    car_parts.remove(mouse.hovered_entity)
                    # Return broken block back to the user's inventory
                    part_id = mouse.hovered_entity.part_id
                    if not unlimited_parts:
                        PART_DATA[part_id]['inventory'] += 1
                    update_hotbar_ui()
                    warning_text.text = ""  # Clear any active inventory warning
                destroy(mouse.hovered_entity)
                if coord_key in remote_blocks: del remote_blocks[coord_key]

    if key == 'e' and is_driving:
        exit_vehicle()
    
    if key == 'shift' and is_driving:
        global is_drifting
        is_drifting = True
    
    if key == 'shift up' and is_driving:
        is_drifting = False

def enter_vehicle(seat_entity):
    global is_driving, car_weight, max_speed, acceleration, deceleration, current_speed 
    global lowest_y_offset, vehicle_y_velocity, car_velocity, max_fuel, current_fuel
    global mouse_accelerate, mouse_brake
    
    # Check for required parts
    has_engine = any(part.part_id == 4 for part in car_parts)
    has_fuel = any(part.part_id == 6 for part in car_parts)
    has_wheels = sum(1 for part in car_parts if part.part_id == 2) >= 2
    
    if not has_engine:
        warning_text.text = "MISSING ENGINE!"
        return
    if not has_fuel:
        warning_text.text = "MISSING FUEL TANK!"
        return
    if not has_wheels:
        warning_text.text = "MISSING WHEELS!"
        return
    
    warning_text.text = ""
    car_weight = sum(part.weight for part in car_parts)
    num_engines = sum(1 for part in car_parts if part.part_id == 4)
    total_engine_power = base_engine_power * max(1, num_engines)
    max_speed = total_engine_power / (car_weight * 0.05)
    acceleration = total_engine_power / (car_weight * 0.2)
    deceleration = acceleration * 1.5 
    current_speed = 0.0; vehicle_y_velocity = 0.0  
    mouse_accelerate = False
    mouse_brake = False
    
    # Fuel calculations: 5L per placed Fuel Tank
    num_tanks = sum(1 for part in car_parts if part.part_id == 6)
    max_fuel = num_tanks * 5 if num_tanks > 0 else 5
    current_fuel = max_fuel
    
    vehicle_parent.position = seat_entity.position
    vehicle_parent.rotation = (0, player.rotation_y, 0)
    
    # Store block positions in absolute scene coords before parenting transforms are applied
    block_positions = [[round(p.x, 2), round(p.y, 2), round(p.z, 2)] for p in car_parts]
    
    for part in car_parts:
        part.world_parent = vehicle_parent

    send_net_msg("drive_start", {"blocks": block_positions})

    lowest_y_offset = 0.0
    for part in car_parts:
        bottom_edge = part.y - (part.scale_y / 2)
        if bottom_edge < lowest_y_offset: lowest_y_offset = bottom_edge
        
    player.enabled = False
    camera.world_parent = scene 
    is_driving = True

def exit_vehicle():
    global is_driving, mouse_accelerate, mouse_brake
    
    send_net_msg("drive_stop", {})
    
    if not in_build_zone(vehicle_parent.position):
        nearest = get_nearest_garage(vehicle_parent.position)
        vehicle_parent.position = Vec3(nearest.x, 5, nearest.z) 
    
    for part in car_parts:
        part.world_parent = scene
        
    camera.parent = player.camera_pivot
    camera.position = (0,0,0); camera.rotation = (0,0,0)
    player.position = vehicle_parent.position + Vec3(3, 1, 0) 
    player.enabled = True
    mouse_accelerate = False
    mouse_brake = False
    is_driving = False 

# ==============================================================================
# --- PRESSURE PLATE HELPERS ---
# ==============================================================================
def save_vehicle_design():
    """Serialize current car_parts relative to the driver seat (or centroid) and write to vehicle_design.json."""
    if not car_parts:
        warning_text.color = color.red
        warning_text.text = "NO PARTS TO SAVE!"
        invoke(setattr, warning_text, 'text', '', delay=3)
        return
    # Anchor to driver seat if present, otherwise use centroid
    seat_parts = [p for p in car_parts if p.part_id == 5]
    if seat_parts:
        anchor = seat_parts[0].world_position
    else:
        avg_x = sum(p.world_position.x for p in car_parts) / len(car_parts)
        avg_y = sum(p.world_position.y for p in car_parts) / len(car_parts)
        avg_z = sum(p.world_position.z for p in car_parts) / len(car_parts)
        anchor = Vec3(avg_x, avg_y, avg_z)
    design = []
    for part in car_parts:
        rel = part.world_position - anchor
        design.append({
            "part_id": part.part_id,
            "rel_pos": [round(rel.x, 3), round(rel.y, 3), round(rel.z, 3)],
            "rot": [round(part.rotation_x, 1), round(part.rotation_y, 1), round(part.rotation_z, 1)]
        })
    with open('vehicle_design.json', 'w') as _f:
        json.dump(design, _f, indent=2)
    warning_text.color = color.green
    warning_text.text = "VEHICLE DESIGN SAVED!"
    invoke(setattr, warning_text, 'text', '', delay=3)
    invoke(setattr, warning_text, 'color', color.red, delay=3)

def load_vehicle_design():
    """Clear the current garage's parts and respawn the saved design from vehicle_design.json."""
    global car_parts
    if not os.path.exists('vehicle_design.json'):
        warning_text.color = color.red
        warning_text.text = "NO SAVED DESIGN FOUND!"
        invoke(setattr, warning_text, 'text', '', delay=3)
        return
    with open('vehicle_design.json', 'r') as _f:
        design = json.load(_f)
    curr_garage = get_nearest_garage(player.position)
    # Remove all local parts inside this garage's build zone
    to_remove = [
        p for p in car_parts
        if abs(p.world_position.x - curr_garage.x) <= 15 and abs(p.world_position.z - curr_garage.z) <= 15
    ]
    for part in to_remove:
        pos = part.world_position
        send_net_msg("break", {"pos": [pos.x, pos.y, pos.z]})
        if not unlimited_parts:
            PART_DATA[part.part_id]['inventory'] += 1
        car_parts.remove(part)
        destroy(part)
    # Respawn the saved layout centred on the garage floor
    load_anchor = Vec3(curr_garage.x, 2, curr_garage.z)
    for entry in design:
        part_id = entry["part_id"]
        rel = entry["rel_pos"]
        rot = entry["rot"]
        spawn_pos = Vec3(load_anchor.x + rel[0], load_anchor.y + rel[1], load_anchor.z + rel[2])
        custom_rot = (rot[0], rot[1], rot[2])
        VehiclePart(position=spawn_pos, part_id=part_id, custom_rot=custom_rot, local_build=True)
        send_net_msg("place", {"pos": [spawn_pos.x, spawn_pos.y, spawn_pos.z], "rot": list(custom_rot), "part_id": part_id})
    update_hotbar_ui()
    warning_text.color = color.yellow
    warning_text.text = "VEHICLE DESIGN LOADED!"
    invoke(setattr, warning_text, 'text', '', delay=3)
    invoke(setattr, warning_text, 'color', color.red, delay=3)

def update():
    global current_speed, vehicle_y_velocity, car_velocity, my_id, current_fuel, fuel_timer, is_drifting, skid_timer
    global player_last_on_save, player_last_on_load, _last_portal_time
    
    if is_multiplayer:
        messages_to_process = []
        with queue_lock:
            if net_queue:
                messages_to_process = list(net_queue)
                net_queue.clear()
                
        for msg in messages_to_process:
            if msg["type"] == "init":
                my_id = msg["id"]
                update_hotbar_ui()
                for b in msg["blocks"]:
                    coord = (round(b["pos"][0],2), round(b["pos"][1],2), round(b["pos"][2],2))
                    if coord not in remote_blocks:
                        VehiclePart(position=b["pos"], part_id=b["part_id"], custom_rot=b["rot"], local_build=False)
                
                # Load active driving states upon joining
                if "driving_vehicles" in msg:
                    for p_id, block_coords in msg["driving_vehicles"].items():
                        if p_id not in remote_vehicles:
                            remote_vehicles[p_id] = []
                        if p_id not in remote_players:
                            remote_players[p_id] = Entity(model='cube', color=color.blue, scale=(0.8, 0.6, 0.4), position=(0, 0.3, 0))
                            Entity(parent=remote_players[p_id], model='cube', color=color.red, scale=(1, 0.8, 0.5), position=(0, 1, 0))
                            Entity(parent=remote_players[p_id], model='cube', color=color.yellow, scale=(0.6, 0.6, 0.6), position=(0, 1.7, 0))
                        for coord in block_coords:
                            coord_key = (round(coord[0], 2), round(coord[1], 2), round(coord[2], 2))
                            if coord_key in remote_blocks:
                                part = remote_blocks[coord_key]
                                part.world_parent = remote_players[p_id]
                                remote_vehicles[p_id].append(part)
                        
            elif msg["type"] == "place":
                b = msg["data"]
                coord = (round(b["pos"][0],2), round(b["pos"][1],2), round(b["pos"][2],2))
                if coord not in remote_blocks:
                    VehiclePart(position=b["pos"], part_id=b["part_id"], custom_rot=b["rot"], local_build=False)
                    
            elif msg["type"] == "break":
                pos = msg["data"]["pos"]
                coord_key = (round(pos[0],2), round(pos[1],2), round(pos[2],2))
                if coord_key in remote_blocks:
                    for r_parts in remote_vehicles.values():
                        if remote_blocks[coord_key] in r_parts:
                            r_parts.remove(remote_blocks[coord_key])
                    destroy(remote_blocks[coord_key])
                    del remote_blocks[coord_key]
                    
            elif msg["type"] == "sync_players":
                for p_id, p_data in msg["players"].items():
                    if p_id == my_id: continue
                    
                    # 1. Sanitize Inbound data
                    coords = [p_data.get("x"), p_data.get("y"), p_data.get("z"), p_data.get("rot_y")]
                    if any(c is None or c != c for c in coords): 
                        continue 
                        
                    if p_id not in remote_players:
                        remote_players[p_id] = Entity(model='cube', color=color.orange, scale=(1.5, 1, 3))
                    
                    target_pos = Vec3(p_data["x"], p_data["y"], p_data["z"])
                    remote_players[p_id].position = lerp(remote_players[p_id].position, target_pos, time.dt * 15)
                    remote_players[p_id].rotation_y = p_data["rot_y"]
                    
            elif msg["type"] == "player_left":
                p_id = msg["id"]
                if p_id in remote_players:
                    destroy(remote_players[p_id])
                    del remote_players[p_id]
                if p_id in remote_vehicles:
                    for part in remote_vehicles[p_id]:
                        if part and not part.destroyed:
                            part.world_parent = scene
                    del remote_vehicles[p_id]
                    
            elif msg["type"] == "drive_start":
                p_id = msg["id"]
                block_coords = msg["blocks"]
                if p_id not in remote_players:
                    remote_players[p_id] = Entity(model='cube', color=color.orange, scale=(1.5, 1, 3))
                if p_id not in remote_vehicles:
                    remote_vehicles[p_id] = []
                for coord in block_coords:
                    coord_key = (round(coord[0], 2), round(coord[1], 2), round(coord[2], 2))
                    if coord_key in remote_blocks:
                        part = remote_blocks[coord_key]
                        part.world_parent = remote_players[p_id]
                        remote_vehicles[p_id].append(part)
                        
            elif msg["type"] == "drive_stop":
                p_id = msg["id"]
                if p_id in remote_vehicles:
                    for part in remote_vehicles[p_id]:
                        if part and not part.destroyed:
                            part.world_parent = scene
                    remote_vehicles[p_id].clear()

        # 2. Sanitize Outbound data
        my_pos = vehicle_parent.position if is_driving else player.position
        my_rot = vehicle_parent.rotation_y if is_driving else player.rotation_y
        
        if not (my_pos.x != my_pos.x or my_pos.y != my_pos.y or my_pos.z != my_pos.z):
            send_net_msg("move", {"x": my_pos.x, "y": my_pos.y, "z": my_pos.z, "rot_y": my_rot, "is_driving": is_driving})

    if is_driving and vehicle_parent.y < -30:
        exit_vehicle()
    elif not is_driving and player.y < -30:
        nearest = get_nearest_garage(player.position)
        player.position = (nearest.x, 2, nearest.z - 10)

    if not is_driving and mouse.locked:
        hologram.enabled = True
        hologram.model = PART_DATA[selected_block_type]['model']
        hologram.scale = PART_DATA[selected_block_type]['scale']
        build_pos, custom_rotation, is_valid = get_build_pos_rot()
        if build_pos:
            hologram.position = build_pos; hologram.rotation = custom_rotation
            hologram.color = PART_DATA[selected_block_type]['color'] if is_valid else color.red
            hologram.alpha = 0.5
        else: hologram.enabled = False
    else: hologram.enabled = False
    
    if is_driving:
        total_thrusters = sum(1 for part in car_parts if part.part_id == 7)
        bottom_thrusters = sum(1 for part in car_parts if part.part_id == 7 and part.y < -0.1)
        # Suspension count: each suspension part improves braking and drift stability
        suspension_count = sum(1 for part in car_parts if part.part_id == 3)
        suspension_boost = 1.0 + suspension_count * 0.25  # 25% braking boost per suspension
        is_ctrl_held = held_keys['left control'] or held_keys['control']
        
        # Update thruster colors depending on activation
        for part in car_parts:
            if part.part_id == 7:
                if is_ctrl_held:
                    part.color = color.orange
                    part.scale = Vec3(0.9, 0.9, 0.9) if time.time() % 0.2 > 0.1 else Vec3(0.8, 0.8, 0.8)
                else:
                    part.color = color.magenta
                    part.scale = Vec3(0.8, 0.8, 0.8)

        ray = raycast(vehicle_parent.world_position + Vec3(0, 1, 0), Vec3(0, -1, 0), ignore=car_parts, distance=200)
        if ray.hit:
            target_seat_y = ray.world_point.y - lowest_y_offset 
            if vehicle_parent.y > target_seat_y + 0.05:
                # We are in the air!
                if is_ctrl_held and bottom_thrusters > 0:
                    upward_thrust = bottom_thrusters * 40.0
                    vehicle_y_velocity += (upward_thrust - 25) * time.dt
                else:
                    vehicle_y_velocity -= 25 * time.dt
                
                vehicle_y_velocity = clamp(vehicle_y_velocity, -50.0, bottom_thrusters * 25.0 if bottom_thrusters > 0 else 0)
                vehicle_parent.y += vehicle_y_velocity * time.dt
            else:
                # We are on the ground!
                if is_ctrl_held and bottom_thrusters > 0:
                    vehicle_y_velocity = bottom_thrusters * 15.0  # Launch off the ground!
                    vehicle_parent.y += vehicle_y_velocity * time.dt
                else:
                    vehicle_parent.y = target_seat_y
                    vehicle_y_velocity = 0
        else:
            # Beyond raycast range or in empty air
            if is_ctrl_held and bottom_thrusters > 0:
                upward_thrust = bottom_thrusters * 40.0
                vehicle_y_velocity += (upward_thrust - 25) * time.dt
            else:
                vehicle_y_velocity -= 25 * time.dt
            
            vehicle_y_velocity = clamp(vehicle_y_velocity, -50.0, bottom_thrusters * 25.0 if bottom_thrusters > 0 else 0)
            vehicle_parent.y += vehicle_y_velocity * time.dt

        # Input and Fuel Management
        if current_fuel > 0:
            thrust_accel = 0.0
            temp_max_speed = max_speed
            if is_ctrl_held and total_thrusters > 0:
                thrust_accel = total_thrusters * 40.0
                temp_max_speed += total_thrusters * 15.0

            if held_keys['w'] or mouse_accelerate:
                current_speed += (acceleration + thrust_accel) * time.dt
            elif is_ctrl_held and total_thrusters > 0:
                current_speed += thrust_accel * time.dt
            elif held_keys['s'] or mouse_brake:
                decel_amount = deceleration * suspension_boost
                current_speed -= decel_amount * time.dt
            else:
                current_speed = lerp(current_speed, 0, time.dt * 2)
            
            # Drifting reduces speed
            if is_drifting:
                current_speed *= 0.95
            
            # Fuel Consumption Loop - 1 unit every 30 seconds
            fuel_timer += time.dt
            if fuel_timer >= 30.0:
                current_fuel -= 1
                fuel_timer = 0.0
                if current_fuel < 0: current_fuel = 0
        else:
            current_speed = lerp(current_speed, 0, time.dt * 2)

        active_max_speed = temp_max_speed if (is_ctrl_held and total_thrusters > 0) else max_speed
        current_speed = clamp(current_speed, -active_max_speed * 0.5, active_max_speed)
        
        if abs(current_speed) > 0.1:
            turn_direction = 1 if current_speed > 0 else -1
            # Smooth turning - increased during drift for responsive control
            turn_speed = 120 if is_drifting else 75
            if held_keys['a']: vehicle_parent.rotation_y -= turn_speed * turn_direction * time.dt
            if held_keys['d']: vehicle_parent.rotation_y += turn_speed * turn_direction * time.dt
                
        # --- DRIFTING MOMENTUM CORE ENGINE ---
        target_velocity = vehicle_parent.forward * current_speed
        # When drifting, reduce control for lateral sliding; otherwise normal physics
        # Adjust drift responsiveness depending on how many suspensions are installed
        if is_drifting and (held_keys['a'] or held_keys['d']):
            drift_factor = 0.8 * (1.0 + suspension_count * 0.5)
        elif held_keys['a'] or held_keys['d']:
            drift_factor = 1.8 * (1.0 + suspension_count * 0.3)
        else:
            drift_factor = 5.5 * (1.0 + suspension_count * 0.1)
        car_velocity = lerp(car_velocity, target_velocity, time.dt * drift_factor)
        vehicle_parent.position += car_velocity * time.dt
                
        # Screen Text updates with speedometer, fuel gauge, and drift indicator
        drift_indicator = " [DRIFTING!]" if is_drifting else ""
        if is_ctrl_held and total_thrusters > 0:
            if bottom_thrusters > 0:
                drift_indicator += " [THRUST UP!]"
            else:
                drift_indicator += " [THRUST ENGAGED!]"
        speedometer.text = f"SPEED: {int(abs(current_speed * 4.2))} km/h{drift_indicator}"
        fuel_text.text = f"FUEL: {int(current_fuel)}/{int(max_fuel)} L"
        
        ideal_cam_pos = vehicle_parent.position - (vehicle_parent.forward * 12) + Vec3(0, 4, 0)
        camera.position = lerp(camera.position, ideal_cam_pos, time.dt * 7)
        camera.look_at(vehicle_parent.position + vehicle_parent.forward * 3 + Vec3(0, 1.5, 0))
        camera.rotation_z = 0

    # --- Portal fill pulsation ---
    _pulse = abs(math.sin(time.time() * 3)) * 0.4 + 0.6
    portal_fill.color = color.rgba(int(180 * _pulse), 0, 255, 150)
    return_fill.color = color.rgba(0, int(220 * _pulse), 255, 150)

    # --- Vehicle portal teleport (XZ distance, vehicle-only) ---
    _now = time.time()
    if is_driving and (_now - _last_portal_time) > portal_cooldown:
        _vx, _vz = vehicle_parent.x, vehicle_parent.z
        # Enter portal: warp to race arena start line
        _enter_dist = (((_vx - portal_pos.x)**2) + ((_vz - portal_pos.z)**2)) ** 0.5
        if _enter_dist < 6:
            vehicle_parent.position = Vec3(race_center.x, 3, race_center.z - 105)
            vehicle_parent.rotation_y = 0
            car_velocity = Vec3(0, 0, 0)
            _last_portal_time = _now
            warning_text.color = color.green
            warning_text.text = "ENTERING RACE ARENA!"
            invoke(setattr, warning_text, 'text', '', delay=2)
            invoke(setattr, warning_text, 'color', color.red, delay=2)
        # Exit portal: warp back to garages
        _exit_dist = (((_vx - return_portal_pos.x)**2) + ((_vz - return_portal_pos.z)**2)) ** 0.5
        if _exit_dist < 6:
            vehicle_parent.position = Vec3(portal_pos.x + 5, 3, portal_pos.z)
            vehicle_parent.rotation_y = 180
            car_velocity = Vec3(0, 0, 0)
            _last_portal_time = _now
            warning_text.color = color.cyan
            warning_text.text = "RETURNED TO GARAGE"
            invoke(setattr, warning_text, 'text', '', delay=2)
            invoke(setattr, warning_text, 'color', color.red, delay=2)

    # --- Pressure Plate Step Detection (on-foot only) ---
    if not is_driving:
        px, pz = player.x, player.z
        on_save = any(abs(px - sp.x) < 1.8 and abs(pz - sp.z) < 1.8 for sp in save_plates)
        on_load = any(abs(px - lp.x) < 1.8 and abs(pz - lp.z) < 1.8 for lp in load_plates)
        if on_save and not player_last_on_save:
            save_vehicle_design()
        if on_load and not player_last_on_load:
            load_vehicle_design()
        player_last_on_save = on_save
        player_last_on_load = on_load

    # --- Rotate floating plate indicator symbols ---
    for sym in rotating_symbols:
        sym.rotation_y += time.dt * 60

if not is_multiplayer:
    VehiclePart(position=(-50, 2, 0), part_id=1, local_build=True)
    update_hotbar_ui()

connect_to_lan()
app.run()