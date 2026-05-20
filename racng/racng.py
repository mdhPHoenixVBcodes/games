import socket
import threading
import json
import time

# ==============================================================================
# --- 1. INTERNAL SERVER LOGIC (Runs inside a background thread if hosting) ---
# ==============================================================================
srv_game_state = {"players": {}, "blocks": []}
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
        conn.sendall(json.dumps({"type": "init", "id": client_id, "blocks": srv_game_state["blocks"]}).encode('utf-8') + b'\n')

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
    except:
        pass
    finally:
        with srv_lock:
            if conn in srv_clients: srv_clients.remove(conn)
            if client_id in srv_game_state["players"]: del srv_game_state["players"][client_id]
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
SERVER_IP = '127.0.0.1'
PORT = 5555

if choice == '2':
    is_multiplayer = True
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
net_queue = []       
queue_lock = threading.Lock()

# --- Physics Constants ---
selected_block_type = 1
is_driving = False
current_speed = 0.0
max_speed = 0.0
acceleration = 0.0
deceleration = 0.0
vehicle_y_velocity = 0.0  
lowest_y_offset = 0.0     
car_weight = 0
base_engine_power = 120 
car_parts = []
car_velocity = Vec3(0, 0, 0) 
max_fuel = 0.0
current_fuel = 0.0

