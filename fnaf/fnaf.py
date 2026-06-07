from ursina import *
import random

# --- INITIALIZE ENGINE ---
app = Ursina()

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
foxy_stage = 0  # 0: Hidden, 1: Peeking, 2: Ready to Sprint, 3: Sprinting

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
# Central Player Office
office = Entity(model='cube', color=color.hex("#333333"), scale=(10, 6, 10), position=(0, 0, 0), double_sided=True)
desk = Entity(model='cube', color=color.brown, scale=(4, 1.5, 2), position=(0, -2, -2))

# Office Security Doors (Visual Cubes)
left_door = Entity(model='cube', color=color.dark_gray, scale=(0.5, 5, 3), position=(-4.9, 0, 0), enabled=False)
right_door = Entity(model='cube', color=color.dark_gray, scale=(0.5, 5, 3), position=(4.9, 0, 0), enabled=False)

# --- SETUP REMOTE CAMERA ROOMS ---
cam_1a_stage  = Entity(model='cube', color=color.hex("#111111"), scale=(15, 6, 15), position=(0, 20, 100))
cam_1b_dining = Entity(model='cube', color=color.hex("#181818"), scale=(20, 6, 20), position=(40, 20, 100))
cam_1c_cove   = Entity(model='cube', color=color.hex("#1a0000"), scale=(15, 6, 15), position=(-40, 20, 100))
cam_2a_whall  = Entity(model='cube', color=color.hex("#222222"), scale=(6, 5, 25), position=(-20, 2, 50))
cam_4a_ehall  = Entity(model='cube', color=color.hex("#222222"), scale=(6, 5, 25), position=(20, 2, 50))
cam_5_bstage  = Entity(model='cube', color=color.hex("#111122"), scale=(10, 5, 10), position=(40, 20, 60))
cam_6_kitchen = Entity(model='cube', color=color.black, scale=(15, 5, 15), position=(40, 20, 20)) # Pitch Black Feed

# --- SETUP ANIMATRONIC ENTITIES ---
bonnie = Entity(model='cube', color=color.purple, scale=(1.2, 2.5, 1.2))
chica  = Entity(model='cube', color=color.yellow, scale=(1.2, 2.5, 1.2))
freddy = Entity(model='cube', color=color.brown, scale=(1.3, 2.6, 1.3))
foxy   = Entity(model='cube', color=color.red, scale=(1.1, 2.4, 1.1))

# --- HEADS UP DISPLAY (HUD) ---
power_text = Text(text="Power: 100%", position=(-0.85, 0.45), scale=1.5, color=color.green)
time_text  = Text(text="12 AM", position=(0.7, 0.45), scale=1.5, color=color.white)
game_over_text = Text(text="", position=(-0.2, 0.1), scale=3, color=color.red)

# --- SECURITY MONITOR UI ---
monitor_ui = Entity(parent=camera.ui, enabled=False)
static_overlay = Panel(color=color.random_color(), scale=(2, 2), parent=monitor_ui, enabled=False)

# Mini-map Interface Setup
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

# --- SYSTEM UTILITIES & HOOKS ---
def action_switch_cam(cam_id):
    """Handles updating system camera feed locations."""
    global current_cam, static_timer
    current_cam = cam_id
    static_timer = 0.20  
    static_overlay.enabled = True
    
    for cid, btn in cam_buttons.items():
        btn.color = color.green if cid == cam_id else color.dark_gray

# Bind click actions to monitor buttons
for cam_id in cam_buttons.keys():
    cam_buttons[cam_id].on_click = lambda cid=cam_id: action_switch_cam(cid)

def toggle_monitor():
    """Toggles the state of the security monitor interface."""
    global monitor_open, static_timer
    if not game_active or power_outage:
        return

    # Check for direct pull-down jumpscare triggers
    if monitor_open: 
        if bonnie_pos == "OFFICE_DOOR" and not left_door_closed and bonnie_attack_timer > 2.0:
            trigger_jumpscare("Bonnie")
            return
        elif chica_pos == "OFFICE_DOOR" and not right_door_closed and chica_attack_timer > 2.0:
            trigger_jumpscare("Chica")
            return

    monitor_open = not monitor_open
    monitor_ui.enabled = monitor_open
    static_overlay.enabled = monitor_open
    if monitor_open:
        static_timer = 0.15
        action_switch_cam(current_cam)

