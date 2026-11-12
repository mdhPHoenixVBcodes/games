# Python Mini-Games Collection

Welcome to this repository containing a collection of fun, interactive 2D and 3D games and simulations built using Python! Each script is a standalone project utilizing libraries such as `ursina`, `pygame`, and `turtle`.


> ***Disclaimer: These projects `3dadventure.py`, `mc.py`, `horror.py`, `lego.py`, `timesurvivor.py`, `puss.py`, `puss2.py`, `racing.py`, `shooter.py`, `happy.py`, and `fnaf.py` are made with AI***.


## ⚙️ Requirements & Installation

To run these games, you will need **Python 3.x** installed on your system. You will also need to install the required external libraries. You can install them via pip:

`pip install ursina pygame`

Pls delete `savegame.json` / `brainrot_save.json` cuz that's technically my data

## 🎮 Included Projects
### 1. 3D Adventure Dungeon 
`3dadventure.py`
This game is still in production so bugs may occur.
A multi-phase 3D action-survival game built with the ursina engine. Progress through different dimensions, talk to NPCs, and defeat bosses.

#### Features:
Multiple levels (Plains, Safe Zone, Final Arena etc.), interactive NPCs, unlockable companions, team up abilities, melee and ranged combat, powers, health UI, and a functioning Save/Load system.

#### Controls:

`W, A, S, D` - Move

`Space` - Jump

`Left Click` - Sword Attack

`Right Click` - Shoot Arrow (requires Bow)

`E` - Throw Shockwave Grenade

`F` - Interact with NPCs

`8` - Save Game

`9` - Load Game

`0` / `Esc` - Main Menu

### 2. LAN Survival Horror 
`horror.py`
A terrifying 3D survival horror game built with the ursina engine. Play alone or brave the woods with a friend.

#### Features: 
Single-player and LAN multiplayer modes via a terminal startup menu, dense fog and procedural forest generation, stamina/health UI, a terrifying monster with dynamic pathfinding and jumpscares, and an interactable inventory system.

#### Controls:

`W, A, S, D` - Move

`E` - Interact / Pick up items (like the Axe)

`Esc` - Pause / Mouse Unlock / Close Inventory

### 3. 2D PyCraft 
`mc.py`
A sandbox game built using pygame.

#### Features: 
Procedural terrain generation (dirt, grass, stone, ores, trees), block mining and placing, hotbar and inventory system, basic crafting mechanics (planks, sticks, tools), tool durability, gravity physics, and a day/night cycle.

#### Controls:

`A, D` - Move left/right

`Space` - Jump

`Left Click` - Mine block

`Right Click` - Place selected block

`1-9` - Select hotbar slot

`E` - Open inventory

`F` - Change Mining Mode

### 4. Steal The Brainrots Base Defense (stb.py)
A humorous 3D base-building and collecting game created using the ursina engine.

#### Features: 
Economy and auto-saving system (brainrot_save.json), custom AI bases, procedural environment generation with pyramid hills and lego-style trees, and interactive meme characters (Brainrots like La Vacca, Tung Tung, Ballerina Cappuccino, Orcalero) that generate passive cash per second.

#### Controls:

`W, A, S, D` - Move

`Left Ctrl` - Sprint

`Space` - Jump

`E` - Buy Brainrot from Conveyor / Steal from Enemy Base

`Q` - Drop carried Brainrot at your Base

`Esc` - Unlock Mouse

### 5. Time Survivor (timesurvivor.py)
A fast-paced 2D top-down arena survival game using Python's turtle module.

#### Features: 
Endless waves of enemies, directional shooting mechanics, AoE shockwave attacks, spawnable powerups (speed boost, damage boost), and a survival timer.

#### Controls:

`W, A, S, D` - Move

`K` - Shoot

`E` - Shockwave attack

`Space` - Pause

`R` - Restart

### 6. Interactive Turtle Drawer (tmnt.py)
A console-driven interactive drawing program using the turtle graphics module.

#### Features: 
Terminal-based inputs translate directly to visual drawing commands on the canvas.

#### Controls:
Follow the on-screen terminal prompts to enter movement distances and turning angles (r for right, l for left). Type restart to clear canvas.

### 7. Puss in Boots 3D Arena (puss.py)
A 3D floating battle arena fighter created using the ursina engine. Features a 3-panel character selection UI with a rotating 3D turntable preview, damage numbers, LAN TCP multiplayer mode (Host/Client), training grounds, custom keybindings, admin cheat panel, and an easter egg radar nuke system (nukeyes).

