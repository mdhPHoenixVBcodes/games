from ursina import *
import random

# --- INITIALIZE ENGINE ---
app = Ursina()
camera.fov = 95  

# --- GLOBAL GAME STATE VARIABLES ---
game_active = True
game_over = False
win_state = False
current_night = 1
current_hour = 12
time_elapsed = 0.0
power = 100.0
power_outage = False

# Camera States
monitor_open = False
current_cam = "1A"
static_timer = 0.0

# Door & Light States
left_door_closed = False
right_door_closed = False
left_light_on = False
right_light_on = False

# AI State Tracking
ai_tick_timer = 0.0
bonnie_pos = "1A"
chica_pos = "1A"
freddy_pos = "1A"
foxy_stage = 0 

# Threat Attack Timers
bonnie_attack_timer = 0.0
chica_attack_timer = 0.0
freddy_attack_timer = 0.0
foxy_sprint_timer = 0.0

# Jumpscare State
jumpscare_active = False
jumpscare_attacker = None
jumpscare_timer = 0.0

# --- BUILD THE 3D ENVIRONMENT ---
office = Entity(model='cube', color=color.hex("#444444"), texture='white_cube', scale=(10, 6, 10), position=(0, 0, 0), double_sided=True)
desk = Entity(model='cube', color=color.brown, texture='white_cube', scale=(4, 1.5, 2), position=(0, -2, -2))

# NEW: Hallway spaces outside the doors to light up!
left_hallway = Entity(model='cube', color=color.hex("#111111"), texture='white_cube', scale=(4, 6, 8), position=(-8, 0, 0), double_sided=True)
right_hallway = Entity(model='cube', color=color.hex("#111111"), texture='white_cube', scale=(4, 6, 8), position=(8, 0, 0), double_sided=True)

# FIXED: Sliding Office Security Doors (Starts open at Y=4.5)
left_door = Entity(model='cube', color=color.dark_gray, texture='white_cube', scale=(1, 5, 3), position=(-4.9, 4.5, 0))
right_door = Entity(model='cube', color=color.dark_gray, texture='white_cube', scale=(1, 5, 3), position=(4.9, 4.5, 0))

# --- 3D INTERACTIVE WALL BUTTONS ---
left_door_btn = Entity(model='cube', color=color.red, scale=(0.2, 0.5, 0.5), position=(-4.8, 0.5, 1.5), collider='box')
left_light_btn = Entity(model='cube', color=color.white, scale=(0.2, 0.5, 0.5), position=(-4.8, -0.5, 1.5), collider='box')

right_door_btn = Entity(model='cube', color=color.red, scale=(0.2, 0.5, 0.5), position=(4.8, 0.5, 1.5), collider='box')
right_light_btn = Entity(model='cube', color=color.white, scale=(0.2, 0.5, 0.5), position=(4.8, -0.5, 1.5), collider='box')

# --- SETUP REMOTE CAMERA ROOMS (Fixed double_sided so we can see them) ---
cam_1a_stage  = Entity(model='cube', color=color.hex("#111111"), texture='white_cube', scale=(15, 6, 15), position=(0, 20, 100), double_sided=True)
cam_1b_dining = Entity(model='cube', color=color.hex("#181818"), texture='white_cube', scale=(20, 6, 20), position=(40, 20, 100), double_sided=True)
cam_1c_cove   = Entity(model='cube', color=color.hex("#1a0000"), texture='white_cube', scale=(15, 6, 15), position=(-40, 20, 100), double_sided=True)
cam_2a_whall  = Entity(model='cube', color=color.hex("#222222"), texture='white_cube', scale=(6, 5, 25), position=(-20, 2, 50), double_sided=True)
cam_4a_ehall  = Entity(model='cube', color=color.hex("#222222"), texture='white_cube', scale=(6, 5, 25), position=(20, 2, 50), double_sided=True)
cam_5_bstage  = Entity(model='cube', color=color.hex("#111122"), texture='white_cube', scale=(10, 5, 10), position=(40, 20, 60), double_sided=True)
cam_6_kitchen = Entity(model='cube', color=color.black, scale=(15, 5, 15), position=(40, 20, 20), double_sided=True) 