# Interactive Wall Control Buttons Setup
btn_left_door  = Button(text="DOOR", color=color.red, scale=(0.1, 0.05), position=(-0.75, -0.1))
btn_left_light = Button(text="LIGHT", color=color.white, scale=(0.1, 0.05), position=(-0.75, -0.18))
btn_right_door = Button(text="DOOR", color=color.red, scale=(0.1, 0.05), position=(0.75, -0.1))
btn_right_light= Button(text="LIGHT", color=color.white, scale=(0.1, 0.05), position=(0.75, -0.18))
btn_monitor    = Button(text="CAMERA MONITOR", color=color.blue, scale=(0.25, 0.06), position=(0, -0.4))

# Handle Button Interactions
def toggle_left_door():  global left_door_closed; left_door_closed = not left_door_closed; left_door.enabled = left_door_closed
def toggle_right_door(): global right_door_closed; right_door_closed = not right_door_closed; right_door.enabled = right_door_closed
def toggle_left_light(): global left_light_on; left_light_on = not left_light_on
def toggle_right_light(): global right_light_on; right_light_on = not right_light_on

btn_left_door.on_click = toggle_left_door
btn_right_door.on_click = toggle_right_door
btn_left_light.on_click = toggle_left_light
btn_right_light.on_click = toggle_right_light
btn_monitor.on_click = toggle_monitor

# --- SYSTEM GAME LOGIC MATH ---
def trigger_jumpscare(attacker):
    """Initiates tactical endgame sequencing."""
    global game_active, game_over, jumpscare_active, jumpscare_attacker, monitor_open
    if not game_active:
        return
    game_active = False
    game_over = True
    jumpscare_active = True
    jumpscare_attacker = attacker
    monitor_open = False
    monitor_ui.enabled = False

def process_ai_logic(dt):
    """Increments structural ticks tracking moving threat elements."""
    global ai_tick_timer, bonnie_pos, chica_pos, foxy_stage, foxy_sprint_timer, freddy_pos
    
    # 2 AM Grace Period: 12 AM and 1 AM hours completely bypass AI cycles on Night 1
    if current_night == 1 and current_hour in [12, 1]:
        return
        
    ai_tick_timer += dt
    if ai_tick_timer < 4.0:
        return
    ai_tick_timer = 0.0

    b_diff = 2 + (current_night * 2.5)
    c_diff = 1 + (current_night * 2.2)
    f_diff = 1 + (current_night * 2.0)
    fr_diff = 0.5 + (current_night * 1.5)

    # 1. Bonnie Movement Path
    if random.randint(1, 20) <= b_diff:
        if bonnie_pos == "1A": bonnie_pos = "1B"
        elif bonnie_pos == "1B": bonnie_pos = "5"
        elif bonnie_pos == "5": bonnie_pos = "2A"
        elif bonnie_pos == "2A":
            if not monitor_open: bonnie_pos = "OFFICE_DOOR"
        elif bonnie_pos == "OFFICE_DOOR" and left_door_closed:
            bonnie_pos = "1B"

    # 2. Chica Movement Path
    if random.randint(1, 20) <= c_diff:
        if chica_pos == "1A": chica_pos = "1B"
        elif chica_pos == "1B": chica_pos = "6"
        elif chica_pos == "6": chica_pos = "4A"
        elif chica_pos == "4A":
            if not monitor_open: chica_pos = "OFFICE_DOOR"
        elif chica_pos == "OFFICE_DOOR" and right_door_closed:
            chica_pos = "1B"

    # 3. Foxy Cove Processing (Frozen when viewing CAM 1C)
    if not (monitor_open and current_cam == "1C"):
        if random.randint(1, 20) <= f_diff:
            if foxy_stage < 3:
                foxy_stage += 1
                if foxy_stage == 3:
                    foxy_sprint_timer = 7.0  # Seconds to shut left door

    # 4. Freddy Bear Logic
    if not monitor_open:
        if random.randint(1, 20) <= fr_diff:
            if freddy_pos == "1A": freddy_pos = "1B"
            elif freddy_pos == "1B": freddy_pos = "4A"
            elif freddy_pos == "4A": freddy_pos = "OFFICE_DOOR"
            elif freddy_pos == "OFFICE_DOOR" and right_door_closed:
                freddy_pos = "1A"

