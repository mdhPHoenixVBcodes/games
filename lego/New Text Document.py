from ursina import *
import random
import json
import os

# ---------------------------------------------------------
# TERMINAL INPUT & SAVE DATA
# ---------------------------------------------------------
user_name = input("Enter your username: ")
if not user_name:
    user_name = "Player"

# LOAD SAVE DATA (Starts with $100 now!)
save_file = "brainrot_save.json"
def load_game():
    if os.path.exists(save_file):
        try:
            with open(save_file, "r") as f:
                data = json.load(f)
                return data.get("cash", 100) # Defaults to 100 if no cash saved
        except:
            return 100
    return 100 # Starting cash

def save_game(current_cash):
    with open(save_file, "w") as f:
        json.dump({"cash": int(current_cash)}, f)

app = Ursina()

# ---------------------------------------------------------
# 1. ENVIRONMENT (Land, Conveyor, Pyramids, Trees, & Bases)
# ---------------------------------------------------------

custom_green = color.rgb32(16, 108, 1)

ground = Entity(
    model='plane', 
    scale=(500, 1, 500), 
    color=custom_green, 
    texture='white_cube',   
    texture_scale=(50, 50),
    collider='box',
    position=(0,0,0)
)

path = Entity(
    model='cube',
    scale=(16, 0.1, 500), 
    color=color.dark_gray, 
    position=(0, 0.05, 0), 
    collider='box'
)

# GAME UI & CASH
cash = load_game() 
cash_text = Text(text=f'Cash: ${int(cash)}', position=(-0.85, 0.45), scale=2, color=color.green)
Text(text="[E] Buy (Conveyor) or Steal (Enemy Base) | [Q] Drop at Base", position=(0, 0.4), origin=(0,0), scale=1.5, color=color.yellow)

lucky_house_index = random.randint(0, 5)
current_house_count = 0
bases = []

def create_house(pos, side):
    global current_house_count
    house = Entity(position=pos, scale=5)
    house.rotation_y = 90 if side == 1 else -90
    
    is_player = (current_house_count == lucky_house_index)
    wall_color = color.rgb32(240, 240, 240)
    roof_color = color.green if is_player else color.rgb32(200, 40, 40)
    
    # Walls
    Entity(parent=house, model='cube', color=wall_color, scale=(0.5, 6, 6), position=(-2.75, 3, 0), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(0.5, 6, 6), position=(2.75, 3, 0), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(6, 6, 0.5), position=(0, 3, 2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 6, 0.5), position=(-2, 3, -2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 6, 0.5), position=(2, 3, -2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 2, 0.5), position=(0, 5, -2.75), collider='box')
    
    # Roof
    Entity(parent=house, model='cube', color=roof_color, scale=(6.5, 0.5, 6.5), position=(0, 6.25, 0), collider='box')

    Text(
        text=f"{user_name.upper()}'S BASE" if is_player else "ENEMY BASE",
        parent=house,
        position=(0, 6, -3.1),
        scale=15,
        origin=(0,0),
        color=color.yellow if is_player else color.red,
        background=True
    )
    
    bases.append({
        'entity': house,
        'is_player': is_player,
        'brainrots': [] 
    })
    
    current_house_count += 1

z_positions = [-100, 0, 100] 
for z in z_positions:
    create_house(pos=(35, 0, z), side=1)
    create_house(pos=(-35, 0, z), side=-1)

def create_lego_tree(pos):
    tree = Entity(position=pos, scale=4)
    for i in range(3):
        Entity(parent=tree, model='cube', color=color.brown, scale=(0.4, 0.4, 0.4), position=(0, (i*0.4)+0.2, 0), collider='box')
    canopy_parts = [(0.6, 1.3, 0), (0, 1.3, 0.6), (-0.6, 1.3, 0), (0, 1.3, -0.6), (0, 1.8, 0)]
    for part_pos in canopy_parts:
        Entity(parent=tree, model='cube', color=custom_green, scale=(0.5, 0.5, 0.5), position=part_pos, collider='box')