# --- SETUP ANIMATRONIC ENTITIES ---
bonnie = Entity(model='cube', color=color.hex('#7d5bc6'), texture='white_cube', scale=0.5, rotation_x=-90, z=3)

bonnie_base_color = color.hex('#7d5bc6')
# Torso assembly
bonnie.torso = Entity(model='cube', color=bonnie_base_color, scale=(1.2, 1.6, 0.9), parent=bonnie)
        
# Head assembly
bonnie.head = Entity(model='sphere', color=bonnie_base_color, scale=0.9, y=1.2, parent=bonnie)
    
# Jaw / Snout structure (Lighter blended magenta)
snout_color = lerp(bonnie_base_color, color.white, 0.3)
bonnie.snout = Entity(model='cube', color=snout_color, scale=(0.5, 0.3, 0.4), y=1.1, z=-0.4, parent=bonnie)
    
# Eyes (White sclera)
bonnie.eye_l = Entity(model='sphere', color=color.white, scale=0.15, x=-0.22, y=1.3, z=-0.35, parent=bonnie)
bonnie.eye_r = Entity(model='sphere', color=color.white, scale=0.15, x=0.22, y=1.3, z=-0.35, parent=bonnie)
    
# Pupils (Magenta)
bonnie.pupil_l = Entity(model='sphere', color=color.magenta, scale=0.06, x=-0.22, y=1.3, z=-0.42, parent=bonnie)
bonnie.pupil_r = Entity(model='sphere', color=color.magenta, scale=0.06, x=0.22, y=1.3, z=-0.42, parent=bonnie)
    
# Limbs
bonnie.leg_l = Entity(model='cube', color=bonnie_base_color, scale=(0.3, 1.2, 0.3), x=-0.4, y=-1.3, parent=bonnie)
bonnie.leg_r = Entity(model='cube', color=bonnie_base_color, scale=(0.3, 1.2, 0.3), x=0.4, y=-1.3, parent=bonnie)
    
# Bonnie's Specific Feature: Tall Rabbit Ears
bonnie.ear_l = Entity(model='cube', color=bonnie_base_color, scale=(0.15, 0.7, 0.1), x=-0.3, y=1.9, parent=bonnie)
bonnie.ear_r = Entity(model='cube', color=bonnie_base_color, scale=(0.15, 0.7, 0.1), x=0.3, y=1.9, parent=bonnie)

chica  = Entity(model='cube', color=color.yellow, texture='white_cube', scale=0.5, rotation_x=180, z=3)

chica_base_color = color.yellow
        
# Torso assembly
chica.torso = Entity(model='cube', color=chica_base_color, scale=(1.2, 1.6, 0.9), parent=chica)

# Head assembly
chica.head = Entity(model='sphere', color=chica_base_color, scale=0.9, y=1.2, parent=chica)

# Chica's Specific Features: Orange Beak and Let's Eat Bib
chica.beak = Entity(model='cube', color=color.orange, scale=(0.4, 0.25, 0.5), y=1.1, z=-0.45, parent=chica)
chica.bib = Entity(model='quad', text="Let's Eat!", color=color.white, scale=(0.8, 0.8), y=0.2, z=-0.46, parent=chica)

# Eyes (White sclera)
chica.eye_l = Entity(model='sphere', color=color.white, scale=0.15, x=-0.22, y=1.3, z=-0.35, parent=chica)
chica.eye_r = Entity(model='sphere', color=color.white, scale=0.15, x=0.22, y=1.3, z=-0.35, parent=chica)

# Pupils (Violet)
chica.pupil_l = Entity(model='sphere', color=color.violet, scale=0.06, x=-0.22, y=1.3, z=-0.42, parent=chica)
chica.pupil_r = Entity(model='sphere', color=color.violet, scale=0.06, x=0.22, y=1.3, z=-0.42, parent=chica)

