# Python Mini-Games Collection

Welcome to this repository containing a collection of fun, interactive 2D and 3D games and simulations built using Python! Each script is a standalone project using ***AI*** utilizing different libraries such as `pygame`, `ursina`, and the built-in `turtle` module.


## ⚙️ Requirements & Installation

To run these games, you will need **Python 3.x** installed on your system. You will also need to install the required external libraries. You can install them via pip:

```bash
pip install pygame ursina
```
### ***Pls delete*** `savegame.json` ***cuz that's technically my data***

## 🎮 Included Projects

### 1. 3D Adventure Dungeon (`aidea.py`)
A multi-phase 3D action-survival game built with the `ursina` engine. Progress through different dimensions, talk to NPCs, and defeat bosses.
* **Features:** Multiple levels (Plains, Safe Zone, Final Arena etc.), interactive NPCs, an unlockable companions, melee and ranged combat, powers, health UI, and a functioning Save/Load system.
* **Controls:** * `W, A, S, D` - Move
  * `Space` - Jump
  * `Left Click` - Sword Attack
  * `Right Click` - Shoot Arrow (requires Bow)
  * `E` - Throw Shockwave Grenade
  * `F` - Interact with NPCs
  * `8` - Save Game
  * `9` - Load Game
  * `0` - Pause

### 2. 2D PyCraft (`mc.py`)
A 2D Minecraft-style sandbox game built using `pygame`.
* **Features:** Procedural terrain generation (dirt, grass, stone, ores, trees), block mining and placing, hotbar and inventory system, basic crafting mechanics (planks, sticks, tools), tool durability, gravity physics, and a day/night cycle.
* **Controls:**
  * `A, D` - Move left/right
  * `Space` - Jump
  * `Left Click` - Mine block
  * `Right Click` - Place selected block
  * `1-9` - Select hotbar slot
  * `E` - Open inventory
  * `F` - Change Mining Mode

### 3. Time Survivor (`timesurvivor.py`)
A fast-paced 2D top-down arena survival game using Python's `turtle` module.
* **Features:** Endless waves of enemies, directional shooting mechanics, AoE shockwave attacks, spawnable powerups (speed boost, damage boost), and a survival timer.
* **Controls:**
  * `W, A, S, D` - Move
  * `K` - Shoot
  * `E` - Shockwave attack
  * `Space` - Pause
  * `R` - Restart

### 4. Interactive Turtle Drawer (`tmnt.py`)
A console-driven interactive drawing program using the `turtle` graphics module.
* **Features:** Terminal-based inputs translate directly to visual drawing commands on the canvas.
* **Controls:** Follow the on-screen terminal prompts to enter movement distances and turning angles (`r` for right, `l` for left). Type `restart` to clear the canvas or `exit` to quit the program.

---
Regards,
*mdhPHoenixVBcodes* and *AI* (***Gemini 3.1 and Flash***)