def create_pyramid_hill(pos, steps):
    hill = Entity(position=pos)
    for i in range(steps):
        step_size = (steps - i) * 3.5 
        step_height = 0.6 
        y_pos = (i * step_height) + (step_height / 2)
        Entity(parent=hill, model='cube', color=custom_green, scale=(step_size, step_height, step_size), position=(0, y_pos, 0), collider='box')

for _ in range(30):
    hx, hz = random.uniform(-200, 200), random.uniform(-200, 200)
    if abs(hx) < 60: continue
    create_pyramid_hill((hx, 0, hz), steps=random.randint(6, 15))

for _ in range(60):
    tx, tz = random.uniform(-240, 240), random.uniform(-240, 240)
    if abs(tx) < 60: continue
    create_lego_tree((tx, 0, tz))

# ---------------------------------------------------------
# BRAINROT CHARACTERS GENERATION 
# ---------------------------------------------------------
brainrot_types = {
    "La Vacca": 10,
    "Tung Tung": 25,
    "Italian Brainrot": 50,
    "Orcalero": 100
}

brainrots_in_world = []
carried_brainrot = None

def spawn_brainrot():
    b = Entity(model='cube', color=color.random_color(), scale=1.5, position=(0, 1, 240), collider='box')
    
    b_name = random.choice(list(brainrot_types.keys()))
    b.value = brainrot_types[b_name]
    
    # NEW: Text size increased to 15, positioned slightly higher (y=1.5) to avoid overlapping the cube
    b.name_tag = Text(text=f"{b_name}\nCost: ${b.value} (+${b.value}/s)", parent=b, y=1.5, scale=15, origin=(0,0))
    b.state = 'conveyor' 
    b.base_owner = None
    brainrots_in_world.append(b)
    
    if random.random() > 0.5:
        enemy_bases = [base for base in bases if not base['is_player']]
        target_base = random.choice(enemy_bases)
        enemy_b = Entity(model='cube', color=color.random_color(), scale=1.5, position=target_base['entity'].position + Vec3(0, 1, 0), collider='box')
        
        eb_name = random.choice(list(brainrot_types.keys()))
        enemy_b.value = brainrot_types[eb_name]
        # NEW: Text size 15 for enemy base brainrots as well
        enemy_b.name_tag = Text(text=f"{eb_name}\nCost: ${enemy_b.value} (+${enemy_b.value}/s)", parent=enemy_b, y=1.5, scale=15, origin=(0,0))
        
        enemy_b.state = 'base'
        enemy_b.base_owner = target_base
        target_base['brainrots'].append(enemy_b)
        brainrots_in_world.append(enemy_b)

    invoke(spawn_brainrot, delay=6)

invoke(spawn_brainrot, delay=2)

# ---------------------------------------------------------
# 2. PLAYER & CAMERA
# ---------------------------------------------------------
player = Entity(position=(0, 5, 0))
Entity(parent=player, model='cube', color=color.blue, scale=(0.8, 0.6, 0.4), position=(0, 0.3, 0))
Entity(parent=player, model='cube', color=color.red, scale=(1, 0.8, 0.5), position=(0, 1, 0))
Entity(parent=player, model='cube', color=color.yellow, scale=(0.6, 0.6, 0.6), position=(0, 1.7, 0))
Entity(parent=player, model='cube', color=color.yellow, scale=(0.3, 0.2, 0.3), position=(0, 2.1, 0))

player_name_tag = Text(text=user_name, parent=player, position=(0, 3, 0), scale=10, origin=(0,0), color=color.white)

player.normal_speed = 10     
player.sprint_speed = 18    
player.speed = player.normal_speed 
player.velocity_y = 0
player.is_jumping = False
player.gravity = 1.5
player.jump_power = 0.85 

camera_pivot = Entity(parent=player, position=(0, 2, 0))
camera.parent = camera_pivot
camera.position = (0, 2, -12) 
camera.fov = 90 
mouse.locked = True 