# Limbs
chica.leg_l = Entity(model='cube', color=chica_base_color, scale=(0.3, 1.2, 0.3), x=-0.4, y=-1.3, parent=chica)
chica.leg_r = Entity(model='cube', color=chica_base_color, scale=(0.3, 1.2, 0.3), x=0.4, y=-1.3, parent=chica)

freddy = Entity(model='cube', color=color.brown, texture='white_cube', scale=0.5, rotation_x=90, z=3)

freddy_base_color = color.brown
        
# Torso assembly
freddy.torso = Entity(model='cube', color=freddy_base_color, scale=(1.2, 1.6, 0.9), parent=freddy)

# Head assembly
freddy.head = Entity(model='sphere', color=freddy_base_color, scale=0.9, y=1.2, parent=freddy)

freddy.ears_l = Entity(model='cube', color=freddy_base_color, scale=(0.6, 0.3, 0.1), y=1.6, x=-0.3, parent=freddy, rotation=(0, 0, 75))
freddy.ears_r = Entity(model='cube', color=freddy_base_color, scale=(0.6, 0.3, 0.1), y=1.7, x=0.3, parent=freddy, rotation=(0, 0, -75))

# Jaw / Snout structure (Lighter brown)
snout_color = lerp(freddy_base_color, color.white, 0.3)
freddy.snout = Entity(model='cube', color=snout_color, scale=(0.5, 0.3, 0.4), y=1.1, z=-0.4, parent=freddy)

# Eyes (White sclera)
freddy.eye_l = Entity(model='sphere', color=color.white, scale=0.15, x=-0.22, y=1.3, z=-0.35, parent=freddy)
freddy.eye_r = Entity(model='sphere', color=color.white, scale=0.15, x=0.22, y=1.3, z=-0.35, parent=freddy)

# Pupils (Blue)
freddy.pupil_l = Entity(model='sphere', color=color.blue, scale=0.06, x=-0.22, y=1.3, z=-0.42, parent=freddy)
freddy.pupil_r = Entity(model='sphere', color=color.blue, scale=0.06, x=0.22, y=1.3, z=-0.42, parent=freddy)

# Limbs
freddy.leg_l = Entity(model='cube', color=freddy_base_color, scale=(0.3, 1.2, 0.3), x=-0.4, y=-1.3, parent=freddy)
freddy.leg_r = Entity(model='cube', color=freddy_base_color, scale=(0.3, 1.2, 0.3), x=0.4, y=-1.3, parent=freddy)

# Freddy's Specific Features: Top Hat and Bowtie
freddy.hat_brim = Entity(model='cylinder', color=color.black, scale=(0.6, 0.05, 0.6), y=1.65, parent=freddy)
freddy.hat_top = Entity(model='cylinder', color=color.black, scale=(0.4, 0.4, 0.4), y=1.85, parent=freddy)
freddy.bowtie = Entity(model='cube', color=color.black, scale=(0.3, 0.15, 0.1), y=0.6, z=-0.5, parent=freddy)

foxy= Entity(model='cube', color=color.red, texture='white_cube', scale=0.5, rotation_x=90, z=3)

foxy_base_color = color.red

# Torso assembly
foxy.torso = Entity(model='cube', color=foxy_base_color, scale=(1.2, 1.6, 0.9), parent=foxy)

# Head assembly
foxy.head = Entity(model='sphere', color=foxy_base_color, scale=0.9, y=1.2, parent=foxy)

# Jaw / Snout structure (Lighter blended red)
snout_color = lerp(foxy_base_color, color.white, 0.3)
foxy.snout = Entity(model='cube', color=snout_color, scale=(0.5, 0.3, 0.4), y=1.1, z=-0.4, parent=foxy)

# Eyes (White sclera)
foxy.eye_l = Entity(model='sphere', color=color.white, scale=0.15, x=-0.22, y=1.3, z=-0.35, parent=foxy)
foxy.eye_r = Entity(model='sphere', color=color.white, scale=0.15, x=0.22, y=1.3, z=-0.35, parent=foxy)

