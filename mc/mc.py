import pygame
import random
import math
import json
import os
import sys
import threading
from pathlib import Path
import mc_network
import discovery
import time

# --- Configuration & Specs ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
WORLD_WIDTH = 1000
CHUNK_SIZE = 16
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
COLOR_DIAMOND = (80, 220, 220)
COLOR_OAK_BROWN = (101, 67, 33)
COLOR_BIRCH_WHITE = (220, 220, 220)
COLOR_PLANKS = (210, 180, 140)
COLOR_LEAVES_G = (34, 100, 34)
COLOR_LEAVES_B = (50, 120, 50)
COLOR_RED = (255, 0, 0)
COLOR_DARK_RED = (200, 0, 0)

def sanitize_display_name(raw_name):
    name = "".join(ch for ch in raw_name.strip() if ch.isprintable())
    if not name:
        name = f"Player{random.randint(1000, 9999)}"
    return name[:16]

def draw_nameplate(surface, font, label, center_x, top_y, text_color=(255, 255, 255)):
    if not label:
        return
    txt = font.render(label, True, text_color)
    pad_x = 6
    pad_y = 2
    box_w = txt.get_width() + pad_x * 2
    box_h = txt.get_height() + pad_y * 2
    box_x = int(center_x - box_w / 2)
    box_y = int(top_y - box_h - 4)
    pygame.draw.rect(surface, (0, 0, 0), (box_x, box_y, box_w, box_h))
    pygame.draw.rect(surface, (255, 255, 255), (box_x, box_y, box_w, box_h), 1)
    surface.blit(txt, (box_x + pad_x, box_y + pad_y))

BASE_DIR = Path(__file__).resolve().parent
WORLDS_DIR = BASE_DIR / "worlds"
WORLDS_DIR.mkdir(exist_ok=True)

class RemotePlayer:
    def __init__(self, p_id, x, y, display_name=None):
        self.id = p_id
        self.x = x
        self.y = y
        self.direction = 1
        self.anim_timer = 0
        self.armor = [None]*4
        self.display_name = sanitize_display_name(display_name or p_id)

    def draw(self, surface, scroll_x, scroll_y, font):
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx = self.x - int(scroll_x) + offset
            if dx < -50 or dx > SCREEN_WIDTH + 50: continue
            dy = self.y - int(scroll_y)
            
            # Body (Blue)
            pygame.draw.rect(surface, (50, 100, 200), (dx, dy, 24, 62))
            pygame.draw.rect(surface, (0, 0, 150), (dx-2, dy, 28, 32))
            
            # Hand/Tool indicator
            ax_end = dx + 12 + (self.direction * 10)
            pygame.draw.line(surface, (255, 255, 255), (dx+12, dy+16), (ax_end, dy+16), 2)

            # Name tag
            draw_nameplate(surface, font, self.display_name, dx + 12, dy)

class Particle:
    def __init__(self, x, y, color, vel_x=None, vel_y=None, life=30):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vel_x if vel_x is not None else random.uniform(-2, 2)
        self.vy = vel_y if vel_y is not None else random.uniform(-4, -1)
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2 # Gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surface, scroll_x, scroll_y):
        alpha = int((self.life / self.max_life) * 255)
        size = max(1, int((self.life / self.max_life) * 4))
        p_surf = pygame.Surface((size, size))
        p_surf.fill(self.color)
        p_surf.set_alpha(alpha)
        # Handle infinite wrap for particles too?
        # For simplicity, just draw once
        surface.blit(p_surf, (self.x - scroll_x, self.y - scroll_y))

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
DIAMOND_ORE = 68
DIAMOND = 69
DOOR_TOP = 70
DOOR_OPEN_TOP = 71
BED_RIGHT = 72
COAL_BLOCK_ITEM = 73
ENDER_PEARL = 74
STRING_ITEM = 75
BOW = 76
RAW_CHICKEN = 77
COOKED_CHICKEN = 78
FEATHER = 79
EGG = 80
TORCH = 81
RAW_COD = 82
COOKED_COD = 83
FISHING_ROD = 84
RAW_SALMON = 85
COOKED_SALMON = 86
RAW_FISH = RAW_COD
COOKED_FISH = COOKED_COD

# Tool IDs
W_PICK = 100; S_PICK = 101; I_PICK = 110
W_AXE = 102; S_AXE = 103; I_AXE = 111
W_SHOVEL = 104; S_SHOVEL = 105; I_SHOVEL = 112
W_SWORD = 106; S_SWORD = 107; I_SWORD = 113
W_HOE = 108; S_HOE = 109; I_HOE = 114
D_PICK = 115; D_AXE = 116; D_SHOVEL = 117; D_SWORD = 118; D_HOE = 119

# Armor IDs
I_HELMET = 120; I_CHEST = 121; I_LEGS = 122; I_BOOTS = 123
D_HELMET = 124; D_CHEST = 125; D_LEGS = 126; D_BOOTS = 127
SHIELD = 134

BLOCK_HARDNESS = {
    GRASS_BLOCK: 0.1, DIRT_BLOCK: 0.5, STONE_BLOCK: 1.5, 
    COAL_BLOCK: 3.0, IRON_BLOCK: 3.0, DIAMOND_ORE: 4.0, OAK_LOG: 2.0, BIRCH_LOG: 2.0,
    OAK_LEAVES: 0.2, BIRCH_LEAVES: 0.2, PLANKS: 2.0, CRAFTING_TABLE: 2.5,
    FURNACE: 3.5, SMOKER: 3.5, BLAST_FURNACE: 3.5, COBBLESTONE: 2.0, SMOOTH_STONE: 2.0, IRON_BLOCK_PROD: 5.0,
    CHEST: 2.5, HAY_BALE: 0.5, FARMLAND: 0.6, FENCE: 2.0, FENCE_GATE: 2.0,
    DOOR: 3.0, TRAPDOOR: 3.0, W_STAIRS: 2.0, C_STAIRS: 2.0, SS_STAIRS: 2.0, I_STAIRS: 3.0,
    W_SLAB: 2.0, C_SLAB: 2.0, SS_SLAB: 2.0, I_SLAB: 3.0, LADDER: 0.4, TORCH: 0.1
}

BLOCK_NAMES = {
    GRASS_BLOCK: "Grass", DIRT_BLOCK: "Dirt", STONE_BLOCK: "Stone",
    COAL_BLOCK: "Coal Ore", IRON_BLOCK: "Iron Ore", DIAMOND_ORE: "Diamond Ore", OAK_LOG: "Oak Log",
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
    D_PICK: "Diamond Pickaxe", D_AXE: "Diamond Axe", D_SHOVEL: "Diamond Shovel",
    D_SWORD: "Diamond Sword", D_HOE: "Diamond Hoe",
    I_HELMET: "Iron Helmet", I_CHEST: "Iron Chestplate",
    I_LEGS: "Iron Leggings", I_BOOTS: "Iron Boots",
    D_HELMET: "Diamond Helmet", D_CHEST: "Diamond Chestplate",
    D_LEGS: "Diamond Leggings", D_BOOTS: "Diamond Boots",
    SHIELD: "Shield",
    LADDER: "Ladder",
    DIAMOND: "Diamond",
    COAL_BLOCK_ITEM: "Coal Block",
    ENDER_PEARL: "Ender Pearl",
    STRING_ITEM: "String",
    BOW: "Bow",
    RAW_CHICKEN: "Raw Chicken",
    COOKED_CHICKEN: "Cooked Chicken",
    FEATHER: "Feather",
    EGG: "Egg",
    RAW_COD: "Cod",
    COOKED_COD: "Cooked Cod",
    RAW_SALMON: "Salmon",
    COOKED_SALMON: "Cooked Salmon",
    FISHING_ROD: "Fishing Rod",
    TORCH: "Torch"
}

MAX_DURABILITY = {
    W_PICK: 60, W_AXE: 60, W_SHOVEL: 60, W_SWORD: 60, W_HOE: 60,
    S_PICK: 132, S_AXE: 132, S_SHOVEL: 132, S_SWORD: 132, S_HOE: 132,
    I_PICK: 250, I_AXE: 250, I_SHOVEL: 250, I_SWORD: 250, I_HOE: 250,
    D_PICK: 1561, D_AXE: 1561, D_SHOVEL: 1561, D_SWORD: 1561, D_HOE: 1561,
    I_HELMET: 165, I_CHEST: 240, I_LEGS: 225, I_BOOTS: 195,
    D_HELMET: 363, D_CHEST: 528, D_LEGS: 495, D_BOOTS: 429,
    BOW: 384,
    FISHING_ROD: 64,
    SHIELD: 336
}

