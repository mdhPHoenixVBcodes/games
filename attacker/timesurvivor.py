import turtle
import time
import random
import os

# Set up the screen
screen = turtle.Screen()
screen.title("Time Survivor")
screen.bgcolor("black")
screen.setup(width=720, height=720)
screen.tracer(0)

# Constants
ARENA_SIZE = 350
PLAYER_BASE_SPEED = 5
PLAYER_BOOST_SPEED = 8
ENEMY_BASE_SPEED = 3.5
BULLET_BASE_DMG = 15
BULLET_BOOST_DMG = 25
POWERUP_DURATION = 1500

# Draw visual walls
wall = turtle.Turtle()
wall.hideturtle()
wall.speed(0)
wall.color("white")
wall.pensize(5)
wall.penup()
wall.goto(-ARENA_SIZE, -ARENA_SIZE) # Assuming ARENA_SIZE is defined earlier
wall.pendown()
for _ in range(4):
    wall.forward(ARENA_SIZE * 2)
    wall.left(90)

wall.penup()
# Lift the pen and move the turtle so it doesn't draw a line
wall.goto(300, -300) 
# Write text with custom alignment and font
wall.write("WASD = Move\n" + "K = Shoot\n" + "E = Shockwave\n" + "R = Reset game\n" + "Space = Pause Game\n" + "Q = Quit", align="right", font=("Arial", 12, "italic"))

timer_pen = turtle.Turtle()
timer_pen.hideturtle()
timer_pen.speed(0)
timer_pen.color("white") # Keep it white to match your walls
timer_pen.penup()        # Don't draw a line when moving
timer_pen.goto(0, -300)

# Variables to keep track of time and state
seconds = 0
game_state = "PLAYING" 

# Define the function that updates the timer
def update_timer():
    global seconds

    # 2. THE FIX: Only count up if the game is actively playing
    if game_state == "PLAYING":
        # This now ONLY clears the timer text, keeping your walls and controls safe!
        timer_pen.clear()

        # Write the current time
        timer_pen.write(f"Time: {seconds}s", align="center", font=("Arial", 16, "bold"))
        
        # Add 1 to the seconds counter
        seconds += 1
    
    # Tell the screen to run this function again after 1000 milliseconds (1 second)
    # This MUST stay outside the 'if' statement so the background loop never stops.
    screen.ontimer(update_timer, 1000)

# Start the timer for the first time
update_timer()


# Player setup
player = turtle.Turtle()
player.shape("triangle")
player.color("red")
player.penup()
player_speed = PLAYER_BASE_SPEED
player_health = 100
player_dmg = BULLET_BASE_DMG
player_triple = False

# Health bar turtle
hb_turtle = turtle.Turtle()
hb_turtle.hideturtle()
hb_turtle.penup()
hb_turtle.pensize(10)

# Writer for messages
writer = turtle.Turtle()
writer.hideturtle()
writer.penup()
writer.color("white")

# Powerup setup
p_turtle = turtle.Turtle()
p_turtle.shape("circle")
p_turtle.hideturtle()
p_turtle.penup()

p_active = False
p_type = None 
p_spawn_timer = 200
p_effect_timer = 0

def spawn_powerup():
    global p_active, p_type, p_spawn_timer
    p_active = True
    p_type = random.choice(["SPEED", "STRENGTH", "TRIPLE", "HEALTH"])
    x = random.randint(-ARENA_SIZE + 50, ARENA_SIZE - 50)
    y = random.randint(-ARENA_SIZE + 50, ARENA_SIZE - 50)
    p_turtle.goto(x, y)
    
    colors = {"SPEED": "yellow", "STRENGTH": "blue", "TRIPLE": "red", "HEALTH": "lime"}
    p_turtle.color(colors[p_type])
    p_turtle.showturtle()

