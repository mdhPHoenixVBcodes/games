import pygame
import random
import math
import json
import os

# --- Configuration & Specs ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
WORLD_WIDTH = 400
WORLD_PIXELS = WORLD_WIDTH * TILE_SIZE
WORLD_HEIGHT = 128 
GRAVITY = 0.5

# Colors (RGB)
COLOR_SKY_BLUE = (135, 206, 235)
COLOR_DIRT = (80, 50, 30)
COLOR_GRASS = (34, 139, 34)
COLOR_STONE = (160, 160, 175)
COLOR_COAL = (40, 40, 40)
COLOR_IRON = (219, 192, 171)
COLOR_OAK_BROWN = (101, 67, 33)
COLOR_BIRCH_WHITE = (220, 220, 220)
COLOR_PLANKS = (210, 180, 140)
COLOR_LEAVES_G = (34, 100, 34)
COLOR_LEAVES_B = (50, 120, 50)
COLOR_RED = (255, 0, 0)
COLOR_DARK_RED = (200, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 100, 100)
COLOR_BLACK = (0, 0, 0)

# Block Types
AIR = 0
GRASS_BLOCK = 1
DIRT_BLOCK = 2
STONE_BLOCK = 3
COAL_BLOCK = 4
IRON_BLOCK = 5
OAK_LOG = 6
OAK_LEAVES = 7
BIRCH_LOG = 8
BIRCH_LEAVES = 9
PLANKS = 10
STICK = 11
CRAFTING_TABLE = 12
FURNACE = 13
IRON_INGOT = 14
CHARCOAL = 15
COAL = 16
DOOR = 17
TRAPDOOR = 18
PRESSURE_PLATE = 19
BUTTON = 20
LEVER = 21
COBBLESTONE = 22
SMOOTH_STONE = 23
IRON_BLOCK_PROD = 24
IRON_DOOR = 25
IRON_TRAPDOOR = 26
IRON_PRESSURE_PLATE = 27
CHAIN = 28
W_STAIRS = 29
C_STAIRS = 30
W_SLAB = 31
C_SLAB = 32
SS_STAIRS = 33
SS_SLAB = 34
I_STAIRS = 35
I_SLAB = 36
TALL_GRASS = 37
SEEDS = 38
FARMLAND = 39
WHEAT_STG0 = 40
WHEAT_STG1 = 41
WHEAT_STG2 = 42
WHEAT_STG3 = 43
WHEAT_ITEM = 44
BREAD = 45
HAY_BALE = 46
CHEST = 47
RAW_BEEF = 48
STEAK = 49
FENCE = 50
FENCE_GATE = 51
FENCE_GATE_OPEN = 52
DOOR_OPEN = 53
ROTTEN_FLESH = 54
BONE = 55
TRAPDOOR_OPEN = 56
WOOL = 57
BED = 58
RAW_MUTTON = 59
COOKED_MUTTON = 60
SMOKER = 61
BLAST_FURNACE = 62
BUCKET = 63
MILK_BUCKET = 64
WATER = 65
BOAT = 66
LADDER = 67

# Tool IDs
W_PICK = 100; S_PICK = 101; I_PICK = 110
W_AXE = 102; S_AXE = 103; I_AXE = 111
W_SHOVEL = 104; S_SHOVEL = 105; I_SHOVEL = 112
W_SWORD = 106; S_SWORD = 107; I_SWORD = 113
W_HOE = 108; S_HOE = 109; I_HOE = 114

# Armor IDs
I_HELMET = 120; I_CHEST = 121; I_LEGS = 122; I_BOOTS = 123

BLOCK_HARDNESS = {
    GRASS_BLOCK: 0.6, DIRT_BLOCK: 0.5, STONE_BLOCK: 1.5, 
    COAL_BLOCK: 3.0, IRON_BLOCK: 3.0, OAK_LOG: 2.0, BIRCH_LOG: 2.0,
    OAK_LEAVES: 0.2, BIRCH_LEAVES: 0.2, PLANKS: 2.0, CRAFTING_TABLE: 2.5,
    FURNACE: 3.5, SMOKER: 3.5, BLAST_FURNACE: 3.5, COBBLESTONE: 2.0, SMOOTH_STONE: 2.0, IRON_BLOCK_PROD: 5.0,
    CHEST: 2.5, HAY_BALE: 0.5, FARMLAND: 0.6, FENCE: 2.0, FENCE_GATE: 2.0,
    DOOR: 3.0, TRAPDOOR: 3.0, W_STAIRS: 2.0, C_STAIRS: 2.0, SS_STAIRS: 2.0, I_STAIRS: 3.0,
    W_SLAB: 2.0, C_SLAB: 2.0, SS_SLAB: 2.0, I_SLAB: 3.0, LADDER: 0.4
}

BLOCK_NAMES = {
    GRASS_BLOCK: "Grass", DIRT_BLOCK: "Dirt", STONE_BLOCK: "Stone",
    COAL_BLOCK: "Coal Ore", IRON_BLOCK: "Iron Ore", OAK_LOG: "Oak Log",
    BIRCH_LOG: "Birch Log", OAK_LEAVES: "Oak Leaves", BIRCH_LEAVES: "Birch Leaves",
    PLANKS: "Planks", STICK: "Stick", CRAFTING_TABLE: "Crafting Table",
    W_PICK: "Wooden Pickaxe", S_PICK: "Stone Pickaxe",
    W_AXE: "Wooden Axe", S_AXE: "Stone Axe",
    W_SHOVEL: "Wooden Shovel", S_SHOVEL: "Stone Shovel",
    W_SWORD: "Wooden Sword", S_SWORD: "Stone Sword",
    W_HOE: "Wooden Hoe", S_HOE: "Stone Hoe",
    FURNACE: "Furnace", IRON_INGOT: "Iron Ingot", CHARCOAL: "Charcoal", COAL: "Coal",
    DOOR: "Wooden Door", TRAPDOOR: "Trapdoor", PRESSURE_PLATE: "Pressure Plate",
    BUTTON: "Button", LEVER: "Lever",
    COBBLESTONE: "Cobblestone", SMOOTH_STONE: "Smooth Stone",
    IRON_BLOCK_PROD: "Iron Block", IRON_DOOR: "Iron Door", 
    IRON_TRAPDOOR: "Iron Trapdoor", IRON_PRESSURE_PLATE: "Iron Pressure Plate",
    CHAIN: "Chain",
    W_STAIRS: "Wooden Stairs", C_STAIRS: "Cobblestone Stairs",
    W_SLAB: "Wooden Slab", C_SLAB: "Cobblestone Slab",
    SS_STAIRS: "Smooth Stone Stairs", SS_SLAB: "Smooth Stone Slab",
    I_STAIRS: "Iron Stairs", I_SLAB: "Iron Slab",
    TALL_GRASS: "Tall Grass", SEEDS: "Seeds",
    FARMLAND: "Farmland", WHEAT_ITEM: "Wheat",
    BREAD: "Bread", HAY_BALE: "Hay Bale",
    CHEST: "Chest",
    RAW_BEEF: "Raw Beef", STEAK: "Steak",
    ROTTEN_FLESH: "Rotten Flesh", BONE: "Bone",
    FENCE: "Fence", FENCE_GATE: "Fence Gate",
    FENCE_GATE_OPEN: "Open Fence Gate", DOOR_OPEN: "Open Door",
    TRAPDOOR_OPEN: "Open Trapdoor",
    WOOL: "Wool", BED: "Bed", RAW_MUTTON: "Raw Mutton", COOKED_MUTTON: "Cooked Mutton",
    SMOKER: "Smoker", BLAST_FURNACE: "Blast Furnace",
    BUCKET: "Bucket", MILK_BUCKET: "Milk Bucket",
    WATER: "Water", BOAT: "Boat",
    I_PICK: "Iron Pickaxe", I_AXE: "Iron Axe", I_SHOVEL: "Iron Shovel",
    I_SWORD: "Iron Sword", I_HOE: "Iron Hoe",
    I_HELMET: "Iron Helmet", I_CHEST: "Iron Chestplate",
    I_LEGS: "Iron Leggings", I_BOOTS: "Iron Boots",
    LADDER: "Ladder"
}

MAX_DURABILITY = {
    W_PICK: 60, W_AXE: 60, W_SHOVEL: 60, W_SWORD: 60, W_HOE: 60,
    S_PICK: 132, S_AXE: 132, S_SHOVEL: 132, S_SWORD: 132, S_HOE: 132,
    I_PICK: 250, I_AXE: 250, I_SHOVEL: 250, I_SWORD: 250, I_HOE: 250,
    I_HELMET: 165, I_CHEST: 240, I_LEGS: 225, I_BOOTS: 195
}

PLACEABLE_BLOCKS = {
    GRASS_BLOCK, DIRT_BLOCK, STONE_BLOCK, COAL_BLOCK, IRON_BLOCK,
    OAK_LOG, BIRCH_LOG, OAK_LEAVES, BIRCH_LEAVES, PLANKS,
    CRAFTING_TABLE, FURNACE, COBBLESTONE, SMOOTH_STONE,
    IRON_BLOCK_PROD, DOOR, TRAPDOOR, PRESSURE_PLATE, BUTTON,
    LEVER, CHAIN, W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS,
    W_SLAB, C_SLAB, SS_SLAB, I_SLAB, FARMLAND, HAY_BALE, CHEST,
    FENCE, FENCE_GATE, WOOL, BED, LADDER
}

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, 50, 24, (TILE_SIZE * 2) - 2) 
        self.vel_y = 0
        self.speed = 5
        self.jump_strength = -8.0 # Stronger jump for easier towering
        self.on_ground = False
        self.direction = 1 
        
        self.max_health = 20
        self.health = self.max_health
        self.highest_y = self.rect.y 
        self.invincible_until = pygame.time.get_ticks() + 5000 # 5s at startup
        self.last_action_time = 0 # Cooldown for building/breaking
        
        self.inventory = [None] * 36 # 0-8 Hotbar, 9-35 Main Inventory
        self.inventory[0] = {"type": DIRT_BLOCK, "count": 10}
        self.armor = [None] * 4 # 0: Helmet, 1: Chest, 2: Legs, 3: Boots
        self.selected_slot = 0
        
        # Crafting
        self.crafting_grid = [None] * 4 # 2x2
        self.crafting_output = None
        self.crafting_3x3 = [None] * 9 # 3x3
        self.output_3x3 = None
        
        self.held_item = None
        self.show_inventory = False
        self.show_3x3 = False
        self.active_furnace_pos = None
        self.active_chest_pos = None
        self.active_chest_is_large = False
        
        # Mining State
        self.breaking_block = None # (x, y)
        self.breaking_progress = 0.0
        
        # Stats
        self.hunger = 20
        self.max_hunger = 20
        self.hunger_timer = 0
        self.regen_timer = 0

    def update(self, world):
        # Hunger Logic
        self.hunger_timer += 1
        if self.hunger_timer >= 600: # Every 10 seconds lose some hunger
            self.hunger = max(0, self.hunger - 0.2)
            self.hunger_timer = 0
            
        # Health Regen / Starvation
        self.regen_timer += 1
        if self.regen_timer >= 240: # Every 4 seconds
            if self.hunger >= 18 and self.health < self.max_health:
                self.health = min(self.max_health, self.health + 1)
            elif self.hunger <= 0:
                self.take_damage(1)
            self.regen_timer = 0

        if self.show_inventory: return # Freeze movement
        
        if self.on_ground:
            self.highest_y = self.rect.y
        else:
            self.highest_y = min(self.highest_y, self.rect.y)

        dx = 0
        keys = pygame.key.get_pressed()
        
        # Physics Check: Water
        in_water = False
        px, py = self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE
        if (px, py) in world.data and world.data[(px, py)] == WATER:
            in_water = True

        # Boat Speed Boost
        below_x, below_y = self.rect.centerx // TILE_SIZE, (self.rect.bottom + 2) // TILE_SIZE
        speed_mult = 1.0
        if (below_x, below_y) in world.data and world.data[(below_x, below_y)] == BOAT:
            speed_mult = 2.5 # Fast boat travel
        
        if keys[pygame.K_a]:
            dx -= self.speed * (0.5 if in_water else speed_mult)
            self.direction = -1
        if keys[pygame.K_d]:
            dx += self.speed * (0.5 if in_water else speed_mult)
            self.direction = 1
        
        if keys[pygame.K_SPACE]:
            if in_water:
                self.vel_y = -3 # Swim up
            elif self.on_ground:
                self.vel_y = self.jump_strength

        self.vel_y += GRAVITY * (0.3 if in_water else 1.0)
        
        # Ladder climbing
        on_ladder = False
        lx = self.rect.centerx // TILE_SIZE
        # Check top, middle, and bottom of player for ladder contact
        for ly in [self.rect.top // TILE_SIZE, self.rect.centery // TILE_SIZE, (self.rect.bottom - 1) // TILE_SIZE]:
            if (lx, ly) in world.data and world.data[(lx, ly)] == LADDER:
                on_ladder = True
                break
        
        if on_ladder:
            self.vel_y = 0 # Default to staying still
            if keys[pygame.K_w] or keys[pygame.K_SPACE]:
                self.vel_y = -4 # Climb up
            elif keys[pygame.K_s]:
                self.vel_y = 4 # Climb down
            # Don't let gravity pull us down if we're on a ladder
            dy = self.vel_y
        else:
            if self.vel_y > 15: self.vel_y = 15
            dy = self.vel_y

        self.on_ground = False
        
        # X Movement with Infinite Wrap
        self.rect.x += dx
        self.rect.x %= WORLD_PIXELS # Seamless math wrap
        self.handle_collisions(world, dx, 0)
        
        # Y Movement
        self.rect.y += dy
        self.handle_collisions(world, 0, dy)

        # Bottom Border
        if self.rect.bottom > WORLD_HEIGHT * TILE_SIZE:
            self.rect.bottom = WORLD_HEIGHT * TILE_SIZE
            if not self.on_ground: self.calculate_fall_damage()
            self.on_ground = True
            self.vel_y = 0

        if self.health <= 0:
            self.respawn()

    def handle_collisions(self, world, dx, dy):
        for block_rect in world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block_rect):
                if dx > 0: self.rect.right = block_rect.left
                if dx < 0: self.rect.left = block_rect.right
                if dy > 0:
                    self.rect.bottom = block_rect.top
                    self.vel_y = 0
                    if not self.on_ground: self.calculate_fall_damage()
                    self.on_ground = True
                if dy < 0:
                    self.rect.top = block_rect.bottom
                    self.vel_y = 0

    def calculate_fall_damage(self):
        if pygame.time.get_ticks() < self.invincible_until:
            return
        fall_distance = (self.rect.y - self.highest_y) / TILE_SIZE
        if fall_distance >= 4:
            self.health -= int(fall_distance - 3)
            self.health = max(0, self.health)
        self.highest_y = self.rect.y

    def respawn(self):
        self.rect.x, self.rect.y = 100, 50
        self.vel_y = 0
        self.health = 20
        self.max_health = 20
        self.hunger = 20
        self.max_hunger = 20
        self.hunger_timer = 0
        self.regen_timer = 0
        self.invincible_until = pygame.time.get_ticks() + 5000

    def take_damage(self, amount):
        if pygame.time.get_ticks() < self.invincible_until: return
        # Armor reduction
        reduction = 0
        for part in self.armor:
            if part: reduction += 0.15 # 15% per piece
        final_dmg = amount * (1.0 - reduction)
        self.health -= final_dmg
        self.invincible_until = pygame.time.get_ticks() + 500 # Brief i-frames
        if self.health < 0: self.health = 0