PLACEABLE_BLOCKS = {
    GRASS_BLOCK, DIRT_BLOCK, STONE_BLOCK, COAL_BLOCK, IRON_BLOCK,
    OAK_LOG, BIRCH_LOG, OAK_LEAVES, BIRCH_LEAVES, PLANKS,
    CRAFTING_TABLE, FURNACE, COBBLESTONE, SMOOTH_STONE,
    IRON_BLOCK_PROD, DOOR, TRAPDOOR, PRESSURE_PLATE, BUTTON,
    LEVER, CHAIN, W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS,
    W_SLAB, C_SLAB, SS_SLAB, I_SLAB, FARMLAND, HAY_BALE, CHEST,
    FENCE, FENCE_GATE, WOOL, BED, LADDER, COAL_BLOCK_ITEM, BOAT, TORCH
}

class Player:
    def __init__(self, display_name="Player"):
        # Persistent ID for multiplayer saves
        self.persistent_id = "player_" + str(random.randint(1000, 9999))
        try:
            player_id_file = WORLDS_DIR / "player_id.json"
            if player_id_file.exists():
                with open(player_id_file, "r") as f:
                    self.persistent_id = json.load(f).get("id", self.persistent_id)
            else:
                with open(player_id_file, "w") as f:
                    json.dump({"id": self.persistent_id}, f)
        except: pass

        self.display_name = sanitize_display_name(display_name)

        self.rect = pygame.Rect(100, 50, 24, (TILE_SIZE * 2) - 2) 
        self.vel_y = 0
        self.speed = 5
        self.jump_strength = -8.0 
        self.on_ground = False
        self.direction = 1 
        self.anim_timer = 0
        
        self.health = 20
        self.max_health = 20
        self.invincible_until = 0
        self.jump_attack_timer = 0
        
        self.inventory = [None] * 36
        self.selected_slot = 0
        self.armor = [None] * 4
        self.offhand = None
        self.blocking = False
        
        self.fishing_hook = None
        self.breaking_block = None
        self.breaking_progress = 0.0
        
        self.hunger = 20
        self.max_hunger = 20
        self.hunger_timer = 0
        self.regen_timer = 0
        self.show_inventory = False

    def update(self, world):
        if self.jump_attack_timer > 0:
            self.jump_attack_timer -= 1
        self.hunger_timer += 1
        if self.hunger_timer >= 600:
            self.hunger = max(0, self.hunger - 0.2)
            self.hunger_timer = 0
        self.regen_timer += 1
        if self.regen_timer >= 240:
            if self.hunger >= 18 and self.health < self.max_health:
                self.health = min(self.max_health, self.health + 1)
            elif self.hunger <= 0:
                self.take_damage(1)
            self.regen_timer = 0

        if self.show_inventory: return

    def respawn(self):
        self.rect.x, self.rect.y = 100, 50
        self.vel_y = 0
        self.health = 20
        self.hunger = 20
        self.invincible_until = pygame.time.get_ticks() + 5000

    def take_damage(self, amount):
        if pygame.time.get_ticks() < self.invincible_until: return
        reduction = 0
        for part in self.armor:
            if part:
                if part["type"] in (D_HELMET, D_CHEST, D_LEGS, D_BOOTS): reduction += 0.2
                else: reduction += 0.15
        if self.blocking: reduction = 1.0
        final_dmg = amount * (1.0 - reduction)
        self.health -= final_dmg
        self.invincible_until = pygame.time.get_ticks() + 500
        if self.health < 0: self.health = 0

