from ursina import *
import random

# ---------------------------------------------------------
# TERMINAL INPUT
# ---------------------------------------------------------
user_name = input("Enter your username: ")
if not user_name:
    user_name = "Player"

app = Ursina()

# ---------------------------------------------------------
# 1. ENVIRONMENT (Land, Path, Pyramids, Trees, & Houses)
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
    color=color.rgb32(150, 111, 83), 
    position=(0, 0.05, 0), 
    collider='box'
)

lucky_house_index = random.randint(0, 5)
current_house_count = 0

def create_house(pos, side):
    global current_house_count
    house = Entity(position=pos, scale=5)
    house.rotation_y = 90 if side == 1 else -90
    
    wall_color = color.rgb32(240, 240, 240)
    roof_color = color.rgb32(200, 40, 40)
    
    # Walls
    Entity(parent=house, model='cube', color=wall_color, scale=(0.5, 6, 6), position=(-2.75, 3, 0), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(0.5, 6, 6), position=(2.75, 3, 0), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(6, 6, 0.5), position=(0, 3, 2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 6, 0.5), position=(-2, 3, -2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 6, 0.5), position=(2, 3, -2.75), collider='box')
    Entity(parent=house, model='cube', color=wall_color, scale=(2, 2, 0.5), position=(0, 5, -2.75), collider='box')
    
    # Roof
    Entity(parent=house, model='cube', color=roof_color, scale=(6.5, 0.5, 6.5), position=(0, 6.25, 0), collider='box')

    if current_house_count == lucky_house_index:
        Text(
            text=user_name.upper(),
            parent=house,
            position=(0, 8, 0),
            scale=15,
            origin=(0,0),
            color=color.yellow,
            background=True
        )
    
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
# 2. PLAYER (Lego Minifigure)
# ---------------------------------------------------------

player = Entity(position=(0, 5, 0))

Entity(parent=player, model='cube', color=color.blue, scale=(0.8, 0.6, 0.4), position=(0, 0.3, 0))
Entity(parent=player, model='cube', color=color.red, scale=(1, 0.8, 0.5), position=(0, 1, 0))
Entity(parent=player, model='cube', color=color.yellow, scale=(0.6, 0.6, 0.6), position=(0, 1.7, 0))
Entity(parent=player, model='cube', color=color.yellow, scale=(0.3, 0.2, 0.3), position=(0, 2.1, 0))

player_name_tag = Text(
    text=user_name,
    parent=player,
    position=(0, 3, 0),
    scale=10,
    origin=(0,0),
    color=color.white
)

player.normal_speed = 10     
player.sprint_speed = 18    
player.speed = player.normal_speed 
player.velocity_y = 0
player.is_jumping = False
player.gravity = 1.5
player.jump_power = 0.85 

# ---------------------------------------------------------
# 3. CAMERA RESTORED
# ---------------------------------------------------------
camera_pivot = Entity(parent=player, position=(0, 2, 0))
camera.parent = camera_pivot

# REVERTED: Back to the original third-person position
camera.position = (0, 2, -12) 
camera.fov = 90 
mouse.locked = True 

def update():
    player_name_tag.look_at(camera, 'back')

    # Mouse movement handles the LOOKING
    player.rotation_y += mouse.velocity[0] * 150
    camera_pivot.rotation_x -= mouse.velocity[1] * 150
    camera_pivot.rotation_x = clamp(camera_pivot.rotation_x, -20, 80)

    # FOV Stretch logic
    if held_keys['left control'] or held_keys['right control']:
        player.speed = player.sprint_speed
        camera.fov = lerp(camera.fov, 110, time.dt * 8) 
    else:
        player.speed = player.normal_speed
        camera.fov = lerp(camera.fov, 90, time.dt * 8)

    direction = player.forward * (held_keys['w'] - held_keys['s']) + \
                player.right * (held_keys['d'] - held_keys['a'])
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

def input(key):
    if key == 'escape':
        mouse.locked = not mouse.locked

app.run()