def sync_actor_positions():
    """Maps structural coordinate transformations onto 3D actors."""
    # Bonnie Layout Sync
    if bonnie_pos == "1A":     bonnie.position, bonnie.rotation = (-2.5, 20.5, 102), (0, 180, 0)
    elif bonnie_pos == "1B":   bonnie.position, bonnie.rotation = (35, 20.5, 98), (0, 150, 0)
    elif bonnie_pos == "5":    bonnie.position, bonnie.rotation = (38, 20.5, 62), (0, 180, 0)
    elif bonnie_pos == "2A":   bonnie.position, bonnie.rotation = (-20, 0.6, 52), (0, 90, 0)
    elif bonnie_pos == "OFFICE_DOOR": bonnie.position, bonnie.rotation = (-4.2, 0.6, 0), (0, 90, 0)
    bonnie.enabled = left_light_on if bonnie_pos == "OFFICE_DOOR" else True

    # Chica Layout Sync
    if chica_pos == "1A":     chica.position, chica.rotation = (2.5, 20.5, 102), (0, 180, 0)
    elif chica_pos == "1B":   chica.position, chica.rotation = (45, 20.5, 102), (0, 210, 0)
    elif chica_pos == "6":    chica.position, chica.rotation = (42, 20.5, 22), (0, 180, 0)
    elif chica_pos == "4A":   chica.position, chica.rotation = (20, 0.6, 52), (0, -90, 0)
    elif chica_pos == "OFFICE_DOOR": chica.position, chica.rotation = (4.2, 0.6, 0), (0, -90, 0)
    chica.enabled = right_light_on if chica_pos == "OFFICE_DOOR" else True

    # Foxy Stage Sync
    if foxy_stage == 0:   foxy.position, foxy.rotation = (-42, 20.5, 104), (0, 180, 0)
    elif foxy_stage == 1: foxy.position, foxy.rotation = (-40, 20.5, 101), (0, 150, 0)
    elif foxy_stage == 2: foxy.position, foxy.rotation = (-37, 20.5, 98), (0, 130, 0)
    elif foxy_stage == 3: foxy.position, foxy.rotation = (-20, 0.6, 45), (0, 180, 0)
    foxy.enabled = (monitor_open and current_cam == "1C") if foxy_stage < 3 else (monitor_open and current_cam == "2A")

    # Freddy Sync
    if freddy_pos == "1A":     freddy.position, freddy.rotation = (0, 20.5, 104), (0, 180, 0)
    elif freddy_pos == "1B":   freddy.position, freddy.rotation = (40, 20.5, 105), (0, 180, 0)
    elif freddy_pos == "4A":   freddy.position, freddy.rotation = (20, 0.6, 42), (0, -90, 0)
    elif freddy_pos == "OFFICE_DOOR": freddy.position, freddy.rotation = (4.2, 0.6, -1.0), (0, -90, 0)
    
    if power_outage:
        freddy.enabled = True
    else:
        freddy.enabled = right_light_on if freddy_pos == "OFFICE_DOOR" else True