# Pupils (Yellow)
foxy.pupil_l = Entity(model='sphere', color=color.yellow, scale=0.06, x=-0.22, y=1.3, z=-0.42, parent=foxy)
foxy.pupil_r = Entity(model='sphere', color=color.yellow, scale=0.06, x=0.22, y=1.3, z=-0.42, parent=foxy)

# Limbs
foxy.leg_l = Entity(model='cube', color=foxy_base_color, scale=(0.3, 1.2, 0.3), x=-0.4, y=-1.3, parent=foxy)
foxy.leg_r = Entity(model='cube', color=foxy_base_color, scale=(0.3, 1.2, 0.3), x=0.4, y=-1.3, parent=foxy)

# Foxy's Specific Features: Eyepatch and Pirate Hook
foxy.patch = Entity(model='cube', color=color.black, scale=(0.22, 0.22, 0.05), x=-0.22, y=1.33, z=-0.38, parent=foxy)
foxy.hook = Entity(model='cylinder', color=color.light_gray, scale=(0.1, 0.4, 0.1), x=0.7, y=-0.5, parent=foxy)


# --- HEADS UP DISPLAY (HUD) ---
power_text = Text(text="Power: 100%", position=(-0.85, 0.45), scale=1.5, color=color.green)
time_text  = Text(text="12 AM", position=(0.7, 0.45), scale=1.5, color=color.white)
game_over_text = Text(text="", position=(-0.2, 0.1), scale=3, color=color.red)

# --- SECURITY MONITOR UI ---
monitor_ui = Entity(parent=camera.ui, enabled=False)
static_overlay = Panel(color=color.random_color(), scale=(2, 2), parent=monitor_ui, enabled=False)

map_panel = Panel(color=color.black66, scale=(0.35, 0.42), position=(0.62, -0.15), parent=monitor_ui)
map_label = Text(text="CAM NETWORK MAP", scale=0.8, position=(0.48, 0.04), parent=monitor_ui)

cam_buttons = {
    "1A": Button(text="1A: Stage", scale=(0.12, 0.04), position=(0.52, -0.02), parent=monitor_ui, color=color.dark_gray),
    "1B": Button(text="1B: Dining", scale=(0.12, 0.04), position=(0.52, -0.07), parent=monitor_ui, color=color.dark_gray),
    "1C": Button(text="1C: Cove", scale=(0.12, 0.04), position=(0.52, -0.12), parent=monitor_ui, color=color.dark_gray),
    "2A": Button(text="2A: W_Hall", scale=(0.12, 0.04), position=(0.52, -0.19), parent=monitor_ui, color=color.dark_gray),
    "5":  Button(text="5: B_Stage", scale=(0.12, 0.04), position=(0.52, -0.24), parent=monitor_ui, color=color.dark_gray),
    "4A": Button(text="4A: E_Hall", scale=(0.12, 0.04), position=(0.72, -0.19), parent=monitor_ui, color=color.dark_gray),
    "6":  Button(text="6: Kitchen", scale=(0.12, 0.04), position=(0.72, -0.24), parent=monitor_ui, color=color.dark_gray)
}

def action_switch_cam(cam_id):
    global current_cam, static_timer
    current_cam = cam_id
    static_timer = 0.20  
    static_overlay.enabled = True
    for cid, btn in cam_buttons.items():
        btn.color = color.green if cid == cam_id else color.dark_gray

for cam_id in cam_buttons.keys():
    cam_buttons[cam_id].on_click = lambda cid=cam_id: action_switch_cam(cid)

def toggle_monitor():
    global monitor_open, static_timer
    if not game_active or power_outage: return

    if monitor_open: 
        if bonnie_pos == "OFFICE_DOOR" and not left_door_closed and bonnie_attack_timer > 2.0:
            trigger_jumpscare("Bonnie"); return
        elif chica_pos == "OFFICE_DOOR" and not right_door_closed and chica_attack_timer > 2.0:
            trigger_jumpscare("Chica"); return

    monitor_open = not monitor_open
    monitor_ui.enabled = monitor_open
    static_overlay.enabled = monitor_open
    if monitor_open:
        static_timer = 0.15
        action_switch_cam(current_cam)