def draw_ui():
    hb_turtle.clear()
    # Player Health Bar (max 150) — drawn just inside the top wall
    hb_turtle.goto(-150, ARENA_SIZE - 30)
    hb_turtle.color("red")
    hb_turtle.pendown()
    hb_turtle.goto(150, ARENA_SIZE - 30)
    hb_turtle.penup()
    
    if player_health > 0:
        hb_turtle.goto(-150, ARENA_SIZE - 30)
        hb_turtle.color("lime")
        hb_turtle.pendown()
        hb_turtle.goto(-150 + (player_health * 2), ARENA_SIZE - 30)
        hb_turtle.penup()
    
    writer.goto(0, ARENA_SIZE - 25)
    writer.clear()
    status_text = f"Health: {max(0, int(player_health))}%"
    if p_effect_timer > 0:
        # Display the timer in seconds (assuming 100 updates per second)
        status_text += f" | {p_type} ACTIVE! ({p_effect_timer // 100}s)"
    writer.write(status_text, align="center", font=("Arial", 12, "bold"))

    # Enemy Health Bars
    for i in range(len(enemies)):
        enemy = enemies[i]
        hp = enemy_healths[i]
        max_hp = enemy_traits[i]["max_hp"]
        if hp > 0:
            hb_turtle.pensize(5)
            # Background
            hb_turtle.goto(enemy.xcor() - 20, enemy.ycor() + 25)
            hb_turtle.color("red")
            hb_turtle.pendown()
            hb_turtle.goto(enemy.xcor() + 20, enemy.ycor() + 25)
            hb_turtle.penup()
            # Foreground
            hb_turtle.goto(enemy.xcor() - 20, enemy.ycor() + 25)
            hb_turtle.color("lime")
            hb_turtle.pendown()
            hb_turtle.goto(enemy.xcor() - 20 + (hp / max_hp * 40), enemy.ycor() + 25)
            hb_turtle.penup()
            hb_turtle.pensize(10)

# Enemies setup
enemies = []
enemy_healths = []
enemy_traits = []

def create_enemy_traits():
    roll = random.random()
    traits = {
        "speed": ENEMY_BASE_SPEED,
        "damage": 10,
        "triple": False,
        "max_hp": 50,
        "color": "white"
    }
    
    if roll < 0.05: # 5% Triple Shot
        traits["triple"] = True
        traits["color"] = "red"
    elif roll < 0.10: # 5% Tank (HP)
        traits["max_hp"] = 100
        traits["color"] = "lime"
    elif roll < 0.20: # 10% High Damage
        traits["damage"] = 20
        traits["color"] = "blue"
    elif roll < 0.40: # 20% Fast
        traits["speed"] = ENEMY_BASE_SPEED * 1.5
        traits["color"] = "yellow"
        
    return traits

for _ in range(3):
    enemy = turtle.Turtle()
    enemy.shape("triangle")
    enemy.penup()
    enemies.append(enemy)
    # Traits and initial setup handled in reset_positions() or respawn

last_pause_time = 0  # Cooldown tracker for the pause button

# Key tracking
keys = {"w": False, "a": False, "s": False, "d": False, "e": False, "k": False, "r": False, "q": False, "Return": False}

def k_on(key): keys[key] = True
def k_off(key): keys[key] = False

def shoot_player_bullet():
    if game_state == "PLAYING":
        if player_triple:
            # Spread of 3
            for offset in [-15, 0, 15]:
                bullets_player.append(create_bullet(player.pos(), player.heading() + offset, is_player=True))
        else:
            bullets_player.append(create_bullet(player.pos(), player.heading(), is_player=True))

# Setup Pause Pen
pause_pen = turtle.Turtle()
pause_pen.hideturtle()
pause_pen.color("white")  # Or any color that stands out
pause_pen.penup()
pause_pen.goto(0, 0)

def toggle_pause():
    global game_state, last_pause_time
    
    # Anti-flicker cooldown for use with onkeypress
    current_time = time.time()
    if current_time - last_pause_time < 0.2:
        return
    last_pause_time = current_time
    
    if game_state.strip() == "PLAYING":
        game_state = "PAUSED"
        screen.title("Time Survivor - PAUSED")
        pause_pen.write("PAUSED", align="center", font=("Arial", 36, "bold"))
    elif game_state.strip() == "PAUSED":
        game_state = "PLAYING"
        screen.title("Time Survivor")
        pause_pen.clear()  # Erase the "PAUSED" text to resume
        
    # Force the screen to draw the text!
    screen.update()

def move_up():
    if game_state == "PLAYING":
        player.setheading(90)
        player.forward(player_speed)

def close_window():
    os.system("cls")
    turtle.bye()

# Shockwave
shockwave = turtle.Turtle()
shockwave.hideturtle()
shockwave.penup()
shockwave.color("cyan")
shockwave.pensize(2)

shockwave_active = False
shockwave_radius = 0
shockwave_max_radius = 150
shockwave_pos = (0, 0)

# Bullets
bullets_enemy = []
bullets_player = []
bullet_speed = 10
shoot_delay = 75
shoot_timers = [random.randint(0, shoot_delay) for _ in range(3)]

def create_bullet(pos, heading_or_target, is_player=False, damage=10):
    bullet = turtle.Turtle()
    bullet.shape("circle")
    bullet.shapesize(0.3)
    bullet.color("red" if is_player else "white")
    bullet.penup()
    bullet.goto(pos)
    bullet.damage = damage # Custom attribute
    
    if isinstance(heading_or_target, (int, float)): # It's a heading
        bullet.setheading(heading_or_target)
    else: # It's a target pos
        angle = bullet.towards(heading_or_target)
        if not is_player and random.random() > 0.5: angle += random.uniform(-20, 20)
        bullet.setheading(angle)
    return bullet