# --- FRAME UPDATE SYSTEM INTERACTION LOOP ---
def update():
    global power, left_door_closed, right_door_closed, left_light_on, right_light_on
    global monitor_open, time_elapsed, current_hour, game_active, game_over
    global win_state, power_outage, static_timer, foxy_sprint_timer, foxy_stage
    global bonnie_attack_timer, chica_attack_timer, freddy_attack_timer, jumpscare_timer
    global jumpscare_active, jumpscare_attacker

    # 1. HANDLE JUMPSCARE RUNTIME ANIMATION
    if jumpscare_active:
        jumpscare_timer += time.dt
        camera.position = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), -3.5)
        
        # Pull specified threat entity straight up into player window bounds
        if jumpscare_attacker == "Bonnie":   bonnie.position = (0, 0, -2); bonnie.enabled = True
        elif jumpscare_attacker == "Chica":  chica.position = (0, 0, -2); chica.enabled = True
        elif jumpscare_attacker == "Freddy": freddy.position = (0, 0, -2); freddy.enabled = True
        elif jumpscare_attacker == "Foxy":   foxy.position = (0, 0, -2); foxy.enabled = True
        
        if jumpscare_timer >= 2.5:
            jumpscare_active = False
            game_over_text.text = "GAME OVER\nPress Esc to Quit"
        return

    if not game_active:
        return

    # 2. STATIC SCREEN FLICKER EFFECTS
    if monitor_open and static_timer > 0:
        static_timer -= time.dt
        static_overlay.color = color.random_color()
        if static_timer <= 0:
            static_overlay.enabled = False

    # 3. TIME PASSAGE PROCESSING (60s Real-Time = 1 Hour In-Game)
    time_elapsed += time.dt
    if time_elapsed >= 60.0:
        time_elapsed = 0.0
        if current_hour == 12:
            current_hour = 1
        else:
            current_hour += 1
            
        if current_hour == 6:
            game_active = False
            win_state = True
            game_over_text.text = "6 AM\nYOU WIN!"
            game_over_text.color = color.green
            return
    time_text.text = f"{current_hour} AM"

    # 4. POWER DRAW MATH & PROCESSING
    drain_factor = 0.15
    if left_door_closed: drain_factor += 0.25
    if right_door_closed: drain_factor += 0.25
    if left_light_on: drain_factor += 0.15
    if right_light_on: drain_factor += 0.15
    if monitor_open: drain_factor += 0.20

    power -= drain_factor * time.dt
    if power <= 0:
        power = 0.0
        power_outage = True
        monitor_open = False
        monitor_ui.enabled = False
        left_door_closed = right_door_closed = left_light_on = right_light_on = False
        left_door.enabled = right_door.enabled = False
        # Instantly trigger Freddy power outage cycle
        freddy_pos = "OFFICE_DOOR"
    power_text.text = f"Power: {int(power)}%"

    # 5. EXECUTE AI ROUTINES
    process_ai_logic(time.dt)
    sync_actor_positions()

    # 6. CAMERA VIEWPANEL SYSTEM ALIGNMENT
    if not monitor_open:
        # Ground player back inside the central hub desk bounds
        camera.position = (0, 0, -4)
        camera.rotation = (0, 0, 0)
    else:
        # Snap central projection matrix over targeted remote facility node structures
        if current_cam == "1A":   camera.position, camera.rotation = (0, 23.5, 94.5), (12, 180, 0)
        elif current_cam == "1B": camera.position, camera.rotation = (40, 23.5, 90.5), (15, 180, 0)
        elif current_cam == "1C": camera.position, camera.rotation = (-40, 23.5, 94.5), (12, 180, 0)
        elif current_cam == "2A": camera.position, camera.rotation = (-20, 3.5, 61.5), (15, 180, 0)
        elif current_cam == "5":  camera.position, camera.rotation = (40, 22.5, 54.5), (15, 180, 0)
        elif current_cam == "4A": camera.position, camera.rotation = (20, 3.5, 61.5), (15, 180, 0)
        elif current_cam == "6":  camera.position, camera.rotation = (40, 22.5, 14.5), (15, 180, 0)

    # 7. THREAT ATTACK COUNTDOWN ENGINE
    # Foxy Sprint Logic
    if foxy_stage == 3:
        foxy_sprint_timer -= time.dt
        if foxy_sprint_timer <= 0:
            if left_door_closed:
                foxy_stage = 0
                power -= 8.0
                action_switch_cam(current_cam) 
            else:
                trigger_jumpscare("Foxy")

    # Bonnie Attack Tracking
    if bonnie_pos == "OFFICE_DOOR":
        if not left_door_closed:
            bonnie_attack_timer += time.dt
            if monitor_open and bonnie_attack_timer > 10.0:
                trigger_jumpscare("Bonnie")
            elif not monitor_open and bonnie_attack_timer > 5.0:
                trigger_jumpscare("Bonnie")
        else:
            bonnie_attack_timer = 0.0

    # Chica Attack Tracking
    if chica_pos == "OFFICE_DOOR":
        if not right_door_closed:
            chica_attack_timer += time.dt
            if monitor_open and chica_attack_timer > 10.0:
                trigger_jumpscare("Chica")
            elif not monitor_open and chica_attack_timer > 5.0:
                trigger_jumpscare("Chica")
        else:
            chica_attack_timer = 0.0

    # Freddy Attack Tracking
    if freddy_pos == "OFFICE_DOOR":
        if not right_door_closed:
            freddy_attack_timer += time.dt
            if monitor_open and freddy_attack_timer > 6.0:
                trigger_jumpscare("Freddy")
            elif not monitor_open and freddy_attack_timer > 3.0:
                trigger_jumpscare("Freddy")
        else:
            freddy_attack_timer = 0.0

# Run the game loop
app.run()