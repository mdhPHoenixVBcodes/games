# Python Mini-Games Collection

Welcome to this repository containing a collection of fun, interactive 2D and 3D games and simulations built using Python! Each script is a standalone project using ***AI*** utilizing different libraries such as `pygame`, `ursina`, and the built-in `turtle` module.


> ***Disclaimer: These projects `3dadventure.py`, `mc.py`, `horror.py`, `lego.py` and `timesurvivor.py` are made with AI***.


## ⚙️ Requirements & Installation

To run these games, you will need **Python 3.x** installed on your system. You will also need to install the required external libraries. You can install them via pip:

```bash
pip install pygame ursina
```
> Pls delete savegame.json cuz that's technically my data

# 🎮 Included Projects
## 1. 3D Adventure Dungeon (3dadventure.py)
### This game is still in production so bugs may occur.
A multi-phase 3D action-survival game built with the ursina engine. Progress through different dimensions, talk to NPCs, and defeat bosses.

Features: Multiple levels (Plains, Safe Zone, Final Arena etc.), interactive NPCs, unlockable companions, team up abilities, melee and ranged combat, powers, health UI, and a functioning Save/Load system.

**Controls:**

* `W, A, S, D` - Move

* `Space` - Jump

* `Left Click` - Sword Attack

* `Right Click` - Shoot Arrow (requires Bow)

* `E` - Throw Shockwave Grenade

* `F` - Interact with NPCs

* `8` - Save Game

* `9` - Load Game

* `0` - Pause/Main Menu

* `Esc` - Main Menu

## 2. LAN Survival Horror (horror.py)
A terrifying 3D survival horror game built with the ursina engine. Play alone or brave the woods with a friend.

Features: Single-player and LAN multiplayer modes via a terminal startup menu, dense fog and procedural forest generation, stamina/health UI, a terrifying monster with dynamic pathfinding and jumpscares, and an interactable inventory system.

**Controls:**

* `W, A, S, D` - Move

* `E` - Interact / Pick up items (like the Axe)

* `Esc` - Pause / Mouse Unlock / Close Inventory

## 3. 2D PyCraft (mc.py)
A sandbox game built using pygame.

Features: Procedural terrain generation (dirt, grass, stone, ores, trees), block mining and placing, hotbar and inventory system, basic crafting mechanics (planks, sticks, tools), tool durability, gravity physics, and a day/night cycle.

**Controls:**

* `A, D` - Move left/right

* `Space` - Jump

* `Left Click` - Mine block

* `Right Click` - Place selected block

* `1-9` - Select hotbar slot

* `E` - Open inventory

* `F` - Change Mining Mode

## 4. Lego Base Defense (lego.py)
A humorous 3D base-building and collecting game created using the ursina engine.

Features: Economy and saving/loading system, custom AI bases, procedural environment generation with pyramids and lego-style trees, and interactive meme-based characters (Brainrots) that you can buy or steal.

**Controls:**

* `W, A, S, D` - Move

* `E` - Buy from Conveyor or Steal from Enemy Base

* `Q` - Drop carried item at your base

## 5. Time Survivor (timesurvivor.py)
A fast-paced 2D top-down arena survival game using Python's turtle module.

Features: Endless waves of enemies, directional shooting mechanics, AoE shockwave attacks, spawnable powerups (speed boost, damage boost), and a survival timer.

**Controls:**

* `W, A, S, D` - Move

* `K` - Shoot

* `E` - Shockwave attack

* `Space` - Pause

* `R` - Restart

## 6. Interactive Turtle Drawer (tmnt.py)
A console-driven interactive drawing program using the turtle graphics module.

**Features:** * Terminal-based inputs translate directly to visual drawing commands on the canvas.

**Controls:** Follow the on-screen terminal prompts to enter movement distances and turning angles (r for right, l for left). Type restart to clear...