def reset_game():
    global player_health, game_state, shockwave_active, player_speed, player_dmg, player_triple, p_active, p_effect_timer, seconds
    
    player_health = 100
    player_speed = PLAYER_BASE_SPEED
    player_dmg = BULLET_BASE_DMG
    player_triple = False
    p_active = False
    p_effect_timer = 0
    p_turtle.hideturtle()
    
    # Reset timer
    seconds = 0
    timer_pen.clear()
    timer_pen.write("Time: 0s", align="center", font=("Arial", 16, "bold"))
    
    # FIX: Erase the pause text in case the user resets while the game is paused
    game_state = "PLAYING"
    screen.title("Time Survivor")
    pause_pen.clear() 
    
    shockwave_active = False
    shockwave.clear()
    player.goto(0, 0)
    
    enemy_healths.clear()
    enemy_traits.clear()
    for i in range(len(enemies)):
        x = random.choice([random.randint(-ARENA_SIZE+20, -100), random.randint(100, ARENA_SIZE-20)])
        y = random.choice([random.randint(-ARENA_SIZE+20, -100), random.randint(100, ARENA_SIZE-20)])
        enemies[i].goto(x, y)
        traits = create_enemy_traits()
        enemy_traits.append(traits)
        enemy_healths.append(traits["max_hp"])
        enemies[i].color(traits["color"])
        enemies[i].showturtle()
        
    for b in bullets_enemy + bullets_player:
        b.hideturtle()
    bullets_enemy.clear()
    bullets_player.clear()
    writer.clear()
    for k in keys: keys[k] = False

# --- KEY BINDINGS ---
# Bind movement and utility keys
for key in ["w", "a", "s", "d", "e", "W", "A", "S", "D", "E"]:
    screen.onkeypress(lambda k=key.lower(): k_on(k), key)
    screen.onkeyrelease(lambda k=key.lower(): k_off(k), key)

screen.onkeypress(shoot_player_bullet, "k")
screen.onkeypress(shoot_player_bullet, "K")
screen.onkeypress(reset_game, "r")
screen.onkeypress(reset_game, "R")
screen.onkeypress(lambda: k_on("Return"), "Return")
screen.onkeypress(close_window, "q")
screen.onkeypress(close_window, "Q")
screen.onkeypress(toggle_pause, "p")
screen.onkeypress(toggle_pause, "P")
screen.onkeypress(toggle_pause, "space")

# listen() must be called after bindings are set for best compatibility
screen.listen()

reset_game()
screen.update() # Ensure everything is drawn before the startup pause