#### Features:
Selectable characters (Puss in Boots, Kitty Softpaws, Death, Perrito), directional attacks, parrying, jump physics, dash cooldowns, Death's whistle audio ability, and custom procedural 3D models with GLB facial meshes.

#### Controls:

`W, A, S, D` - Move

`Left Ctrl` - Sprint

`Space` - Jump

`Left Click` - Attack (Rapier, Daggers, Dual Sickles, or Stick)

`Right Click` - Hold to Block / Parrying

`Shift` - Dash forward

`F`- Death's Whistle ability (Death only)

`Esc` - Pause menu / Unlock mouse

### 8. Puss in Boots 3D Class Brawler (puss2.py)
An upgraded 3D class brawler built in ursina featuring Fortnite-style floating damage numbers, class selection, floating health UI, enemy bot tracking AI, and custom character models.

#### Features: 
7 Playable characters (Puss in Boots, Kitty Softpaws, Death, Perrito, Big Jack Horner, Goldilocks, and Baby Bear) with individual speeds, attack damage, and unique weapon rigs (Wand, Staff, Claws, Dual Sickles). Includes crit multiplier mechanics when attacking mid-air!

#### Controls:

`W, A, S, D` - Move

`Left Ctrl` - Sprint

`Space` - Jump

`Left Click` - Class Attack / Weapon Swing (Airborne hits deal Critical Damage!)

`Right Click` - Hold to Block

`Shift` - Dash forward

`Esc` - Pause Menu / Change Character

### 9. Phoenix Vehicle Builder & Racer (racing.py)
A full 3D vehicle building and racing sandbox built with the ursina engine, featuring singleplayer and LAN multiplayer modes, custom garage build zones, pressure plate blueprint saving/loading, a parts shop, full vehicle physics (acceleration, top speed, suspension braking, drifting, thruster flight), and a complete 10-checkpoint race track circuit with lap timers.

#### Features: 
Build custom cars using Base Blocks, Wheels, Suspensions, Engines, Driver Seats, Fuel Tanks, Aerodynamic Wings, and Thrusters. Includes a functional speed gauge, fuel consumption meter, race portal teleportation, and animated plates.

#### Controls:

`W / S` - Accelerate / Reverse (or Right Click / Left Click)

`A / D` - Steer Vehicle

`Left Ctrl` - Activate Thrusters (Flight / Jump Boost)

`Shift` - Drift / Handbrake

`Space` - Jump vehicle

`E` - Exit Vehicle

`1-9` - Select Build Tool

`Right Click` - Place Block / Enter Driver Seat

`Left Click` - Break Block

`Esc` - Lock / Unlock Mouse

### 10. 3D FPS Shooter (shooter.py)
A 3D first-person shooter framework created using the ursina engine and Panda3D Actors.

#### Features: 
First-person camera movement, animated gun actor (gun.glb) with reload animations, shooting projectile mechanics, aiming down sights (ADS), and a background TCP server architecture for multiplayer expansion.

#### Controls:

`W, A, S, D` - Move

`Space` - Jump

`Left Click` - Shoot projectile

`Right Click` - Aim Down Sights (ADS)

`R` - Play Reload Animation

`Z` - Teleport to Spawn Point

`Esc` - Toggle Mouse Lock

### 11. Trapdoor Rage (happy.py)
A rage platformer built in pygame with random control inversions, jump lockouts, crumbling trap platforms, side walls, level transitions, play timer, death counter, and humorous death quotes.

#### Features: 
3 distinct levels—Level 1 (Trap Platforms & Flag), Level 2 (Infinite Ground, Gap Jumps, Mid-Jump Trap Walls, and Hallucination Flags), and Level 3 (Advanced Traps). Supports both Keyboard and Mouse movement controls!

#### Controls:

`Left / Right Arrows` (or Left Click left/right side of screen) - Move

`Space` (or Right Click) - Jump


### 12. Nights at Python's (fnaf.py)
A full 3D survival horror game built in the ursina engine, inspired by Five Nights at Freddy's.

#### Features:
3D interactive office, interactive wall buttons, sliding security doors, hallway light toggles, camera monitor UI with 7 camera feeds, power management drain system, night progression (12 AM to 6 AM), animatronic AI movement (Bonnie, Chica, Freddy, Foxy), and animated 3D jumpscares.

#### Controls:

`Mouse Movement` - Pan office view

`Left Click` - Click 3D wall buttons (Doors / Lights) or Camera Monitor button

`Camera UI Buttons` (1A - 6) - Switch camera feeds

`Esc` - Quit Game