PART_DATA = {
    1: {'name': 'Base Block', 'color': color.white, 'weight': 5, 'inventory': 99, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
    2: {'name': 'Wheel', 'color': color.black, 'weight': 4, 'inventory': 99, 'model': 'cube', 'scale': (0.8, 0.8, 0.3), 'rot': (0, 0, 0)}, 
    3: {'name': 'Suspension', 'color': color.green, 'weight': 3, 'inventory': 99, 'model': 'cube', 'scale': (0.3, 0.3, 1), 'rot': (0, 0, 0)}, 
    4: {'name': 'Engine', 'color': color.red, 'weight': 15, 'inventory': 99, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
    5: {'name': 'Driver Seat', 'color': color.azure, 'weight': 4, 'inventory': 99, 'model': 'cube', 'scale': (1, 0.5, 1), 'rot': (0, 0, 0)}, 
    6: {'name': 'Fuel Tank', 'color': color.orange, 'weight': 10, 'inventory': 99, 'model': 'cube', 'scale': (1, 1, 1), 'rot': (0, 0, 0)},
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
sky = Sky(color=color.rgb(135/255, 206/255, 250/255))

player = FirstPersonController(position=(-50, 2, -10))

# Display UI Surfaces
hotbar_text = Text(text="Loading...", position=(-0.85, 0.45), scale=1.2, color=color.yellow, background=True)
warning_text = Text(text="", position=(0, 0.2), scale=2, color=color.red, origin=(0,0))
fuel_text = Text(text="", position=(0, -0.32), scale=2, color=color.orange, origin=(0,0))
speedometer = Text(text="", position=(0, -0.4), scale=2, color=color.yellow, origin=(0,0))

def update_hotbar_ui():
    if is_multiplayer:
        role = "[HOST]" if is_hosting else "[CLIENT]"
        display_name = f"{username} {role} (ID: {my_id})"
    else:
        display_name = f"{username} [OFFLINE]"
        
    ui_string = f"PLAYER: {display_name}\nHOTBAR:\n"
    for key, data in PART_DATA.items():
        prefix = "> " if key == selected_block_type else "  "
        ui_string += f"{prefix}[{key}] {data['name']}\n"
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
hologram = Entity(model='cube', color=color.white, alpha=0.5, collider=None, add_to_scene_entities=False)

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
    if not mouse.hovered_entity: return None, None, False
    snapped_rot_y = round(player.rotation_y / 90) * 90
    custom_rotation = (0, snapped_rot_y, 0)
    local_scale = PART_DATA[selected_block_type]['scale']
    part_thickness = local_scale[1] if abs(mouse.normal.y) > 0.5 else local_scale[0]
    
    if hasattr(mouse.hovered_entity, 'part_id'):
        h_thickness = mouse.hovered_entity.scale_y if abs(mouse.normal.y) > 0.5 else mouse.hovered_entity.scale_x
        build_pos = mouse.hovered_entity.position + mouse.normal * ((h_thickness / 2) + (part_thickness / 2))
    else:
        build_pos = mouse.world_point + mouse.normal * (part_thickness / 2)
        build_pos.x = round(build_pos.x); build_pos.z = round(build_pos.z); build_pos.y = local_scale[1] / 2
        
    is_valid = in_build_zone(build_pos) and distance(build_pos, player.position) > 0.8
    return build_pos, custom_rotation, is_valid

class VehiclePart(Entity):
    def __init__(self, position=(0,0,0), part_id=1, custom_rot=(0,0,0), local_build=True):
        super().__init__(
            parent=scene, position=position, model=PART_DATA[part_id]['model'],
            scale=PART_DATA[part_id]['scale'], rotation=custom_rot, origin_y=0,
            color=PART_DATA[part_id]['color'], collider='box'
        )
        self.part_id = part_id
        self.weight = PART_DATA[part_id]['weight']
        
        if local_build:
            car_parts.append(self)
        
        coord_key = (round(position[0],2), round(position[1],2), round(position[2],2))
        remote_blocks[coord_key] = self

def input(key):
    global selected_block_type, is_driving

    if key == 'escape':
        mouse.locked = not mouse.locked
        player.enabled = mouse.locked 
        return

    if key.isdigit() and int(key) in PART_DATA:
        selected_block_type = int(key)
        update_hotbar_ui()
        
    if not is_driving and mouse.locked: 
        if key == 'right mouse down' and mouse.hovered_entity:
            if hasattr(mouse.hovered_entity, 'part_id') and mouse.hovered_entity.part_id == 5:
                enter_vehicle(mouse.hovered_entity)
                return 

            build_pos, custom_rotation, is_valid = get_build_pos_rot()
            if build_pos and is_valid:
                VehiclePart(position=build_pos, part_id=selected_block_type, custom_rot=custom_rotation, local_build=True)
                send_net_msg("place", {"pos": [build_pos.x, build_pos.y, build_pos.z], "rot": list(custom_rotation), "part_id": selected_block_type})
                
        if key == 'left mouse down' and mouse.hovered_entity:
            if hasattr(mouse.hovered_entity, 'part_id'):
                pos = mouse.hovered_entity.position
                coord_key = (round(pos.x,2), round(pos.y,2), round(pos.z,2))
                
                send_net_msg("break", {"pos": [pos.x, pos.y, pos.z]})
                if mouse.hovered_entity in car_parts:
                    car_parts.remove(mouse.hovered_entity)
                destroy(mouse.hovered_entity)
                if coord_key in remote_blocks: del remote_blocks[coord_key]

    if key == 'e' and is_driving:
        exit_vehicle()

def enter_vehicle(seat_entity):
    global is_driving, car_weight, max_speed, acceleration, deceleration, current_speed 
    global lowest_y_offset, vehicle_y_velocity, car_velocity, max_fuel, current_fuel
    
    car_weight = sum(part.weight for part in car_parts)
    max_speed = base_engine_power / (car_weight * 0.05) 
    acceleration = base_engine_power / (car_weight * 0.2)
    deceleration = acceleration * 1.5 
    current_speed = 0.0; vehicle_y_velocity = 0.0  
    current_fuel = 100.0; max_fuel = 100.0
    
    vehicle_parent.position = seat_entity.position
    vehicle_parent.rotation = (0, player.rotation_y, 0)
    
    for part in car_parts:
        part.world_parent = vehicle_parent

    lowest_y_offset = 0.0
    for part in car_parts:
        bottom_edge = part.y - (part.scale_y / 2)
        if bottom_edge < lowest_y_offset: lowest_y_offset = bottom_edge
        
    player.enabled = False
    camera.world_parent = scene 
    is_driving = True

def exit_vehicle():
    global is_driving
    if not in_build_zone(vehicle_parent.position):
        nearest = get_nearest_garage(vehicle_parent.position)
        vehicle_parent.position = Vec3(nearest.x, 5, nearest.z) 
    
    for part in car_parts:
        part.world_parent = scene
        
    camera.parent = player.camera_pivot
    camera.position = (0,0,0); camera.rotation = (0,0,0)
    player.position = vehicle_parent.position + Vec3(3, 1, 0) 
    player.enabled = True
    is_driving = False 

def update():
    global current_speed, vehicle_y_velocity, car_velocity, my_id
    
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
                        
            elif msg["type"] == "place":
                b = msg["data"]
                coord = (round(b["pos"][0],2), round(b["pos"][1],2), round(b["pos"][2],2))
                if coord not in remote_blocks:
                    VehiclePart(position=b["pos"], part_id=b["part_id"], custom_rot=b["rot"], local_build=False)
                    
            elif msg["type"] == "break":
                pos = msg["data"]["pos"]
                coord_key = (round(pos[0],2), round(pos[1],2), round(pos[2],2))
                if coord_key in remote_blocks:
                    destroy(remote_blocks[coord_key])
                    del remote_blocks[coord_key]
                    
            elif msg["type"] == "sync_players":
                for p_id, p_data in msg["players"].items():
                    if p_id == my_id: continue
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

        my_pos = vehicle_parent.position if is_driving else player.position
        my_rot = vehicle_parent.rotation_y if is_driving else player.rotation_y
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
        else: hologram.enabled = False
    else: hologram.enabled = False
    
    if is_driving:
        ray = raycast(vehicle_parent.world_position + Vec3(0, 1, 0), Vec3(0, -1, 0), ignore=car_parts, distance=200)
        if ray.hit:
            target_seat_y = ray.world_point.y - lowest_y_offset 
            if vehicle_parent.y > target_seat_y + 0.05:
                vehicle_y_velocity -= 25 * time.dt; vehicle_parent.y += vehicle_y_velocity * time.dt
            else: vehicle_parent.y = target_seat_y; vehicle_y_velocity = 0
        else:
            vehicle_y_velocity -= 25 * time.dt; vehicle_parent.y += vehicle_y_velocity * time.dt

        if held_keys['w']: current_speed += acceleration * time.dt
        elif held_keys['s']: current_speed -= deceleration * time.dt
        else: current_speed = lerp(current_speed, 0, time.dt * 2)

        current_speed = clamp(current_speed, -max_speed * 0.5, max_speed)
        
        if abs(current_speed) > 0.1:
            turn_direction = 1 if current_speed > 0 else -1
            if held_keys['a']: vehicle_parent.rotation_y -= 60 * turn_direction * time.dt
            if held_keys['d']: vehicle_parent.rotation_y += 60 * turn_direction * time.dt
                
        vehicle_parent.position += vehicle_parent.forward * current_speed * time.dt
                
        ideal_cam_pos = vehicle_parent.position - (vehicle_parent.forward * 12) + Vec3(0, 4, 0)
        camera.position = lerp(camera.position, ideal_cam_pos, time.dt * 7)
        camera.look_at(vehicle_parent.position + vehicle_parent.forward * 3 + Vec3(0, 1.5, 0))
        camera.rotation_z = 0 

if not is_multiplayer:
    VehiclePart(position=(-50, 2, 0), part_id=1, local_build=True)
    update_hotbar_ui()

connect_to_lan()
app.run()