class World:
    def __init__(self):
        self.chunks = {} # (cx, cy) -> {(tx, ty): block_id}
        self.block_meta = {} # (tx, ty) -> {"facing": 1 or -1}
        self.furnace_data = {} 
        self.chest_data = {} 
        self.remote_players_data = {} 
        self.mobs = []
        self.dropped_items = [] 
        self.projectiles = [] 
        self.egg_projectiles = [] 
        self.arrows = [] 
        self.fishing_hooks = [] 
        self.particles = []
        self.liquid_tick_timer = 0
        self.time = 0 
        self.generate_world()

    def get_chunk_id(self, tx, ty):
        return (tx // CHUNK_SIZE, ty // CHUNK_SIZE)

    def set_block(self, tx, ty, b_type):
        cid = self.get_chunk_id(tx, ty)
        if b_type is None or b_type == AIR:
            if cid in self.chunks and (tx, ty) in self.chunks[cid]:
                del self.chunks[cid][(tx, ty)]
                if not self.chunks[cid]: del self.chunks[cid]
            return
        if cid not in self.chunks: self.chunks[cid] = {}
        self.chunks[cid][(tx, ty)] = b_type

    def get_block(self, tx, ty):
        cid = self.get_chunk_id(tx, ty)
        if cid in self.chunks:
            return self.chunks[cid].get((tx, ty))
        return None

    def spawn_particles(self, x, y, color, count=5):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def tick_liquids(self):
        water_to_add = []
        for chunk in self.chunks.values():
            for (tx, ty), b_type in chunk.items():
                if b_type == WATER:
                    fill = self.block_meta.get((tx, ty), {}).get("fill", 7)
                    if ty + 1 < WORLD_HEIGHT:
                        below = self.get_block(tx, ty + 1)
                        if below is None or below == AIR:
                            water_to_add.append((tx, ty + 1, 7))
                            continue
                    if fill > 0:
                        for dx in [-1, 1]:
                            side_x = (tx + dx) % WORLD_WIDTH
                            if self.get_block(side_x, ty) is None:
                                water_to_add.append((side_x, ty, fill - 1))
        for tx, ty, f in water_to_add:
            self.set_block(tx, ty, WATER)
            if (tx, ty) not in self.block_meta: self.block_meta[(tx, ty)] = {}
            self.block_meta[(tx, ty)]["fill"] = f

    def generate_world(self):
        # Surface & Lakes
        for x in range(WORLD_WIDTH):
            h = int(12 + math.sin(x * 0.15) * 4 + math.cos(x * 0.05) * 2)
            is_lake = False
            if 30 < x < 50 or 75 < x < 90:
                h += 3
                is_lake = True
            for y in range(WORLD_HEIGHT):
                if y > h: self.set_block(x, y, STONE_BLOCK if y > h+4 else DIRT_BLOCK)
                elif y == h: 
                    self.set_block(x, y, GRASS_BLOCK)
                    if random.random() < 0.2: self.set_block(x, y - 1, TALL_GRASS)
                elif is_lake and y > h - 4: self.set_block(x, y, WATER)
                
        # Generate Caves
        for _ in range(15):
            cx, cy = random.randint(0, WORLD_WIDTH - 1), random.randint(20, WORLD_HEIGHT - 20)
            for _ in range(random.randint(20, 50)):
                for dx in range(-1, 2):
                    for dy in range(-1, 2): self.set_block(cx+dx, cy+dy, AIR)
                cx = (cx + random.randint(-1, 1)) % WORLD_WIDTH
                cy = min(WORLD_HEIGHT - 5, max(10, cy + random.randint(-1, 1)))

        # Ore Veins
        for _ in range(WORLD_WIDTH // 3): 
            vx, vy = random.randint(0, WORLD_WIDTH - 1), random.randint(15, 60)
            for _ in range(random.randint(6, 12)):
                if self.get_block(vx, vy) == STONE_BLOCK: self.set_block(vx, vy, COAL_BLOCK)
                vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(15, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))

        # Trees
        for x in range(WORLD_WIDTH):
            h = 0
            while self.get_block(x, h) != GRASS_BLOCK:
                h += 1
                if h >= WORLD_HEIGHT: break
            if h < WORLD_HEIGHT and random.random() < 0.15:
                tree_type = "oak" if random.random() < 0.7 else "birch"
                t_h = random.randint(3, 5)
                log_b = OAK_LOG if tree_type == "oak" else BIRCH_LOG
                leaf_b = OAK_LEAVES if tree_type == "oak" else BIRCH_LEAVES
                for th in range(1, t_h + 1): self.set_block(x, h - th, log_b)
                for lx in range(-2, 3):
                    for ly in range(-2, 1):
                        tx, ty = (x + lx) % WORLD_WIDTH, (h - t_h + ly)
                        if self.get_block(tx, ty) == AIR or self.get_block(tx, ty) is None:
                            self.set_block(tx, ty, leaf_b)

    def find_safe_spawn(self, player):
        start_x = int(player.rect.centerx // TILE_SIZE) % WORLD_WIDTH
        for y in range(0, WORLD_HEIGHT - 2):
            if self.get_block(start_x, y) is None and self.get_block(start_x, y+1) is None:
                if self.get_block(start_x, y+2) is not None:
                    player.rect.y = y * TILE_SIZE
                    player.vel_y = 0
                    return
        player.rect.y = 10 * TILE_SIZE

    def get_surrounding_blocks(self, player_rect):
        blocks = []
        p_x, p_y = int(player_rect.x // TILE_SIZE), int(player_rect.y // TILE_SIZE)
        for x_off in range(-2, 3):
            for y_off in range(-2, 4):
                tx, ty = (p_x + x_off) % WORLD_WIDTH, p_y + y_off
                b_type = self.get_block(tx, ty)
                if b_type:
                    if b_type in (AIR, TALL_GRASS, WATER, LADDER, TORCH): continue 
                    if WHEAT_STG0 <= b_type <= WHEAT_STG3: continue
                    bx, by = (p_x + x_off) * TILE_SIZE, ty * TILE_SIZE
                    blocks.append(pygame.Rect(bx, by, TILE_SIZE, TILE_SIZE))
        return blocks

    def draw(self, surface, scroll_x, scroll_y):
        scroll_x, scroll_y = int(scroll_x), int(scroll_y)
        t = self.time % 24000
        if 1000 <= t < 11000: bg_color = (135, 206, 235)
        elif 11000 <= t < 13000 or 23000 <= t <= 24000 or 0 <= t < 1000: bg_color = (80, 60, 100)
        else: bg_color = (15, 15, 30)
        surface.fill(bg_color)
        
        start_cx = int(scroll_x // (CHUNK_SIZE * TILE_SIZE)) - 1
        end_cx = int((scroll_x + SCREEN_WIDTH) // (CHUNK_SIZE * TILE_SIZE)) + 1
        
        torch_glows = []
        for cx in range(start_cx, end_cx + 1):
            lookup_cx = cx % (WORLD_WIDTH // CHUNK_SIZE)
            for cy in range(0, WORLD_HEIGHT // CHUNK_SIZE + 1):
                chunk = self.chunks.get((lookup_cx, cy))
                if chunk:
                    for (tx, ty), b_type in chunk.items():
                        rel_tx = tx % CHUNK_SIZE
                        draw_x = (cx * CHUNK_SIZE + rel_tx) * TILE_SIZE - scroll_x
                        draw_y = ty * TILE_SIZE - scroll_y
                        if -TILE_SIZE < draw_x < SCREEN_WIDTH and -TILE_SIZE < draw_y < SCREEN_HEIGHT:
                            if b_type in (COAL_BLOCK, IRON_BLOCK, DIAMOND_ORE):
                                pygame.draw.rect(surface, COLOR_STONE, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                ore_color = COLOR_COAL if b_type == COAL_BLOCK else (COLOR_IRON if b_type == IRON_BLOCK else COLOR_DIAMOND)
                                pygame.draw.rect(surface, ore_color, (draw_x + 6, draw_y + 8, 8, 8))
                            elif b_type == OAK_LOG: pygame.draw.rect(surface, COLOR_OAK_BROWN, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                            elif b_type == BIRCH_LOG: pygame.draw.rect(surface, COLOR_BIRCH_WHITE, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                            elif b_type == WATER: pygame.draw.rect(surface, (0, 100, 255, 180), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                            elif b_type == TORCH: 
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + TILE_SIZE//2 - 2, draw_y + 12, 4, 20))
                                torch_glows.append((draw_x + TILE_SIZE//2, draw_y + 8))
                            else:
                                color = COLOR_GRASS if b_type == GRASS_BLOCK else (COLOR_DIRT if b_type == DIRT_BLOCK else COLOR_STONE)
                                pygame.draw.rect(surface, color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
        
        # Draw Glow
        for gx, gy in torch_glows:
            glow_surf = pygame.Surface((128, 128), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 200, 50, 40), (64, 64), 64)
            surface.blit(glow_surf, (gx - 64, gy - 64), special_flags=pygame.BLEND_RGBA_ADD)

        # Draw Particles
        self.particles = [p for p in self.particles if p.update()]
        for p in self.particles: p.draw(surface, scroll_x, scroll_y)


def save_game(world, player, filename):
    # Flatten chunks for JSON saving
    flat_data = {}
    for chunk in world.chunks.values():
        for (tx, ty), b_type in chunk.items():
            flat_data[f"{tx},{ty}"] = b_type

    save_data = {
        "world_data": flat_data,
        "block_meta": {f"{k[0]},{k[1]}": v for k, v in world.block_meta.items()},
        "chest_data": {f"{k[0]},{k[1]}": v for k, v in world.chest_data.items()},
        "furnace_data": {f"{k[0]},{k[1]}": v for k, v in world.furnace_data.items()},
        "time": world.time,
        "player": {
            "x": player.rect.x, "y": player.rect.y,
            "health": player.health, "hunger": player.hunger,
            "h_timer": player.hunger_timer, "r_timer": player.regen_timer,
            "inventory": player.inventory, "armor": player.armor,
            "offhand": getattr(player, 'offhand', None),
            "name": getattr(player, "display_name", "Player")
        },
        "remote_players": world.remote_players_data,
        "mobs": [{"x": m.rect.x, "y": m.rect.y, "type": m.m_type, "hp": m.health} for m in world.mobs]
    }
    with open(filename, "w") as f:
        json.dump(save_data, f)
    return True

def load_game(world, player, filename):
    if not os.path.exists(filename): return
    try:
        with open(filename, "r") as f:
            sd = json.load(f)
            # Restore World
            world.chunks = {}
            for k, v in sd["world_data"].items():
                tx, ty = map(int, k.split(','))
                world.set_block(tx, ty, v)
            
            world.block_meta = {tuple(map(int, k.split(','))): v for k, v in sd.get("block_meta", {}).items()}
            world.chest_data = {tuple(map(int, k.split(','))): v for k, v in sd.get("chest_data", {}).items()}
            world.furnace_data = {tuple(map(int, k.split(','))): v for k, v in sd.get("furnace_data", {}).items()}
            world.time = sd.get("time", 0)
            
            # Check for diamonds (legacy/fallback)
            has_diamonds = False
            for chunk in world.chunks.values():
                if DIAMOND_ORE in chunk.values():
                    has_diamonds = True
                    break
            
            if not has_diamonds:
                for _ in range(max(8, WORLD_WIDTH // 24)):
                    vx = random.randint(0, WORLD_WIDTH - 1)
                    vy = random.randint(80, WORLD_HEIGHT - 8)
                    for _ in range(random.randint(3, 6)):
                        if world.get_block(vx, vy) == STONE_BLOCK:
                            world.set_block(vx, vy, DIAMOND_ORE)
                        vx = (vx + random.choice([-1, 0, 1])) % WORLD_WIDTH
                        vy = max(80, min(WORLD_HEIGHT - 1, vy + random.choice([-1, 0, 1])))
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
            player.offhand = p_data.get("offhand", None)
            player.display_name = sanitize_display_name(p_data.get("name", player.display_name))

            # Restore Remote Players
            world.remote_players_data = sd.get("remote_players", {})
            # Restore Mobs
            world.mobs = []
            for m_data in sd.get("mobs", []):
                m = Mob(m_data["x"], m_data["y"], m_data["type"])
                m.health = m_data["hp"]
                world.mobs.append(m)
    except Exception as e:
        print(f"Load error: {e}")

def add_item_to_inventory(player, item_type, count=1, durability=None):
    for slot in player.inventory:
        if slot and slot["type"] == item_type and slot["count"] < 80:
            slot["count"] += count
            if durability is not None and "durability" not in slot:
                slot["durability"] = durability
            return True

    for i in range(36):
        if player.inventory[i] is None:
            player.inventory[i] = {"type": item_type, "count": count}
            if durability is not None:
                player.inventory[i]["durability"] = durability
            return True

    return False

def _can_smelt_in_furnace(item_type):
    return item_type in (
        COBBLESTONE, IRON_BLOCK, RAW_BEEF, RAW_MUTTON, RAW_CHICKEN, RAW_COD,
        RAW_SALMON, OAK_LOG, BIRCH_LOG
    )

def _is_furnace_fuel(item_type):
    return item_type in (
        COAL_BLOCK, COAL_BLOCK_ITEM, COAL, CHARCOAL,
        OAK_LOG, BIRCH_LOG, PLANKS, STICK,
        CRAFTING_TABLE, DOOR, TRAPDOOR
    )

def _move_inventory_stack_to_chest(player, world, inv_idx, chest_slots):
    slot = player.inventory[inv_idx]
    if not slot:
        return False

    for chest_slot in chest_slots:
        if chest_slot and chest_slot["type"] == slot["type"] and chest_slot["count"] < 80:
            transfer = min(slot["count"], 80 - chest_slot["count"])
            chest_slot["count"] += transfer
            slot["count"] -= transfer
            if slot["count"] <= 0:
                player.inventory[inv_idx] = None
            return True

    for i in range(len(chest_slots)):
        if chest_slots[i] is None:
            chest_slots[i] = slot.copy()
            player.inventory[inv_idx] = None
            return True

    return False

def _move_inventory_stack_to_crafting(player, inv_idx, grid):
    slot = player.inventory[inv_idx]
    if not slot:
        return False

    for i in range(len(grid)):
        if grid[i] is None:
            grid[i] = slot.copy()
            player.inventory[inv_idx] = None
            return True

    return False

def _move_inventory_stack_to_furnace(player, inv_idx, f_data):
    slot = player.inventory[inv_idx]
    if not slot:
        return False

    item_type = slot["type"]
    target_key = None
    if _can_smelt_in_furnace(item_type):
        target_key = "input"
    elif _is_furnace_fuel(item_type):
        target_key = "fuel"
    else:
        return False

    target_slot = f_data[target_key]
    if target_slot is None:
        f_data[target_key] = slot.copy()
        player.inventory[inv_idx] = None
        return True

    if target_slot["type"] == item_type and target_slot["count"] < 80:
        transfer = min(slot["count"], 80 - target_slot["count"])
        target_slot["count"] += transfer
        slot["count"] -= transfer
        if slot["count"] <= 0:
            player.inventory[inv_idx] = None
        return True

    return False

def _get_hovered_inventory_slot(mx, my, player):
    inv_x, inv_y = SCREEN_WIDTH // 2 - 200, 360
    for i in range(36):
        if i < 9:
            sx, sy = inv_x + i * 44, inv_y + 150
        else:
            sx, sy = inv_x + ((i - 9) % 9) * 44, inv_y + ((i - 9) // 9) * 44
        if sx <= mx <= sx + 40 and sy <= my <= sy + 40:
            return i
    return None

def teleport_player_to(world, player, x, y):
    # Place the player at the pearl landing spot, then nudge upward if needed.
    player.rect.centerx = int(x) % WORLD_PIXELS
    player.rect.centery = int(y)
    player.vel_y = 0
    player.on_ground = False
    player.highest_y = player.rect.y

    for _ in range(12):
        if any(player.rect.colliderect(block_rect) for block_rect in world.get_surrounding_blocks(player.rect)):
            player.rect.y -= 4
        else:
            break

    if any(player.rect.colliderect(block_rect) for block_rect in world.get_surrounding_blocks(player.rect)):
        world.find_safe_spawn(player)

def start_terminal_chat(net, display_name, on_send=None):
    def chat_loop():
        while True:
            try:
                line = input()
            except EOFError:
                break
            except Exception:
                break

            text = line.strip()
            if not text:
                continue
            if not net or not getattr(net, "running", False):
                break

            payload = {
                "type": "CHAT",
                "name": display_name,
                "text": text
            }
            if net.send(payload):
                print(f"[YOU] {display_name}: {text}")
                if on_send:
                    on_send(display_name, text)
            else:
                print("[CHAT] Failed to send message.")

    threading.Thread(target=chat_loop, daemon=True).start()

def append_chat_message(chat_log, name, text, limit=6):
    chat_log.append((sanitize_display_name(name), str(text)))
    if len(chat_log) > limit:
        del chat_log[:-limit]

def draw_chat_feed(surface, font, chat_log):
    if not chat_log:
        return

    max_width = 290
    lines = []
    for name, text in chat_log[-6:]:
        raw = f"{name}: {text}"
        if font.size(raw)[0] <= max_width - 16:
            lines.append(raw)
            continue

        words = raw.split()
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width - 16:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

    lines = lines[-6:]
    line_h = font.get_height() + 2
    box_w = max_width
    box_h = line_h * len(lines) + 10
    x = SCREEN_WIDTH - box_w - 12
    y = 82

    panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    surface.blit(panel, (x, y))
    pygame.draw.rect(surface, (255, 255, 255), (x, y, box_w, box_h), 1)

    for i, line in enumerate(lines):
        txt = font.render(line, True, COLOR_WHITE)
        surface.blit(txt, (x + 8, y + 5 + i * line_h))

def main():
    print("Enter your username for LAN and local display.")
    player_name = sanitize_display_name(input("Username: ").strip())
    print()
    print("="*30)
    print("   MINECRAFT 2D - MAIN MENU")
    print("="*30)
    print("1. Play Singleplayer")
    print("2. Host LAN Game")
    print("3. Join LAN Game")
    print("4. Exit")
    
    choice = input("\
Select option (1-4): ").strip() or "1"
    mode = "single"
    if choice == "2": mode = "host"
    elif choice == "3": mode = "join"
    elif choice == "4":
        return
    
    world_name = "default"
    if mode != "join":
        # List existing worlds
        saves = [f.name for f in WORLDS_DIR.iterdir() if f.is_file() and f.name.startswith("savegame") and f.name.endswith(".json")]
        if saves:
            print("\
Existing Worlds:")
            for s in saves:
                if s == "savegame.json": name = "default"
                elif s.startswith("savegame_"): name = s[9:-5]
                else: name = s[8:-5]
                print(f" - {name}")
        
        print("\
(Type a world name to load, or 'create' for a new world)")
        world_name = input("Enter world name: ").strip() or "default"
        if world_name.lower() == "create":
            world_name = input("Enter name for new world: ").strip() or f"world_{int(time.time())}"
    else:
        world_name = input("\
Enter World Name OR Host IP Address to Join: ").strip()
        if not world_name: return

    # Resolve filename
    save_filename = None
    candidate_files = [
        WORLDS_DIR / "savegame.json",
        WORLDS_DIR / f"savegame_{world_name}.json",
        WORLDS_DIR / f"savegame{world_name}.json",
    ]
    for candidate in candidate_files:
        if candidate.exists():
            save_filename = candidate
            break
    if save_filename is None:
        save_filename = candidate_files[1] if world_name != "default" else candidate_files[0]
    if mode == "single" and not save_filename.exists():
        existing_saves = sorted(
            p for p in WORLDS_DIR.iterdir()
            if p.is_file() and p.name.startswith("savegame") and p.name.endswith(".json")
        )
        if len(existing_saves) == 1:
            save_filename = existing_saves[0]
    
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    world, player = World(), Player(player_name)
    
    net = None
    discovery_service = None
    remote_players = {}
    chat_log = []

    if mode == "host":
        load_game(world, player, save_filename)
        world.find_safe_spawn(player)
        net = mc_network.GameServer(world_name)
        if net.start(world):
            discovery_service = discovery.DiscoveryBroadcaster(world_name)
            discovery_service.start()
            start_terminal_chat(net, player.display_name, on_send=lambda name, text: append_chat_message(chat_log, name, text))
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                print(f"\n{'='*30}\n[SERVER] HOSTING WORLD '{world_name}'\n[SERVER] YOUR IP ADDRESS: {local_ip}\n{'='*30}\n")
            except:
                pass
        else:
            print("Failed to start server. Switching to singleplayer.")
            mode = "single"
elif mode == "join":
        host_ip = discovery.DiscoveryListener.find_host(world_name, screen=screen, font=font)
        if host_ip:
            net = mc_network.GameClient()
            if net.connect(host_ip):
                print(f"Connected to {world_name}!")
                # Send initial JOIN packet with persistent ID and current data
                net.send({
                    "type": "JOIN", 
                    "p_id": player.persistent_id,
                    "name": player.display_name,
                    "player_data": {
                        "inventory": player.inventory,
                        "health": player.health,
                        "hunger": player.hunger,
                        "armor": player.armor,
                        "offhand": getattr(player, 'offhand', None),
                        "x": player.rect.x,
                        "y": player.rect.y,
                        "name": player.display_name
                    }
                })
                start_terminal_chat(net, player.display_name, on_send=lambda name, text: append_chat_message(chat_log, name, text))
            else:
                screen.fill((50, 0, 0))
                txt = font.render(f"Failed to connect to {host_ip}", True, (255, 255, 255))
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2))
                pygame.display.flip()
                time.sleep(3)
                return
        else:
            screen.fill((50, 0, 0))
            txt = font.render(f"World '{world_name}' not found on LAN.", True, (255, 255, 255))
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2))
            pygame.display.flip()
            time.sleep(3)
            return
    else:
        load_game(world, player, save_filename)
        world.find_safe_spawn(player)

    scroll_x, scroll_y = 0, player.rect.centery - SCREEN_HEIGHT // 2
    target_mode = 0
    auto_save_timer = 0
    save_msg_timer = 0
    save_msg_text = "Game Saved!"
    sleep_anim_timer = 0
    sleep_anim_total = 90
    sleep_wake_timer = 0
    sleep_bed_pos = None

    network_timer = 0
    running = True
    while running:
        screen.fill(COLOR_SKY_BLUE)
        
        if mode == "host":
            active_remote_ids = set()
            for p_id, p_data in world.remote_players_data.items():
                if p_id == "host" or not isinstance(p_data, dict):
                    continue
                active_remote_ids.add(p_id)
                if p_id not in remote_players:
                    remote_players[p_id] = RemotePlayer(
                        p_id,
                        p_data.get("x", player.rect.x),
                        p_data.get("y", player.rect.y),
                        p_data.get("name", p_id),
                    )
                rp = remote_players[p_id]
                rp.x = p_data.get("x", rp.x)
                rp.y = p_data.get("y", rp.y)
                rp.direction = p_data.get("dir", rp.direction)
                if "name" in p_data:
                    rp.display_name = sanitize_display_name(p_data.get("name", rp.display_name))
            for p_id in list(remote_players.keys()):
                if p_id not in active_remote_ids:
                    del remote_players[p_id]
        
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

        # --- Join Loading Screen ---
        if mode == "join" and not world.data:
            screen.fill((15, 15, 30))
            txt = font.render(f"Downloading World '{world_name}'...", True, (255, 255, 255))
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2))
            pygame.display.flip()
            # Process network messages while showing loading
            if net:
                while net.messages:
                    msg = net.messages.pop(0)
                    if msg["type"] == "INIT":
                        new_data = {}
                        for k, v in msg["world_data"].items():
                            try:
                                coords = k.split(',')
                                new_data[(int(coords[0]), int(coords[1]))] = v
                            except: continue
                        world.data = new_data
                        
                        new_meta = {}
                        for k, v in msg.get("block_meta", {}).items():
                            try:
                                coords = k.split(',')
                                new_meta[(int(coords[0]), int(coords[1]))] = v
                            except: continue
                        world.block_meta = new_meta
                        
                        world.time = msg.get("time", 0)
                        
                        # Restore my specific player data from host
                        p_save = msg.get("player_data", {})
                        if p_save:
                            player.rect.x = p_save.get("x", player.rect.x)
                            player.rect.y = p_save.get("y", player.rect.y)
                            player.inventory = p_save.get("inventory", player.inventory)
                            player.armor = p_save.get("armor", player.armor)
                            player.offhand = p_save.get("offhand", player.offhand)
                            player.health = p_save.get("health", player.health)
                            player.display_name = sanitize_display_name(p_save.get("name", player.display_name))
                        
                        world.find_safe_spawn(player)
                        print("World Sync Complete!")
            continue # Don't run game logic until world is loaded

        # --- Network Updates ---
        if net:
            if mode == "host" and hasattr(net, "drain_world_updates"):
                net.drain_world_updates()
            network_timer += 1
            if network_timer >= 3: # Send 20 times per second (at 60fps)
                net.send({
                    "type": "POS",
                    "x": player.rect.x,
                    "y": player.rect.y,
                    "dir": player.direction,
                    "health": player.health,
                    "hunger": player.hunger,
                    "inventory": player.inventory,
                    "armor": player.armor,
                    "offhand": getattr(player, 'offhand', None),
                    "name": player.display_name
                })
                network_timer = 0
            
            # Process received messages
            while net.messages:
                msg = net.messages.pop(0)
                if msg["type"] == "INIT" and mode == "join":
                    # Faster world data loading
                    new_data = {}
                    raw_data = msg["world_data"]
                    for k, v in raw_data.items():
                        try:
                            coords = k.split(',')
                            new_data[(int(coords[0]), int(coords[1]))] = v
                        except: continue
                    world.data = new_data
                    
                    new_meta = {}
                    for k, v in msg.get("block_meta", {}).items():
                        try:
                            coords = k.split(',')
                            new_meta[(int(coords[0]), int(coords[1]))] = v
                        except: continue
                    world.block_meta = new_meta
                    
                    world.time = msg.get("time", 0)
                    world.find_safe_spawn(player)
                    if "player_data" in msg and isinstance(msg["player_data"], dict):
                        player.display_name = sanitize_display_name(msg["player_data"].get("name", player.display_name))
                    print("World Sync Complete!")
                elif msg["type"] == "POS":
                    p_id = msg.get("id", "host")
                    if p_id != getattr(net, 'client_id', None):
                        if p_id not in remote_players:
                            remote_players[p_id] = RemotePlayer(p_id, msg["x"], msg["y"], msg.get("name", p_id))
                        rp = remote_players[p_id]
                        rp.x, rp.y, rp.direction = msg["x"], msg["y"], msg["dir"]
                        if "name" in msg:
                            rp.display_name = sanitize_display_name(msg["name"])
                elif msg["type"] == "HURT":
                    target = msg["target_id"]
                    # Determine if I am the one getting hit
                    am_i_target = False
                    if mode == "join" and getattr(net, 'client_id', None) == target:
                        am_i_target = True
                    elif mode == "host" and target == "host":
                        am_i_target = True
                    
                    if am_i_target:
                        player.take_damage(msg.get("dmg", 1))
                        player.vel_y = -6
                        player.rect.x = (player.rect.x + msg.get("dir", 1) * 20) % WORLD_PIXELS
                elif msg["type"] == "BLOCK":
                    pos = tuple(map(int, msg["pos"].split(',')))
                    if msg["b_type"] is None:
                        if pos in world.data: del world.data[pos]
                        if pos in world.block_meta: del world.block_meta[pos]
                    else:
                        world.data[pos] = msg["b_type"]
                        if "meta" in msg and msg["meta"]:
                            world.block_meta[pos] = msg["meta"]
                elif msg["type"] == "QUIT":
                    p_id = msg["id"]
                    if p_id in remote_players: del remote_players[p_id]
                elif msg["type"] == "CHAT":
                    chat_name = msg.get("name", msg.get("id", "unknown"))
                    chat_text = msg.get("text", "")
                    append_chat_message(chat_log, chat_name, chat_text)
                    print(f"[CHAT] {chat_name}: {chat_text}")

        if sleep_anim_timer > 0:
            sleep_anim_timer -= 1
            if sleep_anim_timer == 0:
                world.time = 0
                save_game(world, player, save_filename)
                save_msg_text = "Slept until morning!"
                save_msg_timer = 120
                sleep_wake_timer = sleep_anim_total
                sleep_bed_pos = None
        elif sleep_wake_timer > 0:
            sleep_wake_timer -= 1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                save_game(world, player, save_filename)
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    if player.show_inventory and (player.active_furnace_pos or player.active_chest_pos or player.show_3x3):
                        mx, my = pygame.mouse.get_pos()
                        hovered_idx = _get_hovered_inventory_slot(mx, my, player)
                        if hovered_idx is not None:
                            moved = False
                            if player.active_furnace_pos:
                                f_data = world.furnace_data[player.active_furnace_pos]
                                moved = _move_inventory_stack_to_furnace(player, hovered_idx, f_data)
                                if moved:
                                    update_furnaces(world)
                            elif player.active_chest_pos:
                                tx, ty = player.active_chest_pos
                                master_pos = (tx, ty)
                                if (tx-1, ty) in world.chest_data:
                                    master_pos = (tx-1, ty)
                                c_slots = world.chest_data.get(master_pos, [])
                                moved = _move_inventory_stack_to_chest(player, world, hovered_idx, c_slots)
                            elif player.show_3x3:
                                moved = _move_inventory_stack_to_crafting(player, hovered_idx, player.crafting_3x3)
                                if moved:
                                    update_crafting(player)
                            else:
                                moved = _move_inventory_stack_to_crafting(player, hovered_idx, player.crafting_grid)
                                if moved:
                                    update_crafting(player)
                            if moved:
                                continue
                    target_mode = (target_mode + 1) % 5
                if event.key == pygame.K_q: 
                    if save_game(world, player, save_filename):
                        save_msg_timer = 120
                        save_msg_text = "Game Saved!"
                    running = False
                if event.key == pygame.K_r: player.respawn()
                if event.key == pygame.K_e and sleep_anim_timer == 0 and sleep_wake_timer == 0: 
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
                        save_game(world, player, save_filename)
                        running = False
                
                if event.key == pygame.K_u: # Emergency Unlock Key
                    print("[DEBUG] Force Unlocking Player...")
                    player.show_inventory = False
                    player.show_3x3 = False
                    player.active_furnace_pos = None
                    player.active_chest_pos = None
                    world.find_safe_spawn(player)
                    sleep_anim_timer = 0
                    sleep_wake_timer = 0
                
                if not player.show_inventory and sleep_anim_timer == 0 and sleep_wake_timer == 0:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                        player.selected_slot = event.key - pygame.K_1
                    if event.key == pygame.K_z:
                        slot = player.inventory[player.selected_slot]
                        if slot:
                            drop = DroppedItem(player.rect.centerx, player.rect.centery, slot["type"], 1, slot.get("durability"))
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
                        drop = DroppedItem(player.rect.centerx, player.rect.centery, player.held_item["type"], 1, player.held_item.get("durability"))
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
                    if world.get_block(tx, ty) is not None:
                        player.breaking_block = (tx, ty)
                        break
            
            if player.breaking_block:
                tx, ty = player.breaking_block
                b_type = world.get_block(tx, ty)
                
                # Tool Efficiency
                tool = player.inventory[player.selected_slot]
                t_type = tool["type"] if tool else None
                speed = 1.0
                if b_type == DIAMOND_ORE and t_type not in (I_PICK, D_PICK):
                    speed = 0.0
                elif t_type in (W_PICK, S_PICK, I_PICK, D_PICK) and b_type in (STONE_BLOCK, COAL_BLOCK, IRON_BLOCK, DIAMOND_ORE):
                    if t_type == W_PICK: speed = 3.0
                    elif t_type == S_PICK: speed = 6.0
                    elif t_type == I_PICK: speed = 10.0
                    else: speed = 12.0 # Diamond
                elif t_type in (W_AXE, S_AXE, I_AXE, D_AXE) and b_type in (OAK_LOG, BIRCH_LOG, PLANKS, CRAFTING_TABLE, FURNACE, IRON_BLOCK_PROD):
                    if t_type == W_AXE: speed = 3.0
                    elif t_type == S_AXE: speed = 6.0
                    elif t_type == I_AXE: speed = 10.0
                    else: speed = 12.0 # Diamond
                elif t_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL, D_SHOVEL) and b_type in (GRASS_BLOCK, DIRT_BLOCK):
                    if t_type == W_SHOVEL: speed = 3.0
                    elif t_type == S_SHOVEL: speed = 6.0
                    elif t_type == I_SHOVEL: speed = 10.0
                    else: speed = 12.0 # Diamond
                
                hardness = BLOCK_HARDNESS.get(b_type, 1.0)
                if b_type == TALL_GRASS: hardness = 0.01 # Instant break
                player.breaking_progress += (1.0 / (60 * hardness)) * speed
                
                if player.breaking_progress >= 1.0:
                    player.last_action_time = now
                    # Break ALL valid targets that exist
                    for bx, by in valid_targets:
                        if world.get_block(bx, by) is not None:
                            drop_type = world.get_block(bx, by)
                            to_remove = [(bx, by)]
                            if drop_type in (DOOR_TOP, DOOR_OPEN_TOP):
                                base_pos = (bx, by + 1)
                                if base_pos in world.data:
                                    to_remove.append(base_pos)
                                drop_type = DOOR
                            elif drop_type in (DOOR, DOOR_OPEN):
                                top_pos = (bx, by - 1)
                                if top_pos in world.data:
                                    to_remove.append(top_pos)
                                drop_type = DOOR
                            elif drop_type == BED_RIGHT:
                                left_pos = ((bx - 1) % WORLD_WIDTH, by)
                                if left_pos in world.data:
                                    to_remove.append(left_pos)
                                drop_type = BED
                            elif drop_type == BED:
                                right_pos = ((bx + 1) % WORLD_WIDTH, by)
                                if right_pos in world.data:
                                    to_remove.append(right_pos)
                                drop_type = BED
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
                            elif drop_type == DIAMOND_ORE: drop_type = DIAMOND
                            elif drop_type == STONE_BLOCK: drop_type = COBBLESTONE
                            
                            for pos in to_remove:
                                if pos in world.data:
                                    del world.data[pos]
                                    if pos in world.block_meta: del world.block_meta[pos]
                                    if net:
                                        net.send({"type": "BLOCK", "pos": f"{pos[0]},{pos[1]}", "b_type": None})
                            
                            if drop_type and drop_type not in (OAK_LEAVES, BIRCH_LEAVES):
                                world.dropped_items.append(DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, drop_type))
                        
                        # Durability Loss
                        if tool and tool["type"] >= 100:
                            if "durability" not in tool:
                                # Fallback: add durability if missing (legacy items)
                                tool["durability"] = MAX_DURABILITY.get(tool["type"], 60)
                            
                            tool["durability"] -= 1
                            if tool["durability"] <= 0:
                                player.inventory[player.selected_slot] = None
                                
                    player.breaking_block = None
                    player.breaking_progress = 0.0

        elif m_btns[2] and now - player.last_action_time > 120:
            # --- Placing/Interacting Logic ---
            action_taken = False
            slot = player.inventory[player.selected_slot]

            # Ender Pearl: throw toward the mouse cursor and teleport on landing.
            if slot and slot["type"] == ENDER_PEARL:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                world.projectiles.append(ThrownPearl(player.rect.centerx, player.rect.centery, target_x, target_y))
                slot["count"] -= 1
                if slot["count"] <= 0:
                    player.inventory[player.selected_slot] = None
                player.last_action_time = now
                action_taken = True
            elif slot and slot["type"] == EGG:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                world.egg_projectiles.append(EggShot(player.rect.centerx, player.rect.centery, target_x, target_y))
                slot["count"] -= 1
                if slot["count"] <= 0:
                    player.inventory[player.selected_slot] = None
                player.last_action_time = now
                action_taken = True
            elif slot and slot["type"] == BOW:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                if slot.get("durability", 0) > 0:
                    start_x = (player.rect.centerx + (player.direction * 16)) % WORLD_PIXELS
                    start_y = player.rect.centery - 4
                    world.arrows.append(ArrowShot(start_x, start_y, target_x, target_y))
                    slot["durability"] -= 1
                    if slot["durability"] <= 0:
                        player.inventory[player.selected_slot] = None
                    player.last_action_time = now
                    action_taken = True
            elif slot and slot["type"] == FISHING_ROD:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                if slot.get("durability", 0) > 0 and getattr(player, "fishing_hook", None) is None:
                    hook = FishingHook(player, player.rect.centerx, player.rect.centery - 4, target_x, target_y)
                    player.fishing_hook = hook
                    world.fishing_hooks.append(hook)
                    slot["durability"] -= 1
                    if slot["durability"] <= 0:
                        player.inventory[player.selected_slot] = None
                    player.last_action_time = now
                    action_taken = True

            for tx, ty in ([] if action_taken else valid_targets):
                if world.get_block(tx, ty) is not None and world.get_block(tx, ty) == BOAT:
                    player.rect.centerx = tx * TILE_SIZE + TILE_SIZE // 2
                    player.rect.bottom = ty * TILE_SIZE
                    player.vel_y = 0
                    player.on_ground = True
                    player.highest_y = player.rect.y
                    action_taken = True
                    break

                # Boat: place without replacing terrain, then allow right-click to mount it.
                if slot and slot["type"] == BOAT:
                    boat_pos = None
                    if world.get_block(tx, ty) is None:
                        boat_pos = (tx, ty)
                    elif ty > 0 and world.get_block(tx, ty - 1) is None:
                        boat_pos = (tx, ty - 1)

                    if boat_pos is not None:
                        world.data[boat_pos] = BOAT
                        if net:
                            net.send({"type": "BLOCK", "pos": f"{boat_pos[0]},{boat_pos[1]}", "b_type": BOAT})
                        slot["count"] -= 1
                        if slot["count"] <= 0:
                            player.inventory[player.selected_slot] = None
                        action_taken = True
                        break

                # Eating / Drinking
                if slot and slot["type"] in (BREAD, RAW_BEEF, STEAK, ROTTEN_FLESH, RAW_MUTTON, COOKED_MUTTON, RAW_COD, COOKED_COD, RAW_SALMON, COOKED_SALMON, MILK_BUCKET):
                    if slot["type"] == MILK_BUCKET or player.hunger < player.max_hunger:
                        fill = {BREAD: 5, RAW_BEEF: 3, STEAK: 8, ROTTEN_FLESH: 4, RAW_MUTTON: 3, COOKED_MUTTON: 7, RAW_COD: 2, COOKED_COD: 5, RAW_SALMON: 2, COOKED_SALMON: 6, MILK_BUCKET: 2}[slot["type"]]
                        player.hunger = min(player.max_hunger, player.hunger + fill)
                        if slot["type"] == MILK_BUCKET:
                            slot["type"] = BUCKET # Return empty bucket
                        else:
                            slot["count"] -= 1
                        if slot["count"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                if slot and slot["type"] in (RAW_CHICKEN, COOKED_CHICKEN):
                    if player.hunger < player.max_hunger:
                        fill = {RAW_CHICKEN: 2, COOKED_CHICKEN: 5}[slot["type"]]
                        player.hunger = min(player.max_hunger, player.hunger + fill)
                        slot["count"] -= 1
                        if slot["count"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                
                # Hoe Interaction (Tilling)
                if slot and slot["type"] in (W_HOE, S_HOE, I_HOE):
                    if world.get_block(tx, ty) is not None and world.get_block(tx, ty) in (GRASS_BLOCK, DIRT_BLOCK):
                        world.set_block(tx, ty, FARMLAND)
                        slot["durability"] -= 1
                        if slot["durability"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                # Planting Seeds
                if slot and slot["type"] == SEEDS:
                    if world.get_block(tx, ty) is not None and world.get_block(tx, ty) == FARMLAND:
                        if world.get_block(tx, ty - 1) is None:
                            world.set_block(tx, ty - 1, WHEAT_STG0)
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
                if world.get_block(tx, ty) is not None and world.get_block(tx, ty) == CRAFTING_TABLE:
                    player.show_inventory = True
                    player.show_3x3 = True
                    action_taken = True
                    break # Only open one table
                elif world.get_block(tx, ty) is not None and world.get_block(tx, ty) in (FURNACE, SMOKER, BLAST_FURNACE):
                    if (tx, ty) not in world.furnace_data:
                        world.furnace_data[(tx, ty)] = {"input": None, "fuel": None, "output": None, "cook_time": 0.0, "fuel_time": 0.0}
                    player.show_inventory = True
                    player.show_3x3 = False
                    player.active_furnace_pos = (tx, ty)
                    player.active_chest_pos = None
                    action_taken = True
                    break
                elif world.get_block(tx, ty) is not None and world.get_block(tx, ty) == CHEST:
                    player.show_inventory = True
                    player.show_3x3 = False
                    player.active_furnace_pos = None
                    player.active_chest_pos = (tx, ty)
                    # Check for neighbor chest
                    is_large = False
                    master_pos = (tx, ty)
                    if world.get_block(tx-1, ty) is not None and world.get_block(tx-1, ty) == CHEST:
                        is_large = True
                        master_pos = (tx-1, ty)
                    elif world.get_block(tx+1, ty) is not None and world.get_block(tx+1, ty) == CHEST:
                        is_large = True
                    
                    player.active_chest_is_large = is_large
                    if master_pos not in world.chest_data:
                        size = 54 if is_large else 27
                        world.chest_data[master_pos] = [None] * size
                    action_taken = True
                    break
                elif world.get_block(tx, ty) is not None and world.get_block(tx, ty) in (DOOR, DOOR_TOP, DOOR_OPEN, DOOR_OPEN_TOP, TRAPDOOR, TRAPDOOR_OPEN, FENCE_GATE, FENCE_GATE_OPEN, BED, BED_RIGHT):
                    b_type = world.get_block(tx, ty)
                    if b_type in (DOOR, DOOR_TOP):
                        base = (tx, ty) if b_type == DOOR else (tx, ty + 1)
                        top = (base[0], base[1] - 1)
                        world.data[base] = DOOR_OPEN
                        world.data[top] = DOOR_OPEN_TOP
                    elif b_type in (DOOR_OPEN, DOOR_OPEN_TOP):
                        base = (tx, ty) if b_type == DOOR_OPEN else (tx, ty + 1)
                        top = (base[0], base[1] - 1)
                        world.data[base] = DOOR
                        world.data[top] = DOOR_TOP
                    elif b_type == TRAPDOOR: world.set_block(tx, ty, TRAPDOOR_OPEN)
                    elif b_type == TRAPDOOR_OPEN: world.set_block(tx, ty, TRAPDOOR)
                    elif b_type == FENCE_GATE: world.set_block(tx, ty, FENCE_GATE_OPEN)
                    elif b_type == FENCE_GATE_OPEN: world.set_block(tx, ty, FENCE_GATE)
                    elif b_type in (BED, BED_RIGHT):
                        sleep_anim_timer = sleep_anim_total
                        sleep_bed_pos = (tx, ty)
                        action_taken = True
                        break
                    action_taken = True
                    break
                elif world.get_block(tx, ty) is None:
                    slot = player.inventory[player.selected_slot]
                    if slot is not None and slot["type"] == DOOR:
                        if ty > 0 and world.get_block(tx, ty - 1) is None:
                            bottom_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            top_rect = pygame.Rect(tx * TILE_SIZE, (ty - 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            p_placement_rect = player.rect.inflate(-6, -6)
                            p_placement_rect.x %= WORLD_PIXELS
                            if not p_placement_rect.colliderect(bottom_rect) and not p_placement_rect.colliderect(top_rect):
                                world.set_block(tx, ty, slot["type"])
                                world.set_block(tx, ty - 1, DOOR_TOP)
                                slot["count"] -= 1
                                action_taken = True
                                if slot["count"] <= 0:
                                    player.inventory[player.selected_slot] = None
                                    break
                    elif slot is not None and slot["type"] == BED:
                        bed_dx = 1 if player.direction > 0 else -1
                        tx2 = (tx + bed_dx) % WORLD_WIDTH
                        if world.get_block(tx2, ty) is None:
                            bed_rect_1 = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            bed_rect_2 = pygame.Rect(tx2 * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            p_placement_rect = player.rect.inflate(-6, -6)
                            p_placement_rect.x %= WORLD_PIXELS
                            if not p_placement_rect.colliderect(bed_rect_1) and not p_placement_rect.colliderect(bed_rect_2):
                                world.set_block(tx, ty, BED)
                                world.set_block(tx2, ty, BED_RIGHT)
                                if net:
                                    net.send({"type": "BLOCK", "pos": f"{tx},{ty}", "b_type": BED})
                                    net.send({"type": "BLOCK", "pos": f"{tx2},{ty}", "b_type": BED_RIGHT})
                                slot["count"] -= 1
                                action_taken = True
                                if slot["count"] <= 0:
                                    player.inventory[player.selected_slot] = None
                                    break
                    elif slot is not None and slot["type"] in PLACEABLE_BLOCKS:
                        tr = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        p_placement_rect = player.rect.inflate(-6, -6)
                        p_placement_rect.x %= WORLD_PIXELS
                        if not p_placement_rect.colliderect(tr): 
                            world.set_block(tx, ty, slot["type"])
                            if slot["type"] in (W_STAIRS, C_STAIRS, SS_STAIRS, I_STAIRS):
                                world.block_meta[(tx, ty)] = {"facing": player.direction}
                            elif slot["type"] == TORCH:
                                wall_facing = None
                                left_block = world.get_block((tx - 1) % WORLD_WIDTH, ty)
                                right_block = world.get_block((tx + 1) % WORLD_WIDTH, ty)
                                if left_block and left_block != AIR and left_block != WATER:
                                    wall_facing = 1
                                elif right_block and right_block != AIR and right_block != WATER:
                                    wall_facing = -1
                                if wall_facing is not None:
                                    world.block_meta[(tx, ty)] = {"facing": wall_facing}
                                elif world.get_block(tx, ty + 1) is not None and world.get_block(tx, ty + 1) not in (AIR, WATER, TALL_GRASS):
                                    world.block_meta[(tx, ty)] = {"facing": 0}
                            
                            if net:
                                net.send({"type": "BLOCK", "pos": f"{tx},{ty}", "b_type": slot["type"], "meta": world.block_meta.get((tx, ty))})
                            if slot["type"] == CHEST:
                                # New chest placed - check if it merges with a neighbor
                                if world.get_block(tx-1, ty) is not None and world.get_block(tx-1, ty) == CHEST:
                                    # Merge with left
                                    old_data = world.chest_data.get((tx-1, ty), [None]*27)
                                    world.chest_data[(tx-1, ty)] = old_data + [None]*27
                                elif world.get_block(tx+1, ty) is not None and world.get_block(tx+1, ty) == CHEST:
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
            if t_type in (W_SWORD, S_SWORD, I_SWORD, D_SWORD): dmg = 4 if t_type == W_SWORD else (5 if t_type == S_SWORD else (7 if t_type == I_SWORD else 8))
            elif t_type in (W_AXE, S_AXE, I_AXE, D_AXE): dmg = 3 if t_type == W_AXE else (4 if t_type == S_AXE else (6 if t_type == I_AXE else 7))
            elif t_type in (W_PICK, S_PICK, I_PICK, D_PICK): dmg = 2 if t_type == W_PICK else (3 if t_type == S_PICK else (5 if t_type == I_PICK else 6))
            elif t_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL, D_SHOVEL): dmg = 1 if t_type == W_SHOVEL else (2 if t_type == S_SHOVEL else (4 if t_type == I_SHOVEL else 5))
            elif t_type in (W_HOE, S_HOE, I_HOE, D_HOE): dmg = 1 if t_type == W_HOE else (1 if t_type == S_HOE else (2 if t_type == I_HOE else 3))
            crit_bonus = player.jump_attack_timer > 0 or player.vel_y != 0

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
                            mob.health -= dmg * (1.5 if crit_bonus else 1.0)
                            mob.hurt_timer = 10
                            mob.vel_y = -6 # Knockback
                            mob.rect.x = (mob.rect.x + player.direction * 25) % WORLD_PIXELS
                            if mob.m_type == "enderman":
                                mob.angry = True
                                mob.teleport_timer = 0
                            hit_any = True

                # Combat with Remote Players (PvP)
                if net:
                    for rp_id, rp in remote_players.items():
                        dx = abs(player.rect.centerx - rp.x)
                        if dx > WORLD_PIXELS / 2: dx = WORLD_PIXELS - dx
                        dy = abs(player.rect.centery - rp.y)
                        
                        if dx < 60 and dy < player.rect.height:
                            rel_x = (rp.x - player.rect.centerx)
                            if rel_x > WORLD_PIXELS / 2: rel_x -= WORLD_PIXELS
                            if rel_x < -WORLD_PIXELS / 2: rel_x += WORLD_PIXELS
                            
                            if (player.direction > 0 and rel_x > 0) or (player.direction < 0 and rel_x < 0):
                                net.send({"type": "HURT", "target_id": rp_id, "dmg": dmg * (1.5 if crit_bonus else 1.0), "dir": player.direction})
                                hit_any = True
                
                if hit_any:
                    player.last_action_time = now
                    # Durability Loss for tools
                    if tool and tool["type"] >= 100:
                        tool["durability"] -= 1
                        if tool["durability"] <= 0:
                            player.inventory[player.selected_slot] = None

        sleeping_visual = sleep_anim_timer > 0 or sleep_wake_timer > 0
        if not sleeping_visual:
            player.update(world)
            update_furnaces(world)
            world.time = (world.time + 1) % 24000
            
            # Mob Spawning
            t = world.time
            # Zombies at Night
            if (t > 14000 or t < 1000) and len([m for m in world.mobs if m.m_type == "zombie"]) < 6:
                if random.random() < 0.005:
                    world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "zombie"))
            # Endermen at Night
            if (t > 14000 or t < 1000) and len([m for m in world.mobs if m.m_type == "enderman"]) < 2:
                if random.random() < 0.0008:
                    world.mobs.append(Mob((player.rect.x + random.choice([-350, 350])) % WORLD_PIXELS, 50, "enderman"))
            # Spiders at Night
            if (t > 14000 or t < 1000) and len([m for m in world.mobs if m.m_type == "spider"]) < 4:
                if random.random() < 0.004:
                    world.mobs.append(Mob((player.rect.x + random.choice([-450, 450])) % WORLD_PIXELS, 50, "spider"))
            # Cows during Day
            if (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "cow"]) < 4:
                if random.random() < 0.003:
                    world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "cow"))
            if (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "sheep"]) < 4:
                if random.random() < 0.003:
                    world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "sheep"))
            if (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "chicken"]) < 5:
                if random.random() < 0.004:
                    world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "chicken"))
                
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
                    elif mob.m_type == "enderman":
                        spawn_drop(ENDER_PEARL, random.randint(1, 2))
                    elif mob.m_type == "sheep":
                        spawn_drop(WOOL, random.randint(1, 2))
                        spawn_drop(RAW_MUTTON, random.randint(1, 3))
                    elif mob.m_type == "chicken":
                        spawn_drop(RAW_CHICKEN, random.randint(1, 2))
                        if random.random() < 0.65:
                            spawn_drop(FEATHER, random.randint(1, 2))
                    elif mob.m_type == "spider":
                        spawn_drop(STRING_ITEM, random.randint(1, 3))
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
                # Update remote player data before saving (Host only)
                if mode == "host" and net:
                    for p_id, p_data in net.player_data.items():
                        if p_id != "host":
                            world.remote_players_data[p_id] = p_data
                elif mode == "join" and net:
                    # Sync my own data to the host so it can be saved
                    net.send({
                        "type": "SYNC", 
                        "inventory": player.inventory,
                        "health": player.health,
                        "hunger": player.hunger,
                        "armor": player.armor,
                        "offhand": getattr(player, 'offhand', None),
                        "x": player.rect.x,
                        "y": player.rect.y,
                        "name": player.display_name
                    })

                save_game(world, player, save_filename)
                auto_save_timer = 0
                save_msg_timer = 120 # Show for 2 seconds
                save_msg_text = "Game Saved!"
                
        world.draw(screen, scroll_x, scroll_y)

        # Update and Draw Thrown Pearls
        for pearl in world.projectiles[:]:
            landed, land_pos = pearl.update(world)
            pearl.draw(screen, scroll_x, scroll_y)
            if landed:
                if land_pos is not None:
                    teleport_player_to(world, player, land_pos[0], land_pos[1])
                world.projectiles.remove(pearl)

        # Update and Draw Eggs
        for egg in world.egg_projectiles[:]:
            if egg.update(world):
                world.egg_projectiles.remove(egg)
            else:
                egg.draw(screen, scroll_x, scroll_y)

        # Update and Draw Arrows
        for arrow in world.arrows[:]:
            if arrow.update(world):
                world.arrows.remove(arrow)
            else:
                arrow.draw(screen, scroll_x, scroll_y)

        # Update and Draw Fishing Hooks
        for hook in world.fishing_hooks[:]:
            if hook.update(world):
                if hook in world.fishing_hooks:
                    world.fishing_hooks.remove(hook)
            else:
                hook.draw(screen, scroll_x, scroll_y)

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
                            if hasattr(di, 'durability') and di.durability is not None:
                                player.inventory[i]["durability"] = di.durability
                            added = True
                            break
                if added:
                    world.dropped_items.remove(di)

        for mob in world.mobs:
            mob.draw(screen, scroll_x, scroll_y)
            
        # Draw Remote Players
        for rp in remote_players.values():
            rp.draw(screen, scroll_x, scroll_y, font)
            
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
                draw_nameplate(screen, font, player.display_name, px_draw + player.rect.width / 2, py_draw)
                
                if player.blocking:
                    # Draw Shield in front
                    s_off = 18 if player.direction > 0 else -6
                    pygame.draw.rect(screen, (120, 80, 40), (px_draw + s_off, py_draw + 10, 12, 30))
                    pygame.draw.rect(screen, (200, 200, 200), (px_draw + s_off, py_draw + 10, 12, 30), 1)

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
            
            # Draw Offhand Slot
            ox, oy = inv_x - 50, inv_y + 4 * 44 + 10
            pygame.draw.rect(screen, (80, 80, 80), (ox, oy, 40, 40))
            pygame.draw.rect(screen, (50, 50, 50), (ox, oy, 40, 40), 2)
            if player.offhand:
                draw_block_icon(screen, player.offhand["type"], ox + 4, oy + 4, 32, font)
                if "durability" in player.offhand:
                    max_d = MAX_DURABILITY.get(player.offhand["type"], 1)
                    ratio = player.offhand["durability"] / max_d
                    pygame.draw.rect(screen, (0,0,0), (ox + 4, oy + 32, 32, 4))
                    pygame.draw.rect(screen, (int(255*(1-ratio)), int(255*ratio), 0), (ox + 4, oy + 32, int(32 * ratio), 4))
            else:
                # Ghost Shield Icon
                ghost_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                draw_block_icon(ghost_surf, SHIELD, 0, 0, 32, font)
                ghost_surf.fill((60, 60, 60, 150), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(ghost_surf, (ox + 4, oy + 4))

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

            # --- Draw Coordinates ---
            cx, cy = player.rect.centerx // TILE_SIZE, player.rect.centery // TILE_SIZE
            coord_text = font.render(f"X: {cx}, Y: {cy}", True, COLOR_WHITE)
            screen.blit(coord_text, (SCREEN_WIDTH - coord_text.get_width() - 20, 20))
            
            # --- Save Message ---
            if save_msg_timer > 0:
                msg = font.render(save_msg_text, True, (100, 255, 100))
                screen.blit(msg, (SCREEN_WIDTH - msg.get_width() - 20, 45))
                save_msg_timer -= 1

            draw_chat_feed(screen, font, chat_log)
            
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

        if sleep_anim_timer > 0 or sleep_wake_timer > 0:
            sleep_progress = 1.0 - (sleep_anim_timer / sleep_anim_total if sleep_anim_timer > 0 else sleep_wake_timer / sleep_anim_total)
            if sleep_anim_timer > 0:
                sleep_alpha = int(220 * sleep_progress)
            else:
                sleep_alpha = int(220 * (sleep_wake_timer / sleep_anim_total))
            sleep_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            sleep_overlay.fill((10, 10, 20, sleep_alpha))
            screen.blit(sleep_overlay, (0, 0))

            if sleep_bed_pos is not None and sleep_anim_timer > 0:
                bx, by = sleep_bed_pos
                bed_x = bx * TILE_SIZE - int(scroll_x)
                bed_y = by * TILE_SIZE - int(scroll_y)
                for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
                    dx = bed_x + offset
                    if -TILE_SIZE < dx < SCREEN_WIDTH and -TILE_SIZE < bed_y < SCREEN_HEIGHT:
                        z_txt = font.render("Zzz", True, (220, 220, 255))
                        screen.blit(z_txt, (dx + 4, bed_y - 20))
                        break

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