# ---------------------------------------------------------
# 3. GAME LOOP
# ---------------------------------------------------------
save_timer = 0 

# Track key presses to prevent holding 'E' from draining money instantly
e_pressed_last_frame = False 

def update():
    global cash, carried_brainrot, save_timer, e_pressed_last_frame
    
    player_name_tag.look_at(camera, Vec3.back)

    # Mouse movement
    player.rotation_y += mouse.velocity[0] * 150
    camera_pivot.rotation_x -= mouse.velocity[1] * 150
    camera_pivot.rotation_x = clamp(camera_pivot.rotation_x, -20, 80)

    # FOV & Sprint
    if held_keys['left control'] or held_keys['right control']:
        player.speed = player.sprint_speed
        camera.fov = lerp(camera.fov, 110, time.dt * 8) 
    else:
        player.speed = player.normal_speed
        camera.fov = lerp(camera.fov, 90, time.dt * 8)

    # Movement & Jump
    direction = player.forward * (held_keys['w'] - held_keys['s']) + player.right * (held_keys['d'] - held_keys['a'])
    player.position += direction * player.speed * time.dt

    if held_keys['space'] and not player.is_jumping:
        player.velocity_y = player.jump_power
        player.is_jumping = True

    player.velocity_y -= player.gravity * time.dt
    player.y += player.velocity_y

    ground_ray = raycast(player.position + Vec3(0, 0.5, 0), direction=(0, -1, 0), ignore=(player,), distance=0.6)
    if ground_ray.hit:
        player.y = ground_ray.world_point.y
        player.velocity_y = 0
        player.is_jumping = False
    elif player.y <= 0:
        player.y = 0
        player.velocity_y = 0
        player.is_jumping = False

    # -----------------------------------------------------
    # GAME MECHANICS: Cash, Saves, Buying, Stealing
    # -----------------------------------------------------
    
    for base in bases:
        if base['is_player']:
            for b in base['brainrots']:
                cash += b.value * time.dt
            cash_text.text = f'Cash: ${int(cash)}'
            
    save_timer += time.dt
    if save_timer > 3.0:
        save_game(cash)
        save_timer = 0
            
    # Clean Single-Press Logic for 'E'
    e_is_down = held_keys['e']
    just_pressed_e = e_is_down and not e_pressed_last_frame
    e_pressed_last_frame = e_is_down

    for b in brainrots_in_world:
        b.name_tag.look_at(camera, Vec3.back)
        
        if b.state == 'conveyor':
            b.z -= 5 * time.dt 
            if b.z < -250:
                b.z = 240 
                
            # NEW: Buying logic - Must have enough money!
            if carried_brainrot is None and distance(player, b) < 4 and just_pressed_e:
                if cash >= b.value:
                    cash -= b.value  # Deduct the cost
                    cash_text.text = f'Cash: ${int(cash)}'
                    b.state = 'carried'
                    carried_brainrot = b
                else:
                    # Player doesn't have enough money, do nothing!
                    print("Not enough cash to buy this Brainrot!")
                
        elif b.state == 'carried':
            target_pos = player.world_position + player.back * 3 + Vec3(0, 1.5, 0)
            b.position = lerp(b.position, target_pos, time.dt * 10)
            
            if held_keys['q']:
                for base in bases:
                    if distance(player, base['entity']) < 18:
                        b.state = 'base'
                        b.base_owner = base
                        base['brainrots'].append(b)
                        b.position = base['entity'].position + Vec3(random.uniform(-4, 4), 1, random.uniform(-4, 4))
                        carried_brainrot = None
                        break
                        
        elif b.state == 'base':
            # NEW: Stealing from an enemy base remains totally FREE
            if b.base_owner and not b.base_owner['is_player']:
                if carried_brainrot is None and distance(player, b) < 4 and just_pressed_e:
                    b.base_owner['brainrots'].remove(b)
                    b.state = 'carried'
                    carried_brainrot = b
                    b.base_owner = None

def input(key):
    if key == 'escape':
        mouse.locked = not mouse.locked

app.run()