btn_monitor = Button(text="CAMERA MONITOR", color=color.blue, scale=(0.25, 0.06), position=(0, -0.45))
btn_monitor.on_click = toggle_monitor

# --- 3D BUTTON CLICKING LOGIC ---
def input(key):
    global left_door_closed, left_light_on, right_door_closed, right_light_on
    if not game_active or power_outage or monitor_open: return

    if key == 'left mouse down':
        if mouse.hovered_entity == left_door_btn:
            left_door_closed = not left_door_closed
            left_door_btn.color = color.green if left_door_closed else color.red

        elif mouse.hovered_entity == left_light_btn:
            left_light_on = not left_light_on
            left_light_btn.color = color.yellow if left_light_on else color.white

        elif mouse.hovered_entity == right_door_btn:
            right_door_closed = not right_door_closed
            right_door_btn.color = color.green if right_door_closed else color.red

        elif mouse.hovered_entity == right_light_btn:
            right_light_on = not right_light_on
            right_light_btn.color = color.yellow if right_light_on else color.white

# --- SYSTEM GAME LOGIC MATH ---
def trigger_jumpscare(attacker):
    global game_active, game_over, jumpscare_active, jumpscare_attacker, monitor_open
    if not game_active: return
    game_active = False; game_over = True; jumpscare_active = True
    jumpscare_attacker = attacker
    monitor_open = False; monitor_ui.enabled = False

def process_ai_logic(dt):
    global ai_tick_timer, bonnie_pos, chica_pos, foxy_stage, foxy_sprint_timer, freddy_pos
    if current_night == 1 and current_hour in [12, 1]: return
        
    ai_tick_timer += dt
    if ai_tick_timer < 4.0: return
    ai_tick_timer = 0.0

    b_diff = 2 + (current_night * 2.5)
    c_diff = 1 + (current_night * 2.2)
    f_diff = 1 + (current_night * 2.0)
    fr_diff = 0.5 + (current_night * 1.5)

    if random.randint(1, 20) <= b_diff:
        if bonnie_pos == "1A": bonnie_pos = "1B"
        elif bonnie_pos == "1B": bonnie_pos = "5"
        elif bonnie_pos == "5": bonnie_pos = "2A"
        elif bonnie_pos == "2A":
            if not monitor_open: bonnie_pos = "OFFICE_DOOR"
        elif bonnie_pos == "OFFICE_DOOR" and left_door_closed: bonnie_pos = "1B"

    if random.randint(1, 20) <= c_diff:
        if chica_pos == "1A": chica_pos = "1B"
        elif chica_pos == "1B": chica_pos = "6"
        elif chica_pos == "6": chica_pos = "4A"
        elif chica_pos == "4A":
            if not monitor_open: chica_pos = "OFFICE_DOOR"
        elif chica_pos == "OFFICE_DOOR" and right_door_closed: chica_pos = "1B"

    if not (monitor_open and current_cam == "1C"):
        if random.randint(1, 20) <= f_diff:
            if foxy_stage < 3:
                foxy_stage += 1
                if foxy_stage == 3: foxy_sprint_timer = 7.0

    if not monitor_open:
        if random.randint(1, 20) <= fr_diff:
            if freddy_pos == "1A": freddy_pos = "1B"
            elif freddy_pos == "1B": freddy_pos = "4A"
            elif freddy_pos == "4A": freddy_pos = "OFFICE_DOOR"
            elif freddy_pos == "OFFICE_DOOR" and right_door_closed: freddy_pos = "1A"