time.sleep(1)  # 1-second pause before game start
# Game loop
try:
    while True:
        if game_state == "PLAYING":
            draw_ui()

            # Powerup Spawning
            if not p_active and p_effect_timer <= 0:
                p_spawn_timer -= 1
                if p_spawn_timer <= 0:
                    spawn_powerup()
            
            if p_active:
                if player.distance(p_turtle) < 25:
                    p_active = False
                    p_turtle.hideturtle()
                    if p_type == "HEALTH":
                        player_health = min(150, player_health + 50)
                        p_spawn_timer = 300
                    else:
                        p_effect_timer = POWERUP_DURATION
                        if p_type == "SPEED": player_speed = PLAYER_BOOST_SPEED
                        elif p_type == "STRENGTH": player_dmg = BULLET_BOOST_DMG
                        elif p_type == "TRIPLE": player_triple = True
            
            if p_effect_timer > 0:
                p_effect_timer -= 1
                if p_effect_timer <= 0:
                    player_speed = PLAYER_BASE_SPEED
                    player_dmg = BULLET_BASE_DMG
                    player_triple = False
                    p_spawn_timer = 300 

            # Move player
            new_x = player.xcor()
            new_y = player.ycor()
            moving = False
            if keys["w"]: new_y += player_speed; moving = True
            if keys["s"]: new_y -= player_speed; moving = True
            if keys["a"]: new_x -= player_speed; moving = True
            if keys["d"]: new_x += player_speed; moving = True
            
            if -ARENA_SIZE+10 < new_x < ARENA_SIZE-10: player.setx(new_x)
            if -ARENA_SIZE+10 < new_y < ARENA_SIZE-10: player.sety(new_y)
            
            if moving:
                if keys["w"] and keys["d"]: player.setheading(45)
                elif keys["w"] and keys["a"]: player.setheading(135)
                elif keys["s"] and keys["d"]: player.setheading(315)
                elif keys["s"] and keys["a"]: player.setheading(225)
                elif keys["w"]: player.setheading(90)
                elif keys["s"]: player.setheading(270)
                elif keys["a"]: player.setheading(180)
                elif keys["d"]: player.setheading(0)

            # Shockwave
            if keys["e"] and not shockwave_active:
                shockwave_active = True
                shockwave_radius = 0
                shockwave_pos = (player.xcor(), player.ycor())

            if shockwave_active:
                shockwave.clear()
                shockwave.goto(shockwave_pos[0], shockwave_pos[1] - shockwave_radius)
                shockwave.setheading(0)
                shockwave.pendown()
                shockwave.circle(shockwave_radius)
                shockwave.penup()
                shockwave_radius += 10
                if shockwave_radius > shockwave_max_radius:
                    shockwave_active = False; shockwave.clear()

            # Enemies
            for i in range(len(enemies)):
                enemy = enemies[i]
                if enemy_healths[i] <= 0: continue
                traits = enemy_traits[i]

                shoot_timers[i] -= 1
                if shoot_timers[i] <= 0:
                    if traits["triple"]:
                        # Triple shot towards player
                        base_angle = enemy.towards(player)
                        for offset in [-15, 0, 15]:
                            # Hacky way to set heading directly in create_bullet
                            b = create_bullet(enemy.pos(), player.pos(), damage=traits["damage"])
                            b.setheading(b.heading() + offset)
                            bullets_enemy.append(b)
                    else:
                        bullets_enemy.append(create_bullet(enemy.pos(), player.pos(), damage=traits["damage"]))
                    shoot_timers[i] = shoot_delay

                if shockwave_active and enemy.distance(shockwave_pos) < shockwave_radius:
                    enemy.setheading(enemy.towards(shockwave_pos))
                    enemy.backward(traits["speed"] * 4) 
                else:
                    enemy.setheading(enemy.towards(player))
                    enemy.forward(traits["speed"])
                
                for j in range(len(enemies)):
                    if i != j and enemy_healths[j] > 0:
                        if enemy.distance(enemies[j]) < 20:
                            enemy.setheading(enemy.towards(enemies[j]))
                            enemy.backward(2)

                if enemy.distance(player) < 15:
                    player.setheading(player.towards(enemy))
                    player.backward(15)
                    if player.xcor() > ARENA_SIZE-10: player.setx(ARENA_SIZE-10)
                    if player.xcor() < -ARENA_SIZE+10: player.setx(-ARENA_SIZE+10)
                    if player.ycor() > ARENA_SIZE-10: player.sety(ARENA_SIZE-10)
                    if player.ycor() < -ARENA_SIZE+10: player.sety(-ARENA_SIZE+10)

            # Enemy Bullets
            for bullet in bullets_enemy[:]:
                bullet.forward(bullet_speed)
                if bullet.distance(player) < 15:
                    player_health -= bullet.damage
                    bullet.hideturtle()
                    if bullet in bullets_enemy: bullets_enemy.remove(bullet)
                    player.color("orange"); screen.update(); time.sleep(0.02); player.color("red")
                elif abs(bullet.xcor()) > ARENA_SIZE or abs(bullet.ycor()) > ARENA_SIZE:
                    bullet.hideturtle()
                    if bullet in bullets_enemy: bullets_enemy.remove(bullet)

            # Player Bullets
            for bullet in bullets_player[:]:
                bullet.forward(bullet_speed + 2)
                hit = False
                for i in range(len(enemies)):
                    if enemy_healths[i] > 0 and bullet.distance(enemies[i]) < 20:
                        enemy_healths[i] -= player_dmg
                        bullet.hideturtle()
                        if bullet in bullets_player: bullets_player.remove(bullet)
                        hit = True
                        if enemy_healths[i] <= 0:
                            enemies[i].hideturtle()
                            def respawn(idx=i):
                                enemies[idx].goto(random.choice([-ARENA_SIZE+50, ARENA_SIZE-50]), random.choice([-ARENA_SIZE+50, ARENA_SIZE-50]))
                                traits = create_enemy_traits()
                                enemy_traits[idx] = traits
                                enemy_healths[idx] = traits["max_hp"]
                                enemies[idx].color(traits["color"])
                                enemies[idx].showturtle()
                            screen.ontimer(respawn, 3000)
                        break
                if not hit and (abs(bullet.xcor()) > ARENA_SIZE or abs(bullet.ycor()) > ARENA_SIZE):
                    bullet.hideturtle()
                    if bullet in bullets_player: bullets_player.remove(bullet)

            if player_health <= 0:
                game_state = "GAMEOVER"
                writer.goto(0, 0)
                writer.write("GAME OVER\nPress ENTER to Restart", align="center", font=("Arial", 24, "bold"))

        elif game_state == "GAMEOVER":
            if keys["Return"]:
                reset_game()

        screen.update()
        time.sleep(0.01)

except turtle.Terminator:
    pass
except Exception:
    pass