class World:
    def __init__(self):
        self.data = {}
        self.furnace_data = {} # (tx, ty) -> {"input": slot, "fuel": slot, "output": slot, "cook_time": float, "fuel_time": float}
        self.chest_data = {} # (tx, ty) -> [slots]
        self.mobs = []
        self.dropped_items = [] # (DroppedItem instances)
        self.time = 0 # 0 corresponds to 6:00 AM (Sunrise)
        self.generate_world()

    def generate_world(self):
        # Surface & Lakes
        for x in range(WORLD_WIDTH):
            # Base height with some variation
            h = int(12 + math.sin(x * 0.15) * 4 + math.cos(x * 0.05) * 2)
            
            # Lake Generation
            is_lake = False
            if 30 < x < 50 or 75 < x < 90:
                h += 3 # Dip for water
                is_lake = True

            for y in range(WORLD_HEIGHT):
                if y > h: 
                    self.data[(x, y)] = STONE_BLOCK if y > h+4 else DIRT_BLOCK
                elif y == h: 
                    self.data[(x, y)] = GRASS_BLOCK
                    if random.random() < 0.2: # 20% chance for tall grass
                        self.data[(x, y - 1)] = TALL_GRASS
                elif is_lake and y > h - 4:
                    self.data[(x, y)] = WATER
                
        # Generate Caves (Random Walks)
        for _ in range(15):
            cx = random.randint(0, WORLD_WIDTH - 1)
            cy = random.randint(20, WORLD_HEIGHT - 20)
            for _ in range(random.randint(20, 50)):
                # Carve a small sphere
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if (cx+dx, cy+dy) in self.data:
                            del self.data[(cx+dx, cy+dy)]
                cx = (cx + random.randint(-1, 1)) % WORLD_WIDTH
                cy = min(WORLD_HEIGHT - 5, max(10, cy + random.randint(-1, 1)))

        # Generate Ravines (Long vertical slits)
        for _ in range(3):
            rx = random.randint(10, WORLD_WIDTH - 10)
            ry = random.randint(20, 50)
            r_len = random.randint(15, 25)
            for i in range(r_len):
                curr_y = ry + i
                curr_x = rx + int(math.sin(i * 0.5) * 2)
                for dx in range(-2, 3):
                    if (curr_x + dx, curr_y) in self.data:
                        del self.data[(curr_x + dx, curr_y)]
                
        # Generate Veins (Coal and Iron) - Scaled for world size
        # Surface/Mid Coal
        for _ in range(WORLD_WIDTH // 3): 
            vx = random.randint(0, WORLD_WIDTH - 1)
            vy = random.randint(15, 60)
            for _ in range(random.randint(6, 12)):
                if (vx, vy) in self.data and self.data[(vx, vy)] == STONE_BLOCK:
                    self.data[(vx, vy)] = COAL_BLOCK
                vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(15, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))
        
        # Deep Coal
        for _ in range(WORLD_WIDTH // 5):
            vx = random.randint(0, WORLD_WIDTH - 1)
            vy = random.randint(60, WORLD_HEIGHT - 10)
            for _ in range(random.randint(8, 14)):
                if (vx, vy) in self.data and self.data[(vx, vy)] == STONE_BLOCK:
                    self.data[(vx, vy)] = COAL_BLOCK
                vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(60, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))
                
        # Iron Veins
        for _ in range(WORLD_WIDTH // 6):
            vx = random.randint(0, WORLD_WIDTH - 1)
            vy = random.randint(40, WORLD_HEIGHT - 10)
            for _ in range(random.randint(5, 9)):
                if (vx, vy) in self.data and self.data[(vx, vy)] == STONE_BLOCK:
                    self.data[(vx, vy)] = IRON_BLOCK
                vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(40, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))

        # Generate Trees
        for x in range(WORLD_WIDTH):
            h = 0
            while (x, h) not in self.data or self.data[(x, h)] != GRASS_BLOCK:
                h += 1
                if h >= WORLD_HEIGHT: break
            if h < WORLD_HEIGHT and random.random() < 0.15: # 15% chance for a tree
                tree_type = "oak" if random.random() < 0.7 else "birch"
                t_h = random.randint(3, 5)
                log_b = OAK_LOG if tree_type == "oak" else BIRCH_LOG
                leaf_b = OAK_LEAVES if tree_type == "oak" else BIRCH_LEAVES
                # Trunk
                for th in range(1, t_h + 1):
                    self.data[(x, h - th)] = log_b
                # Leaves
                for lx in range(-2, 3):
                    for ly in range(-2, 1):
                        tx, ty = (x + lx) % WORLD_WIDTH, (h - t_h + ly)
                        if (tx, ty) not in self.data:
                            self.data[(tx, ty)] = leaf_b

        # Generate Caves (Worms)
        for _ in range(15): # 15 cave systems
            vx, vy = random.randint(0, WORLD_WIDTH-1), random.randint(50, 90)
            for _ in range(30): # Worm length
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        ctx, cty = (vx + dx) % WORLD_WIDTH, max(0, min(WORLD_HEIGHT-1, vy + dy))
                        if (ctx, cty) in self.data and self.data[(ctx, cty)] == STONE_BLOCK:
                            del self.data[(ctx, cty)]
                vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(40, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))
        
        # Generate Ravines
        for _ in range(2):
            rx = random.randint(0, WORLD_WIDTH-1)
            ry = random.randint(40, 60)
            r_len = random.randint(20, 40)
            r_width = random.randint(2, 4)
            for i in range(r_len):
                cur_x = (rx + i) % WORLD_WIDTH
                cur_y = ry + int(math.sin(i * 0.2) * 5)
                for dx in range(-r_width, r_width+1):
                    for dy in range(-4, 5):
                        ctx, cty = (cur_x + dx) % WORLD_WIDTH, max(0, min(WORLD_HEIGHT-1, cur_y + dy))
                        if (ctx, cty) in self.data:
                            del self.data[(ctx, cty)]

    def get_surrounding_blocks(self, player_rect):
        blocks = []
        p_x = int(player_rect.x // TILE_SIZE)
        p_y = int(player_rect.y // TILE_SIZE)
        for x_off in range(-2, 3):
            for y_off in range(-2, 4):
                tx, ty = (p_x + x_off) % WORLD_WIDTH, p_y + y_off
                if (tx, ty) in self.data:
                    b_type = self.data[(tx, ty)]
                    if b_type == TALL_GRASS or WHEAT_STG0 <= b_type <= WHEAT_STG3 or b_type in (FENCE_GATE_OPEN, DOOR_OPEN, TRAPDOOR_OPEN, WATER, LADDER): continue # Non-solid
                    bx, by = (p_x + x_off) * TILE_SIZE, ty * TILE_SIZE
                    if b_type == FARMLAND:
                        blocks.append(pygame.Rect(bx, by + 4, TILE_SIZE, TILE_SIZE - 4))
                    elif b_type in (W_SLAB, C_SLAB, SS_SLAB, I_SLAB):
                        blocks.append(pygame.Rect(bx, by + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                    elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS):
                        # Simple 2-part hitbox for stairs
                        blocks.append(pygame.Rect(bx, by + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2)) # Base
                        blocks.append(pygame.Rect(bx, by, TILE_SIZE//2, TILE_SIZE//2)) # Top Step
                    else:
                        blocks.append(pygame.Rect(bx, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        return blocks

    def draw(self, surface, scroll_x, scroll_y):
        # Convert float to integer to stop the screen from shaking/jittering!
        scroll_x, scroll_y = int(scroll_x), int(scroll_y)
        
        # Draw Sky based on time
        t = self.time % 24000
        if 1000 <= t < 11000: # Full Day
            bg_color = (135, 206, 235)
        elif 11000 <= t < 13000 or 23000 <= t <= 24000 or 0 <= t < 1000: # Sunrise/Sunset
            bg_color = (80, 60, 100)
        else: # Night
            bg_color = (15, 15, 30)
        surface.fill(bg_color)
        
        # Celestial Bodies
        # Offset angle by pi/2 so t=0 is Sunrise (horizon)
        angle = (t / 24000.0) * math.pi * 2 + math.pi / 2
        sun_x = SCREEN_WIDTH//2 + math.sin(angle) * 300
        sun_y = SCREEN_HEIGHT//2 + math.cos(angle) * 300
        moon_x = SCREEN_WIDTH//2 + math.sin(angle + math.pi) * 300
        moon_y = SCREEN_HEIGHT//2 + math.cos(angle + math.pi) * 300
        
        pygame.draw.circle(surface, (255, 255, 0), (int(sun_x), int(sun_y)), 30) # Sun
        pygame.draw.circle(surface, (220, 220, 255), (int(moon_x), int(moon_y)), 25) # Moon
        
        # Draw the world 3 times to cover the infinite wrap smoothly
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            for (x, y), b_type in self.data.items():
                draw_x = x * TILE_SIZE - scroll_x + offset
                draw_y = y * TILE_SIZE - scroll_y
                # Only draw blocks that are visible on screen
                if -TILE_SIZE < draw_x < SCREEN_WIDTH and -TILE_SIZE < draw_y < SCREEN_HEIGHT:
                    if b_type in (COAL_BLOCK, IRON_BLOCK):
                        pygame.draw.rect(surface, COLOR_STONE, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        ore_color = COLOR_COAL if b_type == COAL_BLOCK else COLOR_IRON
                        # Chunky ore shapes
                        pygame.draw.rect(surface, ore_color, (draw_x + 4, draw_y + 6, 10, 8))
                        pygame.draw.rect(surface, ore_color, (draw_x + 16, draw_y + 18, 12, 10))
                        pygame.draw.rect(surface, ore_color, (draw_x + 22, draw_y + 4, 8, 8))
                    elif b_type == OAK_LOG:
                        pygame.draw.rect(surface, COLOR_OAK_BROWN, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                    elif b_type == BIRCH_LOG:
                        pygame.draw.rect(surface, COLOR_BIRCH_WHITE, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, COLOR_GRAY, (draw_x, draw_y + 8, 8, 3)) # Bark dash
                        pygame.draw.rect(surface, COLOR_GRAY, (draw_x + 20, draw_y + 18, 8, 3)) # Bark dash
                    elif b_type == PLANKS:
                        pygame.draw.rect(surface, COLOR_PLANKS, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, (150, 110, 60), (draw_x, draw_y, TILE_SIZE, TILE_SIZE), 1) # Board outline
                        pygame.draw.rect(surface, (150, 110, 60), (draw_x, draw_y + 16, TILE_SIZE, 1)) # Middle board line
                    elif b_type == CRAFTING_TABLE:
                        pygame.draw.rect(surface, (140, 100, 60), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, (80, 50, 30), (draw_x + 2, draw_y + 2, TILE_SIZE - 4, TILE_SIZE - 4), 2) # Top border
                        pygame.draw.rect(surface, (0, 0, 0), (draw_x + 6, draw_y + 6, 4, 4)) # Tool icon
                    elif b_type == FURNACE:
                        pygame.draw.rect(surface, (60, 60, 60), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, (30, 30, 30), (draw_x + 4, draw_y + 8, TILE_SIZE - 8, TILE_SIZE - 16)) # Front opening
                    elif b_type in (OAK_LEAVES, BIRCH_LEAVES):
                        color = COLOR_LEAVES_G if b_type == OAK_LEAVES else COLOR_LEAVES_B
                        pygame.draw.rect(surface, color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                    elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS):
                        color = COLOR_PLANKS if b_type == W_STAIRS else ((100, 100, 100) if b_type == C_STAIRS else ((180, 180, 190) if b_type == SS_STAIRS else (200, 200, 220)))
                        pygame.draw.rect(surface, color, (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                        pygame.draw.rect(surface, color, (draw_x, draw_y, TILE_SIZE//2, TILE_SIZE//2))
                        pygame.draw.rect(surface, (0,0,0), (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), 1)
                        pygame.draw.rect(surface, (0,0,0), (draw_x, draw_y, TILE_SIZE//2, TILE_SIZE//2), 1)
                    elif b_type in (W_SLAB, C_SLAB, SS_SLAB, I_SLAB):
                        color = COLOR_PLANKS if b_type == W_SLAB else ((100, 100, 100) if b_type == C_SLAB else ((180, 180, 190) if b_type == SS_SLAB else (200, 200, 220)))
                        pygame.draw.rect(surface, color, (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                        pygame.draw.rect(surface, (0,0,0), (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), 1)
                    elif b_type == TALL_GRASS:
                        # Draw blades
                        pygame.draw.line(surface, COLOR_GRASS, (draw_x + 8, draw_y + TILE_SIZE), (draw_x + 6, draw_y + 16), 2)
                        pygame.draw.line(surface, COLOR_GRASS, (draw_x + 16, draw_y + TILE_SIZE), (draw_x + 16, draw_y + 12), 2)
                        pygame.draw.line(surface, COLOR_GRASS, (draw_x + 24, draw_y + TILE_SIZE), (draw_x + 26, draw_y + 16), 2)
                    elif b_type == FARMLAND:
                        pygame.draw.rect(surface, (80, 50, 30), (draw_x, draw_y + 4, TILE_SIZE, TILE_SIZE - 4))
                        pygame.draw.rect(surface, (60, 40, 20), (draw_x, draw_y + 4, TILE_SIZE, 4)) # Tilled top
                    elif WHEAT_STG0 <= b_type <= WHEAT_STG3:
                        stage = b_type - WHEAT_STG0
                        color = (50, 200, 50) if stage < 3 else (220, 200, 50)
                        h = 8 + stage * 6
                        for x_off in [8, 16, 24]:
                            pygame.draw.line(surface, color, (draw_x + x_off, draw_y + TILE_SIZE), (draw_x + x_off, draw_y + TILE_SIZE - h), 2)
                    elif b_type == CHEST:
                        # Draw chest body
                        pygame.draw.rect(surface, (120, 80, 40), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 4))
                        
                        # Handle connections for visual double chests
                        left = self.data.get(((x - 1) % WORLD_WIDTH, y)) == CHEST
                        right = self.data.get(((x + 1) % WORLD_WIDTH, y)) == CHEST
                        
                        if left:
                            pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 4, 4, TILE_SIZE - 4)) # Connect left
                        if right:
                            pygame.draw.rect(surface, (120, 80, 40), (draw_x + TILE_SIZE - 4, draw_y + 4, 4, TILE_SIZE - 4)) # Connect right
                        
                        # Lock (only on the master/left chest or single chest)
                        if not left:
                            lock_x = draw_x + (TILE_SIZE if right else TILE_SIZE // 2) - 2
                            pygame.draw.rect(surface, (200, 160, 40), (lock_x, draw_y + 10, 4, 6))
                    elif b_type == HAY_BALE:
                        pygame.draw.rect(surface, (220, 200, 50), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, (150, 100, 50), (draw_x, draw_y + 8, TILE_SIZE, 3)) # Rope
                        pygame.draw.rect(surface, (150, 100, 50), (draw_x, draw_y + 22, TILE_SIZE, 3)) # Rope
                    elif b_type in (FENCE, FENCE_GATE, FENCE_GATE_OPEN):
                        pygame.draw.rect(surface, (120, 80, 40), (draw_x + 12, draw_y, 8, TILE_SIZE)) # Post
                        if b_type == FENCE_GATE:
                            pygame.draw.rect(surface, (140, 100, 50), (draw_x + 4, draw_y + 8, 24, 16))
                        elif b_type == FENCE_GATE_OPEN:
                            pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y, 4, TILE_SIZE))
                            pygame.draw.rect(surface, (120, 80, 40), (draw_x + 28, draw_y, 4, TILE_SIZE))
                        if b_type == FENCE:
                            left = self.data.get(((x-1)%WORLD_WIDTH, y))
                            if left and (left in (FENCE, FENCE_GATE, FENCE_GATE_OPEN) or left not in (TALL_GRASS, WHEAT_STG0, WHEAT_STG1, WHEAT_STG2, WHEAT_STG3)):
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 8, 12, 4))
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 20, 12, 4))
                            right = self.data.get(((x+1)%WORLD_WIDTH, y))
                            if right and (right in (FENCE, FENCE_GATE, FENCE_GATE_OPEN) or right not in (TALL_GRASS, WHEAT_STG0, WHEAT_STG1, WHEAT_STG2, WHEAT_STG3)):
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + 20, draw_y + 8, 12, 4))
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + 20, draw_y + 20, 12, 4))
                    elif b_type == DOOR:
                        pygame.draw.rect(surface, (100, 60, 20), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(surface, (80, 40, 10), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)
                        pygame.draw.circle(surface, (200, 150, 50), (draw_x + 24, draw_y + 16), 3) # Knob
                    elif b_type == DOOR_OPEN:
                        pygame.draw.rect(surface, (100, 60, 20), (draw_x, draw_y, 6, TILE_SIZE))
                    elif b_type == TRAPDOOR:
                        pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 4, TILE_SIZE, 8))
                    elif b_type == TRAPDOOR_OPEN:
                        pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y, 8, TILE_SIZE))
                    elif b_type == LADDER:
                        # Draw ladder rungs
                        color = (120, 80, 40)
                        pygame.draw.rect(surface, color, (draw_x + 4, draw_y, 4, TILE_SIZE)) # Left rail
                        pygame.draw.rect(surface, color, (draw_x + TILE_SIZE - 8, draw_y, 4, TILE_SIZE)) # Right rail
                        for i in range(4):
                            ry = draw_y + 4 + i * 8
                            pygame.draw.rect(surface, color, (draw_x + 4, ry, TILE_SIZE - 8, 3)) # Rungs
                        continue
                    elif b_type == WATER:
                        # Draw semi-transparent water
                        water_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                        water_surf.fill((0, 100, 255, 150))
                        surface.blit(water_surf, (draw_x, draw_y))
                        continue
                    elif b_type == BOAT:
                        # Draw boat in world
                        pygame.draw.polygon(surface, (100, 70, 40), [(draw_x, draw_y + 20), (draw_x + TILE_SIZE, draw_y + 20), (draw_x + TILE_SIZE + 4, draw_y + 10), (draw_x - 4, draw_y + 10)])
                        pygame.draw.rect(surface, (120, 80, 40), (draw_x + 4, draw_y + 18, TILE_SIZE - 8, 4))
                        continue
                    else:
                        block_colors = {
                            GRASS_BLOCK: COLOR_GRASS, DIRT_BLOCK: COLOR_DIRT, STONE_BLOCK: COLOR_STONE,
                            COAL_BLOCK: (30, 30, 30), IRON_BLOCK: (160, 160, 160),
                            IRON_BLOCK_PROD: (220, 220, 220), COBBLESTONE: (120, 120, 120),
                            SMOOTH_STONE: (180, 180, 180), OAK_LOG: (100, 70, 40),
                            BIRCH_LOG: (220, 220, 220), PLANKS: COLOR_PLANKS,
                            BOAT: (100, 70, 40)
                        }
                        color = block_colors.get(b_type, (255, 0, 255)) # Magenta for unknown
                        pygame.draw.rect(surface, color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        if b_type in (COAL_BLOCK, IRON_BLOCK): # Add speckles for ores
                            speckle_c = (0,0,0) if b_type == COAL_BLOCK else (140, 100, 60)
                            # Deterministic speckles based on block pos
                            seed = (x * 7 + y * 13) % 100
                            for i in range(4):
                                sx = 4 + ((seed + i * 21) % 20)
                                sy = 4 + ((seed + i * 37) % 20)
                                pygame.draw.rect(surface, speckle_c, (draw_x + sx, draw_y + sy, 4, 4))


    def draw_cracks(self, surface, scroll_x, scroll_y, pos, progress):
        if progress <= 0: return
        tx, ty = pos
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx, dy = tx * TILE_SIZE - int(scroll_x) + offset, ty * TILE_SIZE - int(scroll_y)
            if dx < -TILE_SIZE or dx > SCREEN_WIDTH: continue
            
            num_lines = int(progress * 10)
            for i in range(num_lines):
                o = i * 3
                pygame.draw.line(surface, (0,0,0), (dx + o, dy), (dx + TILE_SIZE - o, dy + TILE_SIZE), 1)
                pygame.draw.line(surface, (0,0,0), (dx, dy + o), (dx + TILE_SIZE, dy + TILE_SIZE - o), 1)

class DroppedItem:
    def __init__(self, x, y, item_type, count=1):
        self.rect = pygame.Rect(x, y, 16, 16)
        self.item_type = item_type
        self.count = count
        self.vel_y = -3
        self.vel_x = random.uniform(-1, 1)
        self.spawn_time = pygame.time.get_ticks()

    def update(self, world):
        # Gravity
        self.vel_y += 0.2
        if self.vel_y > 8: self.vel_y = 8
        
        # Movement
        self.rect.x = (self.rect.x + self.vel_x) % WORLD_PIXELS
        self.rect.y += self.vel_y
        
        # Collision (simple)
        bx, by = int(self.rect.centerx // TILE_SIZE) % WORLD_WIDTH, int(self.rect.bottom // TILE_SIZE)
        if (bx, by) in world.data and world.data[(bx, by)] not in (AIR, WATER, TALL_GRASS, LADDER):
            self.rect.bottom = by * TILE_SIZE
            self.vel_y = 0
            self.vel_x *= 0.9

    def draw(self, surface, scroll_x, scroll_y, font):
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx = self.rect.x - int(scroll_x) + offset
            if dx < -50 or dx > SCREEN_WIDTH + 50: continue
            dy = self.rect.y - int(scroll_y)
            # Hover effect
            float_y = dy + math.sin(pygame.time.get_ticks() * 0.005) * 3
            draw_block_icon(surface, self.item_type, dx, float_y, 16, font)

class Mob:
    def __init__(self, x, y, m_type="zombie"):
        self.m_type = m_type
        # Cows are a bit wider/shorter
        if m_type == "cow" or m_type == "sheep":
            self.rect = pygame.Rect(x, y, 32, 28)
            self.speed = 0.5
            self.health = 8 if m_type == "sheep" else 10
        else:
            self.rect = pygame.Rect(x, y, 24, TILE_SIZE * 2 - 2)
            self.speed = 2
            self.health = 20
            
        self.vel_x = 0
        self.vel_y = 0
        self.last_hit = 0
        self.on_ground = False
        self.wander_timer = 0
        self.hurt_timer = 0
        self.highest_y = self.rect.y
        self.is_burning = False

    def update(self, world, player):
        if self.hurt_timer > 0: self.hurt_timer -= 1
        # AI Logic
        if self.m_type == "zombie":
            # Chase player
            dist_x = player.rect.x - self.rect.x
            if abs(dist_x) < 400: # Detection range
                self.vel_x = self.speed if dist_x > 0 else -self.speed
            else:
                self.vel_x = 0
        else: # Cow/Sheep Wander / Follow
            slot = player.inventory[player.selected_slot] if not player.show_inventory else player.held_item
            lure_item = WHEAT_ITEM if self.m_type == "cow" else SEEDS
            if slot and slot["type"] == lure_item:
                # Follow Player
                dist_x = player.rect.x - self.rect.x
                if abs(dist_x) < 250: # Lure range
                    self.vel_x = self.speed if dist_x > 0 else -self.speed
                else:
                    self.vel_x = 0
            else:
                # Normal Wander
                self.wander_timer -= 1
                if self.wander_timer <= 0:
                    self.wander_timer = random.randint(60, 180)
                    self.vel_x = random.choice([-self.speed, 0, self.speed])
        
        if self.on_ground:
            self.highest_y = self.rect.y
        else:
            self.highest_y = min(self.highest_y, self.rect.y)
            
        # Gravity
        self.vel_y += 0.5
        
        # Move X
        self.rect.x = (self.rect.x + self.vel_x) % WORLD_PIXELS
        # Collision
        hits = world.get_surrounding_blocks(self.rect)
        for block in hits:
            if self.rect.colliderect(block):
                if self.vel_x > 0: self.rect.right = block.left
                elif self.vel_x < 0: self.rect.left = block.right
                # Jump if blocked and on ground
                if self.on_ground:
                    self.vel_y = -7
                    self.on_ground = False
        
        # Move Y
        self.rect.y += self.vel_y
        hits = world.get_surrounding_blocks(self.rect)
        self.on_ground = False
        for block in hits:
            if self.rect.colliderect(block):
                if self.vel_y > 0:
                    self.rect.bottom = block.top
                    # Fall damage
                    fall_dist = (self.rect.y - self.highest_y) / TILE_SIZE
                    if fall_dist >= 4:
                        self.health -= int(fall_dist - 3)
                        self.hurt_timer = 10
                    self.vel_y = 0
                    self.on_ground = True
                    self.highest_y = self.rect.y
                elif self.vel_y < 0:
                    self.rect.top = block.bottom
                    self.vel_y = 0

        # Bottom Border
        if self.rect.bottom > WORLD_HEIGHT * TILE_SIZE:
            self.rect.bottom = WORLD_HEIGHT * TILE_SIZE
            if not self.on_ground:
                self.health -= 2
                self.hurt_timer = 10
            self.on_ground = True
            self.vel_y = 0
            self.highest_y = self.rect.y

        # Zombies specific behaviors
        if self.m_type == "zombie":
            # Sunlight burn
            t = world.time % 24000
            if 1000 < t < 11000: # Day
                # Check for roof (Sky exposure) - wider check for better house protection
                tx, ty = int(self.rect.centerx // TILE_SIZE) % WORLD_WIDTH, int(self.rect.top // TILE_SIZE)
                is_under_roof = False
                for dx in [-1, 0, 1]:
                    check_x = (tx + dx) % WORLD_WIDTH
                    for check_y in range(ty):
                        if (check_x, check_y) in world.data:
                            is_under_roof = True
                            break
                    if is_under_roof: break
                
                if not is_under_roof:
                    self.health -= 0.1
                    if self.hurt_timer <= 0: self.hurt_timer = 10 # Flash red
                    self.is_burning = True
                else:
                    self.is_burning = False
            else:
                self.is_burning = False
            # Hit player (with wrap handling)
            dist_x = abs(self.rect.centerx - player.rect.centerx)
            if dist_x > WORLD_PIXELS / 2:
                dist_x = WORLD_PIXELS - dist_x
            
            dist_y = abs(self.rect.centery - player.rect.centery)
            
            if dist_x < (self.rect.width + player.rect.width)/2 and dist_y < (self.rect.height + player.rect.height)/2:
                if pygame.time.get_ticks() - self.last_hit > 1000:
                    player.take_damage(2)
                    self.last_hit = pygame.time.get_ticks()

    def draw(self, surface, scroll_x, scroll_y):
        # Draw in all 3 wrapped positions to ensure seamless appearance
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx = self.rect.x - int(scroll_x) + offset
            if dx < -200 or dx > SCREEN_WIDTH + 200: continue
            dy = self.rect.y - int(scroll_y)
            
            # Determine color (red if hurt)
            if self.hurt_timer > 0:
                color_z = (255, 100, 100); color_c = (255, 150, 150)
                color_head = (255, 200, 200); color_spot = (200, 50, 50)
            else:
                color_z = (0, 100, 0); color_c = (255, 255, 255)
                color_head = (180, 140, 100); color_spot = (30, 30, 30)

            # Determine colors
            is_hurt = self.hurt_timer > 0
            if self.m_type == "zombie":
                color = (255, 100, 100) if is_hurt else (0, 100, 0)
                pygame.draw.rect(surface, color, (dx, dy, self.rect.width, self.rect.height))
                pygame.draw.rect(surface, (0, 0, 0), (dx + 4, dy + 8, 4, 4))
                pygame.draw.rect(surface, (0, 0, 0), (dx + 16, dy + 8, 4, 4))
                if getattr(self, 'is_burning', False):
                    # Draw fire
                    for _ in range(3):
                        fx, fy = dx + random.randint(0, 16), dy + random.randint(0, 32)
                        pygame.draw.rect(surface, (255, 100, 0), (fx, fy, 8, 8))
                        pygame.draw.rect(surface, (255, 200, 0), (fx + 2, fy + 2, 4, 4))
            elif self.m_type == "cow":
                color = (255, 100, 100) if is_hurt else (255, 255, 255)
                pygame.draw.rect(surface, color, (dx, dy, self.rect.width, self.rect.height))
                pygame.draw.rect(surface, (30, 30, 30), (dx + 4, dy + 4, 8, 8))
                pygame.draw.rect(surface, (30, 30, 30), (dx + 20, dy + 12, 6, 6))
                hx = dx + (self.rect.width if self.vel_x >= 0 else -8)
                h_color = (255, 150, 150) if is_hurt else (180, 140, 100)
                pygame.draw.rect(surface, h_color, (hx, dy + 4, 8, 12))
            elif self.m_type == "sheep":
                # Sheep draw (Woolly body)
                color = (255, 100, 100) if is_hurt else (240, 240, 240)
                pygame.draw.rect(surface, color, (dx, dy, self.rect.width, self.rect.height), 0, 8)
                pygame.draw.rect(surface, (200, 200, 200), (dx, dy, self.rect.width, self.rect.height), 2, 8)
                hx = dx + (self.rect.width if self.vel_x >= 0 else -6)
                h_color = (255, 100, 100) if is_hurt else (50, 50, 50)
                pygame.draw.rect(surface, h_color, (hx, dy + 6, 8, 10)) # Face

def draw_block_icon(screen, b_type, x, y, size, font):
    if b_type == STICK:
        pygame.draw.line(screen, (101, 67, 33), (x + size//4, y + size - 4), (x + size - 4, y + size//4), 3)
    elif b_type in (COAL_BLOCK, IRON_BLOCK):
        pygame.draw.rect(screen, COLOR_STONE, (x, y, size, size))
        ore_c = COLOR_COAL if b_type == COAL_BLOCK else COLOR_IRON
        pygame.draw.rect(screen, ore_c, (x + 3, y + 5, 8, 6))
        pygame.draw.rect(screen, ore_c, (x + 12, y + 14, 10, 8))
    elif b_type == OAK_LOG:
        pygame.draw.rect(screen, COLOR_OAK_BROWN, (x, y, size, size))
    elif b_type == BIRCH_LOG:
        pygame.draw.rect(screen, COLOR_BIRCH_WHITE, (x, y, size, size))
        pygame.draw.rect(screen, COLOR_GRAY, (x, y + 10, 8, 3))
    elif b_type == PLANKS:
        pygame.draw.rect(screen, COLOR_PLANKS, (x, y, size, size))
        pygame.draw.rect(screen, (150, 110, 60), (x, y, size, size), 1)
    elif b_type == CRAFTING_TABLE:
        pygame.draw.rect(screen, (140, 100, 60), (x, y, size, size))
        pygame.draw.rect(screen, (80, 50, 30), (x+2, y+2, size-4, size-4), 2)
    elif b_type == FURNACE:
        pygame.draw.rect(screen, (60, 60, 60), (x, y, size, size))
        pygame.draw.rect(screen, (30, 30, 30), (x + 4, y + 8, size - 8, size - 16))
    elif b_type == COBBLESTONE:
        pygame.draw.rect(screen, (100, 100, 100), (x, y, size, size))
        for _ in range(5):
            pygame.draw.rect(screen, (70, 70, 70), (x + random.randint(0, size-8), y + random.randint(0, size-8), 8, 4))
    elif b_type == SMOOTH_STONE:
        pygame.draw.rect(screen, (180, 180, 190), (x, y, size, size))
        pygame.draw.rect(screen, (220, 220, 230), (x+2, y+2, size-4, size-4), 1)
    elif b_type == CHARCOAL:
        pygame.draw.circle(screen, (30, 30, 30), (x+size//2, y+size//2), size//3)
    elif b_type == COAL:
        pygame.draw.circle(screen, (20, 20, 20), (x+size//2, y+size//2), size//3)
        pygame.draw.circle(screen, (50, 50, 50), (x+size//3, y+size//3), 4) # Shine
    elif b_type == DOOR:
        pygame.draw.rect(screen, (120, 80, 40), (x + size//4, y, size//2, size))
        pygame.draw.rect(screen, (0, 0, 0), (x + size//2 + 4, y + size//2, 4, 4)) # Handle
    elif b_type == TRAPDOOR:
        pygame.draw.rect(screen, (120, 80, 40), (x, y + size//4, size, size//2))
    elif b_type == FENCE:
        pygame.draw.rect(screen, (120, 80, 40), (x + size//2 - 2, y + 4, 4, size - 8))
        pygame.draw.rect(screen, (120, 80, 40), (x + 4, y + size//4, size - 8, 4))
        pygame.draw.rect(screen, (120, 80, 40), (x + 4, y + size*3//4 - 4, size - 8, 4))
    elif b_type == FENCE_GATE:
        pygame.draw.rect(screen, (120, 80, 40), (x + size//2 - 6, y + 4, 12, size - 8))
        pygame.draw.rect(screen, (120, 80, 40), (x + 4, y + size//4, size - 8, 4))
        pygame.draw.rect(screen, (120, 80, 40), (x + 4, y + size*3//4 - 4, size - 8, 4))
    elif b_type == PRESSURE_PLATE:
        pygame.draw.rect(screen, (120, 80, 40), (x, y + size*3//4, size, size//4))
    elif b_type == BUTTON:
        pygame.draw.rect(screen, (120, 80, 40), (x + size//3, y + size//3, size//3, size//3))
    elif b_type == LEVER:
        pygame.draw.rect(screen, (128, 128, 128), (x + size//4, y + size*3//4, size//2, size//4)) # Base
        pygame.draw.line(screen, (101, 67, 33), (x + size//2, y + size*3//4), (x + size//2 + 4, y + size//4), 3) # Stick
    elif b_type in (OAK_LEAVES, BIRCH_LEAVES):
        l_c = COLOR_LEAVES_G if b_type == OAK_LEAVES else COLOR_LEAVES_B
        pygame.draw.rect(screen, l_c, (x, y, size, size))
    elif b_type >= 100: # Tools
        mat_c = (150, 110, 60) if b_type in (W_PICK, W_AXE, W_SHOVEL, W_SWORD, W_HOE) else (128, 128, 128)
        if b_type in (I_PICK, I_AXE, I_SHOVEL, I_SWORD, I_HOE, I_HELMET, I_CHEST, I_LEGS, I_BOOTS): mat_c = (200, 200, 220)
        
        if b_type in (W_PICK, S_PICK, I_PICK):
            pygame.draw.rect(screen, mat_c, (x, y, size, size//4)) # Top
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//4, 4, size*3//4)) # Stick
        elif b_type in (W_AXE, S_AXE, I_AXE):
            pygame.draw.rect(screen, mat_c, (x, y, size//2, size//2)) # Head
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y, 4, size)) # Stick
        elif b_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL):
            pygame.draw.rect(screen, mat_c, (x + size//4, y, size//2, size//3)) # Head
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//3, 4, size*2//3)) # Stick
        elif b_type in (W_SWORD, S_SWORD, I_SWORD):
            pygame.draw.rect(screen, mat_c, (x + size//2 - 4, y, 8, size*2//3)) # Blade
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size*2//3, 4, size//3)) # Hilt
        elif b_type in (W_HOE, S_HOE, I_HOE):
            pygame.draw.rect(screen, mat_c, (x, y, size*3//4, size//4)) # Top
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//4, 4, size*3//4)) # Stick
        # Armor
        elif b_type == I_HELMET:
            pygame.draw.rect(screen, mat_c, (x+4, y+4, size-8, size-8))
            pygame.draw.rect(screen, (0,0,0), (x+8, y+16, 4, 4)) # Eyes
            pygame.draw.rect(screen, (0,0,0), (x+20, y+16, 4, 4))
        elif b_type == I_CHEST:
            pygame.draw.rect(screen, mat_c, (x+2, y+8, size-4, size-10))
            pygame.draw.rect(screen, mat_c, (x+size//4, y+2, size//2, 8)) # Neck
        elif b_type == I_LEGS:
            pygame.draw.rect(screen, mat_c, (x+4, y+4, size-8, size-12))
            pygame.draw.rect(screen, mat_c, (x+4, y+size-12, size//3, 8)) # Left leg
            pygame.draw.rect(screen, mat_c, (x+size-12, y+size-12, size//3, 8)) # Right leg
        elif b_type == I_BOOTS:
            pygame.draw.rect(screen, mat_c, (x+4, y+size-16, size//3, 12))
            pygame.draw.rect(screen, mat_c, (x+size-12, y+size-16, size//3, 12))
    elif b_type == IRON_BLOCK_PROD:
        pygame.draw.rect(screen, (200, 200, 220), (x, y, size, size))
        pygame.draw.rect(screen, (150, 150, 170), (x, y, size, size), 1)
    elif b_type == IRON_DOOR:
        pygame.draw.rect(screen, (200, 200, 220), (x+4, y, size-8, size))
        pygame.draw.rect(screen, (0,0,0), (x + size//2 + 2, y + size//2, 2, 6)) # Handle
    elif b_type == IRON_TRAPDOOR:
        pygame.draw.rect(screen, (200, 200, 220), (x, y+size//4, size, size//2))
        pygame.draw.rect(screen, (150, 150, 170), (x, y+size//4, size, size//2), 1)
    elif b_type == IRON_PRESSURE_PLATE:
        pygame.draw.rect(screen, (200, 200, 220), (x, y+size*3//4, size, size//4))
    elif b_type == CHAIN:
        pygame.draw.rect(screen, (100, 100, 110), (x + size//2 - 2, y, 4, size))
        pygame.draw.rect(screen, (100, 100, 110), (x + size//2 - 6, y + size//4, 12, 4))
        pygame.draw.rect(screen, (100, 100, 110), (x + size//2 - 6, y + size*3//4, 12, 4))
    elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS, W_SLAB, C_SLAB, SS_SLAB, I_SLAB):
        color = COLOR_PLANKS if b_type in (W_STAIRS, W_SLAB) else ((100, 100, 100) if b_type in (C_STAIRS, C_SLAB) else ((180, 180, 190) if b_type in (SS_STAIRS, SS_SLAB) else (200, 200, 220)))
        if b_type in (W_SLAB, C_SLAB, SS_SLAB, I_SLAB):
            pygame.draw.rect(screen, color, (x, y + size//2, size, size//2))
        else: # Stairs
            pygame.draw.rect(screen, color, (x, y + size//2, size, size//2))
            pygame.draw.rect(screen, color, (x, y, size//2, size//2))
    elif b_type == TALL_GRASS:
        pygame.draw.line(screen, COLOR_GRASS, (x + size//4, y + size), (x + size//4 - 2, y + size//2), 2)
        pygame.draw.line(screen, COLOR_GRASS, (x + size//2, y + size), (x + size//2, y + size//3), 2)
        pygame.draw.line(screen, COLOR_GRASS, (x + 3*size//4, y + size), (x + 3*size//4 + 2, y + size//2), 2)
    elif b_type == SEEDS:
        for _ in range(3):
            pygame.draw.circle(screen, (200, 180, 100), (x + random.randint(8, 24), y + random.randint(8, 24)), 3)
    elif b_type == FARMLAND:
        pygame.draw.rect(screen, (80, 50, 30), (x, y + 4, size, size - 4))
        pygame.draw.rect(screen, (60, 40, 20), (x, y + 4, size, 4))
    elif b_type == WHEAT_ITEM:
        pygame.draw.ellipse(screen, (220, 200, 50), (x + 8, y + 4, 16, 24))
        pygame.draw.line(screen, (150, 130, 30), (x + 16, y + 4), (x + 16, y + 28), 2)
    elif b_type == BREAD:
        pygame.draw.ellipse(screen, (150, 100, 60), (x + 4, y + 10, size - 8, size - 20))
        pygame.draw.line(screen, (200, 150, 100), (x + 10, y + 15), (x + 16, y + 15), 2) # Slashes
        pygame.draw.line(screen, (200, 150, 100), (x + 20, y + 15), (x + 26, y + 15), 2)
    elif b_type == HAY_BALE:
        pygame.draw.rect(screen, (220, 200, 50), (x, y, size, size))
        pygame.draw.rect(screen, (150, 100, 50), (x, y + 8, size, 3))
        pygame.draw.rect(screen, (150, 100, 50), (x, y + 22, size, 3))
    elif b_type == WOOL:
        pygame.draw.rect(screen, (240, 240, 240), (x, y, size, size), 0, 4)
        pygame.draw.rect(screen, (200, 200, 200), (x, y, size, size), 1, 4)
    elif b_type == BED:
        pygame.draw.rect(screen, COLOR_RED, (x, y + size//2, size, size//2)) # Base
        pygame.draw.rect(screen, COLOR_WHITE, (x + 2, y + size//2 + 2, size - 4, size//4)) # Pillow
    elif b_type == RAW_MUTTON:
        pygame.draw.ellipse(screen, (255, 150, 150), (x + 4, y + 8, size - 8, size - 16))
    elif b_type == COOKED_MUTTON:
        pygame.draw.ellipse(screen, (120, 70, 30), (x + 4, y + 8, size - 8, size - 16))
    elif b_type == RAW_BEEF:
        pygame.draw.ellipse(screen, (255, 100, 100), (x + 4, y + 8, size - 8, size - 16))
        pygame.draw.ellipse(screen, (255, 200, 200), (x + 8, y + 12, 8, 4)) # Fat/Grain
    elif b_type == STEAK:
        pygame.draw.ellipse(screen, (100, 50, 20), (x + 4, y + 8, size - 8, size - 16))
        pygame.draw.ellipse(screen, (150, 100, 60), (x + 8, y + 12, 8, 4))
    elif b_type == ROTTEN_FLESH:
        pygame.draw.ellipse(screen, (100, 150, 50), (x + 4, y + 8, size - 8, size - 16)) # Green meat
        pygame.draw.ellipse(screen, (70, 100, 30), (x + 8, y + 12, 8, 4)) # Dark spots
    elif b_type == BONE:
        pygame.draw.line(screen, (240, 240, 240), (x+8, y+size-8), (x+size-8, y+8), 6) # Shaft
        pygame.draw.circle(screen, (240, 240, 240), (x+8, y+size-8), 5) # Knuckle 1
        pygame.draw.circle(screen, (240, 240, 240), (x+size-8, y+8), 5) # Knuckle 2
    elif b_type == IRON_INGOT:
        pygame.draw.rect(screen, (190, 190, 200), (x+4, y+8, size-12, size-16), 0, 4) # Ingot body
        pygame.draw.rect(screen, (150, 150, 160), (x+4, y+8, size-12, size-16), 1, 4) # Border
    elif b_type == BUCKET:
        pygame.draw.polygon(screen, (150, 150, 160), [(x+8, y+8), (x+size-8, y+8), (x+size-12, y+size-8), (x+12, y+size-8)])
        pygame.draw.rect(screen, (120, 120, 130), (x+12, y+8, size-24, 2)) # Rim
    elif b_type == MILK_BUCKET:
        pygame.draw.polygon(screen, (150, 150, 160), [(x+8, y+8), (x+size-8, y+8), (x+size-12, y+size-8), (x+12, y+size-8)])
        pygame.draw.rect(screen, (255, 255, 255), (x+10, y+10, size-20, 4)) # Milk surface
    elif b_type == WATER:
        pygame.draw.rect(screen, (0, 100, 255), (x, y, size, size), 0, 4)
    elif b_type == BOAT:
        pygame.draw.polygon(screen, (100, 70, 40), [(x+4, y+size-8), (x+size-4, y+size-8), (x+size, y+size//2), (x, y+size//2)])
        pygame.draw.line(screen, (80, 50, 30), (x+size//2, y+size//2), (x+size//2, y+size-4), 2) # Oar indicator
    elif b_type == LADDER:
        color = (120, 80, 40)
        pygame.draw.rect(screen, color, (x + 4, y, 4, size))
        pygame.draw.rect(screen, color, (x + size - 8, y, 4, size))
        for i in range(4):
            ry = y + 4 + i * (size // 4)
            pygame.draw.rect(screen, color, (x + 4, ry, size - 8, 2))
    else:
        color = {GRASS_BLOCK: COLOR_GRASS, DIRT_BLOCK: COLOR_DIRT, STONE_BLOCK: COLOR_STONE}.get(b_type, COLOR_WHITE)
        pygame.draw.rect(screen, color, (x, y, size, size))

def update_crafting(player):
    grid = [slot["type"] if slot else None for slot in player.crafting_grid]
    res = None
    
    # 1 Log -> 4 Planks
    logs = [OAK_LOG, BIRCH_LOG]
    for log in logs:
        if grid.count(log) == 1 and grid.count(None) == 3:
            res = {"type": PLANKS, "count": 4}
    
    # 2 Planks (vertical) -> 4 Sticks
    if grid[0] == PLANKS and grid[2] == PLANKS and grid[1] is None and grid[3] is None:
        res = {"type": STICK, "count": 4}
    if grid[1] == PLANKS and grid[3] == PLANKS and grid[0] is None and grid[2] is None:
        res = {"type": STICK, "count": 4}
        
    # 4 Planks -> 1 Crafting Table
    if all(g == PLANKS for g in grid):
        res = {"type": CRAFTING_TABLE, "count": 1}
        
    # 1 Iron Block -> 9 Iron Ingots
    if grid.count(IRON_BLOCK_PROD) == 1 and grid.count(None) == 3:
        res = {"type": IRON_INGOT, "count": 9}
        
    player.crafting_output = res
    
    # 3x3 Crafting
    grid3 = [slot["type"] if slot else None for slot in player.crafting_3x3]
    res3 = None
    
    # 1 Log -> 4 Planks (Shapeless in 3x3)
    for log in logs:
        if grid3.count(log) == 1 and grid3.count(None) == 8:
            res3 = {"type": PLANKS, "count": 4}
    
    # 2 Planks (vertical) -> 4 Sticks (Anywhere in 3x3)
    for col in range(3):
        for row in range(2):
            if grid3[row*3 + col] == PLANKS and grid3[(row+1)*3 + col] == PLANKS and grid3.count(PLANKS) == 2 and grid3.count(None) == 7:
                res3 = {"type": STICK, "count": 4}

    # 4 Planks -> Crafting Table (2x2 square anywhere in 3x3)
    for col in range(2):
        for row in range(2):
            if grid3[row*3 + col] == PLANKS and grid3[row*3 + col+1] == PLANKS and \
               grid3[(row+1)*3 + col] == PLANKS and grid3[(row+1)*3 + col+1] == PLANKS and \
               grid3.count(PLANKS) == 4 and grid3.count(None) == 5:
                res3 = {"type": CRAFTING_TABLE, "count": 1}

    # 1 Iron Block -> 9 Iron Ingots
    if grid3.count(IRON_BLOCK_PROD) == 1 and grid3.count(None) == 8:
        res3 = {"type": IRON_INGOT, "count": 9}

    def match(pattern, result):
        nonlocal res3
        if res3 is not None: return # Already matched
        if grid3 == pattern: 
            res3 = result
            return
        # Horizontal mirror
        mirrored = []
        for row in range(3):
            mirrored.extend(pattern[row*3 : row*3+3][::-1])
        if grid3 == mirrored:
            res3 = result

    # Materials
    W = PLANKS; S = COBBLESTONE; T = STICK; N = None; I = IRON_INGOT; ST = STICK
    # Pickaxes
    match([W,W,W, N,T,N, N,T,N], {"type": W_PICK, "count": 1, "durability": 60})
    match([S,S,S, N,T,N, N,T,N], {"type": S_PICK, "count": 1, "durability": 132})
    match([I,I,I, N,T,N, N,T,N], {"type": I_PICK, "count": 1, "durability": 250})
    # Axes
    match([W,W,N, W,T,N, N,T,N], {"type": W_AXE, "count": 1, "durability": 60})
    match([S,S,N, S,T,N, N,T,N], {"type": S_AXE, "count": 1, "durability": 132})
    match([I,I,N, I,T,N, N,T,N], {"type": I_AXE, "count": 1, "durability": 250})
    # Shovels
    match([N,W,N, N,T,N, N,T,N], {"type": W_SHOVEL, "count": 1, "durability": 60})
    match([N,S,N, N,T,N, N,T,N], {"type": S_SHOVEL, "count": 1, "durability": 132})
    match([N,I,N, N,T,N, N,T,N], {"type": I_SHOVEL, "count": 1, "durability": 250})
    # Swords
    match([N,W,N, N,W,N, N,T,N], {"type": W_SWORD, "count": 1, "durability": 60})
    match([N,S,N, N,S,N, N,T,N], {"type": S_SWORD, "count": 1, "durability": 132})
    match([N,I,N, N,I,N, N,T,N], {"type": I_SWORD, "count": 1, "durability": 250})
    # Hoes
    match([W,W,N, N,T,N, N,T,N], {"type": W_HOE, "count": 1, "durability": 60})
    match([S,S,N, N,T,N, N,T,N], {"type": S_HOE, "count": 1, "durability": 132})
    match([N,S,S, N,T,N, N,T,N], {"type": S_HOE, "count": 1, "durability": 132})
    match([I,I,N, N,T,N, N,T,N], {"type": I_HOE, "count": 1, "durability": 250})
    match([N,I,I, N,T,N, N,T,N], {"type": I_HOE, "count": 1, "durability": 250})
    # Armor
    match([I,I,I, I,N,I, N,N,N], {"type": I_HELMET, "count": 1, "durability": 165})
    match([I,N,I, I,I,I, I,I,I], {"type": I_CHEST, "count": 1, "durability": 240})
    match([I,I,I, I,N,I, I,N,I], {"type": I_LEGS, "count": 1, "durability": 225})
    match([I,N,I, I,N,I, N,N,N], {"type": I_BOOTS, "count": 1, "durability": 195})
    # Furnace
    match([S,S,S, S,N,S, S,S,S], {"type": FURNACE, "count": 1})
    # Iron Products
    match([I,I,I, I,I,I, I,I,I], {"type": IRON_BLOCK_PROD, "count": 1})
    match([I,I,N, I,I,N, I,I,N], {"type": IRON_DOOR, "count": 3})
    match([I,I,I, I,I,I, N,N,N], {"type": IRON_TRAPDOOR, "count": 2})
    match([I,I,N, N,N,N, N,N,N], {"type": IRON_PRESSURE_PLATE, "count": 1})
    match([N,I,N, N,I,N, N,I,N], {"type": CHAIN, "count": 1})
    SS = SMOOTH_STONE; IB = IRON_BLOCK_PROD
    # Stairs
    match([W,N,N, W,W,N, W,W,W], {"type": W_STAIRS, "count": 4})
    match([N,N,W, N,W,W, W,W,W], {"type": W_STAIRS, "count": 4})
    match([S,N,N, S,S,N, S,S,S], {"type": C_STAIRS, "count": 4})
    match([N,N,S, N,S,S, S,S,S], {"type": C_STAIRS, "count": 4})
    match([SS,N,N, SS,SS,N, SS,SS,SS], {"type": SS_STAIRS, "count": 4})
    match([N,N,SS, N,SS,SS, SS,SS,SS], {"type": SS_STAIRS, "count": 4})
    match([IB,N,N, IB,IB,N, IB,IB,IB], {"type": I_STAIRS, "count": 4})
    match([N,N,IB, N,IB,IB, IB,IB,IB], {"type": I_STAIRS, "count": 4})
    # Slabs
    match([N,N,N, N,N,N, W,W,W], {"type": W_SLAB, "count": 6})
    match([N,N,N, N,N,N, S,S,S], {"type": C_SLAB, "count": 6})
    match([N,N,N, N,N,N, SS,SS,SS], {"type": SS_SLAB, "count": 6})
    match([N,N,N, N,N,N, IB,IB,IB], {"type": I_SLAB, "count": 6})
    # Farming
    WH = WHEAT_ITEM
    match([N,N,N, WH,WH,WH, N,N,N], {"type": BREAD, "count": 1})
    match([WH,WH,WH, WH,WH,WH, WH,WH,WH], {"type": HAY_BALE, "count": 1})
    # Chest
    match([W,W,W, W,N,W, W,W,W], {"type": CHEST, "count": 1})
    # Wooden Products
    match([W,W,N, W,W,N, W,W,N], {"type": DOOR, "count": 3})
    match([W,W,W, W,W,W, N,N,N], {"type": TRAPDOOR, "count": 2})
    match([W,W,N, N,N,N, N,N,N], {"type": PRESSURE_PLATE, "count": 1})
    match([W,N,N, N,N,N, N,N,N], {"type": BUTTON, "count": 1})
    match([N,N,N, ST,ST,ST, ST,ST,ST], {"type": FENCE, "count": 2})
    match([N,N,N, ST,W,ST, ST,W,ST], {"type": FENCE_GATE, "count": 1})
    match([T,N,N, S,N,N, N,N,N], {"type": LEVER, "count": 1})
    
    # Bed (3 Wool over 3 Planks)
    match([N,N,N, WOOL,WOOL,WOOL, W,W,W], {"type": BED, "count": 1})
    
    # Smoker (4 Logs around a Furnace)
    L = OAK_LOG
    F = FURNACE
    match([N,L,N, L,F,L, N,L,N], {"type": SMOKER, "count": 1})
    L = BIRCH_LOG
    match([N,L,N, L,F,L, N,L,N], {"type": SMOKER, "count": 1})

    # Blast Furnace (5 Iron + 1 Furnace + 3 Smooth Stone)
    I = IRON_INGOT; S = SMOOTH_STONE
    match([I,I,I, I,F,I, S,S,S], {"type": BLAST_FURNACE, "count": 1})
    
    # Bucket (3 Iron in V shape)
    match([N,N,N, I,N,I, N,I,N], {"type": BUCKET, "count": 1})
    
    # Boat (5 Planks in U shape)
    match([N,N,N, W,N,W, W,W,W], {"type": BOAT, "count": 1})
    
    # Ladder (Sticks in H shape)
    match([T,N,T, T,T,T, T,N,T], {"type": LADDER, "count": 3})
    
    player.output_3x3 = res3


def handle_inventory_click(player, mx, my, button, world=None):
    inv_x, inv_y = SCREEN_WIDTH // 2 - 200, 360
    clicked_slot = None
    slot_list = None
    slot_idx = -1

    # Check Inventory & Hotbar
    for i in range(36):
        if i < 9: sx, sy = inv_x + i * 44, inv_y + 150
        else: sx, sy = inv_x + ((i-9)%9) * 44, inv_y + ((i-9)//9) * 44
        if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
            slot_list, slot_idx = player.inventory, i

    # Check Furnace Slots
    if player.active_furnace_pos:
        f_data = world.furnace_data[player.active_furnace_pos]
        fx, fy = inv_x + 250, inv_y - 180
        # Input
        if fx <= mx <= fx + 40 and fy <= my <= fy + 40:
            slot_list, slot_idx = f_data, "input"
        # Fuel
        if fx <= mx <= fx + 40 and fy + 88 <= my <= fy + 128:
            slot_list, slot_idx = f_data, "fuel"
        
        if slot_list == f_data: # Found a furnace slot
            pass # Continue to common logic
        else:
            # Output (Special handling for output since it's read-only for placement)
            if fx + 100 <= mx <= fx + 144 and fy + 44 <= my <= fy + 88:
                if f_data["output"]:
                    if player.held_item is None:
                        player.held_item = f_data["output"]
                        f_data["output"] = None
                    elif player.held_item["type"] == f_data["output"]["type"] and player.held_item["count"] + f_data["output"]["count"] <= 80:
                        player.held_item["count"] += f_data["output"]["count"]
                        f_data["output"] = None
                return

    # Check Chest Slots
    if player.active_chest_pos:
        tx, ty = player.active_chest_pos
        master_pos = (tx, ty)
        if (tx-1, ty) in world.chest_data: master_pos = (tx-1, ty)
        
        c_slots = world.chest_data.get(master_pos, [])
        cx, cy = inv_x, 40
        for i in range(len(c_slots)):
            row, col = i // 9, i % 9
            sx, sy = cx + col * 44, cy + row * 44
            if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                slot_list, slot_idx = c_slots, i
                break

    # Check Crafting
    if not player.active_furnace_pos and not player.active_chest_pos:
        if not player.show_3x3:
            craft_x, craft_y = inv_x + 250, inv_y - 180
            for i in range(4):
                sx, sy = craft_x + (i % 2) * 44, craft_y + (i // 2) * 44
                if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                    slot_list, slot_idx = player.crafting_grid, i
            # Output (2x2)
            out_sx, out_sy = craft_x + 120, craft_y + 22
            if out_sx <= mx <= out_sx + 44 and out_sy <= my <= out_sy + 44:
                if player.crafting_output:
                    if player.held_item is None:
                        player.held_item = player.crafting_output
                        player.crafting_output = None
                        for i in range(4):
                            if player.crafting_grid[i]:
                                player.crafting_grid[i]["count"] -= 1
                                if player.crafting_grid[i]["count"] <= 0: player.crafting_grid[i] = None
                        return
                    elif player.held_item["type"] == player.crafting_output["type"] and player.held_item["count"] + player.crafting_output["count"] <= 80:
                        player.held_item["count"] += player.crafting_output["count"]
                        player.crafting_output = None
                        for i in range(4):
                            if player.crafting_grid[i]:
                                player.crafting_grid[i]["count"] -= 1
                                if player.crafting_grid[i]["count"] <= 0: player.crafting_grid[i] = None
                        return
        else:
            craft_x, craft_y = inv_x + 210, inv_y - 220
            for i in range(9):
                sx, sy = craft_x + (i % 3) * 44, craft_y + (i // 3) * 44
                if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                    slot_list, slot_idx = player.crafting_3x3, i
            # Output (3x3)
            out_sx, out_sy = craft_x + 150, craft_y + 44
            if out_sx <= mx <= out_sx + 44 and out_sy <= my <= out_sy + 44:
                if player.output_3x3:
                    if player.held_item is None:
                        player.held_item = player.output_3x3
                        player.output_3x3 = None
                        for i in range(9):
                            if player.crafting_3x3[i]:
                                player.crafting_3x3[i]["count"] -= 1
                                if player.crafting_3x3[i]["count"] <= 0: player.crafting_3x3[i] = None
                        return
                    elif player.held_item["type"] == player.output_3x3["type"] and player.held_item["count"] + player.output_3x3["count"] <= 80:
                        player.held_item["count"] += player.output_3x3["count"]
                        player.output_3x3 = None
                        for i in range(9):
                            if player.crafting_3x3[i]:
                                player.crafting_3x3[i]["count"] -= 1
                                if player.crafting_3x3[i]["count"] <= 0: player.crafting_3x3[i] = None
                        return

    # Check Armor Slots
    ax, ay = inv_x - 50, inv_y
    for i in range(4):
        sx, sy = ax, ay + i * 44
        if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
            # Check if held item is valid armor for this slot
            valid = False
            if player.held_item is None: valid = True
            else:
                t = player.held_item["type"]
                if i == 0 and t == I_HELMET: valid = True
                if i == 1 and t == I_CHEST: valid = True
                if i == 2 and t == I_LEGS: valid = True
                if i == 3 and t == I_BOOTS: valid = True
            
            if valid:
                player.armor[i], player.held_item = player.held_item, player.armor[i]
            return

    if slot_list is not None:
        slot = slot_list[slot_idx]
        if button == 1: # Left Click: Swap or merge
            if player.held_item is None:
                player.held_item = slot
                slot_list[slot_idx] = None
            else:
                if slot and slot["type"] == player.held_item["type"]:
                    transfer = min(player.held_item["count"], 80 - slot["count"])
                    slot["count"] += transfer
                    player.held_item["count"] -= transfer
                    if player.held_item["count"] <= 0: player.held_item = None
                else:
                    slot_list[slot_idx], player.held_item = player.held_item, slot
        elif button == 3: # Right Click: Split or drop one
            if player.held_item is None:
                if slot:
                    take = (slot["count"] + 1) // 2
                    player.held_item = {"type": slot["type"], "count": take}
                    slot["count"] -= take
                    if slot["count"] <= 0: slot_list[slot_idx] = None
            else:
                if slot is None:
                    slot_list[slot_idx] = {"type": player.held_item["type"], "count": 1}
                    player.held_item["count"] -= 1
                elif slot["type"] == player.held_item["type"] and slot["count"] < 80:
                    slot["count"] += 1
                    player.held_item["count"] -= 1
                if player.held_item["count"] <= 0: player.held_item = None
    elif player.held_item is not None and button == 1:
        # Clicked outside with item -> Drop it
        drop = DroppedItem(player.rect.centerx, player.rect.centery, player.held_item["type"], player.held_item["count"])
        drop.vel_x = player.direction * 4
        drop.vel_y = -3
        world.dropped_items.append(drop)
        player.held_item = None

def update_furnaces(world):
    for pos, data in world.furnace_data.items():
        if data["input"] is None and data["fuel_time"] <= 0: continue
        
        # Check if can smelt
        can_smelt = False
        result_type = None
        if data["input"]:
            i_type = data["input"]["type"]
            if i_type == COBBLESTONE: result_type = STONE_BLOCK
            elif i_type == IRON_BLOCK: result_type = IRON_INGOT
            elif i_type == RAW_BEEF: result_type = STEAK
            elif i_type == RAW_MUTTON: result_type = COOKED_MUTTON
            elif i_type in (OAK_LOG, BIRCH_LOG): result_type = CHARCOAL
            
            if result_type:
                can_smelt = True
                b_at_pos = world.data.get(pos)
                # Filtering
                if b_at_pos == SMOKER and i_type not in (RAW_BEEF, RAW_MUTTON): can_smelt = False
                if b_at_pos == BLAST_FURNACE and i_type not in (IRON_BLOCK, COBBLESTONE): can_smelt = False
                
                if data["output"] and (data["output"]["type"] != result_type or data["output"]["count"] >= 80):
                    can_smelt = False
        
        if can_smelt and data["fuel_time"] <= 0 and data["fuel"]:
            # Consume fuel
            f_type = data["fuel"]["type"]
            fuel_values = {
                COAL_BLOCK: 720, COAL: 80, CHARCOAL: 80, 
                OAK_LOG: 15, BIRCH_LOG: 15, PLANKS: 15, STICK: 5,
                CRAFTING_TABLE: 15, DOOR: 15, TRAPDOOR: 15, 
                PRESSURE_PLATE: 15, BUTTON: 5, W_STAIRS: 15, W_SLAB: 7.5, 
                CHEST: 15, W_PICK: 10, W_AXE: 10, W_SHOVEL: 10, W_SWORD: 10, W_HOE: 10,
                FENCE: 15, FENCE_GATE: 15
            }
            if f_type in fuel_values:
                data["fuel_time"] = fuel_values[f_type]
                data["fuel"]["count"] -= 1
                if data["fuel"]["count"] <= 0: data["fuel"] = None
        
        # Smelting
        if can_smelt and data["fuel_time"] > 0:
            speed = 1.0
            b_at_pos = world.data.get(pos)
            if b_at_pos in (SMOKER, BLAST_FURNACE): speed = 2.0
            
            data["cook_time"] += (1.0/60.0) * speed
            if data["cook_time"] >= 10.0: # 10 seconds per item (standard)
                data["cook_time"] = 0
                data["input"]["count"] -= 1
                if data["input"]["count"] <= 0: data["input"] = None
                if data["output"]: data["output"]["count"] += 1
                else: data["output"] = {"type": result_type, "count": 1}
        
        if data["fuel_time"] > 0:
            data["fuel_time"] -= 1.0/60.0
            if data["fuel_time"] < 0: data["fuel_time"] = 0

def save_game(world, player):
    save_data = {
        "world_data": {f"{k[0]},{k[1]}": v for k, v in world.data.items()},
        "chest_data": {f"{k[0]},{k[1]}": v for k, v in world.chest_data.items()},
        "furnace_data": {f"{k[0]},{k[1]}": v for k, v in world.furnace_data.items()},
        "time": world.time,
        "player": {
            "x": player.rect.x, "y": player.rect.y,
            "health": player.health, "hunger": player.hunger,
            "h_timer": player.hunger_timer, "r_timer": player.regen_timer,
            "inventory": player.inventory, "armor": player.armor
        },
        "mobs": [{"x": m.rect.x, "y": m.rect.y, "type": m.m_type, "hp": m.health} for m in world.mobs]
    }
    with open("savegame.json", "w") as f:
        json.dump(save_data, f)
    return True

def load_game(world, player):
    if not os.path.exists("savegame.json"): return
    try:
        with open("savegame.json", "r") as f:
            sd = json.load(f)
            # Restore World
            world.data = {tuple(map(int, k.split(','))): v for k, v in sd["world_data"].items()}
            world.chest_data = {tuple(map(int, k.split(','))): v for k, v in sd["chest_data"].items()}
            world.furnace_data = {tuple(map(int, k.split(','))): v for k, v in sd["furnace_data"].items()}
            world.time = sd["time"]
            # Restore Player
            p_data = sd.get("player", {})
            player.rect.x = p_data.get("x", 100)
            player.rect.y = p_data.get("y", 50)
            player.health = p_data.get("health", 20)
            player.hunger = p_data.get("hunger", 20)
            player.hunger_timer = p_data.get("h_timer", 0)
            player.regen_timer = p_data.get("r_timer", 0)
            player.inventory = p_data.get("inventory", [None]*36)
            player.armor = p_data.get("armor", [None]*4)
            # Restore Mobs
            world.mobs = []
            for m_data in sd.get("mobs", []):
                m = Mob(m_data["x"], m_data["y"], m_data["type"])
                m.health = m_data["hp"]
                world.mobs.append(m)
    except Exception as e:
        print(f"Load error: {e}")

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    world, player = World(), Player()
    load_game(world, player)
    scroll_x, scroll_y = 0, player.rect.centery - SCREEN_HEIGHT // 2
    target_mode = 0
    auto_save_timer = 0
    save_msg_timer = 0

    running = True
    while running:
        screen.fill(COLOR_SKY_BLUE)
        
        # --- FIXED INFINITE CAMERA LOGIC ---
        target_scroll_x = player.rect.centerx - SCREEN_WIDTH // 2
        target_scroll_y = player.rect.centery - SCREEN_HEIGHT // 2
        
        # If the camera distance is huge (wrapped around map), snap the scroll_x to prevent the "whip" effect
        diff_x = target_scroll_x - scroll_x
        if diff_x > WORLD_PIXELS / 2:
            scroll_x += WORLD_PIXELS
        elif diff_x < -WORLD_PIXELS / 2:
            scroll_x -= WORLD_PIXELS
            
        scroll_x += (target_scroll_x - scroll_x) * 0.1
        scroll_y += (target_scroll_y - scroll_y) * 0.1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                save_game(world, player)
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f: target_mode = (target_mode + 1) % 5
                if event.key == pygame.K_q: 
                    if save_game(world, player):
                        save_msg_timer = 120
                    running = False
                if event.key == pygame.K_r: player.respawn()
                if event.key == pygame.K_e: 
                    player.show_inventory = not player.show_inventory
                    if not player.show_inventory: 
                        player.show_3x3 = False
                        player.active_furnace_pos = None
                        player.active_chest_pos = None
                
                if event.key == pygame.K_ESCAPE:
                    if player.show_inventory:
                        player.show_inventory = False
                        player.show_3x3 = False
                        player.active_furnace_pos = None
                        player.active_chest_pos = None
                    else:
                        save_game(world, player)
                        running = False
                
                if not player.show_inventory:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                        player.selected_slot = event.key - pygame.K_1
                    if event.key == pygame.K_z:
                        slot = player.inventory[player.selected_slot]
                        if slot:
                            drop = DroppedItem(player.rect.centerx, player.rect.centery, slot["type"])
                            drop.vel_x = player.direction * 4
                            drop.vel_y = -3
                            world.dropped_items.append(drop)
                            slot["count"] -= 1
                            if slot["count"] <= 0:
                                player.inventory[player.selected_slot] = None
            
            if player.show_inventory:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    handle_inventory_click(player, mx, my, event.button, world)
                    update_crafting(player)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_z:
                    if player.held_item:
                        # Drop 1 from held item
                        drop = DroppedItem(player.rect.centerx, player.rect.centery, player.held_item["type"], 1)
                        drop.vel_x = player.direction * 4
                        drop.vel_y = -3
                        world.dropped_items.append(drop)
                        player.held_item["count"] -= 1
                        if player.held_item["count"] <= 0: player.held_item = None

        if player.show_inventory:
            # Skip world interaction
            valid_targets = []
            m_btns = [False, False, False]
        else:
            px, py = player.rect.centerx // TILE_SIZE, player.rect.centery // TILE_SIZE
            # Improved targeting logic for multiple targets
            if target_mode == 0: # Front (Mid)
                targets = [(px + player.direction, py)]
            elif target_mode == 1: # Front (Top)
                targets = [(px + player.direction, player.rect.top // TILE_SIZE)]
            elif target_mode == 2: # Down (Towering)
                targets = [(px, (player.rect.bottom + 28) // TILE_SIZE)]
            elif target_mode == 3: # Up
                targets = [(px, (player.rect.top - 20) // TILE_SIZE)]
            else: # Mining (Both Head and Leg)
                tx = px + player.direction
                targets = [(tx, player.rect.top // TILE_SIZE), (tx, py)]

            valid_targets = []
            for tx, ty in targets:
                tx %= WORLD_WIDTH
                ty = max(0, min(WORLD_HEIGHT - 1, ty)) # Keep blocks in world bounds
                valid_targets.append((tx, ty))

            m_btns = pygame.mouse.get_pressed()
        now = pygame.time.get_ticks()
        if m_btns[0] and valid_targets:
            # --- Mining Logic ---
            # Check if we are still breaking the same set of blocks
            if player.breaking_block not in valid_targets:
                # Find the first real block to target
                player.breaking_block = None
                player.breaking_progress = 0.0
                for tx, ty in valid_targets:
                    if (tx, ty) in world.data:
                        player.breaking_block = (tx, ty)
                        break
            
            if player.breaking_block:
                tx, ty = player.breaking_block
                b_type = world.data[(tx, ty)]
                
                # Tool Efficiency
                tool = player.inventory[player.selected_slot]
                t_type = tool["type"] if tool else None
                speed = 1.0
                if t_type in (W_PICK, S_PICK, I_PICK) and b_type in (STONE_BLOCK, COAL_BLOCK, IRON_BLOCK):
                    if t_type == W_PICK: speed = 3.0
                    elif t_type == S_PICK: speed = 6.0
                    else: speed = 10.0 # Iron
                elif t_type in (W_AXE, S_AXE, I_AXE) and b_type in (OAK_LOG, BIRCH_LOG, PLANKS, CRAFTING_TABLE, FURNACE, IRON_BLOCK_PROD):
                    if t_type == W_AXE: speed = 3.0
                    elif t_type == S_AXE: speed = 6.0
                    else: speed = 10.0 # Iron
                elif t_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL) and b_type in (GRASS_BLOCK, DIRT_BLOCK):
                    if t_type == W_SHOVEL: speed = 3.0
                    elif t_type == S_SHOVEL: speed = 6.0
                    else: speed = 10.0 # Iron
                
                hardness = BLOCK_HARDNESS.get(b_type, 1.0)
                if b_type == TALL_GRASS: hardness = 0.01 # Instant break
                player.breaking_progress += (1.0 / (60 * hardness)) * speed
                
                if player.breaking_progress >= 1.0:
                    player.last_action_time = now
                    # Break ALL valid targets that exist
                    for bx, by in valid_targets:
                        if (bx, by) in world.data:
                            drop_type = world.data[(bx, by)]
                            if drop_type == TALL_GRASS:
                                if random.random() < 0.15: drop_type = SEEDS
                                else: drop_type = None # Usually nothing drops
                            elif WHEAT_STG0 <= drop_type <= WHEAT_STG3:
                                if drop_type == WHEAT_STG3:
                                    # Drop Wheat and Seeds
                                    drop_type = WHEAT_ITEM
                                    # Extra seed logic (adding directly since drop_type only holds one)
                                    added_seeds = False
                                    for slot in player.inventory:
                                        if slot and slot["type"] == SEEDS and slot["count"] < 80:
                                            slot["count"] += random.randint(1, 2)
                                            added_seeds = True
                                            break
                                    if not added_seeds:
                                        for i in range(36):
                                            if player.inventory[i] is None:
                                                player.inventory[i] = {"type": SEEDS, "count": random.randint(1, 2)}
                                                added_seeds = True
                                                break
                                else:
                                    drop_type = SEEDS # Young wheat drops seeds
                            elif drop_type == GRASS_BLOCK: drop_type = DIRT_BLOCK
                            elif drop_type == COAL_BLOCK: drop_type = COAL
                            elif drop_type == STONE_BLOCK: drop_type = COBBLESTONE
                            
                            if (bx, by) in world.data: del world.data[(bx, by)]
                            
                            if drop_type and drop_type not in (OAK_LEAVES, BIRCH_LEAVES):
                                world.dropped_items.append(DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, drop_type))
                        
                        # Durability Loss
                        if tool and tool["type"] >= 100:
                            tool["durability"] -= 1
                            if tool["durability"] <= 0:
                                player.inventory[player.selected_slot] = None
                                
                    player.breaking_block = None
                    player.breaking_progress = 0.0

        elif m_btns[2] and now - player.last_action_time > 120:
            # --- Placing/Interacting Logic ---
            action_taken = False
            for tx, ty in valid_targets:
                slot = player.inventory[player.selected_slot]
                # Eating / Drinking
                if slot and slot["type"] in (BREAD, RAW_BEEF, STEAK, ROTTEN_FLESH, RAW_MUTTON, COOKED_MUTTON, MILK_BUCKET):
                    if slot["type"] == MILK_BUCKET or player.hunger < player.max_hunger:
                        fill = {BREAD: 5, RAW_BEEF: 3, STEAK: 8, ROTTEN_FLESH: 4, RAW_MUTTON: 3, COOKED_MUTTON: 7, MILK_BUCKET: 2}[slot["type"]]
                        player.hunger = min(player.max_hunger, player.hunger + fill)
                        if slot["type"] == MILK_BUCKET:
                            slot["type"] = BUCKET # Return empty bucket
                        else:
                            slot["count"] -= 1
                        if slot["count"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                
                # Hoe Interaction (Tilling)
                if slot and slot["type"] in (W_HOE, S_HOE, I_HOE):
                    if (tx, ty) in world.data and world.data[(tx, ty)] in (GRASS_BLOCK, DIRT_BLOCK):
                        world.data[(tx, ty)] = FARMLAND
                        slot["durability"] -= 1
                        if slot["durability"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                # Planting Seeds
                if slot and slot["type"] == SEEDS:
                    if (tx, ty) in world.data and world.data[(tx, ty)] == FARMLAND:
                        if (tx, ty - 1) not in world.data:
                            world.data[(tx, ty - 1)] = WHEAT_STG0
                            slot["count"] -= 1
                            if slot["count"] <= 0: player.inventory[player.selected_slot] = None
                            action_taken = True
                            break
                
                # Interaction with Mobs
                target_mob = None
                for mob in world.mobs:
                    dx = abs(player.rect.centerx - mob.rect.centerx)
                    if dx > WORLD_PIXELS / 2: dx = WORLD_PIXELS - dx
                    dy = abs(player.rect.centery - mob.rect.centery)
                    if dx < 60 and dy < player.rect.height:
                        # Check direction
                        rel_x = (mob.rect.centerx - player.rect.centerx)
                        if rel_x > WORLD_PIXELS / 2: rel_x -= WORLD_PIXELS
                        if rel_x < -WORLD_PIXELS / 2: rel_x += WORLD_PIXELS
                        if (player.direction > 0 and rel_x > 0) or (player.direction < 0 and rel_x < 0):
                            target_mob = mob
                            break
                
                if target_mob and target_mob.m_type == "cow" and slot and slot["type"] == BUCKET:
                    # Milking
                    if slot["count"] == 1:
                        slot["type"] = MILK_BUCKET
                    else:
                        slot["count"] -= 1
                        # Try to add milk bucket to inventory
                        added_milk = False
                        for i in range(36):
                            if player.inventory[i] is None:
                                player.inventory[i] = {"type": MILK_BUCKET, "count": 1}
                                added_milk = True
                                break
                        if not added_milk: # Drop if inventory full? For now just keep count and dont milk
                            slot["count"] += 1
                            action_taken = False
                            continue
                    action_taken = True
                    player.last_action_time = now
                    break

                # Interaction with Crafting Table
                if (tx, ty) in world.data and world.data[(tx, ty)] == CRAFTING_TABLE:
                    player.show_inventory = True
                    player.show_3x3 = True
                    action_taken = True
                    break # Only open one table
                elif (tx, ty) in world.data and world.data[(tx, ty)] in (FURNACE, SMOKER, BLAST_FURNACE):
                    if (tx, ty) not in world.furnace_data:
                        world.furnace_data[(tx, ty)] = {"input": None, "fuel": None, "output": None, "cook_time": 0.0, "fuel_time": 0.0}
                    player.show_inventory = True
                    player.show_3x3 = False
                    player.active_furnace_pos = (tx, ty)
                    player.active_chest_pos = None
                    action_taken = True
                    break
                elif (tx, ty) in world.data and world.data[(tx, ty)] == CHEST:
                    player.show_inventory = True
                    player.show_3x3 = False
                    player.active_furnace_pos = None
                    player.active_chest_pos = (tx, ty)
                    # Check for neighbor chest
                    is_large = False
                    master_pos = (tx, ty)
                    if (tx-1, ty) in world.data and world.data[(tx-1, ty)] == CHEST:
                        is_large = True
                        master_pos = (tx-1, ty)
                    elif (tx+1, ty) in world.data and world.data[(tx+1, ty)] == CHEST:
                        is_large = True
                    
                    player.active_chest_is_large = is_large
                    if master_pos not in world.chest_data:
                        size = 54 if is_large else 27
                        world.chest_data[master_pos] = [None] * size
                    action_taken = True
                    break
                elif (tx, ty) in world.data and world.data[(tx, ty)] in (DOOR, DOOR_OPEN, TRAPDOOR, TRAPDOOR_OPEN, FENCE_GATE, FENCE_GATE_OPEN):
                    b_type = world.data[(tx, ty)]
                    if b_type == DOOR: world.data[(tx, ty)] = DOOR_OPEN
                    elif b_type == DOOR_OPEN: world.data[(tx, ty)] = DOOR
                    elif b_type == TRAPDOOR: world.data[(tx, ty)] = TRAPDOOR_OPEN
                    elif b_type == TRAPDOOR_OPEN: world.data[(tx, ty)] = TRAPDOOR
                    elif b_type == FENCE_GATE: world.data[(tx, ty)] = FENCE_GATE_OPEN
                    elif b_type == FENCE_GATE_OPEN: world.data[(tx, ty)] = FENCE_GATE
                    elif b_type == BED:
                        world.time = 0 # 6:00 AM
                        save_game(world, player)
                        save_msg_timer = 120
                        action_taken = True
                        break
                    action_taken = True
                    break
                elif (tx, ty) not in world.data:
                    slot = player.inventory[player.selected_slot]
                    if slot is not None and slot["type"] in PLACEABLE_BLOCKS:
                        tr = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        p_placement_rect = player.rect.inflate(-6, -6)
                        p_placement_rect.x %= WORLD_PIXELS
                        if not p_placement_rect.colliderect(tr): 
                            world.data[(tx, ty)] = slot["type"]
                            if slot["type"] == CHEST:
                                # New chest placed - check if it merges with a neighbor
                                if (tx-1, ty) in world.data and world.data[(tx-1, ty)] == CHEST:
                                    # Merge with left
                                    old_data = world.chest_data.get((tx-1, ty), [None]*27)
                                    world.chest_data[(tx-1, ty)] = old_data + [None]*27
                                elif (tx+1, ty) in world.data and world.data[(tx+1, ty)] == CHEST:
                                    # Merge with right - current becomes master
                                    old_data = world.chest_data.get((tx+1, ty), [None]*27)
                                    world.chest_data[(tx, ty)] = [None]*27 + old_data
                                    if (tx+1, ty) in world.chest_data: del world.chest_data[(tx+1, ty)]
                                else:
                                    world.chest_data[(tx, ty)] = [None]*27
                            
                            slot["count"] -= 1
                            action_taken = True
                            if slot["count"] <= 0:
                                player.inventory[player.selected_slot] = None
                                break 
            if action_taken:
                player.last_action_time = now
        else:
            if not m_btns[0]:
                player.breaking_block = None
                player.breaking_progress = 0.0

        # --- Combat Logic ---
        if m_btns[0] and not player.show_inventory:
            tool = player.inventory[player.selected_slot]
            t_type = tool["type"] if tool else None
            
            # Base damage for hand
            dmg = 1
            if t_type in (W_SWORD, S_SWORD, I_SWORD): dmg = 4 if t_type == W_SWORD else (5 if t_type == S_SWORD else 7)
            elif t_type in (W_AXE, S_AXE, I_AXE): dmg = 3 if t_type == W_AXE else (4 if t_type == S_AXE else 6)
            elif t_type in (W_PICK, S_PICK, I_PICK): dmg = 2 if t_type == W_PICK else (3 if t_type == S_PICK else 5)
            elif t_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL): dmg = 1 if t_type == W_SHOVEL else (2 if t_type == S_SHOVEL else 4)
            elif t_type in (W_HOE, S_HOE, I_HOE): dmg = 1 if t_type == W_HOE else (1 if t_type == S_HOE else 2)

            if now - player.last_action_time > 300:
                # Combat with Mobs (with wrap handling)
                hit_any = False
                for mob in world.mobs:
                    dx = abs(player.rect.centerx - mob.rect.centerx)
                    if dx > WORLD_PIXELS / 2:
                        dx = WORLD_PIXELS - dx
                    
                    dy = abs(player.rect.centery - mob.rect.centery)
                    
                    # If mob is within range (horizontally within 60 and vertically within player height)
                    if dx < 60 and dy < player.rect.height:
                        # Check if mob is in front of player
                        rel_x = (mob.rect.centerx - player.rect.centerx)
                        if rel_x > WORLD_PIXELS / 2: rel_x -= WORLD_PIXELS
                        if rel_x < -WORLD_PIXELS / 2: rel_x += WORLD_PIXELS
                        
                        if (player.direction > 0 and rel_x > 0) or (player.direction < 0 and rel_x < 0):
                            mob.health -= dmg
                            mob.hurt_timer = 10
                            mob.vel_y = -6 # Knockback
                            mob.rect.x = (mob.rect.x + player.direction * 25) % WORLD_PIXELS
                            hit_any = True
                
                if hit_any:
                    player.last_action_time = now
                    # Durability Loss for tools
                    if tool and tool["type"] >= 100:
                        tool["durability"] -= 1
                        if tool["durability"] <= 0:
                            player.inventory[player.selected_slot] = None

        player.update(world)
        update_furnaces(world)
        world.time = (world.time + 1) % 24000
        
        # Mob Spawning
        t = world.time
        # Zombies at Night
        if (t > 14000 or t < 1000) and len([m for m in world.mobs if m.m_type == "zombie"]) < 6:
            if random.random() < 0.005:
                world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "zombie"))
        # Cows during Day
        if (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "cow"]) < 4:
            if random.random() < 0.003:
                world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "cow"))
        if (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "sheep"]) < 4:
            if random.random() < 0.003:
                world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "sheep"))
            
        for mob in world.mobs[:]:
            mob.update(world, player)
            if mob.health <= 0:
                def spawn_drop(item_type, count=1):
                    for _ in range(count):
                        world.dropped_items.append(DroppedItem(mob.rect.centerx, mob.rect.centery, item_type))

                if mob.m_type == "cow":
                    spawn_drop(RAW_BEEF, random.randint(2, 4))
                elif mob.m_type == "zombie":
                    spawn_drop(ROTTEN_FLESH, random.randint(1, 2))
                    spawn_drop(BONE, random.randint(1, 2))
                elif mob.m_type == "sheep":
                    spawn_drop(WOOL, random.randint(1, 2))
                    spawn_drop(RAW_MUTTON, random.randint(1, 3))
                world.mobs.remove(mob)
                
        # --- Farming Growth ---
        if random.random() < 0.01: # Growth tick
            crops = [pos for pos, b in world.data.items() if WHEAT_STG0 <= b < WHEAT_STG3]
            if crops:
                cp = random.choice(crops)
                world.data[cp] += 1
                
        # Auto-Save
        auto_save_timer += 1
        if auto_save_timer >= 1800: # 30 seconds
            save_game(world, player)
            auto_save_timer = 0
            save_msg_timer = 120 # Show for 2 seconds
            
        world.draw(screen, scroll_x, scroll_y)
        
        # Update and Draw Dropped Items
        for di in world.dropped_items[:]:
            di.update(world)
            di.draw(screen, scroll_x, scroll_y, font)
            # Pickup logic
            dist_x = abs(di.rect.centerx - player.rect.centerx)
            if dist_x > WORLD_PIXELS / 2: dist_x = WORLD_PIXELS - dist_x
            dist_y = abs(di.rect.centery - player.rect.centery)
            
            if dist_x < 24 and dist_y < 32 and pygame.time.get_ticks() - di.spawn_time > 500:
                # Add to inventory
                added = False
                for slot in player.inventory:
                    if slot and slot["type"] == di.item_type and slot["count"] < 80:
                        slot["count"] += di.count
                        added = True
                        break
                if not added:
                    for i in range(36):
                        if player.inventory[i] is None:
                            player.inventory[i] = {"type": di.item_type, "count": di.count}
                            added = True
                            break
                if added:
                    world.dropped_items.remove(di)

        for mob in world.mobs:
            mob.draw(screen, scroll_x, scroll_y)
            
        if player.breaking_block:
            world.draw_cracks(screen, scroll_x, scroll_y, player.breaking_block, player.breaking_progress)
        
        # --- Mob Hover Highlighting ---
        m_pos = pygame.mouse.get_pos()
        for mob in world.mobs:
            dx = mob.rect.x - int(scroll_x)
            if dx < -200: dx += WORLD_PIXELS
            if dx > SCREEN_WIDTH + 200: dx -= WORLD_PIXELS
            dy = mob.rect.y - int(scroll_y)
            
            mob_screen_rect = pygame.Rect(dx, dy, mob.rect.width, mob.rect.height)
            if mob_screen_rect.collidepoint(m_pos):
                pygame.draw.rect(screen, COLOR_WHITE, mob_screen_rect, 2)
                break # Highlight only one mob at a time
        
        # --- Targeting Rects ---
        if not player.show_inventory:
            for off in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
                for tx, ty in valid_targets:
                    pygame.draw.rect(screen, COLOR_WHITE, (tx*TILE_SIZE - int(scroll_x) + off, ty*TILE_SIZE - int(scroll_y), TILE_SIZE, TILE_SIZE), 2)

        # --- Draw Player ---
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            px_draw = (player.rect.x - int(scroll_x)) + offset
            if px_draw < -100 or px_draw > SCREEN_WIDTH + 100: continue
            py_draw = (player.rect.y - int(scroll_y))

            is_inv = pygame.time.get_ticks() < player.invincible_until
            if not is_inv or (pygame.time.get_ticks() // 150) % 2:
                pygame.draw.rect(screen, COLOR_RED, (px_draw, py_draw, player.rect.width, player.rect.height))
                pygame.draw.rect(screen, COLOR_DARK_RED, (px_draw-2, py_draw, player.rect.width+4, TILE_SIZE))
                # Hand/Tool indicator
                ax_end = px_draw + 12 + (player.direction * 10)
                pygame.draw.line(screen, COLOR_WHITE, (px_draw+12, py_draw+16), (ax_end, py_draw+16), 2)

        # --- UI Drawing ---
        if player.show_inventory:
            # Darken Background
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            # Draw Inventory & Hotbar
            inv_x, inv_y = SCREEN_WIDTH // 2 - 200, 360
            
            # --- Draw Main Inventory Panel ---
            pygame.draw.rect(screen, (140, 140, 140), (inv_x - 10, inv_y - 30, 416, 180))
            pygame.draw.rect(screen, (40, 40, 40), (inv_x - 10, inv_y - 30, 416, 180), 3)
            screen.blit(font.render("Inventory", True, (40, 40, 40)), (inv_x, inv_y - 25))
            
            # --- Draw Hotbar Panel ---
            pygame.draw.rect(screen, (140, 140, 140), (inv_x - 10, inv_y + 140, 416, 60))
            pygame.draw.rect(screen, (40, 40, 40), (inv_x - 10, inv_y + 140, 416, 60), 3)
            
            for i in range(36):
                if i < 9: # Hotbar
                    sx, sy = inv_x + i * 44, inv_y + 150
                else: # Main Inventory
                    row, col = (i - 9) // 9, (i - 9) % 9
                    sx, sy = inv_x + col * 44, inv_y + row * 44
                
                pygame.draw.rect(screen, (100, 100, 100), (sx, sy, 40, 40))
                pygame.draw.rect(screen, (60, 60, 60), (sx, sy, 40, 40), 2)
                
                slot = player.inventory[i]
                if slot:
                    draw_block_icon(screen, slot["type"], sx+4, sy+4, 32, font)
                    if "durability" in slot:
                        max_d = MAX_DURABILITY.get(slot["type"], 1)
                        ratio = slot["durability"] / max_d
                        pygame.draw.rect(screen, (0,0,0), (sx + 4, sy + 32, 32, 4))
                        pygame.draw.rect(screen, (int(255*(1-ratio)), int(255*ratio), 0), (sx + 4, sy + 32, int(32 * ratio), 4))
                    if slot["count"] > 1:
                        c_txt = font.render(str(slot["count"]), True, COLOR_WHITE)
                        screen.blit(c_txt, (sx + 24, sy + 22))

            # Draw Armor Slots
            ax, ay = inv_x - 50, inv_y
            for i in range(4):
                pygame.draw.rect(screen, (80, 80, 80), (ax, ay + i * 44, 40, 40))
                pygame.draw.rect(screen, (50, 50, 50), (ax, ay + i * 44, 40, 40), 2)
                if player.armor[i]:
                    draw_block_icon(screen, player.armor[i]["type"], ax+4, ay + i * 44 + 4, 32, font)
                    if "durability" in player.armor[i]:
                        max_d = MAX_DURABILITY.get(player.armor[i]["type"], 1)
                        ratio = player.armor[i]["durability"] / max_d
                        pygame.draw.rect(screen, (0,0,0), (ax + 4, ay + i * 44 + 32, 32, 4))
                        pygame.draw.rect(screen, (int(255*(1-ratio)), int(255*ratio), 0), (ax + 4, ay + i * 44 + 32, int(32 * ratio), 4))
                else:
                    # Draw Ghost Icon
                    ghost_types = [I_HELMET, I_CHEST, I_LEGS, I_BOOTS]
                    # Create a temporary surface for the ghost icon
                    ghost_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                    draw_block_icon(ghost_surf, ghost_types[i], 0, 0, 32, font)
                    # Tint it dark grey
                    ghost_surf.fill((60, 60, 60, 150), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(ghost_surf, (ax + 4, ay + i * 44 + 4))

            if not player.show_3x3 and not player.active_furnace_pos and not player.active_chest_pos:
                # --- Draw 2x2 Crafting Panel ---
                craft_x, craft_y = inv_x + 250, inv_y - 180
                pygame.draw.rect(screen, (140, 140, 140), (craft_x - 10, craft_y - 30, 160, 130))
                pygame.draw.rect(screen, (40, 40, 40), (craft_x - 10, craft_y - 30, 160, 130), 3)
                screen.blit(font.render("Crafting", True, (40, 40, 40)), (craft_x, craft_y - 25))
                for i in range(4):
                    sx, sy = craft_x + (i % 2) * 44, craft_y + (i // 2) * 44
                    pygame.draw.rect(screen, (100, 100, 100), (sx, sy, 40, 40))
                    slot = player.crafting_grid[i]
                    if slot:
                        draw_block_icon(screen, slot["type"], sx+4, sy+4, 32, font)
                        if slot["count"] > 1:
                            c_txt = font.render(str(slot["count"]), True, COLOR_WHITE)
                            screen.blit(c_txt, (sx + 24, sy + 22))
                
                # Output Slot (2x2)
                out_sx, out_sy = craft_x + 120, craft_y + 22
                pygame.draw.rect(screen, (120, 120, 120), (out_sx, out_sy, 44, 44))
                if player.crafting_output:
                    draw_block_icon(screen, player.crafting_output["type"], out_sx+6, out_sy+6, 32, font)
                    if player.crafting_output["count"] > 1:
                        c_txt = font.render(str(player.crafting_output["count"]), True, COLOR_WHITE)
                        screen.blit(c_txt, (out_sx + 26, out_sy + 24))
            elif player.show_3x3:
                # --- Draw 3x3 Crafting Panel ---
                craft_x, craft_y = inv_x + 210, inv_y - 220
                pygame.draw.rect(screen, (140, 140, 140), (craft_x - 10, craft_y - 30, 220, 170))
                pygame.draw.rect(screen, (40, 40, 40), (craft_x - 10, craft_y - 30, 220, 170), 3)
                screen.blit(font.render("Crafting", True, (40, 40, 40)), (craft_x, craft_y - 25))
                for i in range(9):
                    sx, sy = craft_x + (i % 3) * 44, craft_y + (i // 3) * 44
                    pygame.draw.rect(screen, (100, 100, 100), (sx, sy, 40, 40))
                    slot = player.crafting_3x3[i]
                    if slot:
                        draw_block_icon(screen, slot["type"], sx+4, sy+4, 32, font)
                        if slot["count"] > 1:
                            c_txt = font.render(str(slot["count"]), True, COLOR_WHITE)
                            screen.blit(c_txt, (sx + 24, sy + 22))
                
                # Output Slot (3x3)
                out_sx, out_sy = craft_x + 150, craft_y + 44
                pygame.draw.rect(screen, (120, 120, 120), (out_sx, out_sy, 44, 44))
                if player.output_3x3:
                    draw_block_icon(screen, player.output_3x3["type"], out_sx+6, out_sy+6, 32, font)
                    if player.output_3x3["count"] > 1:
                        c_txt = font.render(str(player.output_3x3["count"]), True, COLOR_WHITE)
                        screen.blit(c_txt, (out_sx + 26, out_sy + 24))
            elif player.active_furnace_pos:
                # --- Draw Furnace Panel ---
                f_data = world.furnace_data[player.active_furnace_pos]
                fx, fy = inv_x + 250, inv_y - 180
                pygame.draw.rect(screen, (140, 140, 140), (fx - 10, fy - 30, 160, 180))
                pygame.draw.rect(screen, (40, 40, 40), (fx - 10, fy - 30, 160, 180), 3)
                screen.blit(font.render("Furnace", True, (40, 40, 40)), (fx, fy - 25))
                # Input
                pygame.draw.rect(screen, (100, 100, 100), (fx, fy, 40, 40))
                if f_data["input"]: draw_block_icon(screen, f_data["input"]["type"], fx+4, fy+4, 32, font)
                # Fuel
                pygame.draw.rect(screen, (100, 100, 100), (fx, fy + 88, 40, 40))
                if f_data["fuel"]: draw_block_icon(screen, f_data["fuel"]["type"], fx+4, fy+92, 32, font)
                # Output
                pygame.draw.rect(screen, (120, 120, 120), (fx + 100, fy + 44, 44, 44))
                if f_data["output"]: draw_block_icon(screen, f_data["output"]["type"], fx+106, fy+50, 32, font)
                # Progress Arrow
                pygame.draw.rect(screen, COLOR_GRAY, (fx + 50, fy + 55, 40, 10))
                if f_data["cook_time"] > 0:
                    pygame.draw.rect(screen, (255, 165, 0), (fx + 50, fy + 55, int(40 * (f_data["cook_time"]/10.0)), 10))
                # Fire icon
                if f_data["fuel_time"] > 0:
                    pygame.draw.polygon(screen, COLOR_RED, [(fx + 10, fy + 75), (fx + 30, fy + 75), (fx + 20, fy + 55)])
            if player.active_chest_pos:
                cx, cy = inv_x, 40
                tx, ty = player.active_chest_pos
                master_pos = (tx, ty)
                if (tx-1, ty) in world.chest_data: master_pos = (tx-1, ty)
                c_slots = world.chest_data.get(master_pos, [])
                
                p_width = 416; p_height = 40 + (len(c_slots)//9) * 44
                pygame.draw.rect(screen, (140, 140, 140), (cx - 10, cy - 30, p_width, p_height))
                pygame.draw.rect(screen, (40, 40, 40), (cx - 10, cy - 30, p_width, p_height), 3)
                screen.blit(font.render("Chest", True, (40, 40, 40)), (cx, cy - 25))
                
                for i in range(len(c_slots)):
                    row, col = i // 9, i % 9
                    sx, sy = cx + col * 44, cy + row * 44
                    pygame.draw.rect(screen, (100, 100, 100), (sx, sy, 40, 40))
                    pygame.draw.rect(screen, (60, 60, 60), (sx, sy, 40, 40), 2)
                    slot = c_slots[i]
                    if slot:
                        draw_block_icon(screen, slot["type"], sx+4, sy+4, 32, font)
                        if slot["count"] > 1:
                            c_txt = font.render(str(slot["count"]), True, COLOR_WHITE)
                            screen.blit(c_txt, (sx + 24, sy + 22))

            # Held Item
            if player.held_item:
                mx, my = pygame.mouse.get_pos()
                draw_block_icon(screen, player.held_item["type"], mx - 16, my - 16, 32, font)
                if player.held_item["count"] > 1:
                    c_txt = font.render(str(player.held_item["count"]), True, COLOR_WHITE)
                    screen.blit(c_txt, (mx + 8, my + 6))

            # Hover Tooltips
            mx, my = pygame.mouse.get_pos()
            hovered_item = None
            
            # Check Inventory/Hotbar
            for i in range(36):
                if i < 9: sx, sy = inv_x + i * 44, inv_y + 150
                else: sx, sy = inv_x + ((i-9)%9) * 44, inv_y + ((i-9)//9) * 44
                if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                    if player.inventory[i]: hovered_item = player.inventory[i]
            
            # Check Crafting
            if not player.show_3x3:
                for i in range(4):
                    sx, sy = inv_x + 250 + (i % 2) * 44, inv_y - 150 + (i // 2) * 44
                    if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                        if player.crafting_grid[i]: hovered_item = player.crafting_grid[i]
                if inv_x + 370 <= mx <= inv_x + 414 and inv_y - 128 <= my <= inv_y - 84:
                    if player.crafting_output: hovered_item = player.crafting_output
            else:
                for i in range(9):
                    sx, sy = inv_x + 230 + (i % 3) * 44, inv_y - 200 + (i // 3) * 44
                    if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                        if player.crafting_3x3[i]: hovered_item = player.crafting_3x3[i]
                if inv_x + 380 <= mx <= inv_x + 424 and inv_y - 156 <= my <= inv_y - 112:
                    if player.output_3x3: hovered_item = player.output_3x3
            
            # Check Armor Hover
            for i in range(4):
                sx, sy = inv_x - 50, inv_y + i * 44
                if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
                    if player.armor[i]: hovered_item = player.armor[i]

            if hovered_item:
                name = BLOCK_NAMES.get(hovered_item["type"], "Unknown")
                t_txt = font.render(name, True, COLOR_WHITE)
                tw, th = t_txt.get_size()
                pygame.draw.rect(screen, (30, 30, 30), (mx + 15, my - 25, tw + 10, th + 6))
                pygame.draw.rect(screen, (100, 100, 100), (mx + 15, my - 25, tw + 10, th + 6), 1)
                screen.blit(t_txt, (mx + 20, my - 22))

        else: # Normal Game UI
            # --- Draw Hearts (HP) ---
            for i in range(10):
                hx, hy = 20 + i * 18, 20
                pygame.draw.rect(screen, (50, 0, 0), (hx, hy, 16, 16)) # Background
                if player.health > i * 2 + 1:
                    pygame.draw.rect(screen, COLOR_RED, (hx + 2, hy + 2, 12, 12)) # Full heart
                elif player.health > i * 2:
                    pygame.draw.rect(screen, COLOR_RED, (hx + 2, hy + 2, 6, 12)) # Half heart
            
            # --- Draw Hunger (Drumsticks) ---
            for i in range(10):
                hx, hy = 20 + i * 18, 40
                pygame.draw.rect(screen, (30, 20, 10), (hx, hy, 16, 16)) # Background
                if player.hunger > i * 2 + 1:
                    pygame.draw.rect(screen, (150, 100, 50), (hx + 2, hy + 4, 12, 8)) # Full drumstick
                    pygame.draw.rect(screen, (200, 150, 100), (hx + 10, hy + 4, 4, 4))
                elif player.hunger > i * 2:
                    pygame.draw.rect(screen, (150, 100, 50), (hx + 2, hy + 4, 6, 8)) # Half drumstick

            # --- Draw Armor (Shields) ---
            armor_level = 0
            for part in player.armor:
                if part: armor_level += 1
            for i in range(10):
                hx, hy = 20 + i * 18, 60
                pygame.draw.rect(screen, (40, 40, 60), (hx, hy, 16, 16)) # Background
                if armor_level > i:
                    pygame.draw.rect(screen, (200, 200, 255), (hx + 4, hy + 2, 8, 12)) # Shield
                    pygame.draw.rect(screen, (100, 100, 150), (hx + 4, hy + 2, 8, 12), 1)

            mode_names = ["FRONT (LEG)", "FRONT (HEAD)", "DOWN (TOWER)", "UP", "MINING (BOTH)"]
            mode_text = font.render(f"MODE: {mode_names[target_mode]} (F to Cycle)", True, COLOR_WHITE)
            screen.blit(mode_text, (20, 85))
            
            # --- Save Message ---
            if save_msg_timer > 0:
                msg = font.render("Game Saved!", True, (100, 255, 100))
                screen.blit(msg, (SCREEN_WIDTH - 120, 20))
                save_msg_timer -= 1
            
            # --- Draw Hotbar ---
            hotbar_y = SCREEN_HEIGHT - 50
            hotbar_x = SCREEN_WIDTH // 2 - (9 * 44) // 2
            for i in range(9):
                slot_x = hotbar_x + i * 44
                pygame.draw.rect(screen, (80, 80, 80), (slot_x, hotbar_y, 40, 40))
                if i == player.selected_slot:
                    pygame.draw.rect(screen, (255, 255, 255), (slot_x - 2, hotbar_y - 2, 44, 44), 3)
                
                slot = player.inventory[i]
                if slot:
                    draw_block_icon(screen, slot["type"], slot_x+4, hotbar_y+4, 32, font)
                    if "durability" in slot:
                        max_d = MAX_DURABILITY.get(slot["type"], 1)
                        ratio = slot["durability"] / max_d
                        pygame.draw.rect(screen, (0,0,0), (slot_x + 4, hotbar_y + 32, 32, 4))
                        pygame.draw.rect(screen, (int(255*(1-ratio)), int(255*ratio), 0), (slot_x + 4, hotbar_y + 32, int(32 * ratio), 4))
                    if slot["count"] > 1:
                        count_str = str(slot["count"])
                        c_text = font.render(count_str, True, COLOR_WHITE)
                        screen.blit(c_text, (slot_x + 24, hotbar_y + 22))

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()