def sync_actor_positions():
    # FIXED: Perfectly aligned Z coordinates and rotations so they show up on the cameras!
    if bonnie_pos == "1A":     bonnie.position, bonnie.rotation = (-2.5, 18.5, 102), (0, 180, 0)
    elif bonnie_pos == "1B":   bonnie.position, bonnie.rotation = (35, 18.5, 98), (0, 150, 0)
    elif bonnie_pos == "5":    bonnie.position, bonnie.rotation = (38, 18.5, 62), (0, 180, 0)
    elif bonnie_pos == "2A":   bonnie.position, bonnie.rotation = (-20, 1, 52), (0, 180, 0)
    elif bonnie_pos == "OFFICE_DOOR": bonnie.position, bonnie.rotation = (-6, 0.5, 1), (0, 90, 0)
    bonnie.enabled = left_light_on if bonnie_pos == "OFFICE_DOOR" else True

    if chica_pos == "1A":     chica.position, chica.rotation = (2.5, 18.5, 102), (0, 180, 0)
    elif chica_pos == "1B":   chica.position, chica.rotation = (45, 18.5, 102), (0, 210, 0)
    elif chica_pos == "6":    chica.position, chica.rotation = (42, 18.5, 22), (0, 180, 0)
    elif chica_pos == "4A":   chica.position, chica.rotation = (20, 1, 52), (0, 180, 0)
    elif chica_pos == "OFFICE_DOOR": chica.position, chica.rotation = (6, 0.5, 1), (0, -90, 0)
    chica.enabled = right_light_on if chica_pos == "OFFICE_DOOR" else True

    if foxy_stage == 0:   foxy.position, foxy.rotation = (-42, 18.5, 104), (0, 180, 0)
    elif foxy_stage == 1: foxy.position, foxy.rotation = (-40, 18.5, 101), (0, 150, 0)
    elif foxy_stage == 2: foxy.position, foxy.rotation = (-37, 18.5, 98), (0, 130, 0)
    elif foxy_stage == 3: foxy.position, foxy.rotation = (-20, 1, 45), (0, 180, 0)
    foxy.enabled = (monitor_open and current_cam == "1C") if foxy_stage < 3 else (monitor_open and current_cam == "2A")

    if freddy_pos == "1A":     freddy.position, freddy.rotation = (0, 18.5, 104), (0, 180, 0)
    elif freddy_pos == "1B":   freddy.position, freddy.rotation = (40, 18.5, 105), (0, 180, 0)
    elif freddy_pos == "4A":   freddy.position, freddy.rotation = (20, 1, 42), (0, 180, 0)
    elif freddy_pos == "OFFICE_DOOR": freddy.position, freddy.rotation = (6, 0.5, 2), (0, -90, 0)
    
    if power_outage: 
        freddy.position, freddy.rotation = (-6, 0.5, 1), (0, 90, 0)
        freddy.enabled = True
    else: freddy.enabled = right_light_on if freddy_pos == "OFFICE_DOOR" else True

# --- FRAME UPDATE SYSTEM INTERACTION LOOP ---
def update():
    global power, left_door_closed, right_door_closed, left_light_on, right_light_on
    global monitor_open, time_elapsed, current_hour, game_active, game_over
    global win_state, power_outage, static_timer, foxy_sprint_timer, foxy_stage
    global bonnie_attack_timer, chica_attack_timer, freddy_attack_timer, jumpscare_timer
    global jumpscare_active, jumpscare_attacker, freddy_pos

    if jumpscare_active:
        jumpscare_timer += time.dt
        camera.position = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), -1.5)
        camera.rotation = (0, 0, 0)
        
        if jumpscare_attacker == "Bonnie":   bonnie.position = (0, 0, 1); bonnie.enabled = True
        elif jumpscare_attacker == "Chica":  chica.position = (0, 0, 1); chica.enabled = True
        elif jumpscare_attacker == "Freddy": freddy.position = (0, 0, 1); freddy.enabled = True
        elif jumpscare_attacker == "Foxy":   foxy.position = (0, 0, 1); foxy.enabled = True
        
        if jumpscare_timer >= 2.5:
            jumpscare_active = False; game_over_text.text = "GAME OVER\nPress Esc to Quit"
        return

    if not game_active: return

    # FIXED: Mathematically animate sliding doors instead of making them invisible
    left_door.y = lerp(left_door.y, 0 if left_door_closed else 4.5, time.dt * 8)
    right_door.y = lerp(right_door.y, 0 if right_door_closed else 4.5, time.dt * 8)

    # FIXED: Turn hallways bright white when lights are active!
    left_hallway.color = color.white if left_light_on else color.hex("#111111")
    right_hallway.color = color.white if right_light_on else color.hex("#111111")

    if monitor_open and static_timer > 0:
        static_timer -= time.dt
        static_overlay.color = color.random_color()
        if static_timer <= 0: static_overlay.enabled = False

    time_elapsed += time.dt
    if time_elapsed >= 60.0:
        time_elapsed = 0.0
        current_hour = 1 if current_hour == 12 else current_hour + 1
        if current_hour == 6:
            game_active = False; win_state = True
            game_over_text.text = "6 AM\nYOU WIN!"; game_over_text.color = color.green
            return
    time_text.text = f"{current_hour} AM"

    drain_factor = 0.15
    if left_door_closed: drain_factor += 0.25
    if right_door_closed: drain_factor += 0.25
    if left_light_on: drain_factor += 0.15
    if right_light_on: drain_factor += 0.15
    if monitor_open: drain_factor += 0.20

    power -= drain_factor * time.dt
    if power <= 0:
        power = 0.0; power_outage = True; monitor_open = False; monitor_ui.enabled = False
        left_door_closed = right_door_closed = left_light_on = right_light_on = False
        freddy_pos = "OFFICE_DOOR"
    power_text.text = f"Power: {int(power)}%"

    process_ai_logic(time.dt)
    sync_actor_positions()

    # CAMERA VIEWPANEL & PANNING LOGIC
    if not monitor_open:
        camera.position = (0, 0, 0)
        
        if mouse.x < -0.15: camera.rotation_y -= 110 * time.dt
        elif mouse.x > 0.15: camera.rotation_y += 110 * time.dt
            
        camera.rotation_y = clamp(camera.rotation_y, -60, 60)
        camera.rotation_x = 0
    else:
        # FIXED: Rotated the cameras 180 degrees so they face the monsters!
        if current_cam == "1A":   camera.position, camera.rotation = (0, 21.5, 94), (10, 0, 0)
        elif current_cam == "1B": camera.position, camera.rotation = (40, 21.5, 92), (10, 0, 0)
        elif current_cam == "1C": camera.position, camera.rotation = (-40, 21.5, 92), (10, 0, 0)
        elif current_cam == "2A": camera.position, camera.rotation = (-20, 1.5, 40), (5, 0, 0)
        elif current_cam == "5":  camera.position, camera.rotation = (40, 21.5, 56), (10, 0, 0)
        elif current_cam == "4A": camera.position, camera.rotation = (20, 1.5, 40), (5, 0, 0)
        elif current_cam == "6":  camera.position, camera.rotation = (40, 21.5, 14), (10, 0, 0)

    if foxy_stage == 3:
        foxy_sprint_timer -= time.dt
        if foxy_sprint_timer <= 0:
            if left_door_closed:
                foxy_stage = 0; power -= 8.0; action_switch_cam(current_cam) 
            else: trigger_jumpscare("Foxy")

    if bonnie_pos == "OFFICE_DOOR":
        if not left_door_closed:
            bonnie_attack_timer += time.dt
            if monitor_open and bonnie_attack_timer > 10.0: trigger_jumpscare("Bonnie")
            elif not monitor_open and bonnie_attack_timer > 5.0: trigger_jumpscare("Bonnie")
        else: bonnie_attack_timer = 0.0

    if chica_pos == "OFFICE_DOOR":
        if not right_door_closed:
            chica_attack_timer += time.dt
            if monitor_open and chica_attack_timer > 10.0: trigger_jumpscare("Chica")
            elif not monitor_open and chica_attack_timer > 5.0: trigger_jumpscare("Chica")
        else: chica_attack_timer = 0.0

    if freddy_pos == "OFFICE_DOOR":
        if not right_door_closed:
            freddy_attack_timer += time.dt
            if monitor_open and freddy_attack_timer > 6.0: trigger_jumpscare("Freddy")
            elif not monitor_open and freddy_attack_timer > 3.0: trigger_jumpscare("Freddy")
        else: freddy_attack_timer = 0.0

app.run()