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
WORLD_WIDTH = 1024
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
COLOR_LEAVES_G = (9, 127, 2)
COLOR_LEAVES_B = (88, 115, 59)
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


def _rect_overlaps_water(rect, world):
    left = rect.left // TILE_SIZE
    right = (rect.right - 1) // TILE_SIZE
    top = rect.top // TILE_SIZE
    bottom = (rect.bottom - 1) // TILE_SIZE
    for ty in range(top, bottom + 1):
        for tx in range(left, right + 1):
            if world.get_block(tx % WORLD_WIDTH, ty) == WATER:
                return True
    return False


BASE_DIR = Path(__file__).resolve().parent
WORLDS_DIR = BASE_DIR / "worlds"
WORLDS_DIR.mkdir(exist_ok=True)

def play_loading_screens(screen):
    fade_duration = 0.65
    image_duration = 3.0
    clock = pygame.time.Clock()
    screen.fill((0, 0, 0))
    pygame.display.flip()

    for image_path in (BASE_DIR.parent.parent / "loading1pygame.png", BASE_DIR.parent.parent / "loading2.png"):
        image = pygame.image.load(str(image_path))
        image_width, image_height = image.get_size()
        scale = min(SCREEN_WIDTH / image_width, SCREEN_HEIGHT / image_height)
        scaled_size = (int(image_width * scale), int(image_height * scale))
        image = pygame.transform.smoothscale(image, scaled_size)
        image_rect = image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        elapsed = 0.0

        while elapsed < image_duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            screen.fill((0, 0, 0))
            screen.blit(image, image_rect)
            fade_in = min(1.0, elapsed / fade_duration)
            fade_out = min(1.0, (image_duration - elapsed) / fade_duration)
            opacity = int(255 * (1.0 - min(fade_in, fade_out)))
            if opacity:
                fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                fade.fill((0, 0, 0))
                fade.set_alpha(opacity)
                screen.blit(fade, (0, 0))
            pygame.display.flip()
            elapsed += clock.tick(60) / 1000

    return True

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
GLASS = 35
GLASS_PANE = 36
VILLAGE_GENERATION_VERSION = 12
VILLAGE_FOOTPRINT_WIDTH = 128
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
SAND_BLOCK = 87
CACTUS = 88
DEAD_BUSH = 89
BEDROCK = 90
SADDLE = 91
BOAT = 66
LADDER = 67
DIAMOND_ORE = 68
DIAMOND = 69
DOOR_TOP = 70
DOOR_OPEN_TOP = 71
BED_RIGHT = 72
RED_DYE = 188
RED_BED = 189
RED_BED_RIGHT = 190
YELLOW_DYE = 191
YELLOW_BED = 192
YELLOW_BED_RIGHT = 193
ORANGE_DYE = 194
ORANGE_BED = 195
ORANGE_BED_RIGHT = 196
GREEN_DYE = 197
GREEN_BED = 198
GREEN_BED_RIGHT = 199
CORNFLOWER = 200
BLUE_DYE = 201
BLUE_BED = 202
BLUE_BED_RIGHT = 203
PURPLE_DYE = 204
PURPLE_BED = 205
PURPLE_BED_RIGHT = 206
CYAN_DYE = 207
CYAN_BED = 208
CYAN_BED_RIGHT = 209
FIRE = 210
BED_BLOCKS = (BED, BED_RIGHT, RED_BED, RED_BED_RIGHT, YELLOW_BED, YELLOW_BED_RIGHT, ORANGE_BED, ORANGE_BED_RIGHT, GREEN_BED, GREEN_BED_RIGHT, BLUE_BED, BLUE_BED_RIGHT, PURPLE_BED, PURPLE_BED_RIGHT, CYAN_BED, CYAN_BED_RIGHT)
BED_ITEMS = (BED, RED_BED, YELLOW_BED, ORANGE_BED, GREEN_BED, BLUE_BED, PURPLE_BED, CYAN_BED)
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
DIORITE = 92
GRANITE = 93
GRAVEL = 94
ANDESITE = 95
DEEPSLATE = 96
COPPER_ORE = 97
COPPER_INGOT = 98
FLINT = 99
CARROT_STG0 = 152
CARROT_STG1 = 153
CARROT_STG2 = 154
CARROT_STG3 = 155
POTATO_STG0 = 156
POTATO_STG1 = 157
POTATO_STG2 = 158
POTATO_STG3 = 159
BEETROOT_STG0 = 160
BEETROOT_STG1 = 161
BEETROOT_STG2 = 162
BEETROOT_STG3 = 163
CARROT_ITEM = 164
POTATO_ITEM = 165
POISONOUS_POTATO = 166
BEETROOT_ITEM = 167
BEETROOT_SEEDS = 168
APPLE = 169
OAK_SAPLING = 170
BUNDLE = 171
EMERALD = 172
DANDELION = 173
GOLD_NUGGET = 174
BOOK = 175
POPPY = 176
OBSIDIAN = 177
GOLD_INGOT = 178
COPPER_SPEAR = 179
IRON_SPEAR = 180
COPPER_HORSE_ARMOR = 181
IRON_HORSE_ARMOR = 182
GOLDEN_HORSE_ARMOR = 183
DIAMOND_HORSE_ARMOR = 184
LEATHER = 185
LEATHER_HORSE_ARMOR = 186
BIRCH_SAPLING = 187

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
FLINT_STEEL = 140
SHEARS = 141
WATER_BUCKET = 142
ROCKET_LAUNCHER = 143

BLOCK_HARDNESS = {
    GRASS_BLOCK: 0.1, DIRT_BLOCK: 0.5, STONE_BLOCK: 1.5, 
    COAL_BLOCK: 3.0, IRON_BLOCK: 3.0, DIAMOND_ORE: 4.0, OAK_LOG: 2.0, BIRCH_LOG: 2.0,
    OAK_LEAVES: 0.2, BIRCH_LEAVES: 0.2, OAK_SAPLING: 0.1, BIRCH_SAPLING: 0.1,
    PLANKS: 2.0, CRAFTING_TABLE: 2.5,
    FURNACE: 3.5, SMOKER: 3.5, BLAST_FURNACE: 3.5, COBBLESTONE: 2.0, SMOOTH_STONE: 2.0, IRON_BLOCK_PROD: 5.0,
    CHEST: 2.5, HAY_BALE: 0.5, FARMLAND: 0.6, FENCE: 2.0, FENCE_GATE: 2.0,
    DOOR: 3.0, TRAPDOOR: 3.0, W_STAIRS: 2.0, C_STAIRS: 2.0, SS_STAIRS: 2.0,
    W_SLAB: 2.0, C_SLAB: 2.0, SS_SLAB: 2.0, LADDER: 0.4, TORCH: 0.1,
    SAND_BLOCK: 0.5, CACTUS: 0.4, DEAD_BUSH: 0.1, FIRE: 0.1,
    POPPY: 0.1, DANDELION: 0.1, CORNFLOWER: 0.1,
    DIORITE: 1.5, GRANITE: 1.5, GRAVEL: 0.6, ANDESITE: 1.5,
    DEEPSLATE: 3.0, COPPER_ORE: 3.0, GLASS: 0.3, GLASS_PANE: 0.3
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
    TALL_GRASS: "Tall Grass", SEEDS: "Seeds",
    FARMLAND: "Farmland", WHEAT_ITEM: "Wheat",
    BREAD: "Bread", HAY_BALE: "Hay Bale",
    CHEST: "Chest",
    RAW_BEEF: "Raw Beef", STEAK: "Steak",
    ROTTEN_FLESH: "Rotten Flesh", BONE: "Bone",
    FENCE: "Fence", FENCE_GATE: "Fence Gate",
    FENCE_GATE_OPEN: "Open Fence Gate", DOOR_OPEN: "Open Door",
    TRAPDOOR_OPEN: "Open Trapdoor",
    WOOL: "Wool", BED: "Bed", BED_RIGHT: "Bed",
    RED_DYE: "Red Dye", YELLOW_DYE: "Yellow Dye", ORANGE_DYE: "Orange Dye",
    GREEN_DYE: "Green Dye", BLUE_DYE: "Blue Dye", PURPLE_DYE: "Purple Dye",
    CYAN_DYE: "Cyan Dye",
    RED_BED: "Red Bed", RED_BED_RIGHT: "Red Bed",
    YELLOW_BED: "Yellow Bed", YELLOW_BED_RIGHT: "Yellow Bed",
    ORANGE_BED: "Orange Bed", ORANGE_BED_RIGHT: "Orange Bed",
    GREEN_BED: "Green Bed", GREEN_BED_RIGHT: "Green Bed",
    BLUE_BED: "Blue Bed", BLUE_BED_RIGHT: "Blue Bed",
    PURPLE_BED: "Purple Bed", PURPLE_BED_RIGHT: "Purple Bed",
    CYAN_BED: "Cyan Bed", CYAN_BED_RIGHT: "Cyan Bed",
    RAW_MUTTON: "Raw Mutton", COOKED_MUTTON: "Cooked Mutton",
    SMOKER: "Smoker", BLAST_FURNACE: "Blast Furnace",
    BUCKET: "Bucket", MILK_BUCKET: "Milk Bucket",
    WATER: "Water", BOAT: "Boat", FIRE: "Fire",
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
    TORCH: "Torch",
    SAND_BLOCK: "Sand", CACTUS: "Cactus", DEAD_BUSH: "Dead Bush", BEDROCK: "Bedrock", SADDLE: "Saddle",
    DIORITE: "Diorite", GRANITE: "Granite", GRAVEL: "Gravel", ANDESITE: "Andesite",
    DEEPSLATE: "Deepslate", COPPER_ORE: "Copper Ore", COPPER_INGOT: "Copper Ingot",
    FLINT: "Flint", FLINT_STEEL: "Flint and Steel", SHEARS: "Shears",
    GLASS: "Glass", GLASS_PANE: "Glass Pane",
    CARROT_STG0: "Carrot Crop", CARROT_STG1: "Carrot Crop",
    CARROT_STG2: "Carrot Crop", CARROT_STG3: "Carrot Crop",
    POTATO_STG0: "Potato Crop", POTATO_STG1: "Potato Crop",
    POTATO_STG2: "Potato Crop", POTATO_STG3: "Potato Crop",
    BEETROOT_STG0: "Beetroot Crop", BEETROOT_STG1: "Beetroot Crop",
    BEETROOT_STG2: "Beetroot Crop", BEETROOT_STG3: "Beetroot Crop",
    CARROT_ITEM: "Carrot", POTATO_ITEM: "Potato",
    POISONOUS_POTATO: "Poisonous Potato", BEETROOT_ITEM: "Beetroot",
    BEETROOT_SEEDS: "Beetroot Seeds",
    APPLE: "Apple",
    OAK_SAPLING: "Oak Sapling",
    BUNDLE: "Bundle",
    EMERALD: "Emerald",
    DANDELION: "Dandelion",
    GOLD_NUGGET: "Gold Nugget",
    BOOK: "Book",
    POPPY: "Poppy",
    CORNFLOWER: "Cornflower",
    OBSIDIAN: "Obsidian",
    GOLD_INGOT: "Gold Ingot",
    COPPER_SPEAR: "Copper Spear",
    IRON_SPEAR: "Iron Spear",
    COPPER_HORSE_ARMOR: "Copper Horse Armor",
    IRON_HORSE_ARMOR: "Iron Horse Armor",
    GOLDEN_HORSE_ARMOR: "Golden Horse Armor",
    DIAMOND_HORSE_ARMOR: "Diamond Horse Armor",
    LEATHER: "Leather",
    LEATHER_HORSE_ARMOR: "Leather Horse Armor",
    BIRCH_SAPLING: "Birch Sapling",
    WATER_BUCKET: "Water Bucket", ROCKET_LAUNCHER: "Rocket Launcher"
}

CROP_STAGES = {
    "wheat": (WHEAT_STG0, WHEAT_STG1, WHEAT_STG2, WHEAT_STG3),
    "carrot": (CARROT_STG0, CARROT_STG1, CARROT_STG2, CARROT_STG3),
    "potato": (POTATO_STG0, POTATO_STG1, POTATO_STG2, POTATO_STG3),
    "beetroot": (BEETROOT_STG0, BEETROOT_STG1, BEETROOT_STG2, BEETROOT_STG3),
}
CROP_STAGE_TO_KIND = {
    block_type: kind
    for kind, stages in CROP_STAGES.items()
    for block_type in stages
}
FIRE_NON_SOLID_BLOCKS = {
    AIR, WATER, TALL_GRASS, POPPY, DANDELION, CORNFLOWER, LADDER, TORCH, FIRE,
    OAK_SAPLING, BIRCH_SAPLING, FENCE_GATE_OPEN, DOOR_OPEN, DOOR_OPEN_TOP,
    TRAPDOOR_OPEN, *CROP_STAGE_TO_KIND,
}
CROP_PLANT_ITEMS = {
    SEEDS: "wheat",
    CARROT_ITEM: "carrot",
    POTATO_ITEM: "potato",
    BEETROOT_SEEDS: "beetroot",
}

def get_crop_drops(block_type):
    crop_kind = CROP_STAGE_TO_KIND.get(block_type)
    if crop_kind is None:
        return []
    if block_type != CROP_STAGES[crop_kind][-1]:
        if crop_kind == "wheat":
            return [(SEEDS, 1)]
        if crop_kind == "beetroot":
            return [(BEETROOT_SEEDS, 1)]
        return []
    if crop_kind == "wheat":
        return [(WHEAT_ITEM, 1), (SEEDS, random.randint(1, 2))]
    if crop_kind == "carrot":
        return [(CARROT_ITEM, random.randint(1, 3))]
    if crop_kind == "potato":
        drops = [(POTATO_ITEM, random.randint(1, 4))]
        if random.random() < 0.02:
            drops.append((POISONOUS_POTATO, 1))
        return drops
    return [(BEETROOT_ITEM, random.randint(1, 3)), (BEETROOT_SEEDS, random.randint(1, 2))]

def ignite_fire(world, tx, ty):
    clicked_block = world.get_block(tx, ty)
    if clicked_block is None:
        fire_pos = (tx, ty)
        support_pos = (tx, ty + 1)
    elif clicked_block not in FIRE_NON_SOLID_BLOCKS and ty > 0:
        fire_pos = (tx, ty - 1)
        support_pos = (tx, ty)
    else:
        return None

    if world.get_block(*fire_pos) is not None:
        return None
    if world.get_block(*support_pos) in FIRE_NON_SOLID_BLOCKS:
        return None

    world.set_block(*fire_pos, FIRE)
    return fire_pos

MAX_DURABILITY = {
    W_PICK: 60, W_AXE: 60, W_SHOVEL: 60, W_SWORD: 60, W_HOE: 60,
    S_PICK: 132, S_AXE: 132, S_SHOVEL: 132, S_SWORD: 132, S_HOE: 132,
    I_PICK: 250, I_AXE: 250, I_SHOVEL: 250, I_SWORD: 250, I_HOE: 250,
    D_PICK: 1561, D_AXE: 1561, D_SHOVEL: 1561, D_SWORD: 1561, D_HOE: 1561,
    I_HELMET: 165, I_CHEST: 240, I_LEGS: 225, I_BOOTS: 195,
    D_HELMET: 363, D_CHEST: 528, D_LEGS: 495, D_BOOTS: 429,
    COPPER_SPEAR: 180, IRON_SPEAR: 250,
    BOW: 384,
    FISHING_ROD: 64,
    SHIELD: 336,
    FLINT_STEEL: 64,
    SHEARS: 238
}

ACHIEVEMENTS = {
    "first_break": ("Getting Started", "Mine your first block"),
    "first_build": ("Builder", "Place your first block"),
    "first_craft": ("Crafting Time", "Craft your first item"),
    "first_hunt": ("First Hunt", "Defeat a creature"),
    "find_diamond": ("Shiny!", "Mine diamond ore"),
    "collect_water": ("Water Carrier", "Collect water with a bucket"),
    "shear_sheep": ("Wool Gatherer", "Shear a sheep"),
    "harvest_wheat": ("Harvest Time", "Harvest mature wheat"),
}

PLACEABLE_BLOCKS = {
    GRASS_BLOCK, DIRT_BLOCK, STONE_BLOCK, COAL_BLOCK, IRON_BLOCK,
    OAK_LOG, BIRCH_LOG, OAK_LEAVES, BIRCH_LEAVES, PLANKS,
    CRAFTING_TABLE, FURNACE, COBBLESTONE, SMOOTH_STONE,
    IRON_BLOCK_PROD, DOOR, TRAPDOOR, PRESSURE_PLATE, BUTTON,
    LEVER, CHAIN, W_STAIRS, C_STAIRS, SS_STAIRS,
    W_SLAB, C_SLAB, SS_SLAB, FARMLAND, HAY_BALE, CHEST,
    FENCE, FENCE_GATE, WOOL, BED, RED_BED, YELLOW_BED, ORANGE_BED, GREEN_BED,
    BLUE_BED, PURPLE_BED, CYAN_BED, POPPY, DANDELION, CORNFLOWER,
    LADDER, COAL_BLOCK_ITEM, BOAT, TORCH, SAND_BLOCK,
    CACTUS, BEDROCK, DIORITE, GRANITE, GRAVEL, ANDESITE, DEEPSLATE, COPPER_ORE,
    GLASS, GLASS_PANE, OAK_SAPLING, BIRCH_SAPLING
}

def unlock_achievement(world, achievement_id):
    if world is None:
        return False
    achievement = ACHIEVEMENTS.get(achievement_id)
    if achievement is None or achievement_id in world.unlocked_achievements:
        return False

    world.unlocked_achievements.add(achievement_id)
    toast = {"title": achievement[0], "description": achievement[1], "timer": 240}
    if world.achievement_toast is None:
        world.achievement_toast = toast
    else:
        world.achievement_queue.append(toast)
    return True


def draw_achievement_toast(surface, font, world):
    if world.achievement_toast is None and world.achievement_queue:
        world.achievement_toast = world.achievement_queue.pop(0)
    toast = world.achievement_toast
    if toast is None:
        return

    width, height = 360, 80
    margin = 16
    y = SCREEN_HEIGHT - height - 52
    remaining = toast["timer"]
    progress = min(1.0, (240 - remaining) / 12, remaining / 12)
    x = margin - int(width * (1.0 - max(0.0, progress)))

    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (25, 30, 28, 235), (0, 0, width, height), border_radius=4)
    pygame.draw.rect(panel, (100, 180, 110, 255), (0, 0, width, height), 2, border_radius=4)
    pygame.draw.rect(panel, (195, 160, 65, 255), (12, 14, 34, 34), border_radius=3)
    pygame.draw.rect(panel, (55, 45, 28, 255), (19, 20, 20, 14))
    pygame.draw.rect(panel, (55, 45, 28, 255), (15, 17, 5, 5))
    pygame.draw.rect(panel, (55, 45, 28, 255), (38, 17, 5, 5))
    pygame.draw.rect(panel, (55, 45, 28, 255), (24, 34, 10, 4))

    header = font.render("Achievement Unlocked!", True, (255, 222, 125))
    title = font.render(toast["title"], True, COLOR_WHITE)
    description = font.render(toast["description"], True, (190, 195, 190))
    panel.blit(header, (56, 4))
    panel.blit(title, (56, 28))
    panel.blit(description, (56, 52))
    surface.blit(panel, (x, y))

    toast["timer"] -= 1
    if toast["timer"] <= 0:
        world.achievement_toast = None


def _load_persistent_player_id(player):
    id_sources = (
        (WORLDS_DIR / "savegame.json", "player_id"),
        (WORLDS_DIR / "player_id.json", "id"),
    )
    for path, key in id_sources:
        if not path.exists():
            continue
        try:
            with open(path, "r") as f:
                saved_data = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            print(f"[SAVE] Could not read player ID from {path}: {error}")
            continue

        saved_id = saved_data.get(key) if isinstance(saved_data, dict) else None
        if isinstance(saved_id, str) and saved_id:
            player.persistent_id = saved_id
            return
        print(f"[SAVE] No valid player ID found in {path}")


class Player:
    def __init__(self, display_name="Player"):
        self.persistent_id = "player_" + str(random.randint(1000, 9999))
        _load_persistent_player_id(self)

        self.display_name = sanitize_display_name(display_name)

        self.rect = pygame.Rect(100, 50, 24, (TILE_SIZE * 2) - 2) 
        self.vel_y = 0
        self.speed = 5
        self.jump_strength = -8.0 # Stronger jump for easier towering
        self.on_ground = False
        self.flying = False
        self.direction = 1 
        self.riding_mob = None
        
        self.max_health = 20
        self.health = self.max_health
        self.last_damage_cause = None
        self.highest_y = self.rect.y 
        self.invincible_until = pygame.time.get_ticks() + 5000 # 5s at startup
        self.last_action_time = 0 # Cooldown for building/breaking
        
        self.inventory = [None] * 36 # 0-8 Hotbar, 9-35 Main Inventory
        self.inventory[0] = {"type": DIRT_BLOCK, "count": 10}
        self.inventory[1] = {"type": SADDLE, "count": 5}
        self.armor = [None] * 4 # 0: Helmet, 1: Chest, 2: Legs, 3: Boots
        self.selected_slot = 0
        
        # Crafting
        self.crafting_grid = [None] * 4 # 2x2
        self.crafting_output = None
        self.crafting_3x3 = [None] * 9 # 3x3
        self.output_3x3 = None
        
        self.offhand = None
        self.blocking = False
        self.jump_attack_timer = 0
        self.fishing_hook = None
        
        self.held_item = None
        self.show_inventory = False
        self.show_3x3 = False
        self.recipe_book_open = False
        self.recipe_book_page = 0
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
        self.air = 10 # 10 bubbles
        self.air_timer = 0 # Timer for air depletion
        self.show_inventory = False # Ensure movement isn't locked on start

    def update(self, world):
        if self.flying:
            self.health = self.max_health
        if self.jump_attack_timer > 0:
            self.jump_attack_timer -= 1

        # Cactus contact damage (1 HP every 0.5s)
        if not hasattr(self, 'cactus_dmg_timer'): self.cactus_dmg_timer = 0
        if self.cactus_dmg_timer > 0:
            self.cactus_dmg_timer -= 1
        else:
            # Check all 4 sides of the player's bounding box for cactus
            cx = self.rect.centerx // TILE_SIZE
            top_ty = self.rect.top // TILE_SIZE
            bot_ty = (self.rect.bottom - 1) // TILE_SIZE
            left_tx = (self.rect.left - 1) // TILE_SIZE
            right_tx = self.rect.right // TILE_SIZE
            touching_cactus = False
            for check in [(cx, top_ty), (cx, bot_ty), (left_tx, top_ty),
                          (left_tx, bot_ty), (right_tx, top_ty), (right_tx, bot_ty)]:
                if world.get_block(check[0] % WORLD_WIDTH, check[1]) == CACTUS:
                    touching_cactus = True
                    break
            if touching_cactus:
                self.take_damage(1, cause="cactus")
                self.cactus_dmg_timer = 30  # 0.5s cooldown at 60fps

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
                self.take_damage(1, cause="starvation")
            self.regen_timer = 0

        if self.show_inventory: return # Freeze movement
        
        if self.flying:
            self.highest_y = self.rect.y
        elif self.on_ground:
            self.highest_y = self.rect.y
        else:
            self.highest_y = min(self.highest_y, self.rect.y)

        dx = 0
        keys = pygame.key.get_pressed()
        
        # Use the whole hitbox so swimming works while the player is only partly submerged.
        in_water = _rect_overlaps_water(self.rect, world)
        if in_water:
            self.highest_y = self.rect.y
            self.vel_y = min(self.vel_y, 2.0)

        head_underwater = False
        hx, hy = self.rect.centerx // TILE_SIZE, self.rect.top // TILE_SIZE
        if world.get_block(hx % WORLD_WIDTH, hy) == WATER:
            head_underwater = True

        # Drowning Logic
        if head_underwater:
            self.air_timer += 1
            if self.air_timer >= 60: # Every 1 second
                if self.air > 0:
                    self.air -= 1
                else:
                    self.take_damage(4, cause="drowning") # 2 Hearts damage
                self.air_timer = 0
        else:
            if self.air < 10:
                self.air_timer += 1
                if self.air_timer >= 10: # Faster refill
                    self.air = 10
                    self.air_timer = 0

        # Boat Speed Boost
        below_x, below_y = self.rect.centerx // TILE_SIZE, (self.rect.bottom + 2) // TILE_SIZE
        speed_mult = 1.0
        on_boat = (below_x, below_y) in world.data and world.data[(below_x, below_y)] == BOAT
        if on_boat:
            speed_mult = 2.5 # Fast boat travel

        weather_speed_mult = 1.0
        weather_jump_mult = 1.0
        if world.is_precipitating() and world.is_outdoors(self.rect):
            weather_speed_mult = 0.78 if world.weather_type == "rain" else 0.86
            weather_jump_mult = 0.92

        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            speed_mult *= 2.0 # Sprint
        sprinting = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]

        if self.riding_mob:
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                self.riding_mob = None
                self.vel_y = 0
                self.on_ground = False
                self.highest_y = self.rect.y
                return
            else:
                self.rect.centerx = self.riding_mob.rect.centerx
                self.rect.bottom = self.riding_mob.rect.top
                self.vel_y = 0
                self.on_ground = True
                self.highest_y = self.rect.y
                if keys[pygame.K_a]:
                    self.direction = -1
                elif keys[pygame.K_d]:
                    self.direction = 1
                return

        if on_boat and not self.flying and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            exit_dx = 1 if self.direction > 0 else -1
            exit_x = (below_x + exit_dx) % WORLD_WIDTH
            self.rect.x = exit_x * TILE_SIZE
            world.find_safe_spawn(self)
            self.vel_y = 0
            self.on_ground = False
            self.highest_y = self.rect.y
            return

        if keys[pygame.K_a]:
            dx -= self.speed * (0.5 if in_water else speed_mult) * weather_speed_mult
            self.direction = -1
        if keys[pygame.K_d]:
            dx += self.speed * (0.5 if in_water else speed_mult) * weather_speed_mult
            self.direction = 1
        sneaking = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and not self.flying
        
        # Blocking
        self.blocking = False
        if sneaking:
            item_in_hand = self.inventory[self.selected_slot]
            if (item_in_hand and item_in_hand["type"] == SHIELD) or (self.offhand and self.offhand["type"] == SHIELD):
                self.blocking = True
                dx *= 0.3 # Slow down while blocking

        if sneaking and not self.blocking:
            dx *= 0.3

        if self.flying:
            if keys[pygame.K_SPACE] or keys[pygame.K_w]:
                self.vel_y = -self.speed
            elif keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_s]:
                self.vel_y = self.speed
            else:
                self.vel_y = 0
        elif keys[pygame.K_SPACE] or keys[pygame.K_w]:
            if in_water:
                self.vel_y = -6
            elif self.on_ground and keys[pygame.K_SPACE]:
                self.vel_y = self.jump_strength * weather_jump_mult * (1.2 if sprinting else 1.0)
                self.jump_attack_timer = 12

        if not self.flying:
            self.vel_y += GRAVITY * (0.3 if in_water else 1.0)
        
        # Ladder climbing
        on_ladder = False
        lx = self.rect.centerx // TILE_SIZE
        # Check top, middle, and bottom of player for ladder contact
        if not self.flying:
            for ly in [self.rect.top // TILE_SIZE, self.rect.centery // TILE_SIZE, (self.rect.bottom - 1) // TILE_SIZE]:
                if (lx, ly) in world.data and world.data[(lx, ly)] == LADDER:
                    on_ladder = True
                    break
        
        if on_ladder:
            # Touching a ladder breaks the fall, so don't carry pre-ladder fall distance forward.
            self.highest_y = self.rect.y
            self.on_ground = False
            self.vel_y = 0 # Default to staying still
            if keys[pygame.K_w] or keys[pygame.K_SPACE]:
                self.vel_y = -4 # Climb up
            elif keys[pygame.K_s]:
                self.vel_y = 4 # Climb down
        else:
            if sprinting and self.on_ground and (keys[pygame.K_a] or keys[pygame.K_d]):
                dx *= 1.15 # Small takeoff boost while sprinting
            if self.vel_y > 15: self.vel_y = 15

        if in_water and sneaking and not (keys[pygame.K_SPACE] or keys[pygame.K_w]):
            self.vel_y = max(self.vel_y, 3.0)
        dy = self.vel_y

        if sneaking and self.on_ground and dx:
            direction = 1 if dx > 0 else -1
            safe_distance = 0.0
            while safe_distance < abs(dx):
                step = min(1.0, abs(dx) - safe_distance)
                candidate = self.rect.copy()
                candidate.x += direction * (safe_distance + step)
                foot_probe = pygame.Rect(candidate.left, candidate.bottom, candidate.width, 2)
                if not any(
                    foot_probe.colliderect(block)
                    for block in world.get_surrounding_blocks(candidate)
                ):
                    break
                safe_distance += step
            dx = direction * safe_distance

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
            self.take_damage(20, cause="void")
            self.vel_y = 0

        if self.health <= 0:
            self.die(world)

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
        if self.flying:
            self.health = self.max_health
            self.highest_y = self.rect.y
            return
        if pygame.time.get_ticks() < self.invincible_until:
            return
        fall_distance = (self.rect.y - self.highest_y) / TILE_SIZE
        if fall_distance >= 4:
            dmg = fall_distance - 3
            boots = self.armor[3]
            if boots:
                if boots["type"] == D_BOOTS:
                    dmg *= 0.6
                elif boots["type"] == I_BOOTS:
                    dmg *= 0.75
            self.health -= max(1, math.ceil(dmg))
            self.health = max(0, self.health)
            self.last_damage_cause = "fall"
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
        self.jump_attack_timer = 0
        self.fishing_hook = None
        self.riding_mob = None

    def die(self, world):
        cause = getattr(self, 'last_damage_cause', None)
        msg_text = f"{self.display_name} died"
        if cause == "cactus":
            msg_text = f"{self.display_name} was pricked to death by a cactus"
        elif cause == "drowning":
            msg_text = f"{self.display_name} drowned"
        elif cause == "starvation":
            msg_text = f"{self.display_name} starved to death"
        elif cause == "fall":
            msg_text = f"{self.display_name} fell from a high place"
        elif cause == "zombie":
            msg_text = f"{self.display_name} was slain by Zombie"
        elif cause == "husk":
            msg_text = f"{self.display_name} was slain by Husk"
        elif cause == "spider":
            msg_text = f"{self.display_name} was slain by Spider"
        elif cause == "enderman":
            msg_text = f"{self.display_name} was slain by Enderman"
        elif cause == "void":
            msg_text = f"{self.display_name} fell out of the world"
        
        if hasattr(world, 'death_messages'):
            world.death_messages.append({"text": msg_text, "timer": 300}) # 5 seconds
        
        print(f"[DEATH] {msg_text}")
        self.last_damage_cause = None
        self.respawn()

    def take_damage(self, amount, cause=None):
        if self.flying:
            self.health = self.max_health
            return
        if pygame.time.get_ticks() < self.invincible_until: return
        # Armor reduction
        reduction = 0
        for part in self.armor:
            if part:
                if part["type"] in (D_HELMET, D_CHEST, D_LEGS, D_BOOTS):
                    reduction += 0.20 # 20% per diamond piece
                else:
                    reduction += 0.15 # 15% per iron piece
        
        if self.blocking:
            reduction = 1.0 # 100% block
            # Damage the shield
            shield_slot = None
            if self.offhand and self.offhand["type"] == SHIELD:
                shield_slot = self.offhand
            elif self.inventory[self.selected_slot] and self.inventory[self.selected_slot]["type"] == SHIELD:
                shield_slot = self.inventory[self.selected_slot]
            
            if shield_slot:
                shield_slot["durability"] -= amount
                if shield_slot["durability"] <= 0:
                    if shield_slot == self.offhand: self.offhand = None
                    else: self.inventory[self.selected_slot] = None

        final_dmg = amount * (1.0 - reduction)
        self.health -= final_dmg
        self.invincible_until = pygame.time.get_ticks() + 500 # Brief i-frames
        if self.health < 0: self.health = 0
        if cause is not None:
            self.last_damage_cause = cause

class World:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.SystemRandom().getrandbits(64)
        self.rng = random.Random(self.seed)
        self.chunks = {}
        self.unloaded_chunks = {}
        self.loaded_chunk_columns = None
        self.villages_generated = False
        self.village_generation_version = VILLAGE_GENERATION_VERSION
        self.village_locations = []
        self.block_meta = {} # (tx, ty) -> {"facing": 1 or -1}
        self.death_messages = []
        self.furnace_data = {} # (tx, ty) -> {"input": slot, "fuel": slot, "output": slot, "cook_time": float, "fuel_time": float}
        self.chest_data = {} # (tx, ty) -> [slots]
        self.remote_players_data = {} # persistent_id -> player_stats
        self.mobs = []
        self.dropped_items = [] # (DroppedItem instances)
        self.projectiles = [] # ThrownPearl instances
        self.egg_projectiles = [] # EggShot instances
        self.arrows = [] # ArrowShot instances
        self.rocket_projectiles = [] # RocketShot instances
        self.explosions = []
        self.fishing_hooks = [] # FishingHook instances
        self.time = 0 # 0 corresponds to 6:00 AM (Sunrise)
        self.weather_type = "clear"  # clear, rain, snow
        self.weather_timer = 0
        self.weather_intensity = 0.0
        self.unlocked_achievements = set()
        self.achievement_queue = []
        self.achievement_toast = None
        self.active_water = set() # Track coordinates of flowing water
        self.water_cascade_removed = []
        self.falling_sand = set() # Track coordinates of sand/cactus blocks that should fall
        self.generate_world()
        self.choose_weather()

    def get_chunk_id(self, tx, ty):
        return ((tx % WORLD_WIDTH) // CHUNK_SIZE, ty // CHUNK_SIZE)

    def update_loaded_chunks(self, player_x):
        column_count = WORLD_WIDTH // CHUNK_SIZE
        center_column = (int(player_x) % WORLD_PIXELS) // (CHUNK_SIZE * TILE_SIZE)
        desired_columns = {
            (center_column + offset) % column_count
            for offset in (-1, 0, 1)
        }
        if self.loaded_chunk_columns == desired_columns:
            return

        for chunk_id, chunk in list(self.chunks.items()):
            if chunk_id[0] not in desired_columns:
                self.unloaded_chunks[chunk_id] = chunk
                del self.chunks[chunk_id]

        for chunk_id in list(self.unloaded_chunks):
            if chunk_id[0] in desired_columns:
                self.chunks[chunk_id] = self.unloaded_chunks.pop(chunk_id)

        self.loaded_chunk_columns = desired_columns

    def iter_all_chunks(self):
        yield from self.chunks.values()
        yield from self.unloaded_chunks.values()

    def _remove_chunk_block(self, tx, ty):
        tx %= WORLD_WIDTH
        chunk_id = self.get_chunk_id(tx, ty)
        for storage in (self.chunks, self.unloaded_chunks):
            chunk = storage.get(chunk_id)
            if chunk is not None and (tx, ty) in chunk:
                del chunk[(tx, ty)]
                if not chunk:
                    del storage[chunk_id]
                return

    def _remove_dependent_water_flows(self, tx, ty, source_level):
        root = (tx % WORLD_WIDTH, ty)
        candidates = set()
        levels = {}
        queue = [(root, source_level)]
        while queue:
            parent_pos, parent_level = queue.pop()
            px, py = parent_pos
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                pos = ((px + dx) % WORLD_WIDTH, py + dy)
                if pos in candidates or self.get_block(*pos) != WATER:
                    continue
                water_meta = self.block_meta.get(pos, {})
                level = water_meta.get("level", 7)
                is_source = water_meta.get("source", level == 7)
                if level < parent_level or not is_source:
                    candidates.add(pos)
                    levels[pos] = level
                    queue.append((pos, level))

        supported = set()
        for x, y in candidates:
            level = levels[(x, y)]
            for support_pos in (
                ((x - 1) % WORLD_WIDTH, y),
                ((x + 1) % WORLD_WIDTH, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if (
                    support_pos != root
                    and support_pos not in candidates
                    and self.get_block(*support_pos) == WATER
                    and self.block_meta.get(support_pos, {}).get("level", 7) > level
                ):
                    supported.add((x, y))
                    break

        queue = list(supported)
        while queue:
            x, y = queue.pop()
            parent_level = levels[(x, y)]
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                pos = ((x + dx) % WORLD_WIDTH, y + dy)
                if pos in candidates and pos not in supported and levels[pos] < parent_level:
                    supported.add(pos)
                    queue.append(pos)

        for x, y in candidates - supported:
            pos = (x, y)
            self._remove_chunk_block(x, y)
            self.block_meta.pop(pos, None)
            self.active_water.discard(pos)
            self.water_cascade_removed.append(pos)

    def choose_weather(self):
        if random.random() < 0.60:
            self.weather_type = "clear"
            self.weather_intensity = 0.0
            self.weather_timer = random.randint(2400, 7200)
        else:
            self.weather_type = "rain" if random.random() < 0.66 else "snow"
            self.weather_intensity = random.uniform(0.45, 1.0)
            self.weather_timer = random.randint(1800, 4800)
            if self.weather_type == "snow" and self.weather_intensity < 0.6:
                self.weather_intensity = 0.6

    def update_weather(self):
        if self.weather_timer > 0:
            self.weather_timer -= 1
        if self.weather_timer <= 0:
            self.choose_weather()

    def is_precipitating(self):
        return self.weather_type in ("rain", "snow") and self.weather_intensity > 0.0

    def is_outdoors(self, rect):
        cx = rect.centerx // TILE_SIZE
        top_ty = rect.top // TILE_SIZE
        for y in range(0, top_ty + 1):
            if (cx, y) in self.data:
                return False
        return True
    def _break_cactus_column_upward(self, tx, ty):
        """Remove all CACTUS blocks from (tx, ty) upward. Drops each as an item."""
        cy = ty
        while self.get_block(tx, cy) == CACTUS:
            self._remove_chunk_block(tx, cy)
            self.dropped_items.append(DroppedItem(tx * TILE_SIZE + 8, cy * TILE_SIZE + 8, CACTUS))
            cy -= 1  # go up

    def set_block(self, tx, ty, b_type):
        tx %= WORLD_WIDTH
        cid = self.get_chunk_id(tx, ty)
        old_type = self.get_block(tx, ty)
        if old_type == WATER and b_type != WATER:
            level = self.block_meta.get((tx, ty), {}).get("level", 7)
            self._remove_dependent_water_flows(tx, ty, level)
        
        if b_type is None or b_type == AIR:
            # Wake up adjacent water blocks when a block is broken
            for nx, ny in [(tx-1, ty), (tx+1, ty), (tx, ty-1), (tx, ty+1)]:
                if self.get_block(nx, ny) == WATER:
                    self.active_water.add((nx, ny))
            # Wake up sand above this position when a block is broken
            above = self.get_block(tx, ty - 1)
            if above in (SAND_BLOCK, GRAVEL):
                self.falling_sand.add((tx, ty - 1))
            # If we're removing a CACTUS, cascade-break all cactus above it
            if self.get_block(tx, ty) == CACTUS:
                # First remove this block normally
                self._remove_chunk_block(tx, ty)
                # Then cascade upward
                self._break_cactus_column_upward(tx, ty - 1)
                return
                    
            self._remove_chunk_block(tx, ty)
            self.block_meta.pop((tx, ty), None)
            return

        if b_type != WATER:
            self.active_water.discard((tx, ty))
            self.block_meta.pop((tx, ty), None)
            
        # --- Placing a block: check if adjacent to cactus ---
        if b_type != AIR:
            for nx, ny in [(tx - 1, ty), (tx + 1, ty)]:
                if self.get_block(nx, ny) == CACTUS:
                    # Find the base of this cactus column
                    base_y = ny  # ny is the same row as ty
                    while self.get_block(nx, base_y + 1) == CACTUS:
                        base_y += 1
                    # Break the entire column from bottom up
                    col_y = base_y
                    while self.get_block(nx, col_y) == CACTUS:
                        self._remove_chunk_block(nx, col_y)
                        self.dropped_items.append(DroppedItem(nx * TILE_SIZE + 8, col_y * TILE_SIZE + 8, CACTUS))
                        col_y -= 1  # go up

        storage = self.chunks
        if self.loaded_chunk_columns is not None and cid[0] not in self.loaded_chunk_columns:
            storage = self.unloaded_chunks
        if cid not in storage:
            storage[cid] = {}
        storage[cid][(tx, ty)] = b_type
        
        if b_type == WATER:
            self.active_water.add((tx, ty))
        elif b_type in (SAND_BLOCK, GRAVEL):
            # A new sand block was placed — check if it should fall
            if self.get_block(tx, ty + 1) is None:
                self.falling_sand.add((tx, ty))


    def get_block(self, tx, ty):
        tx %= WORLD_WIDTH
        cid = self.get_chunk_id(tx, ty)
        if cid in self.chunks:
            return self.chunks[cid].get((tx, ty))
        if cid in self.unloaded_chunks:
            return self.unloaded_chunks[cid].get((tx, ty))
        return None

    def update_water(self):
        if not self.active_water:
            return
            
        next_active = set()
        
        # Process all currently active water blocks
        for tx, ty in list(self.active_water):
            b_type = self.get_block(tx, ty)
            if b_type != WATER:
                continue # Block was removed/changed
                
            level = self.block_meta.get((tx, ty), {}).get("level", 7)
            spread_occurred = False
            
            # Rule 1: Downward Flow
            below_type = self.get_block(tx, ty + 1)
            
            if below_type is None or below_type == AIR:
                # Falling water is full-height but still depends on its source.
                self.set_block(tx, ty + 1, WATER)
                self.block_meta[(tx, ty + 1)] = {"level": 7, "source": False}
                next_active.add((tx, ty + 1))
                spread_occurred = True
                
            # Rule 2: Horizontal Spread (if sitting on a solid block or full water block)
            elif below_type != WATER or self.block_meta.get((tx, ty + 1), {}).get("level", 7) == 7:
                if level > 0:
                    for dx in [-1, 1]:
                        nx, ny = (tx + dx) % WORLD_WIDTH, ty
                        neighbor_type = self.get_block(nx, ny)
                        
                        can_spread = False
                        if neighbor_type is None or neighbor_type == AIR:
                            can_spread = True
                        elif neighbor_type == WATER:
                            n_level = self.block_meta.get((nx, ny), {}).get("level", 7)
                            # Only overwrite if we can provide a higher level
                            if n_level < level - 1:
                                can_spread = True
                                
                        if can_spread:
                            self.set_block(nx, ny, WATER)
                            self.block_meta[(nx, ny)] = {"level": level - 1, "source": False}
                            next_active.add((nx, ny))
                            spread_occurred = True
                            
            # If a block successfully spread, we keep it active in case neighbors are broken.
            # Actually, to prevent infinite loops, we only add new blocks to next_active.
            # The set_block method handles waking up adjacent blocks when broken.
            
        self.active_water = next_active

    def update_falling_sand(self):
        if not self.falling_sand:
            return

        next_falling = set()
        GRAVITY_BLOCKS = (SAND_BLOCK, GRAVEL)

        for tx, ty in list(self.falling_sand):
            b_type = self.get_block(tx, ty)
            if b_type not in GRAVITY_BLOCKS:
                continue  # Block was removed/changed

            below = ty + 1
            # Don't fall through the bottom of the world
            if below >= WORLD_HEIGHT:
                continue

            below_block = self.get_block(tx, below)

            if below_block is None:  # Air below — fall one step
                # Move the block down by one tile
                self.set_block(tx, below, b_type)
                self.set_block(tx, ty, None)
                next_falling.add((tx, below))
                # Also propagate: if there's more sand above us, wake it up
                above_block = self.get_block(tx, ty - 1)
                if above_block in GRAVITY_BLOCKS:
                    next_falling.add((tx, ty - 1))
            # If blocked by something solid, this block is settled — don't re-add

        self.falling_sand = next_falling

    def is_farmland_watered(self, tx, ty):
        for dx in range(-4, 5):
            for dy in (-1, 0):
                if self.get_block(tx + dx, ty + dy) == WATER:
                    return True
        return False

    def update_farmland_moisture(self):
        changes = []
        for (tx, ty), block_type in list(self.data.items()):
            if block_type != FARMLAND:
                continue

            pos = (tx, ty)
            moisture = self.block_meta.get(pos, {}).get("moisture", 7)
            moisture = 7 if self.is_farmland_watered(tx, ty) else moisture - 1
            if moisture <= 0:
                self.set_block(tx, ty, DIRT_BLOCK)
                changes.append((pos, DIRT_BLOCK, None))
                crop_pos = (tx, ty - 1)
                if self.get_block(*crop_pos) in CROP_STAGE_TO_KIND:
                    self.set_block(*crop_pos, None)
                    changes.append((crop_pos, None, None))
            else:
                metadata = dict(self.block_meta.get(pos, {}))
                metadata["moisture"] = moisture
                self.block_meta[pos] = metadata
                changes.append((pos, FARMLAND, metadata))
        return changes

    def grow_sapling(self, tx, ty, sapling_type):
        is_birch = sapling_type == BIRCH_SAPLING
        tree_height = self.rng.randint(5, 7) if is_birch else self.rng.randint(4, 6)
        if ty < tree_height + 2:
            return []
        for dx in range(-2, 3):
            for dy in range(-tree_height - 2, 0):
                block_type = self.get_block(tx + dx, ty + dy)
                if block_type is not None:
                    return []
        if self.get_block(tx, ty + 1) not in (GRASS_BLOCK, DIRT_BLOCK):
            return []

        log_type = BIRCH_LOG if is_birch else OAK_LOG
        leaves_type = BIRCH_LEAVES if is_birch else OAK_LEAVES
        changes = []
        base_pos = (tx % WORLD_WIDTH, ty)
        self.set_block(*base_pos, log_type)
        changes.append((base_pos, log_type, None))
        for height in range(1, tree_height + 1):
            pos = ((tx + WORLD_WIDTH) % WORLD_WIDTH, ty - height)
            self.set_block(*pos, log_type)
            changes.append((pos, log_type, None))

        for dx in range(-2, 3):
            for dy in range(-2, 1):
                pos = ((tx + dx) % WORLD_WIDTH, ty - tree_height + dy)
                if self.get_block(*pos) is None:
                    self.set_block(*pos, leaves_type)
                    changes.append((pos, leaves_type, None))
        return changes

    def update_natural_growth(self):
        changes = []
        crops = []
        saplings = []
        grass_candidates = []
        for (tx, ty), block_type in self.data.items():
            if (
                block_type in CROP_STAGE_TO_KIND
                and block_type != CROP_STAGES[CROP_STAGE_TO_KIND[block_type]][-1]
            ):
                crops.append((tx, ty, block_type))
            elif block_type in (OAK_SAPLING, BIRCH_SAPLING):
                saplings.append((tx, ty, block_type))
            elif block_type == DIRT_BLOCK and self.get_block(tx, ty - 1) is None:
                if any(
                    self.get_block(tx + dx, ty) == GRASS_BLOCK
                    for dx in (-1, 1)
                ):
                    grass_candidates.append((tx, ty))

        if crops:
            tx, ty, block_type = self.rng.choice(crops)
            crop_kind = CROP_STAGE_TO_KIND[block_type]
            farmland_pos = (tx, ty + 1)
            if (
                block_type != CROP_STAGES[crop_kind][-1]
                and self.get_block(*farmland_pos) == FARMLAND
                and self.is_farmland_watered(*farmland_pos)
            ):
                next_stage = block_type + 1
                self.set_block(tx, ty, next_stage)
                changes.append(((tx, ty), next_stage, None))

        if saplings:
            tx, ty, sapling_type = self.rng.choice(saplings)
            growth_chance = 1 / 360 if sapling_type == BIRCH_SAPLING else 1 / 180
            if self.rng.random() < growth_chance:
                changes.extend(self.grow_sapling(tx, ty, sapling_type))

        if grass_candidates and self.rng.random() < 0.02:
            tx, ty = self.rng.choice(grass_candidates)
            self.set_block(tx, ty, GRASS_BLOCK)
            changes.append(((tx, ty), GRASS_BLOCK, None))

        return changes

    @property
    def data(self):
        # This proxy allows existing code to use world.data[(x,y)] while storing in chunks internally
        class DataProxy:
            def __init__(self, w): self.w = w
            def __getitem__(self, key): return self.w.get_block(key[0], key[1])
            def __setitem__(self, key, val): self.w.set_block(key[0], key[1], val)
            def __contains__(self, key): return self.w.get_block(key[0], key[1]) is not None
            def __delitem__(self, key): self.w.set_block(key[0], key[1], None)
            def items(self):
                for storage in (self.w.chunks, self.w.unloaded_chunks):
                    for chunk in storage.values():
                        yield from chunk.items()
            def values(self):
                for storage in (self.w.chunks, self.w.unloaded_chunks):
                    for chunk in storage.values():
                        yield from chunk.values()
            def keys(self):
                for storage in (self.w.chunks, self.w.unloaded_chunks):
                    for chunk in storage.values():
                        yield from chunk.keys()
            def pop(self, key, default=None):
                val = self.w.get_block(key[0], key[1])
                if val is not None:
                    self.w.set_block(key[0], key[1], None)
                    return val
                return default
            def get(self, key, default=None):
                val = self.w.get_block(key[0], key[1])
                return val if val is not None else default
            def __bool__(self):
                return bool(self.w.chunks or self.w.unloaded_chunks)
        return DataProxy(self)

    @data.setter
    def data(self, new_dict):
        # Allow clearing/setting world data directly (used by network sync)
        self.chunks = {}
        self.unloaded_chunks = {}
        self.loaded_chunk_columns = None
        if isinstance(new_dict, dict):
            for k, v in new_dict.items():
                self.set_block(k[0], k[1], v)
        elif hasattr(new_dict, "items"): # Handle proxy objects
            for k, v in new_dict.items():
                self.set_block(k[0], k[1], v)

    def generate_world(self):
        rng = self.rng

        # Build irregular, seeded terrain from random height anchors.
        anchor_spacing = 8
        height_anchors = [
            rng.randint(10, 20)
            for _ in range((WORLD_WIDTH + anchor_spacing - 1) // anchor_spacing)
        ]
        surface_heights = []
        for x in range(WORLD_WIDTH):
            anchor_idx, offset = divmod(x, anchor_spacing)
            start_h = height_anchors[anchor_idx]
            end_h = height_anchors[(anchor_idx + 1) % len(height_anchors)]
            blend = offset / anchor_spacing
            h = round(start_h + (end_h - start_h) * blend + rng.uniform(-1.0, 1.0))
            surface_heights.append(max(8, min(22, h)))

        # Surface and underground layers
        for x, h in enumerate(surface_heights):
            for y in range(WORLD_HEIGHT):
                if y > h:
                    if y == WORLD_HEIGHT - 1:
                        self.data[(x, y)] = BEDROCK
                    elif y >= 80:
                        self.data[(x, y)] = DEEPSLATE
                    else:
                        self.data[(x, y)] = STONE_BLOCK if y > h + 4 else DIRT_BLOCK
                elif y == h:
                    self.data[(x, y)] = GRASS_BLOCK
                    if h > 1 and rng.random() < 0.2:
                        self.data[(x, y - 1)] = TALL_GRASS

        # Form small, rounded ponds in low ground rather than rectangular tanks.
        for _ in range(max(5, WORLD_WIDTH // 192)):
            center_x = rng.randrange(WORLD_WIDTH)
            radius = rng.randint(2, 5)
            x_positions = [(center_x + dx) % WORLD_WIDTH for dx in range(-radius, radius + 1)]
            water_y = max(surface_heights[x] for x in x_positions)
            depth = rng.randint(2, 4)
            for dx in range(-radius, radius + 1):
                x = (center_x + dx) % WORLD_WIDTH
                edge_ratio = abs(dx) / radius
                column_depth = max(1, round(depth * (1 - edge_ratio * edge_ratio)))
                if abs(dx) == radius:
                    self.data[(x, water_y)] = DIRT_BLOCK
                    continue
                for y in range(surface_heights[x], water_y):
                    if y < water_y:
                        self.data[(x, y)] = None
                for y in range(water_y, water_y + column_depth):
                    self.data[(x, y)] = WATER
                self.data[(x, water_y + column_depth)] = DIRT_BLOCK
                
        # Generate Caves (Random Walks)
        for _ in range(15):
            cx = rng.randint(0, WORLD_WIDTH - 1)
            cy = rng.randint(20, WORLD_HEIGHT - 20)
            for _ in range(rng.randint(20, 50)):
                # Carve a small sphere
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if self.data.get((cx + dx, cy + dy)) not in (None, WATER):
                            del self.data[(cx+dx, cy+dy)]
                cx = (cx + rng.randint(-1, 1)) % WORLD_WIDTH
                cy = min(WORLD_HEIGHT - 5, max(10, cy + rng.randint(-1, 1)))

        # Generate Ravines (Long vertical slits)
        for _ in range(3):
            rx = rng.randint(10, WORLD_WIDTH - 10)
            ry = rng.randint(20, 50)
            r_len = rng.randint(15, 25)
            for i in range(r_len):
                curr_y = ry + i
                curr_x = rx + int(math.sin(i * 0.5) * 2)
                for dx in range(-2, 3):
                    if (curr_x + dx, curr_y) in self.data:
                        del self.data[(curr_x + dx, curr_y)]
                
        # Place large rock deposits in broad, irregular underground clusters.
        for block_type, cluster_count, y_min, y_max in (
            (DIORITE, WORLD_WIDTH // 48, 24, 76),
            (GRANITE, WORLD_WIDTH // 48, 24, 76),
            (ANDESITE, WORLD_WIDTH // 48, 32, 90),
            (GRAVEL, WORLD_WIDTH // 56, 20, 100),
        ):
            for _ in range(cluster_count):
                vx = rng.randrange(WORLD_WIDTH)
                vy = rng.randint(y_min, y_max)
                for _ in range(rng.randint(18, 30)):
                    radius_x = rng.randint(2, 4)
                    radius_y = rng.randint(2, 3)
                    for dx in range(-radius_x, radius_x + 1):
                        for dy in range(-radius_y, radius_y + 1):
                            if (dx * dx) / (radius_x * radius_x) + (dy * dy) / (radius_y * radius_y) > 1.2:
                                continue
                            pos = ((vx + dx) % WORLD_WIDTH, max(1, min(WORLD_HEIGHT - 2, vy + dy)))
                            if self.data.get(pos) in (STONE_BLOCK, DEEPSLATE):
                                self.data[pos] = block_type
                    vx = (vx + rng.randint(-3, 3)) % WORLD_WIDTH
                    vy = max(y_min, min(y_max, vy + rng.randint(-2, 2)))

        # Generate Veins (Coal and Iron) - Scaled for world size
        # Surface/Mid Coal
        for _ in range(WORLD_WIDTH // 3): 
            vx = rng.randint(0, WORLD_WIDTH - 1)
            vy = rng.randint(15, 60)
            for _ in range(rng.randint(6, 12)):
                if self.data.get((vx, vy)) in (STONE_BLOCK, DEEPSLATE):
                    self.data[(vx, vy)] = COAL_BLOCK
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(15, min(WORLD_HEIGHT - 1, vy + rng.choice([-1, 0, 1])))
        
        # Deep Coal
        for _ in range(WORLD_WIDTH // 5):
            vx = rng.randint(0, WORLD_WIDTH - 1)
            vy = rng.randint(60, WORLD_HEIGHT - 10)
            for _ in range(rng.randint(8, 14)):
                if self.data.get((vx, vy)) in (STONE_BLOCK, DEEPSLATE):
                    self.data[(vx, vy)] = COAL_BLOCK
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(60, min(WORLD_HEIGHT - 1, vy + rng.choice([-1, 0, 1])))
                
        # Iron Veins
        for _ in range(WORLD_WIDTH // 6):
            vx = rng.randint(0, WORLD_WIDTH - 1)
            vy = rng.randint(40, WORLD_HEIGHT - 10)
            for _ in range(rng.randint(5, 9)):
                if self.data.get((vx, vy)) in (STONE_BLOCK, DEEPSLATE):
                    self.data[(vx, vy)] = IRON_BLOCK
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(40, min(WORLD_HEIGHT - 1, vy + rng.choice([-1, 0, 1])))

        # Copper is more common in shallow and middle underground layers.
        for _ in range(WORLD_WIDTH // 10):
            vx = rng.randrange(WORLD_WIDTH)
            vy = rng.randint(28, 76)
            for _ in range(rng.randint(5, 10)):
                if self.data.get((vx, vy)) in (STONE_BLOCK, DEEPSLATE):
                    self.data[(vx, vy)] = COPPER_ORE
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(28, min(76, vy + rng.choice([-1, 0, 1])))

        # Diamond Veins - rare and deep
        for _ in range(max(8, WORLD_WIDTH // 24)):
            vx = rng.randint(0, WORLD_WIDTH - 1)
            vy = rng.randint(80, WORLD_HEIGHT - 8)
            for _ in range(rng.randint(3, 6)):
                if self.data.get((vx, vy)) == DEEPSLATE:
                    self.data[(vx, vy)] = DIAMOND_ORE
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(80, min(WORLD_HEIGHT - 1, vy + rng.choice([-1, 0, 1])))

        # Generate Trees (only in non-desert biome zones)
        DESERT_START = 200
        DESERT_END = 400
        for x in range(WORLD_WIDTH):
            is_desert = DESERT_START <= x % WORLD_WIDTH < DESERT_END
            h = 0
            while (x, h) not in self.data or self.data[(x, h)] != GRASS_BLOCK:
                h += 1
                if h >= WORLD_HEIGHT: break
            if h < WORLD_HEIGHT and not is_desert and rng.random() < 0.15:
                tree_type = "oak" if rng.random() < 0.7 else "birch"
                t_h = rng.randint(3, 5)
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

        # --- Desert Biome Generation ---
        for x in range(DESERT_START, DESERT_END):
            wx = x % WORLD_WIDTH
            # Find the surface
            h = 0
            while (wx, h) not in self.data:
                h += 1
                if h >= WORLD_HEIGHT: break
            if h >= WORLD_HEIGHT:
                continue
            # Replace top 4 layers with sand
            for depth in range(4):
                sy = h + depth
                if (wx, sy) in self.data and self.data[(wx, sy)] in (GRASS_BLOCK, DIRT_BLOCK):
                    self.data[(wx, sy)] = SAND_BLOCK
            # Remove any tall grass that was placed on sand
            if (wx, h - 1) in self.data and self.data[(wx, h - 1)] == TALL_GRASS:
                del self.data[(wx, h - 1)]
            # Place cacti (10% chance)
            if rng.random() < 0.10:
                cactus_h = rng.randint(2, 3)
                for ch in range(1, cactus_h + 1):
                    self.data[(wx, h - ch)] = CACTUS
            # Place dead bushes (8% chance)
            elif rng.random() < 0.08:
                self.data[(wx, h - 1)] = DEAD_BUSH

        # Generate Caves (Worms)
        for _ in range(15): # 15 cave systems
            vx, vy = rng.randint(0, WORLD_WIDTH-1), rng.randint(50, 90)
            for _ in range(30): # Worm length
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        ctx, cty = (vx + dx) % WORLD_WIDTH, max(0, min(WORLD_HEIGHT-1, vy + dy))
                        if (ctx, cty) in self.data and self.data[(ctx, cty)] == STONE_BLOCK:
                            del self.data[(ctx, cty)]
                vx = (vx + rng.choice([-1, 0, 1])) % WORLD_WIDTH
                vy = max(40, min(WORLD_HEIGHT - 1, vy + rng.choice([-1, 0, 1])))
        
        # Generate Ravines
        for _ in range(2):
            rx = rng.randint(0, WORLD_WIDTH-1)
            ry = rng.randint(40, 60)
            r_len = rng.randint(20, 40)
            r_width = rng.randint(2, 4)
            for i in range(r_len):
                cur_x = (rx + i) % WORLD_WIDTH
                cur_y = ry + int(math.sin(i * 0.2) * 5)
                for dx in range(-r_width, r_width+1):
                    for dy in range(-4, 5):
                        ctx, cty = (cur_x + dx) % WORLD_WIDTH, max(0, min(WORLD_HEIGHT-1, cur_y + dy))
                        if (ctx, cty) in self.data:
                            del self.data[(ctx, cty)]

        # Solid unbreakable Bedrock layer at the bottom of the world
        for x in range(WORLD_WIDTH):
            self.data[(x, WORLD_HEIGHT - 1)] = BEDROCK
        self.generate_villages()
        # Generated ponds are still pools; only newly placed water is simulated.
        self.active_water.clear()

    def generate_villages(self, village_locations=None, house_counts=None):
        if self.villages_generated:
            return

        def surface_y(x):
            for y in range(0, 40):
                if self.get_block(x, y) == GRASS_BLOCK:
                    return y
            return None

        if village_locations is None:
            village_locations = []
            for region_start, region_end in ((24, 180), (420, WORLD_WIDTH - 44)):
                candidates = []
                last_start = region_end - VILLAGE_FOOTPRINT_WIDTH
                for start_x in range(region_start, last_start + 1, 3):
                    surface = [
                        surface_y(x)
                        for x in range(start_x, start_x + VILLAGE_FOOTPRINT_WIDTH)
                    ]
                    if any(y is None for y in surface):
                        continue
                    candidates.append(start_x)
                if candidates:
                    village_locations.append((self.rng.choice(candidates), None))

        generated_locations = []
        for village_index, (village_x, saved_ground_y) in enumerate(village_locations):
            surfaces = [
                surface_y(x)
                for x in range(village_x, village_x + VILLAGE_FOOTPRINT_WIDTH)
            ]
            valid_surfaces = [y for y in surfaces if y is not None]
            if not valid_surfaces and saved_ground_y is None:
                continue
            village_ground_y = min(
                valid_surfaces + ([saved_ground_y] if saved_ground_y is not None else [])
            )
            generated_locations.append((village_x, village_ground_y))

            saved_house_count = (
                house_counts[village_index]
                if house_counts is not None and village_index < len(house_counts)
                else None
            )
            house_count = (
                saved_house_count
                if saved_house_count is not None and 4 <= saved_house_count <= 7
                else self.rng.randint(4, 7)
            )
            blacksmith_index = 0 if self.rng.random() < 0.25 else None
            house_spacing = 16
            for house_index in range(house_count):
                house_x = village_x + house_index * house_spacing
                is_blacksmith = house_index == blacksmith_index
                house_width = 6
                house_surfaces = [
                    surface_y(x) for x in range(house_x, house_x + house_width)
                ]
                house_ground_y = min(
                    (y for y in house_surfaces if y is not None),
                    default=saved_ground_y if saved_ground_y is not None else village_ground_y,
                )
                for x in range(house_x, house_x + house_width):
                    for y in range(house_ground_y):
                        if self.get_block(x, y) is not None:
                            self.set_block(x, y, None)
                    self.set_block(x, house_ground_y, PLANKS)

                if is_blacksmith:
                    for roof_row in range(3):
                        roof_width = min(house_width, 2 + roof_row * 2)
                        left = house_x + (house_width - roof_width) // 2
                        roof_y = house_ground_y - 7 + roof_row
                        for x in range(left, left + roof_width):
                            if x == left or x == left + roof_width - 1:
                                self.set_block(x, roof_y, W_STAIRS)
                                self.block_meta[(x, roof_y)] = {
                                    "facing": 1 if x == left else -1
                                }
                            else:
                                self.set_block(x, roof_y, PLANKS)

                    for x in (house_x, house_x + house_width - 1):
                        support_bottom = max(
                            house_ground_y,
                            house_surfaces[x - house_x]
                            if house_surfaces[x - house_x] is not None
                            else house_ground_y,
                        )
                        for y in range(house_ground_y - 4, support_bottom + 1):
                            self.set_block(x, y, OAK_LOG)
                else:
                    for roof_row in range(3):
                        roof_width = min(house_width, 2 + roof_row * 2)
                        left = house_x + (house_width - roof_width) // 2
                        roof_y = house_ground_y - 6 + roof_row
                        for x in range(left, left + roof_width):
                            if x == left or x == left + roof_width - 1:
                                self.set_block(x, roof_y, W_STAIRS)
                                self.block_meta[(x, roof_y)] = {
                                    "facing": 1 if x == left else -1
                                }
                            else:
                                self.set_block(x, roof_y, PLANKS)
                    for y in range(house_ground_y - 3, house_ground_y):
                        self.set_block(house_x, y, OAK_LOG)
                        self.set_block(house_x + house_width - 1, y, OAK_LOG)
                    self.set_block(house_x, house_ground_y - 2, GLASS_PANE)

                door_x = house_x + house_width - 1
                self.set_block(door_x, house_ground_y - 1, DOOR)
                self.set_block(door_x, house_ground_y - 2, DOOR_TOP)
                bed_x = house_x + (3 if is_blacksmith else 2)
                self.set_block(bed_x, house_ground_y - 1, BED)
                self.set_block(bed_x + 1, house_ground_y - 1, BED_RIGHT)
                chest_pos = (house_x + 1, house_ground_y - 1)
                self.set_block(*chest_pos, CHEST)
                self.chest_data[chest_pos] = self._generate_village_chest_loot(
                    is_blacksmith
                )
                if is_blacksmith:
                    forge_start = house_x - 12
                    for x in range(forge_start, house_x):
                        self.set_block(x, house_ground_y, STONE_BLOCK)

                    for x in range(house_x - 10, house_x - 1):
                        self.set_block(x, house_ground_y - 6, STONE_BLOCK)
                    for y in range(house_ground_y - 6, house_ground_y):
                        self.set_block(house_x - 1, y, LADDER)

                    for x in (house_x - 9, house_x - 8):
                        self.set_block(x, house_ground_y, None)
                        self.set_block(x, house_ground_y - 1, FURNACE)
                villager_x = house_x + 2 if is_blacksmith else house_x + house_width
                villager_ground_y = (
                    house_ground_y if is_blacksmith else surface_y(villager_x)
                )
                if villager_ground_y is None:
                    villager_ground_y = house_ground_y
                villager = Mob(
                    villager_x * TILE_SIZE,
                    (villager_ground_y - 2) * TILE_SIZE,
                    "villager",
                )
                self.mobs.append(villager)

            farm_x = village_x + (house_count - 1) * house_spacing + 18
            farm_surfaces = [
                surface_y(x) for x in range(farm_x, farm_x + 9)
            ]
            farm_ground_y = max(
                (y for y in farm_surfaces if y is not None),
                default=saved_ground_y if saved_ground_y is not None else village_ground_y,
            )
            for x in range(farm_x, farm_x + 9):
                for y in range(farm_ground_y):
                    if self.get_block(x, y) is not None:
                        self.set_block(x, y, None)

            crop_kinds = ("wheat", "carrot", "potato", "beetroot")
            for index in range(9):
                x = farm_x + index
                if index in (0, 8):
                    self.set_block(x, farm_ground_y, OAK_LOG)
                elif index % 2:
                    crop_kind = crop_kinds[index // 2]
                    crop_block = CROP_STAGES[crop_kind][self.rng.randint(1, 3)]
                    self.set_block(x, farm_ground_y, FARMLAND)
                    self.set_block(x, farm_ground_y - 1, crop_block)
                else:
                    self.set_block(x, farm_ground_y, WATER)
                    self.block_meta[(x, farm_ground_y)] = {"level": 7, "source": True}
            self._generate_village_hay_bales(farm_x)
            self._spawn_village_golem(village_x, farm_x)

        self.village_locations = generated_locations
        self.village_generation_version = VILLAGE_GENERATION_VERSION
        self.villages_generated = True
        self._generate_natural_flowers()

    def _generate_village_hay_bales(self, farm_x):
        for offset, height in ((-4, 1), (-3, 2), (-2, 2), (-1, 1)):
            x = farm_x + offset
            ground_y = next(
                (y for y in range(40) if self.get_block(x, y) == GRASS_BLOCK),
                None,
            )
            if ground_y is None:
                continue
            for stack_index in range(height):
                y = ground_y - 1 - stack_index
                if y < 0:
                    break
                block = self.get_block(x, y)
                if block == TALL_GRASS:
                    self.set_block(x, y, None)
                elif block is not None:
                    break
                self.set_block(x, y, HAY_BALE)

    def _generate_hay_bales_for_existing_villages(self):
        for village_x, _ in self.village_locations:
            farm_found = False
            for farm_y in range(1, 40):
                for farm_x in range(village_x, village_x + VILLAGE_FOOTPRINT_WIDTH - 8):
                    if (
                        self.get_block(farm_x, farm_y) == OAK_LOG
                        and self.get_block(farm_x + 8, farm_y) == OAK_LOG
                        and any(
                            self.get_block(farm_x + offset, farm_y) in (FARMLAND, WATER)
                            for offset in range(1, 8)
                        )
                    ):
                        self._generate_village_hay_bales(farm_x)
                        farm_found = True
                        break
                if farm_found:
                    break

    def _generate_natural_flowers(self):
        surface_columns = []
        for x in range(WORLD_WIDTH):
            if 200 <= x < 400:
                continue
            for ground_y in range(40):
                if self.get_block(x, ground_y) == GRASS_BLOCK:
                    if self.get_block(x, ground_y - 1) in (None, TALL_GRASS):
                        surface_columns.append((x, ground_y))
                    break

        if not surface_columns:
            return

        patch_count = min(max(1, WORLD_WIDTH // 128), len(surface_columns))
        for flower_type in (POPPY, DANDELION, CORNFLOWER):
            centers = self.rng.sample(surface_columns, patch_count)
            placed_flower = False
            for center_x, _ in centers:
                for _ in range(self.rng.randint(3, 5)):
                    x = (center_x + self.rng.randint(-2, 2)) % WORLD_WIDTH
                    if 200 <= x < 400:
                        continue
                    ground_y = next(
                        (y for y in range(40) if self.get_block(x, y) == GRASS_BLOCK),
                        None,
                    )
                    if ground_y is None:
                        continue
                    flower_y = ground_y - 1
                    if self.get_block(x, flower_y) in (None, TALL_GRASS):
                        self.set_block(x, flower_y, flower_type)
                        placed_flower = True

            if not placed_flower:
                for x, ground_y in self.rng.sample(
                    surface_columns, min(len(surface_columns), 32)
                ):
                    if self.get_block(x, ground_y - 1) in (None, TALL_GRASS):
                        self.set_block(x, ground_y - 1, flower_type)
                        break

    def _spawn_village_golem(self, village_x, farm_x=None):
        for mob in self.mobs:
            if mob.m_type != "iron_golem":
                continue
            golem_tile_x = mob.rect.centerx // TILE_SIZE
            offset = (golem_tile_x - village_x + WORLD_WIDTH // 2) % WORLD_WIDTH - WORLD_WIDTH // 2
            if 0 <= offset < VILLAGE_FOOTPRINT_WIDTH:
                return mob

        spawn_x = (farm_x + 10) % WORLD_WIDTH if farm_x is not None else (village_x + 64) % WORLD_WIDTH
        ground_y = next(
            (y for y in range(40) if self.get_block(spawn_x, y) == GRASS_BLOCK),
            None,
        )
        if ground_y is None:
            return None

        golem = Mob(
            spawn_x * TILE_SIZE,
            ground_y * TILE_SIZE - (TILE_SIZE * 3 - 4),
            "iron_golem",
        )
        self.mobs.append(golem)
        return golem

    def _spawn_golems_for_existing_villages(self):
        for village_x, _ in self.village_locations:
            farm_x = None
            for farm_y in range(1, 40):
                for candidate_x in range(village_x, village_x + VILLAGE_FOOTPRINT_WIDTH - 8):
                    if (
                        self.get_block(candidate_x, farm_y) == OAK_LOG
                        and self.get_block(candidate_x + 8, farm_y) == OAK_LOG
                        and any(
                            self.get_block(candidate_x + offset, farm_y) in (FARMLAND, WATER)
                            for offset in range(1, 8)
                        )
                    ):
                        farm_x = candidate_x
                        break
                if farm_x is not None:
                    break
            self._spawn_village_golem(village_x, farm_x)

    def _generate_village_chest_loot(self, is_blacksmith):
        if is_blacksmith:
            loot_table = (
                (APPLE, 1, 3, 15),
                (BREAD, 1, 3, 15),
                (IRON_INGOT, 1, 5, 10),
                (COPPER_SPEAR, 1, 1, 7),
                (OAK_SAPLING, 3, 7, 5),
                (OBSIDIAN, 3, 7, 5),
                (GOLD_INGOT, 1, 3, 5),
                (I_PICK, 1, 1, 5),
                (IRON_SPEAR, 1, 1, 5),
                (I_SWORD, 1, 1, 5),
                (I_HELMET, 1, 1, 5),
                (I_CHEST, 1, 1, 5),
                (I_LEGS, 1, 1, 5),
                (I_BOOTS, 1, 1, 5),
                (DIAMOND, 1, 3, 3),
                (SADDLE, 1, 1, 3),
                (COPPER_HORSE_ARMOR, 1, 1, 1),
                (IRON_HORSE_ARMOR, 1, 1, 1),
                (GOLDEN_HORSE_ARMOR, 1, 1, 1),
                (DIAMOND_HORSE_ARMOR, 1, 1, 1),
            )
        else:
            loot_table = (
                (POTATO_ITEM, 1, 7, 10),
                (APPLE, 1, 5, 10),
                (BREAD, 1, 4, 10),
                (OAK_SAPLING, 1, 2, 5),
                (EMERALD, 1, 4, 2),
                (DANDELION, 1, 1, 2),
                (GOLD_NUGGET, 1, 3, 1),
                (BOOK, 1, 1, 1),
                (FEATHER, 1, 1, 1),
                (POPPY, 1, 1, 1),
            )

        chest_slots = [None] * 27
        roll_count = self.rng.randint(3, 8)
        for index in range(roll_count):
            item_type, minimum, maximum, _ = self.rng.choices(
                loot_table,
                weights=[entry[3] for entry in loot_table],
                k=1,
            )[0]
            item = {"type": item_type, "count": self.rng.randint(minimum, maximum)}
            if item_type in MAX_DURABILITY:
                item["durability"] = MAX_DURABILITY[item_type]
            chest_slots[index] = item

        if not is_blacksmith and self.rng.randrange(3) == 0:
            chest_slots[roll_count] = {"type": BUNDLE, "count": 1}
        return chest_slots

    def find_safe_spawn(self, player):
        """Finds a safe Y level for the player at their current X to prevent getting stuck."""
        start_x = int(player.rect.centerx // TILE_SIZE) % WORLD_WIDTH
        # Start from top and go down
        for y in range(0, WORLD_HEIGHT - 2):
            if (start_x, y) not in self.data and (start_x, y+1) not in self.data:
                # Found 2 empty blocks. Check if there is ground below
                if (start_x, y+2) in self.data:
                    player.rect.y = y * TILE_SIZE
                    player.vel_y = 0
                    print(f"Spawned safely at {start_x}, {y}")
                    return
        # Fallback: if no ground found, just find any empty space
        player.rect.y = 10 * TILE_SIZE

    def get_surrounding_blocks(self, player_rect):
        blocks = []
        p_x = int(player_rect.x // TILE_SIZE)
        p_y = int(player_rect.y // TILE_SIZE)
        for x_off in range(-2, 3):
            for y_off in range(-2, 4):
                tx, ty = (p_x + x_off) % WORLD_WIDTH, p_y + y_off
                if (tx, ty) in self.data:
                    b_type = self.data[(tx, ty)]
                    if (
                        b_type == TALL_GRASS
                        or b_type in (POPPY, DANDELION, CORNFLOWER)
                        or b_type in (OAK_SAPLING, BIRCH_SAPLING)
                        or b_type in CROP_STAGE_TO_KIND
                        or b_type in (
                            FENCE_GATE_OPEN, DOOR_OPEN, DOOR_OPEN_TOP,
                            TRAPDOOR_OPEN, WATER, LADDER, BOAT, TORCH, FIRE,
                        )
                    ):
                        continue
                    bx, by = (p_x + x_off) * TILE_SIZE, ty * TILE_SIZE
                    if b_type == FARMLAND:
                        blocks.append(pygame.Rect(bx, by + 4, TILE_SIZE, TILE_SIZE - 4))
                    elif b_type in (W_SLAB, C_SLAB, SS_SLAB):
                        blocks.append(pygame.Rect(bx, by + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                    elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS):
                        # Simple 2-part hitbox for stairs
                        blocks.append(pygame.Rect(bx, by + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2)) # Base
                        facing = self.block_meta.get((tx, ty), {}).get("facing", -1)
                        step_x = bx if facing == -1 else bx + TILE_SIZE//2
                        blocks.append(pygame.Rect(step_x, by, TILE_SIZE//2, TILE_SIZE//2)) # Top Step
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
        if self.is_precipitating():
            dim = 0.72 if self.weather_type == "rain" else 0.82
            bg_color = tuple(max(0, int(c * dim)) for c in bg_color)
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
        if self.is_precipitating():
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            if self.weather_type == "rain":
                overlay.fill((30, 40, 60, int(90 * self.weather_intensity)))
                for _ in range(int(100 * self.weather_intensity)):
                    rx = random.randrange(SCREEN_WIDTH)
                    ry = random.randrange(SCREEN_HEIGHT)
                    pygame.draw.line(overlay, (185, 200, 220, 170), (rx, ry), (rx + 1, ry + 10), 1)
            else:
                overlay.fill((50, 55, 70, int(80 * self.weather_intensity)))
                for _ in range(int(70 * self.weather_intensity)):
                    rx = random.randrange(SCREEN_WIDTH)
                    ry = random.randrange(SCREEN_HEIGHT)
                    pygame.draw.circle(overlay, (230, 235, 245, 200), (rx, ry), 1)
            surface.blit(overlay, (0, 0))
        
        # Draw chunks that are visible on screen
        start_cx = int(scroll_x // (CHUNK_SIZE * TILE_SIZE)) - 1
        end_cx = int((scroll_x + SCREEN_WIDTH) // (CHUNK_SIZE * TILE_SIZE)) + 1
        
        torch_glows = []
        for cx in range(start_cx, end_cx + 1):
            # Wrap chunk index for infinite world
            lookup_cx = cx % (WORLD_WIDTH // CHUNK_SIZE)
            for cy in range(0, WORLD_HEIGHT // CHUNK_SIZE + 1):
                chunk = self.chunks.get((lookup_cx, cy))
                if chunk:
                    for (tx, ty), b_type in chunk.items():
                        # Calculate screen position based on current virtual chunk column
                        rel_tx = tx % CHUNK_SIZE
                        draw_x = (cx * CHUNK_SIZE + rel_tx) * TILE_SIZE - scroll_x
                        draw_y = ty * TILE_SIZE - scroll_y
                        
                        # Only draw blocks that are visible on screen
                        if -TILE_SIZE < draw_x < SCREEN_WIDTH and -TILE_SIZE < draw_y < SCREEN_HEIGHT:
                            if b_type in (COAL_BLOCK, IRON_BLOCK, DIAMOND_ORE, COPPER_ORE):
                                stone_color = (70, 70, 80) if ty >= 80 else COLOR_STONE
                                pygame.draw.rect(surface, stone_color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                ore_color = {
                                    COAL_BLOCK: COLOR_COAL,
                                    IRON_BLOCK: COLOR_IRON,
                                    DIAMOND_ORE: COLOR_DIAMOND,
                                    COPPER_ORE: (190, 110, 55),
                                }[b_type]
                                # Chunky ore shapes
                                pygame.draw.rect(surface, ore_color, (draw_x + 4, draw_y + 6, 10, 8))
                                pygame.draw.rect(surface, ore_color, (draw_x + 16, draw_y + 18, 12, 10))
                                pygame.draw.rect(surface, ore_color, (draw_x + 22, draw_y + 4, 8, 8))
                            elif b_type in (DIORITE, GRANITE, GRAVEL, ANDESITE, DEEPSLATE):
                                base_color, speckle_color = {
                                    DIORITE: ((190, 190, 185), (130, 130, 130)),
                                    GRANITE: ((145, 95, 85), (90, 55, 50)),
                                    GRAVEL: ((125, 120, 110), (80, 75, 70)),
                                    ANDESITE: ((115, 120, 125), (75, 80, 85)),
                                    DEEPSLATE: ((65, 70, 80), (35, 40, 50)),
                                }[b_type]
                                pygame.draw.rect(surface, base_color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                for dx, dy in ((5, 6), (19, 10), (11, 23), (25, 26)):
                                    pygame.draw.rect(surface, speckle_color, (draw_x + dx, draw_y + dy, 3, 3))
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
                            elif b_type == BEDROCK:
                                pygame.draw.rect(surface, (25, 25, 25), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                pygame.draw.rect(surface, (10, 10, 10), (draw_x + 2, draw_y + 2, 8, 8))
                                pygame.draw.rect(surface, (45, 45, 45), (draw_x + 12, draw_y + 4, 10, 6))
                                pygame.draw.rect(surface, (10, 10, 10), (draw_x + 22, draw_y + 12, 6, 12))
                                pygame.draw.rect(surface, (45, 45, 45), (draw_x + 4, draw_y + 20, 8, 8))
                            elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS):
                                color = COLOR_PLANKS if b_type == W_STAIRS else ((100, 100, 100) if b_type == C_STAIRS else (180, 180, 190))
                                pygame.draw.rect(surface, color, (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                                # Orientation from meta
                                facing = self.block_meta.get((tx, ty), {}).get("facing", -1)
                                step_x = draw_x if facing == -1 else draw_x + TILE_SIZE//2
                                pygame.draw.rect(surface, color, (step_x, draw_y, TILE_SIZE//2, TILE_SIZE//2))
                                # Outlines
                                pygame.draw.rect(surface, (0,0,0), (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), 1)
                                pygame.draw.rect(surface, (0,0,0), (step_x, draw_y, TILE_SIZE//2, TILE_SIZE//2), 1)
                            elif b_type in (W_SLAB, C_SLAB, SS_SLAB):
                                color = COLOR_PLANKS if b_type == W_SLAB else ((100, 100, 100) if b_type == C_SLAB else (180, 180, 190))
                                pygame.draw.rect(surface, color, (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2))
                                pygame.draw.rect(surface, (0,0,0), (draw_x, draw_y + TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), 1)
                            elif b_type == TALL_GRASS:
                                # Draw blades
                                pygame.draw.line(surface, COLOR_GRASS, (draw_x + 8, draw_y + TILE_SIZE), (draw_x + 6, draw_y + 16), 2)
                                pygame.draw.line(surface, COLOR_GRASS, (draw_x + 16, draw_y + TILE_SIZE), (draw_x + 16, draw_y + 12), 2)
                                pygame.draw.line(surface, COLOR_GRASS, (draw_x + 24, draw_y + TILE_SIZE), (draw_x + 26, draw_y + 16), 2)
                            elif b_type in (OAK_SAPLING, BIRCH_SAPLING):
                                leaf_color = COLOR_LEAVES_B if b_type == BIRCH_SAPLING else COLOR_LEAVES_G
                                pygame.draw.line(surface, (105, 75, 40), (draw_x + 16, draw_y + TILE_SIZE), (draw_x + 16, draw_y + 13), 3)
                                pygame.draw.circle(surface, leaf_color, (draw_x + 16, draw_y + 13), 7)
                                pygame.draw.circle(surface, leaf_color, (draw_x + 10, draw_y + 18), 4)
                                pygame.draw.circle(surface, leaf_color, (draw_x + 22, draw_y + 18), 4)
                            elif b_type == FARMLAND:
                                wet = self.is_farmland_watered(tx, ty)
                                soil_color = (80, 50, 30) if wet else (126, 91, 58)
                                top_color = (60, 40, 20) if wet else (95, 66, 40)
                                pygame.draw.rect(surface, soil_color, (draw_x, draw_y + 4, TILE_SIZE, TILE_SIZE - 4))
                                pygame.draw.rect(surface, top_color, (draw_x, draw_y + 4, TILE_SIZE, 4))
                            elif b_type in CROP_STAGE_TO_KIND:
                                crop_kind = CROP_STAGE_TO_KIND[b_type]
                                stage = CROP_STAGES[crop_kind].index(b_type)
                                crop_colors = {
                                    "wheat": (50, 200, 50) if stage < 3 else (220, 200, 50),
                                    "carrot": (55, 175, 45),
                                    "potato": (75, 155, 45),
                                    "beetroot": (65, 165, 55),
                                }
                                crop_color = crop_colors[crop_kind]
                                height = 8 + stage * 6
                                for x_off in (8, 16, 24):
                                    top_y = draw_y + TILE_SIZE - height
                                    pygame.draw.line(surface, crop_color, (draw_x + x_off, draw_y + TILE_SIZE), (draw_x + x_off, top_y), 2)
                                    if stage >= 2:
                                        pygame.draw.line(surface, crop_color, (draw_x + x_off, top_y + 7), (draw_x + x_off - 4, top_y + 3), 2)
                                        pygame.draw.line(surface, crop_color, (draw_x + x_off, top_y + 10), (draw_x + x_off + 4, top_y + 6), 2)
                                if crop_kind == "carrot" and stage == 3:
                                    pygame.draw.ellipse(surface, (235, 115, 35), (draw_x + 10, draw_y + 21, 5, 9))
                                    pygame.draw.ellipse(surface, (235, 115, 35), (draw_x + 20, draw_y + 20, 5, 10))
                                elif crop_kind == "potato" and stage == 3:
                                    pygame.draw.circle(surface, (190, 160, 95), (draw_x + 11, draw_y + 25), 3)
                                    pygame.draw.circle(surface, (190, 160, 95), (draw_x + 22, draw_y + 26), 3)
                                elif crop_kind == "beetroot" and stage == 3:
                                    pygame.draw.circle(surface, (155, 40, 55), (draw_x + 11, draw_y + 25), 4)
                                    pygame.draw.circle(surface, (155, 40, 55), (draw_x + 22, draw_y + 25), 4)
                            elif b_type == CHEST:
                                # Draw chest body
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 4))
                                
                                # Handle connections for visual double chests
                                left = self.data.get(((tx - 1) % WORLD_WIDTH, ty)) == CHEST
                                right = self.data.get(((tx + 1) % WORLD_WIDTH, ty)) == CHEST
                                
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
                            elif b_type == TORCH:
                                facing = self.block_meta.get((tx, ty), {}).get("facing", 0)
                                if facing == 1:
                                    torch_glows.append((draw_x + 5, draw_y + 11))
                                    pygame.draw.line(surface, (90, 55, 20), (draw_x + 6, draw_y + 18), (draw_x + 3, draw_y + 8), 3)
                                    pygame.draw.polygon(surface, (255, 180, 60), [
                                        (draw_x + 1, draw_y + 10),
                                        (draw_x + 5, draw_y + 3),
                                        (draw_x + 9, draw_y + 11)
                                    ])
                                    pygame.draw.circle(surface, (255, 245, 200), (draw_x + 5, draw_y + 6), 2)
                                elif facing == -1:
                                    torch_glows.append((draw_x + 11, draw_y + 11))
                                    pygame.draw.line(surface, (90, 55, 20), (draw_x + 10, draw_y + 18), (draw_x + 13, draw_y + 8), 3)
                                    pygame.draw.polygon(surface, (255, 180, 60), [
                                        (draw_x + 7, draw_y + 11),
                                        (draw_x + 11, draw_y + 3),
                                        (draw_x + 15, draw_y + 10)
                                    ])
                                    pygame.draw.circle(surface, (255, 245, 200), (draw_x + 11, draw_y + 6), 2)
                                else:
                                    torch_glows.append((draw_x + 8, draw_y + 14))
                                    pygame.draw.rect(surface, (90, 55, 20), (draw_x + 7, draw_y + 11, 4, 17))
                                    pygame.draw.polygon(surface, (255, 180, 60), [
                                        (draw_x + 5, draw_y + 11),
                                        (draw_x + 9, draw_y + 2),
                                        (draw_x + 13, draw_y + 11)
                                    ])
                                    pygame.draw.circle(surface, (255, 245, 200), (draw_x + 9, draw_y + 6), 2)
                            elif b_type == FIRE:
                                torch_glows.append((draw_x + TILE_SIZE // 2, draw_y + TILE_SIZE // 2))
                                pygame.draw.polygon(surface, (245, 75, 15), [
                                    (draw_x + 4, draw_y + TILE_SIZE),
                                    (draw_x + 7, draw_y + 15),
                                    (draw_x + 13, draw_y + 20),
                                    (draw_x + 16, draw_y + 4),
                                    (draw_x + 24, draw_y + 17),
                                    (draw_x + 28, draw_y + TILE_SIZE),
                                ])
                                pygame.draw.polygon(surface, (255, 195, 35), [
                                    (draw_x + 10, draw_y + TILE_SIZE),
                                    (draw_x + 13, draw_y + 19),
                                    (draw_x + 17, draw_y + 24),
                                    (draw_x + 20, draw_y + 14),
                                    (draw_x + 24, draw_y + TILE_SIZE),
                                ])
                            elif b_type in BED_BLOCKS:
                                is_red_bed = b_type in (RED_BED, RED_BED_RIGHT)
                                is_yellow_bed = b_type in (YELLOW_BED, YELLOW_BED_RIGHT)
                                is_orange_bed = b_type in (ORANGE_BED, ORANGE_BED_RIGHT)
                                is_green_bed = b_type in (GREEN_BED, GREEN_BED_RIGHT)
                                is_blue_bed = b_type in (BLUE_BED, BLUE_BED_RIGHT)
                                is_purple_bed = b_type in (PURPLE_BED, PURPLE_BED_RIGHT)
                                is_cyan_bed = b_type in (CYAN_BED, CYAN_BED_RIGHT)
                                is_bed_head = b_type in (BED, RED_BED, YELLOW_BED, ORANGE_BED, GREEN_BED, BLUE_BED, PURPLE_BED, CYAN_BED)
                                mattress_color = COLOR_RED if is_red_bed else (245, 215, 65) if is_yellow_bed else (245, 135, 35) if is_orange_bed else (60, 170, 65) if is_green_bed else (55, 105, 210) if is_blue_bed else (145, 65, 185) if is_purple_bed else (45, 190, 195) if is_cyan_bed else COLOR_WHITE
                                outline_color = (180, 60, 60) if is_red_bed else (180, 150, 35) if is_yellow_bed else (185, 85, 20) if is_orange_bed else (35, 115, 40) if is_green_bed else (35, 65, 145) if is_blue_bed else (90, 35, 125) if is_purple_bed else (20, 115, 125) if is_cyan_bed else (170, 170, 170)
                                pygame.draw.rect(surface, mattress_color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                if is_bed_head:
                                    pygame.draw.rect(surface, COLOR_WHITE, (draw_x + 2, draw_y + 2, TILE_SIZE - 4, TILE_SIZE // 4))
                                pygame.draw.rect(surface, outline_color, (draw_x, draw_y + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2), 2)
                            elif b_type in (FENCE, FENCE_GATE, FENCE_GATE_OPEN):
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + 12, draw_y, 8, TILE_SIZE)) # Post
                                if b_type == FENCE_GATE:
                                    pygame.draw.rect(surface, (140, 100, 50), (draw_x + 4, draw_y + 8, 24, 16))
                                elif b_type == FENCE_GATE_OPEN:
                                    pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y, 4, TILE_SIZE))
                                    pygame.draw.rect(surface, (120, 80, 40), (draw_x + 28, draw_y, 4, TILE_SIZE))
                                if b_type == FENCE:
                                    left = self.data.get(((tx-1)%WORLD_WIDTH, ty))
                                    if left and (left in (FENCE, FENCE_GATE, FENCE_GATE_OPEN) or left not in (TALL_GRASS, WHEAT_STG0, WHEAT_STG1, WHEAT_STG2, WHEAT_STG3)):
                                        pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 8, 12, 4))
                                        pygame.draw.rect(surface, (120, 80, 40), (draw_x, draw_y + 20, 12, 4))
                                    right = self.data.get(((tx+1)%WORLD_WIDTH, ty))
                                    if right and (right in (FENCE, FENCE_GATE, FENCE_GATE_OPEN) or right not in (TALL_GRASS, WHEAT_STG0, WHEAT_STG1, WHEAT_STG2, WHEAT_STG3)):
                                        pygame.draw.rect(surface, (120, 80, 40), (draw_x + 20, draw_y + 8, 12, 4))
                                        pygame.draw.rect(surface, (120, 80, 40), (draw_x + 20, draw_y + 20, 12, 4))
                            elif b_type == DOOR:
                                pygame.draw.rect(surface, (100, 60, 20), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                pygame.draw.rect(surface, (80, 40, 10), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)
                                pygame.draw.circle(surface, (200, 150, 50), (draw_x + 24, draw_y + 16), 3) # Knob
                            elif b_type == DOOR_TOP:
                                pygame.draw.rect(surface, (100, 60, 20), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                pygame.draw.rect(surface, (80, 40, 10), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)
                            elif b_type == DOOR_OPEN:
                                pygame.draw.rect(surface, (100, 60, 20), (draw_x, draw_y, 6, TILE_SIZE))
                            elif b_type == DOOR_OPEN_TOP:
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
                            elif b_type == WATER:
                                # Dynamic water height based on level (7 = full, 0 = lowest)
                                level = self.block_meta.get((tx, ty), {}).get("level", 7)
                                height_ratio = (level + 1) / 8.0
                                pixel_h = int(TILE_SIZE * height_ratio)
                                y_off = TILE_SIZE - pixel_h
                                
                                water_surf = pygame.Surface((TILE_SIZE, pixel_h), pygame.SRCALPHA)
                                water_surf.fill((0, 100, 255, 150))
                                surface.blit(water_surf, (draw_x, draw_y + y_off))
                            elif b_type == GLASS:
                                glass_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                                glass_surface.fill((170, 220, 235, 105))
                                surface.blit(glass_surface, (draw_x, draw_y))
                                pygame.draw.rect(surface, (215, 240, 245), (draw_x, draw_y, TILE_SIZE, TILE_SIZE), 2)
                            elif b_type == GLASS_PANE:
                                pane_size = TILE_SIZE - 4
                                pane_rect = pygame.Rect(
                                    draw_x + 2, draw_y + 2, pane_size, pane_size
                                )
                                pane_surface = pygame.Surface(
                                    (pane_size, pane_size), pygame.SRCALPHA
                                )
                                pane_surface.fill((175, 225, 240, 75))
                                surface.blit(pane_surface, pane_rect.topleft)
                                pygame.draw.rect(surface, (215, 240, 245), pane_rect, 1)
                                pygame.draw.line(
                                    surface, (215, 240, 245),
                                    (pane_rect.left + 1, pane_rect.top + 1),
                                    (pane_rect.right - 2, pane_rect.top + 1), 1
                                )
                            elif b_type == BOAT:
                                # Draw boat in world
                                pygame.draw.polygon(surface, (100, 70, 40), [(draw_x, draw_y + 20), (draw_x + TILE_SIZE, draw_y + 20), (draw_x + TILE_SIZE + 4, draw_y + 10), (draw_x - 4, draw_y + 10)])
                                pygame.draw.rect(surface, (120, 80, 40), (draw_x + 4, draw_y + 18, TILE_SIZE - 8, 4))
                            elif b_type == SAND_BLOCK:
                                pygame.draw.rect(surface, (220, 200, 130), (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                pygame.draw.rect(surface, (200, 180, 110), (draw_x + 4, draw_y + 4, 10, 8))  # Shade detail
                                pygame.draw.rect(surface, (200, 180, 110), (draw_x + 18, draw_y + 16, 8, 6))
                            elif b_type == CACTUS:
                                # Cactus body
                                pygame.draw.rect(surface, (70, 150, 50), (draw_x + 6, draw_y, TILE_SIZE - 12, TILE_SIZE))
                                # Cactus arms
                                pygame.draw.rect(surface, (70, 150, 50), (draw_x, draw_y + 8, 6, 8))
                                pygame.draw.rect(surface, (70, 150, 50), (draw_x + TILE_SIZE - 6, draw_y + 12, 6, 8))
                                # Spines
                                pygame.draw.line(surface, (90, 70, 20), (draw_x + 3, draw_y + 8), (draw_x - 3, draw_y + 6), 1)
                                pygame.draw.line(surface, (90, 70, 20), (draw_x + 3, draw_y + 12), (draw_x - 3, draw_y + 14), 1)
                                pygame.draw.line(surface, (90, 70, 20), (draw_x + TILE_SIZE - 3, draw_y + 12), (draw_x + TILE_SIZE + 3, draw_y + 10), 1)
                            elif b_type == DEAD_BUSH:
                                # Dead bush - small twigs drawn from center
                                cx, cy = draw_x + TILE_SIZE // 2, draw_y + TILE_SIZE - 4
                                bush_c = (140, 100, 50)
                                pygame.draw.line(surface, bush_c, (cx, cy), (cx - 8, cy - 12), 2)
                                pygame.draw.line(surface, bush_c, (cx, cy), (cx + 8, cy - 12), 2)
                                pygame.draw.line(surface, bush_c, (cx, cy), (cx - 4, cy - 16), 1)
                                pygame.draw.line(surface, bush_c, (cx, cy), (cx + 4, cy - 16), 1)
                                pygame.draw.line(surface, bush_c, (cx - 6, cy - 8), (cx - 12, cy - 6), 1)
                                pygame.draw.line(surface, bush_c, (cx + 6, cy - 8), (cx + 12, cy - 6), 1)
                            elif b_type in (POPPY, DANDELION, CORNFLOWER):
                                pygame.draw.line(surface, (55, 125, 45), (draw_x + 16, draw_y + TILE_SIZE), (draw_x + 16, draw_y + 13), 2)
                                flower_color = (245, 215, 45) if b_type == DANDELION else (55, 105, 220) if b_type == CORNFLOWER else (205, 35, 45)
                                flower_highlight = (255, 245, 120) if b_type == DANDELION else (145, 185, 255) if b_type == CORNFLOWER else (245, 90, 85)
                                pygame.draw.circle(surface, flower_color, (draw_x + 16, draw_y + 11), 5)
                                pygame.draw.circle(surface, flower_highlight, (draw_x + 16, draw_y + 11), 2)
                            else:
                                block_colors = {
                                    GRASS_BLOCK: COLOR_GRASS, DIRT_BLOCK: COLOR_DIRT, STONE_BLOCK: COLOR_STONE,
                                    COAL_BLOCK: (30, 30, 30), IRON_BLOCK: (160, 160, 160),
                                    IRON_BLOCK_PROD: (220, 220, 220), COBBLESTONE: (120, 120, 120),
                                    SMOOTH_STONE: (180, 180, 180), OAK_LOG: (100, 70, 40),
                                    BIRCH_LOG: (220, 220, 220), PLANKS: COLOR_PLANKS,
                                    COAL_BLOCK_ITEM: (20, 20, 20),
                                    BOAT: (100, 70, 40)
                                }
                                color = block_colors.get(b_type, (255, 0, 255)) # Magenta for unknown
                                pygame.draw.rect(surface, color, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                                if b_type in (COAL_BLOCK, IRON_BLOCK, DIAMOND_ORE, COPPER_ORE): # Add speckles for ores
                                    speckle_c = {
                                        COAL_BLOCK: (0, 0, 0),
                                        IRON_BLOCK: (140, 100, 60),
                                        DIAMOND_ORE: (120, 240, 240),
                                        COPPER_ORE: (190, 110, 55),
                                    }[b_type]
                                    # Deterministic speckles based on block pos
                                    seed = (tx * 7 + ty * 13) % 100
                                    for i in range(4):
                                        sx = 4 + ((seed + i * 21) % 20)
                                        sy = 4 + ((seed + i * 37) % 20)
                                        pygame.draw.rect(surface, speckle_c, (draw_x + sx, draw_y + sy, 4, 4))
                                elif b_type == COAL_BLOCK_ITEM:
                                    pygame.draw.rect(surface, (60, 60, 60), (draw_x + 4, draw_y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)

        if torch_glows:
            glow_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for gx, gy in torch_glows:
                pygame.draw.circle(glow_layer, (255, 220, 120, 50), (gx, gy), 96)
                pygame.draw.circle(glow_layer, (255, 180, 80, 34), (gx, gy), 58)
                pygame.draw.circle(glow_layer, (255, 245, 200, 72), (gx, gy), 18)
            surface.blit(glow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


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
    def __init__(self, x, y, item_type, count=1, durability=None):
        self.rect = pygame.Rect(x, y, 16, 16)
        self.item_type = item_type
        self.count = count
        self.durability = durability
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
        if (bx, by) in world.data and world.data[(bx, by)] not in (AIR, WATER, TALL_GRASS, POPPY, DANDELION, CORNFLOWER, LADDER, TORCH, FIRE):
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

class ThrownPearl:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        dx = target_x - self.x
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        dy = target_y - self.y
        distance = max(0.001, math.hypot(dx, dy))
        self.vel_x = (dx / distance) * 14.0
        self.vel_y = (dy / distance) * 14.0
        self.rect = pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)
        self.spawn_time = pygame.time.get_ticks()
        self.last_safe_x = self.x
        self.last_safe_y = self.y

    def update(self, world):
        self.vel_y = min(self.vel_y + 0.2, 8.0)
        steps = max(1, int(math.ceil(max(abs(self.vel_x), abs(self.vel_y)) / 4.0)))
        step_x = self.vel_x / steps
        step_y = self.vel_y / steps

        for _ in range(steps):
            self.x = (self.x + step_x) % WORLD_PIXELS
            self.y += step_y
            self.rect.center = (int(self.x), int(self.y))
            for block_rect in world.get_surrounding_blocks(self.rect):
                if self.rect.colliderect(block_rect):
                    self.x = self.last_safe_x
                    self.y = self.last_safe_y
                    self.rect.center = (int(self.x), int(self.y))
                    return True, (self.x, self.y)
            self.last_safe_x = self.x
            self.last_safe_y = self.y

        if self.y < 0 or self.y > WORLD_HEIGHT * TILE_SIZE or pygame.time.get_ticks() - self.spawn_time > 5000:
            return True, None

        return False, None

    def draw(self, surface, scroll_x, scroll_y):
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx = self.rect.centerx - int(scroll_x) + offset
            if dx < -40 or dx > SCREEN_WIDTH + 40:
                continue
            dy = self.rect.centery - int(scroll_y)
            pygame.draw.circle(surface, (90, 0, 140), (dx, dy), 5)
            pygame.draw.circle(surface, (220, 220, 255), (dx - 1, dy - 1), 2)

class ExplosionEffect:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.age = 0
        self.duration = 18
        self.max_radius = 80

    def update(self):
        self.age += 1
        return self.age >= self.duration

    def draw(self, surface, scroll_x, scroll_y):
        progress = self.age / self.duration
        radius = max(4, int(self.max_radius * progress))
        alpha = max(0, int(255 * (1 - progress)))
        for offset in (-WORLD_PIXELS, 0, WORLD_PIXELS):
            x = int(self.x - scroll_x + offset)
            y = int(self.y - scroll_y)
            if not (-radius <= x <= SCREEN_WIDTH + radius and -radius <= y <= SCREEN_HEIGHT + radius):
                continue
            effect = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            center = (radius + 1, radius + 1)
            pygame.draw.circle(effect, (255, 110, 20, alpha), center, radius, 5)
            pygame.draw.circle(effect, (255, 210, 70, alpha), center, max(2, radius // 3))
            surface.blit(effect, (x - radius - 1, y - radius - 1))

class RocketShot:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = self.x
        self.prev_y = self.y
        dx = target_x - self.x
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        dy = target_y - self.y
        distance = max(0.001, math.hypot(dx, dy))
        self.vel_x = (dx / distance) * 15.0
        self.vel_y = (dy / distance) * 15.0
        self.rect = pygame.Rect(int(self.x) - 6, int(self.y) - 4, 12, 8)
        self.spawn_time = pygame.time.get_ticks()

    def _explode(self, world):
        world.explosions.append(ExplosionEffect(self.x, self.y))
        for mob in world.mobs:
            push_dx = mob.rect.centerx - self.x
            if push_dx > WORLD_PIXELS / 2:
                push_dx -= WORLD_PIXELS
            elif push_dx < -WORLD_PIXELS / 2:
                push_dx += WORLD_PIXELS
            dx = abs(push_dx)
            dy = self.y - mob.rect.centery
            distance = math.hypot(dx, dy)
            if distance <= 80:
                mob.health -= max(2, int(12 * (1 - distance / 100)))
                mob.hurt_timer = 10
                mob.vel_x += 3.0 if push_dx >= 0 else -3.0
                mob.vel_y = min(mob.vel_y, -5)
                anger_village_golem_for_villager(world, mob)
                if mob.m_type == "iron_golem":
                    mob.angry = True
                if mob.m_type == "enderman":
                    mob.angry = True
                    mob.teleport_timer = 0

    def update(self, world):
        self.prev_x, self.prev_y = self.x, self.y
        self.vel_y = min(self.vel_y + 0.12, 8.0)
        steps = max(1, int(math.ceil(max(abs(self.vel_x), abs(self.vel_y)) / 4.0)))
        step_x = self.vel_x / steps
        step_y = self.vel_y / steps

        for _ in range(steps):
            self.x = (self.x + step_x) % WORLD_PIXELS
            self.y += step_y
            self.rect.center = (int(self.x), int(self.y))
            hitbox = self.rect.inflate(8, 8)
            hit_mob = any(
                hitbox.colliderect(mob.rect.move(offset, 0))
                for mob in world.mobs
                for offset in (-WORLD_PIXELS, 0, WORLD_PIXELS)
            )
            hit_block = any(
                hitbox.colliderect(block_rect)
                for block_rect in world.get_surrounding_blocks(hitbox)
            )
            if hit_mob or hit_block:
                self._explode(world)
                return True

        if self.y < 0 or self.y > WORLD_HEIGHT * TILE_SIZE or pygame.time.get_ticks() - self.spawn_time > 3500:
            return True
        return False

    def draw(self, surface, scroll_x, scroll_y):
        for offset in (-WORLD_PIXELS, 0, WORLD_PIXELS):
            x = self.rect.centerx - int(scroll_x) + offset
            y = self.rect.centery - int(scroll_y)
            if -20 <= x <= SCREEN_WIDTH + 20:
                pygame.draw.line(
                    surface, (255, 120, 35),
                    (int(self.prev_x - scroll_x + offset), int(self.prev_y - scroll_y)),
                    (x, y), 5
                )
                pygame.draw.rect(surface, (75, 75, 80), (x - 6, y - 4, 12, 8))
                pygame.draw.polygon(surface, (220, 220, 225), [(x + 6, y - 4), (x + 10, y), (x + 6, y + 4)])
                pygame.draw.circle(surface, (255, 210, 80), (x - 7, y), 3)
                break

class ArrowShot:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = self.x
        self.prev_y = self.y
        dx = target_x - self.x
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        dy = target_y - self.y
        dist = max(0.001, math.hypot(dx, dy))
        self.vel_x = (dx / dist) * 16.0
        self.vel_y = (dy / dist) * 16.0
        self.rect = pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)
        self.spawn_time = pygame.time.get_ticks()

    def update(self, world):
        self.prev_x, self.prev_y = self.x, self.y
        steps = max(1, int(math.ceil(max(abs(self.vel_x), abs(self.vel_y)) / 6.0)))
        step_x = self.vel_x / steps
        step_y = self.vel_y / steps

        for _ in range(steps):
            self.x = (self.x + step_x) % WORLD_PIXELS
            self.y += step_y
            self.rect.center = (int(self.x), int(self.y))

            hitbox = self.rect.inflate(8, 8)
            for mob in world.mobs:
                if hitbox.colliderect(mob.rect):
                    mob.health -= 6
                    mob.hurt_timer = 10
                    mob.vel_x += 2.0 if self.vel_x > 0 else -2.0
                    mob.vel_y = min(mob.vel_y, -4)
                    anger_village_golem_for_villager(world, mob)
                    if mob.m_type == "iron_golem":
                        mob.angry = True
                    if mob.m_type == "enderman":
                        mob.angry = True
                        mob.teleport_timer = 0
                    return True

            for block_rect in world.get_surrounding_blocks(hitbox):
                if hitbox.colliderect(block_rect):
                    return True

        self.vel_y += 0.08

        if self.y < 0 or self.y > WORLD_HEIGHT * TILE_SIZE or pygame.time.get_ticks() - self.spawn_time > 3500:
            return True

        return False

    def draw(self, surface, scroll_x, scroll_y):
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx0 = self.prev_x - int(scroll_x) + offset
            dy0 = self.prev_y - int(scroll_y)
            dx1 = self.rect.centerx - int(scroll_x) + offset
            dy1 = self.rect.centery - int(scroll_y)
            if max(dx0, dx1) < -40 or min(dx0, dx1) > SCREEN_WIDTH + 40:
                continue
            if max(dy0, dy1) < -40 or min(dy0, dy1) > SCREEN_HEIGHT + 40:
                continue
            pygame.draw.line(surface, (210, 180, 120), (dx0, dy0), (dx1, dy1), 4)
            pygame.draw.circle(surface, (245, 235, 220), (dx1, dy1), 3)
            break

class EggShot:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = self.x
        self.prev_y = self.y
        dx = target_x - self.x
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        dy = target_y - self.y
        dist = max(0.001, math.hypot(dx, dy))
        self.vel_x = (dx / dist) * 13.0
        self.vel_y = (dy / dist) * 13.0 - 4.0
        self.rect = pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)
        self.spawn_time = pygame.time.get_ticks()

    def update(self, world):
        self.prev_x, self.prev_y = self.x, self.y
        self.x = (self.x + self.vel_x) % WORLD_PIXELS
        self.y += self.vel_y
        self.vel_y += 0.18
        self.rect.center = (int(self.x), int(self.y))

        for block_rect in world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block_rect):
                hatch = random.random() < 0.35
                if hatch:
                    world.mobs.append(Mob(int(self.x), int(self.y), "chicken"))
                return True

        if self.y < 0 or self.y > WORLD_HEIGHT * TILE_SIZE or pygame.time.get_ticks() - self.spawn_time > 3500:
            if random.random() < 0.35:
                world.mobs.append(Mob(int(self.x), int(self.y), "chicken"))
            return True

        return False

    def draw(self, surface, scroll_x, scroll_y):
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            dx0 = self.prev_x - int(scroll_x) + offset
            dy0 = self.prev_y - int(scroll_y)
            dx1 = self.rect.centerx - int(scroll_x) + offset
            dy1 = self.rect.centery - int(scroll_y)
            if max(dx0, dx1) < -40 or min(dx0, dx1) > SCREEN_WIDTH + 40:
                continue
            if max(dy0, dy1) < -40 or min(dy0, dy1) > SCREEN_HEIGHT + 40:
                continue
            pygame.draw.line(surface, (245, 245, 245), (dx0, dy0), (dx1, dy1), 3)
            pygame.draw.ellipse(surface, (240, 235, 220), (dx1 - 4, dy1 - 4, 8, 10))
            break

class FishingHook:
    def __init__(self, player, x, y, target_x, target_y):
        self.player = player
        self.x = float(x)
        self.y = float(y)
        self.prev_x = self.x
        self.prev_y = self.y
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.speed = 12.0
        self.state = "flying"
        self.bob_timer = 0
        self.catch_timer = random.randint(80, 180)
        self.rect = pygame.Rect(int(self.x) - 3, int(self.y) - 3, 6, 6)
        self.spawn_time = pygame.time.get_ticks()

    def _wrap_dx(self, dx):
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        return dx

    def _tile_at(self):
        return (int(self.rect.centerx // TILE_SIZE) % WORLD_WIDTH, int(self.rect.centery // TILE_SIZE))

    def _is_water(self, world):
        tx, ty = self._tile_at()
        return world.data.get((tx, ty)) == WATER

    def _finish(self):
        if self.player and getattr(self.player, "fishing_hook", None) is self:
            self.player.fishing_hook = None
        return True

    def _give_reward(self, world):
        rewards = [
            (RAW_COD, 1, 45),
            (RAW_COD, 2, 8),
            (RAW_SALMON, 1, 30),
            (RAW_SALMON, 2, 6),
            (STRING_ITEM, 1, 5),
            (BONE, 1, 3),
            (COAL, 1, 3),
        ]
        choices = [r[0] for r in rewards]
        weights = [r[2] for r in rewards]
        item_type = random.choices(choices, weights=weights, k=1)[0]
        count = next(r[1] for r in rewards if r[0] == item_type)
        if not add_item_to_inventory(self.player, item_type, count):
            world.dropped_items.append(DroppedItem(self.player.rect.centerx, self.player.rect.centery, item_type, count))
        print(f"[FISHING] Caught {BLOCK_NAMES.get(item_type, 'Item')}")

    def update(self, world):
        self.prev_x, self.prev_y = self.x, self.y

        if self.state == "flying":
            dx = self._wrap_dx(self.target_x - self.x)
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)

            if dist <= self.speed or dist == 0:
                self.x = self.target_x
                self.y = self.target_y
                self.rect.center = (int(self.x), int(self.y))
                if self._is_water(world):
                    self.state = "bob"
                    self.bob_timer = 0
                else:
                    return self._finish()
            else:
                self.x = (self.x + (dx / dist) * self.speed) % WORLD_PIXELS
                self.y += (dy / dist) * self.speed
                self.rect.center = (int(self.x), int(self.y))

                hit_solid = False
                for block_rect in world.get_surrounding_blocks(self.rect):
                    if self.rect.colliderect(block_rect):
                        hit_solid = True
                        break
                if hit_solid:
                    return self._finish()

                if self._is_water(world):
                    self.state = "bob"
                    self.bob_timer = 0
        else:
            self.bob_timer += 1
            self.y += math.sin(self.bob_timer * 0.25) * 0.15
            self.rect.center = (int(self.x), int(self.y))
            if not self._is_water(world):
                if self.bob_timer > 30:
                    return self._finish()
            elif self.bob_timer >= self.catch_timer:
                self._give_reward(world)
                return self._finish()

        if pygame.time.get_ticks() - self.spawn_time > 10000:
            return self._finish()

        return False

    def draw(self, surface, scroll_x, scroll_y):
        player_x = self.player.rect.centerx
        player_y = self.player.rect.centery - 8
        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
            px = player_x - int(scroll_x) + offset
            py = player_y - int(scroll_y)
            hx = self.rect.centerx - int(scroll_x) + offset
            hy = self.rect.centery - int(scroll_y)
            if max(px, hx) < -50 or min(px, hx) > SCREEN_WIDTH + 50:
                continue
            if max(py, hy) < -50 or min(py, hy) > SCREEN_HEIGHT + 50:
                continue
            pygame.draw.line(surface, (210, 190, 140), (px, py), (hx, hy), 2)
            pygame.draw.circle(surface, (240, 240, 240), (hx, hy), 4)
            pygame.draw.circle(surface, (180, 40, 40), (hx, hy), 2)
            break

class Mob:
    def __init__(self, x, y, m_type="zombie"):
        self.m_type = m_type
        self.sheared = False
        # Cows and sheep are a bit wider/shorter; endermen are 3 blocks tall.
        if m_type == "enderman":
            self.rect = pygame.Rect(x, y, 24, TILE_SIZE * 3 - 2)
            self.speed = 2.5
            self.health = 30
        elif m_type == "spider":
            self.rect = pygame.Rect(x, y, 32, 20)
            self.speed = 2.4
            self.health = 18
        elif m_type == "chicken":
            self.rect = pygame.Rect(x, y, 18, 18)
            self.speed = 0.9
            self.health = 4
            self.egg_timer = random.randint(900, 2400)
        elif m_type == "cow" or m_type == "sheep":
            self.rect = pygame.Rect(x, y, 32, 28)
            self.speed = 0.5
            self.health = 8 if m_type == "sheep" else 10
        elif m_type == "husk":
            self.rect = pygame.Rect(x, y, 24, TILE_SIZE * 2 - 2)
            self.speed = 2.2
            self.health = 20
        elif m_type == "camel":
            self.rect = pygame.Rect(x, y, 48, TILE_SIZE * 2 + 8)
            self.speed = 0.6
            self.health = 32
        elif m_type == "villager":
            self.rect = pygame.Rect(x, y, 24, TILE_SIZE * 2 - 4)
            self.speed = 0.45
            self.health = 20
        elif m_type == "iron_golem":
            self.rect = pygame.Rect(x, y, 36, TILE_SIZE * 3 - 4)
            self.speed = 0.55
            self.health = 100
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
        self.tamed = False
        self.saddled = False
        self.teleport_timer = 0
        self.angry = False
        self.last_attack = 0

    def update(self, world, player):
        if self.hurt_timer > 0: self.hurt_timer -= 1
        t = world.time % 24000
        is_night = (t > 14000 or t < 1000)
        # AI Logic
        if self.m_type == "iron_golem":
            target_mob = None
            target_distance = float("inf")
            if not self.angry:
                hostile_types = ("zombie", "husk", "spider", "enderman")
                for candidate in world.mobs:
                    if candidate is self or candidate.m_type not in hostile_types or candidate.health <= 0:
                        continue
                    dx = candidate.rect.centerx - self.rect.centerx
                    if dx > WORLD_PIXELS / 2:
                        dx -= WORLD_PIXELS
                    elif dx < -WORLD_PIXELS / 2:
                        dx += WORLD_PIXELS
                    dy = candidate.rect.centery - self.rect.centery
                    distance = math.hypot(dx, dy)
                    if distance < 12 * TILE_SIZE and distance < target_distance:
                        target_mob = candidate
                        target_distance = distance

            if self.angry:
                dx = player.rect.centerx - self.rect.centerx
                if dx > WORLD_PIXELS / 2:
                    dx -= WORLD_PIXELS
                elif dx < -WORLD_PIXELS / 2:
                    dx += WORLD_PIXELS
                dy = player.rect.centery - self.rect.centery
                target_distance = math.hypot(dx, dy)
                self.vel_x = self.speed if dx > 0 else -self.speed if dx < 0 else 0
            elif target_mob is not None:
                dx = target_mob.rect.centerx - self.rect.centerx
                if dx > WORLD_PIXELS / 2:
                    dx -= WORLD_PIXELS
                elif dx < -WORLD_PIXELS / 2:
                    dx += WORLD_PIXELS
                dy = target_mob.rect.centery - self.rect.centery
                target_distance = math.hypot(dx, dy)
                self.vel_x = self.speed if dx > 0 else -self.speed if dx < 0 else 0
            else:
                self.wander_timer -= 1
                if self.wander_timer <= 0:
                    self.wander_timer = random.randint(120, 300)
                    self.vel_x = random.choice([-self.speed, 0, 0, self.speed])

            if self.angry and target_distance <= 42 and abs(dy) <= TILE_SIZE * 2:
                if pygame.time.get_ticks() - self.last_attack > 1000:
                    player.take_damage(10, cause="iron_golem")
                    player.vel_y = min(player.vel_y, -8)
                    player.rect.x = (player.rect.x + (3 if dx >= 0 else -3) * TILE_SIZE) % WORLD_PIXELS
                    self.last_attack = pygame.time.get_ticks()
            elif not self.angry and target_mob is not None and abs(dx) <= 42 and abs(dy) <= TILE_SIZE * 2:
                if pygame.time.get_ticks() - self.last_attack > 1000:
                    target_mob.health -= 14
                    target_mob.hurt_timer = 10
                    target_mob.vel_y = min(target_mob.vel_y, -9)
                    target_mob.vel_x += 5 if dx >= 0 else -5
                    if target_mob.m_type == "enderman":
                        target_mob.angry = True
                        target_mob.teleport_timer = 0
                    self.last_attack = pygame.time.get_ticks()
        elif self.m_type == "zombie":
            # Chase player
            dist_x = player.rect.x - self.rect.x
            if abs(dist_x) < 400: # Detection range
                self.vel_x = self.speed if dist_x > 0 else -self.speed
            else:
                self.vel_x = 0
        elif self.m_type == "enderman":
            # Check if touching water
            touching_water = False
            ex = self.rect.centerx // TILE_SIZE
            for ey in [self.rect.top // TILE_SIZE, self.rect.centery // TILE_SIZE, (self.rect.bottom - 1) // TILE_SIZE]:
                if world.get_block(ex % WORLD_WIDTH, ey) == WATER:
                    touching_water = True
                    break
            
            # Check if in rain
            in_rain = False
            if world.weather_type == "rain" and world.weather_intensity > 0:
                is_under_roof = False
                for dx in [-1, 0, 1]:
                    check_x = (ex + dx) % WORLD_WIDTH
                    for check_y in range(int(self.rect.top // TILE_SIZE)):
                        if world.get_block(check_x, check_y) is not None:
                            is_under_roof = True
                            break
                    if is_under_roof:
                        break
                if not is_under_roof:
                    in_rain = True
            
            if (touching_water or in_rain) and self.teleport_timer <= 0:
                # Teleport away to a safe dry spot
                teleported = False
                for _ in range(20):
                    offset_x = random.randint(-300, 300)
                    offset_y = random.randint(-40, 40)
                    target_x = (self.rect.x + offset_x) % WORLD_PIXELS
                    target_y = max(0, min((WORLD_HEIGHT - 4) * TILE_SIZE, self.rect.y + offset_y))
                    
                    tx = target_x // TILE_SIZE
                    ty = target_y // TILE_SIZE
                    under_b = world.get_block(tx % WORLD_WIDTH, ty + 3)
                    space_ok = True
                    for h_off in range(3):
                        b = world.get_block(tx % WORLD_WIDTH, ty + h_off)
                        if b is not None and b != WATER:
                            space_ok = False
                            break
                    
                    target_under_roof = False
                    if world.weather_type == "rain" and world.weather_intensity > 0:
                        for dx in [-1, 0, 1]:
                            cx = (tx + dx) % WORLD_WIDTH
                            for cy in range(ty):
                                if world.get_block(cx, cy) is not None:
                                    target_under_roof = True
                                    break
                            if target_under_roof:
                                break
                    
                    if space_ok and under_b is not None and under_b != WATER and (world.weather_type != "rain" or world.weather_intensity <= 0 or target_under_roof):
                        self.rect.x = target_x
                        self.rect.y = target_y
                        self.teleport_timer = 20
                        teleported = True
                        break
                if not teleported:
                    # Fallback simple teleport
                    self.rect.x = (self.rect.x + random.choice([-200, 200])) % WORLD_PIXELS
                    self.rect.y = max(0, min((WORLD_HEIGHT - 3) * TILE_SIZE, player.rect.y + random.randint(-20, 10)))
                    self.teleport_timer = 20

            dist_x = player.rect.x - self.rect.x
            if self.teleport_timer > 0:
                self.teleport_timer -= 1
            if not self.angry:
                touch_x = abs(self.rect.centerx - player.rect.centerx)
                if touch_x > WORLD_PIXELS / 2:
                    touch_x = WORLD_PIXELS - touch_x
                touch_y = abs(self.rect.centery - player.rect.centery)
                if touch_x < (self.rect.width + player.rect.width) / 2 and touch_y < (self.rect.height + player.rect.height) / 2:
                    self.angry = True
                    self.teleport_timer = 0
                self.vel_x = 0
            else:
                if abs(dist_x) > 350 and self.teleport_timer <= 0 and random.random() < 0.08:
                    offset_x = random.choice([-180, 180])
                    offset_y = random.randint(-20, 10)
                    self.rect.x = (player.rect.x + offset_x) % WORLD_PIXELS
                    self.rect.y = max(0, min((WORLD_HEIGHT - 3) * TILE_SIZE, player.rect.y + offset_y))
                    self.teleport_timer = 90
                elif abs(dist_x) < 700:
                    self.vel_x = self.speed if dist_x > 0 else -self.speed
                else:
                    self.vel_x = 0
        elif self.m_type == "spider":
            dist_x = player.rect.x - self.rect.x
            if is_night:
                if abs(dist_x) < 450:
                    self.vel_x = self.speed if dist_x > 0 else -self.speed
                else:
                    self.vel_x = 0
            else:
                self.wander_timer -= 1
                if self.wander_timer <= 0:
                    self.wander_timer = random.randint(60, 180)
                    self.vel_x = random.choice([-self.speed, 0, self.speed])
        elif self.m_type == "chicken":
            slot = player.inventory[player.selected_slot] if not player.show_inventory else player.held_item
            if slot and slot["type"] == SEEDS:
                dist_x = player.rect.x - self.rect.x
                if abs(dist_x) < 220:
                    self.vel_x = self.speed if dist_x > 0 else -self.speed
                else:
                    self.vel_x = 0
            else:
                self.wander_timer -= 1
                if self.wander_timer <= 0:
                    self.wander_timer = random.randint(50, 140)
                    self.vel_x = random.choice([-self.speed, 0, self.speed])
            self.egg_timer -= 1
            if self.egg_timer <= 0:
                world.dropped_items.append(DroppedItem(self.rect.centerx, self.rect.centery, EGG))
                self.egg_timer = random.randint(1200, 3000)
        elif self.m_type == "husk":
            # Chase player at all times (doesn't burn in sunlight)
            dist_x = player.rect.x - self.rect.x
            if abs(dist_x) < 400:
                self.vel_x = self.speed if dist_x > 0 else -self.speed
            else:
                self.vel_x = 0
        elif self.m_type == "camel":
            if player.riding_mob == self:
                if self.saddled:
                    keys = pygame.key.get_pressed()
                    self.vel_x = 0
                    if keys[pygame.K_a]:
                        self.vel_x = -3.0
                    elif keys[pygame.K_d]:
                        self.vel_x = 3.0
                    if keys[pygame.K_SPACE] and self.on_ground:
                        self.vel_y = -6.5
                else:
                    self.wander_timer -= 1
                    if self.wander_timer <= 0:
                        self.wander_timer = random.randint(120, 300)
                        self.vel_x = random.choice([-self.speed, 0, 0, self.speed])
            else:
                self.wander_timer -= 1
                if self.wander_timer <= 0:
                    self.wander_timer = random.randint(120, 300)
                    self.vel_x = random.choice([-self.speed, 0, 0, self.speed])
        elif self.m_type == "villager":
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.wander_timer = random.randint(120, 300)
                self.vel_x = random.choice([-self.speed, 0, 0, self.speed])
        else: # Cow/Sheep Wander / Follow
            slot = player.inventory[player.selected_slot] if not player.show_inventory else player.held_item
            lure_item = WHEAT_ITEM
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
        hit_wall = False
        for block in hits:
            if self.rect.colliderect(block):
                if self.vel_x > 0: self.rect.right = block.left
                elif self.vel_x < 0: self.rect.left = block.right
                if self.m_type == "spider" and self.vel_x != 0:
                    hit_wall = True
                # Jump if blocked and on ground
                if self.on_ground:
                    self.vel_y = -7
                    self.on_ground = False
        if self.m_type == "spider" and hit_wall and self.vel_y > -3.5:
            self.vel_y = -3.5

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

        # Husk attack
        if self.m_type == "husk":
            dist_x = abs(self.rect.centerx - player.rect.centerx)
            if dist_x > WORLD_PIXELS / 2: dist_x = WORLD_PIXELS - dist_x
            dist_y = abs(self.rect.centery - player.rect.centery)
            if dist_x < (self.rect.width + player.rect.width)/2 and dist_y < (self.rect.height + player.rect.height)/2:
                if pygame.time.get_ticks() - self.last_hit > 1000:
                    player.take_damage(3, cause="husk") # Slightly stronger than zombie
                    self.last_hit = pygame.time.get_ticks()

        # Zombies specific behaviors
        if self.m_type == "zombie":
            # Sunlight burn
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
                    player.take_damage(2, cause="zombie")
                    self.last_hit = pygame.time.get_ticks()
        elif self.m_type == "enderman":
            dist_x = abs(self.rect.centerx - player.rect.centerx)
            if dist_x > WORLD_PIXELS / 2:
                dist_x = WORLD_PIXELS - dist_x
            dist_y = abs(self.rect.centery - player.rect.centery)
            if self.angry and dist_x < 72 and dist_y < self.rect.height:
                if pygame.time.get_ticks() - self.last_hit > 1200:
                    player.take_damage(4, cause="enderman")
                    self.last_hit = pygame.time.get_ticks()
        elif self.m_type == "spider":
            dist_x = abs(self.rect.centerx - player.rect.centerx)
            if dist_x > WORLD_PIXELS / 2:
                dist_x = WORLD_PIXELS - dist_x
            dist_y = abs(self.rect.centery - player.rect.centery)
            if is_night and dist_x < (self.rect.width + player.rect.width)/2 and dist_y < (self.rect.height + player.rect.height)/2:
                if pygame.time.get_ticks() - self.last_hit > 900:
                    player.take_damage(2, cause="spider")
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
            elif self.m_type == "enderman":
                color = (120, 40, 180) if self.angry else (90, 40, 120)
                if is_hurt:
                    color = (180, 80, 220)
                pygame.draw.rect(surface, color, (dx, dy, self.rect.width, self.rect.height))
                eye_color = (255, 80, 80) if self.angry else (180, 100, 255)
                pygame.draw.rect(surface, eye_color, (dx + 3, dy + 10, 5, 5))
                pygame.draw.rect(surface, eye_color, (dx + 16, dy + 10, 5, 5))
            elif self.m_type == "cow":
                color = (255, 100, 100) if is_hurt else (255, 255, 255)
                pygame.draw.rect(surface, color, (dx, dy, self.rect.width, self.rect.height))
                pygame.draw.rect(surface, (30, 30, 30), (dx + 4, dy + 4, 8, 8))
                pygame.draw.rect(surface, (30, 30, 30), (dx + 20, dy + 12, 6, 6))
                hx = dx + (self.rect.width if self.vel_x >= 0 else -8)
                h_color = (255, 150, 150) if is_hurt else (180, 140, 100)
                pygame.draw.rect(surface, h_color, (hx, dy + 4, 8, 12))
            elif self.m_type == "sheep":
                color = (255, 100, 100) if is_hurt else ((145, 110, 75) if self.sheared else (240, 240, 240))
                body_rect = pygame.Rect(dx, dy + (5 if self.sheared else 0), self.rect.width, self.rect.height - (5 if self.sheared else 0))
                pygame.draw.rect(surface, color, body_rect, 0, 8)
                if not self.sheared:
                    pygame.draw.rect(surface, (200, 200, 200), body_rect, 2, 8)
                hx = dx + (self.rect.width if self.vel_x >= 0 else -6)
                h_color = (255, 100, 100) if is_hurt else (50, 50, 50)
                pygame.draw.rect(surface, h_color, (hx, dy + 6, 8, 10)) # Face
            elif self.m_type == "spider":
                body_color = (160, 30, 30) if is_hurt else (30, 30, 30)
                pygame.draw.rect(surface, body_color, (dx + 3, dy + 6, self.rect.width - 6, 12), 0, 6)
                pygame.draw.ellipse(surface, (20, 20, 20), (dx + 7, dy + 1, 18, 14))
                eye_color = (240, 60, 60)
                pygame.draw.circle(surface, eye_color, (dx + 12, dy + 8), 2)
                pygame.draw.circle(surface, eye_color, (dx + 20, dy + 8), 2)
                leg_color = (25, 25, 25)
                leg_pairs = [
                    ((dx + 6, dy + 7), (dx - 3, dy + 2)),
                    ((dx + 6, dy + 11), (dx - 4, dy + 10)),
                    ((dx + 26, dy + 7), (dx + 35, dy + 2)),
                    ((dx + 26, dy + 11), (dx + 36, dy + 10)),
                ]
                for start, end in leg_pairs:
                    pygame.draw.line(surface, leg_color, start, end, 2)
                    pygame.draw.line(surface, leg_color, (start[0], start[1] + 2), (end[0], end[1] + 2), 2)
            elif self.m_type == "chicken":
                body = (255, 245, 220) if not is_hurt else (255, 180, 180)
                wing = (240, 220, 180) if not is_hurt else (220, 120, 120)
                pygame.draw.ellipse(surface, body, (dx, dy + 2, self.rect.width, self.rect.height - 2))
                pygame.draw.circle(surface, (255, 220, 0), (dx + 14, dy + 8), 4)
                pygame.draw.rect(surface, wing, (dx + 4, dy + 8, 8, 5))
                pygame.draw.line(surface, (255, 160, 40), (dx + 13, dy + 12), (dx + 11, dy + 17), 2)
                pygame.draw.line(surface, (255, 160, 40), (dx + 16, dy + 12), (dx + 18, dy + 17), 2)
            elif self.m_type == "husk":
                # Sandy zombie look
                body_c = (255, 150, 150) if is_hurt else (210, 180, 110)
                pygame.draw.rect(surface, body_c, (dx, dy, self.rect.width, self.rect.height))
                eye_c = (255, 80, 80) if is_hurt else (140, 80, 20)
                pygame.draw.rect(surface, eye_c, (dx + 4, dy + 8, 4, 4))
                pygame.draw.rect(surface, eye_c, (dx + 16, dy + 8, 4, 4))
                # Tattered rags - dark strips across body
                pygame.draw.rect(surface, (160, 120, 60), (dx + 2, dy + 20, 20, 3))
                pygame.draw.rect(surface, (160, 120, 60), (dx + 4, dy + 32, 16, 3))
            elif self.m_type == "villager":
                tunic = (255, 100, 100) if is_hurt else (125, 85, 55)
                skin = (255, 180, 180) if is_hurt else (190, 145, 105)
                pygame.draw.rect(surface, tunic, (dx + 2, dy + 16, self.rect.width - 4, self.rect.height - 16))
                pygame.draw.rect(surface, skin, (dx + 4, dy + 2, self.rect.width - 8, 18))
                pygame.draw.rect(surface, (70, 50, 35), (dx + 6, dy + 9, 3, 3))
                pygame.draw.rect(surface, (70, 50, 35), (dx + 15, dy + 9, 3, 3))
                if self.vel_x < 0:
                    nose = [
                        (dx + 12, dy + 10), (dx + 6, dy + 10),
                        (dx + 4, dy + 13), (dx + 7, dy + 15),
                        (dx + 7, dy + 18), (dx + 12, dy + 17),
                    ]
                else:
                    nose = [
                        (dx + 12, dy + 10), (dx + 18, dy + 10),
                        (dx + 20, dy + 13), (dx + 17, dy + 15),
                        (dx + 17, dy + 18), (dx + 12, dy + 17),
                    ]
                pygame.draw.polygon(surface, (155, 110, 75) if not is_hurt else skin, nose)
            elif self.m_type == "iron_golem":
                body = (210, 145, 145) if is_hurt else (190, 190, 180)
                body_dark = (135, 140, 135) if is_hurt else (115, 125, 120)
                body_light = (235, 230, 215) if is_hurt else (225, 220, 200)
                vine = (65, 125, 65)
                pygame.draw.rect(surface, body_dark, (dx + 4, dy + 27, 28, 43), 0, 5)
                pygame.draw.rect(surface, body, (dx + 7, dy + 24, 22, 43), 0, 4)
                pygame.draw.rect(surface, body_light, (dx + 10, dy + 28, 5, 28))
                pygame.draw.rect(surface, body_dark, (dx + 8, dy + 7, 20, 20), 0, 4)
                pygame.draw.rect(surface, body, (dx + 10, dy + 8, 16, 17), 0, 3)
                pygame.draw.rect(surface, body_light, (dx + 12, dy + 9, 4, 9))
                eye_color = (100, 25, 20) if not is_hurt else (255, 230, 220)
                pygame.draw.rect(surface, eye_color, (dx + 12, dy + 15, 3, 3))
                pygame.draw.rect(surface, eye_color, (dx + 21, dy + 15, 3, 3))
                pygame.draw.polygon(surface, body_dark, [(dx + 16, dy + 17), (dx + 21, dy + 17), (dx + 20, dy + 23), (dx + 16, dy + 23)])
                pygame.draw.rect(surface, body_dark, (dx, dy + 29, 8, 35), 0, 3)
                pygame.draw.rect(surface, body, (dx + 1, dy + 30, 6, 30), 0, 2)
                pygame.draw.rect(surface, body_dark, (dx + 28, dy + 29, 8, 35), 0, 3)
                pygame.draw.rect(surface, body, (dx + 29, dy + 30, 6, 30), 0, 2)
                pygame.draw.rect(surface, body_dark, (dx + 8, dy + 65, 8, 23), 0, 2)
                pygame.draw.rect(surface, body_dark, (dx + 20, dy + 65, 8, 23), 0, 2)
                pygame.draw.rect(surface, body_light, (dx + 9, dy + 68, 3, 14))
                pygame.draw.rect(surface, body_light, (dx + 21, dy + 68, 3, 14))
                pygame.draw.line(surface, vine, (dx + 9, dy + 30), (dx + 15, dy + 38), 2)
                pygame.draw.line(surface, vine, (dx + 15, dy + 38), (dx + 10, dy + 48), 2)
                pygame.draw.line(surface, vine, (dx + 26, dy + 34), (dx + 21, dy + 42), 2)
                pygame.draw.line(surface, vine, (dx + 21, dy + 42), (dx + 27, dy + 53), 2)
                pygame.draw.line(surface, vine, (dx + 4, dy + 44), (dx + 8, dy + 49), 2)
                pygame.draw.line(surface, vine, (dx + 29, dy + 50), (dx + 34, dy + 45), 2)
            elif self.m_type == "camel":
                # Camel body
                body_c = (255, 150, 150) if is_hurt else (205, 160, 80)
                pygame.draw.rect(surface, body_c, (dx + 4, dy + 8, self.rect.width - 8, self.rect.height - 16))
                # Hump
                pygame.draw.ellipse(surface, body_c, (dx + 10, dy, 26, 20))
                # Head
                head_c = (255, 130, 130) if is_hurt else (185, 140, 65)
                pygame.draw.rect(surface, head_c, (dx + self.rect.width - 12, dy + 8, 14, 12))
                pygame.draw.rect(surface, (120, 90, 40), (dx + self.rect.width - 10, dy + 18, 10, 5)) # Snout
                pygame.draw.rect(surface, (30, 20, 10), (dx + self.rect.width - 8, dy + 10, 3, 3)) # Eye
                # Legs
                leg_c = (175, 135, 65)
                pygame.draw.rect(surface, leg_c, (dx + 6,  dy + self.rect.height - 14, 6, 14))
                pygame.draw.rect(surface, leg_c, (dx + 16, dy + self.rect.height - 14, 6, 14))
                pygame.draw.rect(surface, leg_c, (dx + 28, dy + self.rect.height - 14, 6, 14))
                pygame.draw.rect(surface, leg_c, (dx + 38, dy + self.rect.height - 14, 6, 14))
                if getattr(self, "saddled", False):
                    pygame.draw.rect(surface, (200, 50, 50), (dx + 12, dy + 12, 22, 10))
                    pygame.draw.rect(surface, (139, 69, 19), (dx + 16, dy + 10, 14, 4))
                    pygame.draw.line(surface, (180, 180, 180), (dx + 23, dy + 14), (dx + 23, dy + 22), 2)

def draw_block_icon(screen, b_type, x, y, size, font):
    if b_type == GLASS:
        pygame.draw.rect(screen, (175, 225, 240), (x, y, size, size))
        pygame.draw.rect(screen, (220, 245, 250), (x, y, size, size), 2)
    elif b_type == GLASS_PANE:
        inset = max(1, size // 12)
        pane_rect = pygame.Rect(x + inset, y + inset, size - inset * 2, size - inset * 2)
        pygame.draw.rect(screen, (175, 225, 240), pane_rect)
        pygame.draw.rect(screen, (220, 245, 250), pane_rect, 2)
    elif b_type == APPLE:
        pygame.draw.ellipse(screen, (190, 35, 30), (x + 4, y + 6, size - 8, size - 8))
        pygame.draw.line(screen, (90, 60, 30), (x + size // 2, y + 7), (x + size // 2 + 2, y + 2), 2)
        pygame.draw.ellipse(screen, (55, 145, 45), (x + size // 2, y + 2, 8, 4))
    elif b_type in (OAK_SAPLING, BIRCH_SAPLING):
        leaf_color = COLOR_LEAVES_B if b_type == BIRCH_SAPLING else (65, 145, 55)
        pygame.draw.line(screen, (110, 75, 35), (x + size // 2, y + size - 4), (x + size // 2, y + size // 2), 3)
        pygame.draw.circle(screen, leaf_color, (x + size // 2, y + size // 3), size // 4)
        pygame.draw.circle(screen, leaf_color, (x + size // 3, y + size // 2), size // 5)
    elif b_type == BUNDLE:
        pygame.draw.polygon(screen, (155, 115, 65), ((x + 5, y + 8), (x + size - 5, y + 8), (x + size - 3, y + size - 4), (x + 3, y + size - 4)))
        pygame.draw.line(screen, (95, 65, 35), (x + 5, y + size // 2), (x + size - 5, y + size // 2), 2)
    elif b_type == EMERALD:
        pygame.draw.polygon(screen, (35, 190, 125), ((x + size // 2, y + 3), (x + size - 4, y + size // 2), (x + size // 2, y + size - 3), (x + 4, y + size // 2)))
        pygame.draw.line(screen, (135, 245, 195), (x + size // 2, y + 4), (x + size // 2, y + size - 4), 2)
    elif b_type in (DANDELION, POPPY, CORNFLOWER):
        flower_color = (245, 215, 45) if b_type == DANDELION else (55, 105, 220) if b_type == CORNFLOWER else (200, 35, 35)
        pygame.draw.line(screen, (55, 130, 45), (x + size // 2, y + size - 3), (x + size // 2, y + size // 2), 2)
        pygame.draw.circle(screen, flower_color, (x + size // 2, y + size // 3), size // 5)
    elif b_type in (RED_DYE, YELLOW_DYE, ORANGE_DYE, GREEN_DYE, BLUE_DYE, PURPLE_DYE, CYAN_DYE):
        dye_color = (190, 25, 35) if b_type == RED_DYE else (235, 195, 35) if b_type == YELLOW_DYE else (230, 115, 25) if b_type == ORANGE_DYE else (45, 150, 55) if b_type == GREEN_DYE else (45, 95, 205) if b_type == BLUE_DYE else (130, 55, 170) if b_type == PURPLE_DYE else (45, 175, 185)
        highlight_color = (235, 75, 75) if b_type == RED_DYE else (255, 235, 100) if b_type == YELLOW_DYE else (255, 170, 65) if b_type == ORANGE_DYE else (110, 210, 95) if b_type == GREEN_DYE else (125, 165, 255) if b_type == BLUE_DYE else (190, 125, 225) if b_type == PURPLE_DYE else (115, 225, 230)
        pygame.draw.polygon(screen, dye_color, ((x + 7, y + 9), (x + 16, y + 4), (x + 25, y + 10), (x + 22, y + 23), (x + 10, y + 25)))
        pygame.draw.circle(screen, highlight_color, (x + 14, y + 12), 3)
    elif b_type == GOLD_NUGGET:
        pygame.draw.ellipse(screen, (235, 185, 35), (x + 5, y + 8, size - 10, size - 12))
        pygame.draw.line(screen, (255, 230, 110), (x + 8, y + size // 2), (x + size - 8, y + size // 2), 2)
    elif b_type == BOOK:
        pygame.draw.rect(screen, (120, 55, 40), (x + 4, y + 3, size - 8, size - 6))
        pygame.draw.rect(screen, (235, 220, 175), (x + 7, y + 5, size - 13, size - 10))
        pygame.draw.line(screen, (120, 55, 40), (x + size // 2, y + 5), (x + size // 2, y + size - 5), 2)
    elif b_type == OBSIDIAN:
        pygame.draw.rect(screen, (50, 35, 75), (x + 3, y + 3, size - 6, size - 6))
        pygame.draw.line(screen, (105, 80, 145), (x + 6, y + 7), (x + size - 7, y + 7), 2)
    elif b_type == GOLD_INGOT:
        pygame.draw.polygon(screen, (235, 185, 35), ((x + 4, y + 8), (x + size - 4, y + 8), (x + size - 7, y + size - 5), (x + 7, y + size - 5)))
        pygame.draw.line(screen, (255, 230, 110), (x + 7, y + 11), (x + size - 7, y + 11), 2)
    elif b_type in (COPPER_SPEAR, IRON_SPEAR):
        spear_color = (190, 110, 55) if b_type == COPPER_SPEAR else (195, 200, 210)
        pygame.draw.line(screen, (110, 75, 40), (x + 5, y + size - 5), (x + size - 7, y + 7), 3)
        pygame.draw.polygon(screen, spear_color, ((x + size - 5, y + 3), (x + size - 2, y + 13), (x + size - 12, y + 8)))
    elif b_type == LEATHER:
        pygame.draw.polygon(screen, (155, 105, 55), ((x + 5, y + 6), (x + size - 5, y + 4), (x + size - 4, y + size - 7), (x + 7, y + size - 4)))
        pygame.draw.line(screen, (195, 145, 85), (x + 8, y + size // 2), (x + size - 8, y + size // 2 - 2), 2)
    elif b_type in (COPPER_HORSE_ARMOR, IRON_HORSE_ARMOR, GOLDEN_HORSE_ARMOR, DIAMOND_HORSE_ARMOR, LEATHER_HORSE_ARMOR):
        armor_color = {
            COPPER_HORSE_ARMOR: (190, 110, 55),
            IRON_HORSE_ARMOR: (195, 200, 210),
            GOLDEN_HORSE_ARMOR: (235, 185, 35),
            DIAMOND_HORSE_ARMOR: COLOR_DIAMOND,
            LEATHER_HORSE_ARMOR: (155, 105, 55),
        }[b_type]
        pygame.draw.arc(screen, armor_color, (x + 4, y + 3, size - 8, size - 6), 0.2, 2.9, 4)
        pygame.draw.line(screen, armor_color, (x + 5, y + size // 2), (x + size - 5, y + size // 2), 3)
    elif b_type == STICK:
        pygame.draw.line(screen, (101, 67, 33), (x + size//4, y + size - 4), (x + size - 4, y + size//4), 3)
    elif b_type in (COAL_BLOCK, IRON_BLOCK, DIAMOND_ORE, COPPER_ORE):
        pygame.draw.rect(screen, (70, 70, 80) if b_type == DIAMOND_ORE else COLOR_STONE, (x, y, size, size))
        ore_c = {
            COAL_BLOCK: COLOR_COAL,
            IRON_BLOCK: COLOR_IRON,
            DIAMOND_ORE: COLOR_DIAMOND,
            COPPER_ORE: (190, 110, 55),
        }[b_type]
        pygame.draw.rect(screen, ore_c, (x + 3, y + 5, 8, 6))
        pygame.draw.rect(screen, ore_c, (x + 12, y + 14, 10, 8))
    elif b_type in (DIORITE, GRANITE, GRAVEL, ANDESITE, DEEPSLATE):
        color = {
            DIORITE: (190, 190, 185),
            GRANITE: (145, 95, 85),
            GRAVEL: (125, 120, 110),
            ANDESITE: (115, 120, 125),
            DEEPSLATE: (65, 70, 80),
        }[b_type]
        pygame.draw.rect(screen, color, (x, y, size, size))
        for dx, dy in ((5, 6), (19, 10), (11, 23), (25, 26)):
            pygame.draw.rect(screen, (55, 55, 55), (x + dx, y + dy, 3, 3))
    elif b_type == DIAMOND:
        pygame.draw.polygon(screen, COLOR_DIAMOND, [
            (x + size//2, y + 3),
            (x + size - 4, y + size//2),
            (x + size//2, y + size - 3),
            (x + 4, y + size//2),
        ])
        pygame.draw.polygon(screen, (180, 255, 255), [
            (x + size//2, y + 3),
            (x + size - 4, y + size//2),
            (x + size//2, y + size//2),
            (x + 6, y + size//2),
        ], 1)
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
    elif b_type == COAL_BLOCK_ITEM:
        pygame.draw.rect(screen, (20, 20, 20), (x, y, size, size))
        pygame.draw.rect(screen, (60, 60, 60), (x + 2, y + 2, size - 4, size - 4), 1)
    elif b_type == ENDER_PEARL:
        pygame.draw.circle(screen, (70, 0, 110), (x + size // 2, y + size // 2), size // 3)
        pygame.draw.circle(screen, (200, 170, 255), (x + size // 2 - 2, y + size // 2 - 2), size // 8)
    elif b_type == STRING_ITEM:
        for i in range(3):
            pygame.draw.line(screen, (235, 235, 235), (x + 2, y + 4 + i * 4), (x + size - 2, y + 2 + i * 4), 1)
    elif b_type == BOW:
        pygame.draw.arc(screen, (160, 110, 70), (x + 6, y + 3, size - 12, size - 6), 1.2, 5.1, 3)
        pygame.draw.line(screen, (235, 235, 235), (x + 10, y + 5), (x + 10, y + size - 5), 1)
        pygame.draw.line(screen, (235, 235, 235), (x + 10, y + size // 2), (x + size - 8, y + size // 2), 1)
    elif b_type in (RAW_CHICKEN, COOKED_CHICKEN, FEATHER):
        if b_type == FEATHER:
            pygame.draw.ellipse(screen, (245, 245, 245), (x + 4, y + 2, size - 8, size - 4))
            pygame.draw.line(screen, (220, 220, 220), (x + size // 2, y + 3), (x + size // 2, y + size - 3), 1)
        else:
            base = (230, 170, 130) if b_type == RAW_CHICKEN else (180, 110, 70)
            accent = (255, 245, 220) if b_type == RAW_CHICKEN else (220, 180, 120)
            pygame.draw.ellipse(screen, base, (x + 2, y + 5, size - 4, size - 8))
            pygame.draw.circle(screen, accent, (x + size - 6, y + 8), 3)
            pygame.draw.line(screen, (160, 90, 40), (x + 4, y + size - 7), (x + 8, y + size - 2), 2)
    elif b_type == EGG:
        pygame.draw.ellipse(screen, (245, 240, 220), (x + 5, y + 3, size - 10, size - 6))
        pygame.draw.ellipse(screen, (220, 210, 190), (x + 6, y + 4, size - 12, size - 8), 1)
    elif b_type == RAW_COD:
        pygame.draw.ellipse(screen, (70, 170, 220), (x + 2, y + 5, size - 6, size - 10))
        pygame.draw.polygon(screen, (50, 140, 190), [
            (x + size - 5, y + size // 2),
            (x + size - 1, y + 4),
            (x + size - 1, y + size - 4),
        ])
        pygame.draw.circle(screen, (240, 240, 240), (x + 7, y + 9), 1)
    elif b_type == COOKED_COD:
        pygame.draw.ellipse(screen, (170, 120, 70), (x + 2, y + 5, size - 6, size - 10))
        pygame.draw.polygon(screen, (140, 90, 50), [
            (x + size - 5, y + size // 2),
            (x + size - 1, y + 4),
            (x + size - 1, y + size - 4),
        ])
        pygame.draw.circle(screen, (240, 220, 180), (x + 7, y + 9), 1)
    elif b_type == RAW_SALMON:
        pygame.draw.ellipse(screen, (240, 120, 90), (x + 2, y + 5, size - 6, size - 10))
        pygame.draw.polygon(screen, (210, 90, 60), [
            (x + size - 5, y + size // 2),
            (x + size - 1, y + 4),
            (x + size - 1, y + size - 4),
        ])
        pygame.draw.circle(screen, (255, 240, 230), (x + 7, y + 9), 1)
    elif b_type == COOKED_SALMON:
        pygame.draw.ellipse(screen, (170, 90, 60), (x + 2, y + 5, size - 6, size - 10))
        pygame.draw.polygon(screen, (130, 70, 45), [
            (x + size - 5, y + size // 2),
            (x + size - 1, y + 4),
            (x + size - 1, y + size - 4),
        ])
        pygame.draw.circle(screen, (245, 220, 200), (x + 7, y + 9), 1)
    elif b_type == FISHING_ROD:
        pygame.draw.line(screen, (101, 67, 33), (x + 4, y + size - 4), (x + size - 7, y + 5), 3)
        pygame.draw.line(screen, (240, 240, 240), (x + size - 7, y + 5), (x + size - 3, y + 1), 1)
        pygame.draw.circle(screen, (240, 240, 240), (x + size - 3, y + 1), 2)
    elif b_type == ROCKET_LAUNCHER:
        pygame.draw.rect(screen, (75, 75, 80), (x + 3, y + size // 3, size - 9, size // 3))
        pygame.draw.rect(screen, (120, 120, 125), (x + size - 8, y + size // 3 - 2, 5, size // 3 + 4))
        pygame.draw.rect(screen, (100, 65, 40), (x + 8, y + size // 2, 5, size // 3))
    elif b_type == TORCH:
        pygame.draw.rect(screen, (90, 55, 20), (x + size//2 - 1, y + 5, 2, size - 7))
        pygame.draw.polygon(screen, (255, 180, 60), [
            (x + size//2 - 3, y + 6),
            (x + size//2, y + 1),
            (x + size//2 + 3, y + 6)
        ])
        pygame.draw.circle(screen, (255, 245, 200), (x + size//2, y + 4), 1)
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
    elif b_type in CROP_STAGE_TO_KIND or b_type in (
        CARROT_ITEM, POTATO_ITEM, POISONOUS_POTATO, BEETROOT_ITEM, BEETROOT_SEEDS
    ):
        crop_kind = CROP_STAGE_TO_KIND.get(b_type)
        if crop_kind == "carrot" or b_type == CARROT_ITEM:
            pygame.draw.ellipse(screen, (235, 115, 35), (x + 8, y + 5, size // 3, size - 10))
            pygame.draw.line(screen, (55, 165, 45), (x + size // 2, y + 8), (x + size // 2 + 5, y + 2), 2)
        elif crop_kind == "potato" or b_type in (POTATO_ITEM, POISONOUS_POTATO):
            if crop_kind:
                color = (110, 150, 70)
            elif b_type == POTATO_ITEM:
                color = (174, 138, 92)
            else:
                color = (100, 150, 55)
            pygame.draw.ellipse(screen, color, (x + 5, y + 8, size - 10, size - 16))
            if b_type == POISONOUS_POTATO:
                pygame.draw.circle(screen, (90, 60, 35), (x + size // 2, y + size // 2), 2)
        elif crop_kind == "beetroot" or b_type in (BEETROOT_ITEM, BEETROOT_SEEDS):
            if b_type == BEETROOT_SEEDS:
                for dx in (8, 15, 22):
                    pygame.draw.circle(screen, (120, 45, 50), (x + dx, y + size // 2), 3)
            else:
                pygame.draw.circle(screen, (155, 40, 55), (x + size // 2, y + size // 2 + 5), size // 4)
                pygame.draw.line(screen, (65, 165, 55), (x + size // 2, y + size // 2), (x + size // 2, y + 5), 3)
        else:
            for dx in (8, 16, 24):
                pygame.draw.line(screen, (220, 200, 50), (x + dx, y + size - 4), (x + dx, y + 5), 2)
    elif b_type in (RED_BED, RED_BED_RIGHT, YELLOW_BED, YELLOW_BED_RIGHT, ORANGE_BED, ORANGE_BED_RIGHT, GREEN_BED, GREEN_BED_RIGHT, BLUE_BED, BLUE_BED_RIGHT, PURPLE_BED, PURPLE_BED_RIGHT, CYAN_BED, CYAN_BED_RIGHT):
        is_red_bed = b_type in (RED_BED, RED_BED_RIGHT)
        is_yellow_bed = b_type in (YELLOW_BED, YELLOW_BED_RIGHT)
        is_orange_bed = b_type in (ORANGE_BED, ORANGE_BED_RIGHT)
        is_green_bed = b_type in (GREEN_BED, GREEN_BED_RIGHT)
        is_blue_bed = b_type in (BLUE_BED, BLUE_BED_RIGHT)
        is_purple_bed = b_type in (PURPLE_BED, PURPLE_BED_RIGHT)
        is_cyan_bed = b_type in (CYAN_BED, CYAN_BED_RIGHT)
        bed_color = COLOR_RED if is_red_bed else (245, 215, 65) if is_yellow_bed else (245, 135, 35) if is_orange_bed else (60, 170, 65) if is_green_bed else (55, 105, 210) if is_blue_bed else (145, 65, 185) if is_purple_bed else (45, 190, 195)
        outline_color = (180, 60, 60) if is_red_bed else (180, 150, 35) if is_yellow_bed else (185, 85, 20) if is_orange_bed else (35, 115, 40) if is_green_bed else (35, 65, 145) if is_blue_bed else (90, 35, 125) if is_purple_bed else (20, 115, 125)
        pygame.draw.rect(screen, bed_color, (x, y, size, size))
        if b_type in (RED_BED, YELLOW_BED, ORANGE_BED, GREEN_BED, BLUE_BED, PURPLE_BED, CYAN_BED):
            pygame.draw.rect(screen, COLOR_WHITE, (x + 2, y + 2, size - 4, size//4))
        pygame.draw.rect(screen, outline_color, (x, y + size//2, size, size//2), 2)
    elif b_type >= 100: # Tools
        mat_c = (150, 110, 60) if b_type in (W_PICK, W_AXE, W_SHOVEL, W_SWORD, W_HOE) else (128, 128, 128)
        if b_type in (I_PICK, I_AXE, I_SHOVEL, I_SWORD, I_HOE, I_HELMET, I_CHEST, I_LEGS, I_BOOTS): mat_c = (200, 200, 220)
        if b_type in (D_PICK, D_AXE, D_SHOVEL, D_SWORD, D_HOE, D_HELMET, D_CHEST, D_LEGS, D_BOOTS): mat_c = COLOR_DIAMOND
        
        if b_type in (W_PICK, S_PICK, I_PICK, D_PICK):
            pygame.draw.rect(screen, mat_c, (x, y, size, size//4)) # Top
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//4, 4, size*3//4)) # Stick
        elif b_type in (W_AXE, S_AXE, I_AXE, D_AXE):
            pygame.draw.rect(screen, mat_c, (x, y, size//2, size//2)) # Head
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y, 4, size)) # Stick
        elif b_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL, D_SHOVEL):
            pygame.draw.rect(screen, mat_c, (x + size//4, y, size//2, size//3)) # Head
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//3, 4, size*2//3)) # Stick
        elif b_type in (W_SWORD, S_SWORD, I_SWORD, D_SWORD):
            pygame.draw.rect(screen, mat_c, (x + size//2 - 4, y, 8, size*2//3)) # Blade
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size*2//3, 4, size//3)) # Hilt
        elif b_type in (W_HOE, S_HOE, I_HOE, D_HOE):
            pygame.draw.rect(screen, mat_c, (x, y, size*3//4, size//4)) # Top
            pygame.draw.rect(screen, (101, 67, 33), (x + size//2 - 2, y + size//4, 4, size*3//4)) # Stick
        # Armor
        elif b_type in (I_HELMET, D_HELMET):
            pygame.draw.rect(screen, mat_c, (x+4, y+4, size-8, size-8))
            pygame.draw.rect(screen, (0,0,0), (x+8, y+16, 4, 4)) # Eyes
            pygame.draw.rect(screen, (0,0,0), (x+20, y+16, 4, 4))
        elif b_type in (I_CHEST, D_CHEST):
            pygame.draw.rect(screen, mat_c, (x+2, y+8, size-4, size-10))
            pygame.draw.rect(screen, mat_c, (x+size//4, y+2, size//2, 8)) # Neck
        elif b_type in (I_LEGS, D_LEGS):
            pygame.draw.rect(screen, mat_c, (x+4, y+4, size-8, size-12))
            pygame.draw.rect(screen, mat_c, (x+4, y+size-12, size//3, 8)) # Left leg
            pygame.draw.rect(screen, mat_c, (x+size-12, y+size-12, size//3, 8)) # Right leg
        elif b_type in (I_BOOTS, D_BOOTS):
            pygame.draw.rect(screen, mat_c, (x+4, y+size-16, size//3, 12))
            pygame.draw.rect(screen, mat_c, (x+size-12, y+size-16, size//3, 12))
        elif b_type == SHIELD:
            pygame.draw.rect(screen, (120, 80, 40), (x+4, y+2, size-8, size-4))
            pygame.draw.rect(screen, (200, 200, 200), (x+4, y+2, size-8, size-4), 2)
            pygame.draw.rect(screen, (150, 150, 150), (x+size//2-2, y+4, 4, size-8))
        elif b_type == FLINT_STEEL:
            pygame.draw.line(screen, (160, 160, 170), (x + 9, y + size - 5), (x + size - 8, y + 7), 4)
            pygame.draw.line(screen, (120, 80, 40), (x + 8, y + size - 8), (x + size - 4, y + size - 5), 3)
            pygame.draw.polygon(screen, (255, 150, 30), [
                (x + size - 9, y + 10), (x + size - 4, y + 2), (x + size - 2, y + 11),
            ])
        elif b_type == SHEARS:
            pygame.draw.circle(screen, (180, 180, 190), (x + 9, y + 20), 6, 2)
            pygame.draw.circle(screen, (180, 180, 190), (x + 23, y + 20), 6, 2)
            pygame.draw.line(screen, (180, 180, 190), (x + 12, y + 16), (x + 25, y + 5), 2)
            pygame.draw.line(screen, (180, 180, 190), (x + 20, y + 16), (x + 7, y + 5), 2)
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
    elif b_type in (W_STAIRS, C_STAIRS, SS_STAIRS, W_SLAB, C_SLAB, SS_SLAB):
        color = COLOR_PLANKS if b_type in (W_STAIRS, W_SLAB) else ((100, 100, 100) if b_type in (C_STAIRS, C_SLAB) else (180, 180, 190))
        if b_type in (W_SLAB, C_SLAB, SS_SLAB):
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
    elif b_type in (BED, BED_RIGHT):
        pygame.draw.rect(screen, COLOR_WHITE, (x, y, size, size))
        if b_type == BED:
            pygame.draw.rect(screen, COLOR_WHITE, (x + 2, y + 2, size - 4, size//4))
        pygame.draw.rect(screen, (170, 170, 170), (x, y + size//2, size, size//2), 2)
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
    elif b_type == COPPER_INGOT:
        pygame.draw.rect(screen, (190, 110, 55), (x + 4, y + 8, size - 12, size - 16), 0, 4)
        pygame.draw.rect(screen, (130, 70, 35), (x + 4, y + 8, size - 12, size - 16), 1, 4)
    elif b_type == FLINT:
        pygame.draw.polygon(screen, (55, 55, 60), [
            (x + 5, y + size - 7), (x + 11, y + 8),
            (x + size - 5, y + 4), (x + size - 9, y + size - 6),
        ])
    elif b_type == BUCKET:
        pygame.draw.polygon(screen, (150, 150, 160), [(x+8, y+8), (x+size-8, y+8), (x+size-12, y+size-8), (x+12, y+size-8)])
        pygame.draw.rect(screen, (120, 120, 130), (x+12, y+8, size-24, 2)) # Rim
    elif b_type == WATER_BUCKET:
        pygame.draw.polygon(screen, (150, 150, 160), [(x+8, y+8), (x+size-8, y+8), (x+size-12, y+size-8), (x+12, y+size-8)])
        pygame.draw.rect(screen, (0, 100, 255), (x + 10, y + 14, size - 20, size // 3))
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
    elif b_type == SAND_BLOCK:
        pygame.draw.rect(screen, (220, 200, 130), (x, y, size, size))
        pygame.draw.rect(screen, (200, 180, 110), (x + size//8, y + size//8, size*5//16, size//4)) # shade
        pygame.draw.rect(screen, (200, 180, 110), (x + size*9//16, y + size*9//16, size//4, size*3//16))
    elif b_type == CACTUS:
        # Cactus body
        pygame.draw.rect(screen, (70, 150, 50), (x + size*3//16, y, size - size*3//8, size))
        # Cactus arms
        pygame.draw.rect(screen, (70, 150, 50), (x, y + size//4, size*3//16, size//4))
        pygame.draw.rect(screen, (70, 150, 50), (x + size - size*3//16, y + size*3//8, size*3//16, size//4))
        # Spines
        pygame.draw.line(screen, (90, 70, 20), (x + size//8, y + size//4), (x - 2, y + size*3//16), 1)
        pygame.draw.line(screen, (90, 70, 20), (x + size//8, y + size*3//8), (x - 2, y + size*7//16), 1)
        pygame.draw.line(screen, (90, 70, 20), (x + size - size//8, y + size*3//8), (x + size + 2, y + size*5//16), 1)
    elif b_type == DEAD_BUSH:
        cx, cy = x + size // 2, y + size - 4
        bush_c = (140, 100, 50)
        pygame.draw.line(screen, bush_c, (cx, cy), (cx - size//4, cy - size*3//8), 2)
        pygame.draw.line(screen, bush_c, (cx, cy), (cx + size//4, cy - size*3//8), 2)
        pygame.draw.line(screen, bush_c, (cx, cy), (cx - size//8, cy - size//2), 1)
        pygame.draw.line(screen, bush_c, (cx, cy), (cx + size//8, cy - size//2), 1)
    elif b_type == BEDROCK:
        pygame.draw.rect(screen, (25, 25, 25), (x, y, size, size))
        pygame.draw.rect(screen, (10, 10, 10), (x + size//8, y + size//8, size//4, size//4))
        pygame.draw.rect(screen, (45, 45, 45), (x + size*3//8, y + size//8, size*5//16, size*3//16))
        pygame.draw.rect(screen, (10, 10, 10), (x + size*11//16, y + size*3//8, size*3//16, size*3//8))
        pygame.draw.rect(screen, (45, 45, 45), (x + size//8, y + size*5//8, size//4, size//4))
    elif b_type == SADDLE:
        pygame.draw.ellipse(screen, (139, 69, 19), (x + 2, y + 6, size - 4, size - 12))
        pygame.draw.rect(screen, (100, 50, 10), (x + 6, y + 8, size - 12, size - 16))
        pygame.draw.rect(screen, (180, 180, 180), (x + size//2 - 6, y + size - 10, 12, 4))
        pygame.draw.rect(screen, (120, 120, 120), (x + size//2 - 4, y + 10, 8, 2))
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

    # 1 Coal + 1 Stick -> 4 Torches
    if ((grid.count(COAL) == 1 and grid.count(STICK) == 1 and grid.count(None) == 2) or
        (grid.count(CHARCOAL) == 1 and grid.count(STICK) == 1 and grid.count(None) == 2)):
        res = {"type": TORCH, "count": 4}
        
    # 4 Planks -> 1 Crafting Table
    if all(g == PLANKS for g in grid):
        res = {"type": CRAFTING_TABLE, "count": 1}
        
    # 1 Iron Block -> 9 Iron Ingots
    if grid.count(IRON_BLOCK_PROD) == 1 and grid.count(None) == 3:
        res = {"type": IRON_INGOT, "count": 9}
    if grid.count(HAY_BALE) == 1 and grid.count(None) == 3:
        res = {"type": WHEAT_ITEM, "count": 9}
    if grid.count(BEETROOT_ITEM) == 1 and grid.count(None) == 3:
        res = {"type": RED_DYE, "count": 1}
    if grid.count(POPPY) == 1 and grid.count(None) == 3:
        res = {"type": RED_DYE, "count": 1}
    if grid.count(DANDELION) == 1 and grid.count(None) == 3:
        res = {"type": YELLOW_DYE, "count": 1}
    if grid.count(CORNFLOWER) == 1 and grid.count(None) == 3:
        res = {"type": BLUE_DYE, "count": 1}
    if grid.count(IRON_INGOT) == 1 and grid.count(FLINT) == 1 and grid.count(None) == 2:
        res = {"type": FLINT_STEEL, "count": 1, "durability": MAX_DURABILITY[FLINT_STEEL]}
    if grid.count(RED_DYE) == 1 and grid.count(YELLOW_DYE) == 1 and grid.count(None) == 2:
        res = {"type": ORANGE_DYE, "count": 1}
    if grid.count(RED_DYE) == 1 and grid.count(BLUE_DYE) == 1 and grid.count(None) == 2:
        res = {"type": PURPLE_DYE, "count": 1}
    if grid.count(BLUE_DYE) == 1 and grid.count(GREEN_DYE) == 1 and grid.count(None) == 2:
        res = {"type": CYAN_DYE, "count": 1}
    if grid.count(BED) == 1 and grid.count(RED_DYE) == 1 and grid.count(None) == 2:
        res = {"type": RED_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(YELLOW_DYE) == 1 and grid.count(None) == 2:
        res = {"type": YELLOW_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(ORANGE_DYE) == 1 and grid.count(None) == 2:
        res = {"type": ORANGE_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(GREEN_DYE) == 1 and grid.count(None) == 2:
        res = {"type": GREEN_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(BLUE_DYE) == 1 and grid.count(None) == 2:
        res = {"type": BLUE_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(PURPLE_DYE) == 1 and grid.count(None) == 2:
        res = {"type": PURPLE_BED, "count": 1}
    if grid.count(BED) == 1 and grid.count(CYAN_DYE) == 1 and grid.count(None) == 2:
        res = {"type": CYAN_BED, "count": 1}
        
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

    # 1 Coal + 1 Stick -> 4 Torches (Anywhere in 3x3)
    if ((grid3.count(COAL) == 1 and grid3.count(STICK) == 1 and grid3.count(None) == 7) or
        (grid3.count(CHARCOAL) == 1 and grid3.count(STICK) == 1 and grid3.count(None) == 7)):
        res3 = {"type": TORCH, "count": 4}

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
    if grid3.count(HAY_BALE) == 1 and grid3.count(None) == 8:
        res3 = {"type": WHEAT_ITEM, "count": 9}
    if grid3.count(BEETROOT_ITEM) == 1 and grid3.count(None) == 8:
        res3 = {"type": RED_DYE, "count": 1}
    if grid3.count(POPPY) == 1 and grid3.count(None) == 8:
        res3 = {"type": RED_DYE, "count": 1}
    if grid3.count(DANDELION) == 1 and grid3.count(None) == 8:
        res3 = {"type": YELLOW_DYE, "count": 1}
    if grid3.count(CORNFLOWER) == 1 and grid3.count(None) == 8:
        res3 = {"type": BLUE_DYE, "count": 1}
    if grid3.count(IRON_INGOT) == 1 and grid3.count(FLINT) == 1 and grid3.count(None) == 7:
        res3 = {"type": FLINT_STEEL, "count": 1, "durability": MAX_DURABILITY[FLINT_STEEL]}
    if grid3.count(RED_DYE) == 1 and grid3.count(YELLOW_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": ORANGE_DYE, "count": 1}
    if grid3.count(RED_DYE) == 1 and grid3.count(BLUE_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": PURPLE_DYE, "count": 1}
    if grid3.count(BLUE_DYE) == 1 and grid3.count(GREEN_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": CYAN_DYE, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(RED_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": RED_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(YELLOW_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": YELLOW_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(ORANGE_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": ORANGE_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(GREEN_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": GREEN_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(BLUE_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": BLUE_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(PURPLE_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": PURPLE_BED, "count": 1}
    if grid3.count(BED) == 1 and grid3.count(CYAN_DYE) == 1 and grid3.count(None) == 7:
        res3 = {"type": CYAN_BED, "count": 1}

    if grid3 == [PLANKS] * 9:
        res3 = {"type": ROCKET_LAUNCHER, "count": 1}

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
    W = PLANKS; S = COBBLESTONE; T = STICK; N = None; I = IRON_INGOT; D = DIAMOND; ST = STICK; STR = STRING_ITEM
    # Pickaxes
    match([W,W,W, N,T,N, N,T,N], {"type": W_PICK, "count": 1, "durability": 60})
    match([S,S,S, N,T,N, N,T,N], {"type": S_PICK, "count": 1, "durability": 132})
    match([I,I,I, N,T,N, N,T,N], {"type": I_PICK, "count": 1, "durability": 250})
    match([D,D,D, N,T,N, N,T,N], {"type": D_PICK, "count": 1, "durability": 1561})
    # Axes
    match([W,W,N, W,T,N, N,T,N], {"type": W_AXE, "count": 1, "durability": 60})
    match([S,S,N, S,T,N, N,T,N], {"type": S_AXE, "count": 1, "durability": 132})
    match([I,I,N, I,T,N, N,T,N], {"type": I_AXE, "count": 1, "durability": 250})
    match([D,D,N, D,T,N, N,T,N], {"type": D_AXE, "count": 1, "durability": 1561})
    # Shovels
    match([N,W,N, N,T,N, N,T,N], {"type": W_SHOVEL, "count": 1, "durability": 60})
    match([N,S,N, N,T,N, N,T,N], {"type": S_SHOVEL, "count": 1, "durability": 132})
    match([N,I,N, N,T,N, N,T,N], {"type": I_SHOVEL, "count": 1, "durability": 250})
    match([N,D,N, N,T,N, N,T,N], {"type": D_SHOVEL, "count": 1, "durability": 1561})
    # Swords
    match([N,W,N, N,W,N, N,T,N], {"type": W_SWORD, "count": 1, "durability": 60})
    match([N,S,N, N,S,N, N,T,N], {"type": S_SWORD, "count": 1, "durability": 132})
    match([N,I,N, N,I,N, N,T,N], {"type": I_SWORD, "count": 1, "durability": 250})
    match([N,D,N, N,D,N, N,T,N], {"type": D_SWORD, "count": 1, "durability": 1561})
    # Spears use a diagonal pair of sticks with the material at the top end.
    match([N,N,COPPER_INGOT, N,T,N, T,N,N], {"type": COPPER_SPEAR, "count": 1, "durability": 180})
    match([N,N,I, N,T,N, T,N,N], {"type": IRON_SPEAR, "count": 1, "durability": 250})
    # Leather horse armor uses an H, leaving the top and bottom center slots empty.
    match([LEATHER,N,LEATHER, LEATHER,LEATHER,LEATHER, LEATHER,N,LEATHER], {"type": LEATHER_HORSE_ARMOR, "count": 1})
    # Hoes
    match([W,W,N, N,T,N, N,T,N], {"type": W_HOE, "count": 1, "durability": 60})
    match([S,S,N, N,T,N, N,T,N], {"type": S_HOE, "count": 1, "durability": 132})
    match([N,S,S, N,T,N, N,T,N], {"type": S_HOE, "count": 1, "durability": 132})
    match([I,I,N, N,T,N, N,T,N], {"type": I_HOE, "count": 1, "durability": 250})
    match([N,I,I, N,T,N, N,T,N], {"type": I_HOE, "count": 1, "durability": 250})
    match([D,D,N, N,T,N, N,T,N], {"type": D_HOE, "count": 1, "durability": 1561})
    match([N,D,D, N,T,N, N,T,N], {"type": D_HOE, "count": 1, "durability": 1561})
    # Armor
    match([I,I,I, I,N,I, N,N,N], {"type": I_HELMET, "count": 1, "durability": 165})
    match([I,N,I, I,I,I, I,I,I], {"type": I_CHEST, "count": 1, "durability": 240})
    match([I,I,I, I,N,I, I,N,I], {"type": I_LEGS, "count": 1, "durability": 225})
    match([N,N,N, I,N,I, I,N,I], {"type": I_BOOTS, "count": 1, "durability": 195})
    match([D,D,D, D,N,D, N,N,N], {"type": D_HELMET, "count": 1, "durability": 363})
    match([D,N,D, D,D,D, D,D,D], {"type": D_CHEST, "count": 1, "durability": 528})
    match([D,D,D, D,N,D, D,N,D], {"type": D_LEGS, "count": 1, "durability": 495})
    match([N,N,N, D,N,D, D,N,D], {"type": D_BOOTS, "count": 1, "durability": 429})
    # Shield: iron in the top-middle slot.
    match([W,I,W, W,W,W, N,W,N], {"type": SHIELD, "count": 1, "durability": 336})
    # Bow
    match([STR,T,N, STR,N,T, STR,T,N], {"type": BOW, "count": 1, "durability": 384})
    # Fishing Rod
    match([N,N,ST, N,ST,STR, ST,N,STR], {"type": FISHING_ROD, "count": 1, "durability": 64})
    # Furnace
    match([S,S,S, S,N,S, S,S,S], {"type": FURNACE, "count": 1})
    # Glass panes
    match([GLASS,GLASS,GLASS, GLASS,GLASS,GLASS, N,N,N], {"type": GLASS_PANE, "count": 16})
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
    # Slabs
    match([N,N,N, N,N,N, W,W,W], {"type": W_SLAB, "count": 6})
    match([N,N,N, N,N,N, S,S,S], {"type": C_SLAB, "count": 6})
    match([N,N,N, N,N,N, SS,SS,SS], {"type": SS_SLAB, "count": 6})
    # Farming
    WH = WHEAT_ITEM
    match([N,N,N, WH,WH,WH, N,N,N], {"type": BREAD, "count": 1})
    match([WH,WH,WH, WH,WH,WH, WH,WH,WH], {"type": HAY_BALE, "count": 1})
    match([COAL,COAL,COAL, COAL,COAL,COAL, COAL,COAL,COAL], {"type": COAL_BLOCK_ITEM, "count": 1})
    # Bow
    match([N,N,N, N,N,N, STR,T,N], {"type": BOW, "count": 1, "durability": 384})
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
    # Shears
    match([I,N,N, N,I,N, N,N,N], {"type": SHEARS, "count": 1, "durability": 238})
    
    # Boat (5 Planks in U shape)
    match([N,N,N, W,N,W, W,W,W], {"type": BOAT, "count": 1})
    
    # Ladder (Sticks in H shape)
    match([T,N,T, T,T,T, T,N,T], {"type": LADDER, "count": 3})
    
    player.output_3x3 = res3


RECIPE_BOOK_ENTRIES = [
    (PLANKS, 4, "1 Oak or Birch Log", "2x2/3x3"),
    (STICK, 4, "2 Planks, vertical", "2x2/3x3"),
    (TORCH, 4, "1 Coal or Charcoal + 1 Stick", "2x2/3x3"),
    (CRAFTING_TABLE, 1, "4 Planks", "2x2/3x3"),
    (IRON_INGOT, 9, "1 Iron Block", "2x2/3x3"),
]

for material, pick, axe, shovel, sword, hoe in (
    ("Planks", W_PICK, W_AXE, W_SHOVEL, W_SWORD, W_HOE),
    ("Cobblestone", S_PICK, S_AXE, S_SHOVEL, S_SWORD, S_HOE),
    ("Iron Ingots", I_PICK, I_AXE, I_SHOVEL, I_SWORD, I_HOE),
    ("Diamonds", D_PICK, D_AXE, D_SHOVEL, D_SWORD, D_HOE),
):
    RECIPE_BOOK_ENTRIES.extend((
        (pick, 1, f"3 {material} + 2 Sticks", "3x3"),
        (axe, 1, f"3 {material} + 2 Sticks", "3x3"),
        (shovel, 1, f"1 {material} + 2 Sticks", "3x3"),
        (sword, 1, f"2 {material} + 1 Stick", "3x3"),
        (hoe, 1, f"2 {material} + 2 Sticks", "3x3"),
    ))

RECIPE_BOOK_ENTRIES.extend((
        (COPPER_SPEAR, 1, "1 Copper Ingot + 2 Sticks, diagonal", "3x3"),
        (IRON_SPEAR, 1, "1 Iron Ingot + 2 Sticks, diagonal", "3x3"),
        (LEATHER_HORSE_ARMOR, 1, "7 Leather, H pattern", "3x3"),
))

for material, helmet, chest, legs, boots in (
    ("Iron Ingots", I_HELMET, I_CHEST, I_LEGS, I_BOOTS),
    ("Diamonds", D_HELMET, D_CHEST, D_LEGS, D_BOOTS),
):
    RECIPE_BOOK_ENTRIES.extend((
        (helmet, 1, f"5 {material}", "3x3"),
        (chest, 1, f"8 {material}", "3x3"),
        (legs, 1, f"7 {material}", "3x3"),
        (boots, 1, f"4 {material}", "3x3"),
    ))

RECIPE_BOOK_ENTRIES.extend((
    (SHIELD, 1, "6 Planks + 1 Iron Ingot", "3x3"),
    (BOW, 1, "3 Strings + 3 Sticks", "3x3"),
    (FISHING_ROD, 1, "3 Sticks + 2 Strings", "3x3"),
    (RED_DYE, 1, "1 Poppy", "2x2/3x3"),
    (RED_DYE, 1, "1 Beetroot", "2x2/3x3"),
    (YELLOW_DYE, 1, "1 Dandelion", "2x2/3x3"),
    (BLUE_DYE, 1, "1 Cornflower", "2x2/3x3"),
    (ORANGE_DYE, 1, "1 Red Dye + 1 Yellow Dye", "2x2/3x3"),
    (PURPLE_DYE, 1, "1 Red Dye + 1 Blue Dye", "2x2/3x3"),
    (CYAN_DYE, 1, "1 Blue Dye + 1 Green Dye", "2x2/3x3"),
    (RED_BED, 1, "1 Bed + 1 Red Dye", "2x2/3x3"),
    (YELLOW_BED, 1, "1 Bed + 1 Yellow Dye", "2x2/3x3"),
    (ORANGE_BED, 1, "1 Bed + 1 Orange Dye", "2x2/3x3"),
    (GREEN_DYE, 1, "Smelt 1 Cactus", "Furnace"),
    (GREEN_BED, 1, "1 Bed + 1 Green Dye", "2x2/3x3"),
    (BLUE_BED, 1, "1 Bed + 1 Blue Dye", "2x2/3x3"),
    (PURPLE_BED, 1, "1 Bed + 1 Purple Dye", "2x2/3x3"),
    (CYAN_BED, 1, "1 Bed + 1 Cyan Dye", "2x2/3x3"),
    (FURNACE, 1, "8 Cobblestone", "3x3"),
    (GLASS_PANE, 16, "6 Glass", "3x3"),
    (IRON_BLOCK_PROD, 1, "9 Iron Ingots", "3x3"),
    (IRON_DOOR, 3, "6 Iron Ingots", "3x3"),
    (IRON_TRAPDOOR, 2, "6 Iron Ingots", "3x3"),
    (IRON_PRESSURE_PLATE, 1, "2 Iron Ingots", "3x3"),
    (CHAIN, 1, "3 Iron Ingots", "3x3"),
    (W_STAIRS, 4, "6 Planks", "3x3"),
    (C_STAIRS, 4, "6 Cobblestone", "3x3"),
    (SS_STAIRS, 4, "6 Smooth Stone", "3x3"),
    (W_SLAB, 6, "3 Planks", "3x3"),
    (C_SLAB, 6, "3 Cobblestone", "3x3"),
    (SS_SLAB, 6, "3 Smooth Stone", "3x3"),
    (BREAD, 1, "3 Wheat", "3x3"),
    (HAY_BALE, 1, "9 Wheat", "3x3"),
    (WHEAT_ITEM, 9, "1 Hay Bale", "2x2/3x3"),
    (COAL_BLOCK_ITEM, 1, "9 Coal", "3x3"),
    (CHEST, 1, "8 Planks", "3x3"),
    (DOOR, 3, "6 Planks", "3x3"),
    (TRAPDOOR, 2, "6 Planks", "3x3"),
    (PRESSURE_PLATE, 1, "2 Planks", "3x3"),
    (BUTTON, 1, "1 Plank", "3x3"),
    (FENCE, 2, "6 Sticks", "3x3"),
    (FENCE_GATE, 1, "4 Sticks + 2 Planks", "3x3"),
    (LEVER, 1, "1 Stick + 1 Cobblestone", "3x3"),
    (BED, 1, "3 Wool + 3 Planks", "3x3"),
    (SMOKER, 1, "4 Oak or Birch Logs + 1 Furnace", "3x3"),
    (BLAST_FURNACE, 1, "5 Iron Ingots + 1 Furnace + 3 Smooth Stone", "3x3"),
    (BUCKET, 1, "3 Iron Ingots", "3x3"),
    (FLINT_STEEL, 1, "1 Iron Ingot + 1 Flint (any order)", "2x2/3x3"),
    (SHEARS, 1, "2 Iron Ingots", "3x3"),
    (BOAT, 1, "5 Planks", "3x3"),
    (LADDER, 3, "7 Sticks", "3x3"),
))

RECIPE_BOOK_PAGE_SIZE = 9
RECIPE_BOOK_BUTTON_RECT = pygame.Rect(16, 16, 150, 34)
RECIPE_BOOK_PANEL_RECT = pygame.Rect(90, 35, 620, 530)


def _recipe_book_page_count():
    return max(1, math.ceil(len(RECIPE_BOOK_ENTRIES) / RECIPE_BOOK_PAGE_SIZE))


def _handle_recipe_book_click(player, mx, my):
    panel = RECIPE_BOOK_PANEL_RECT
    close_rect = pygame.Rect(panel.right - 82, panel.top + 10, 68, 28)
    previous_rect = pygame.Rect(panel.left + 28, panel.bottom - 42, 94, 28)
    next_rect = pygame.Rect(panel.right - 122, panel.bottom - 42, 94, 28)
    if close_rect.collidepoint(mx, my):
        player.recipe_book_open = False
    elif previous_rect.collidepoint(mx, my):
        player.recipe_book_page = max(0, player.recipe_book_page - 1)
    elif next_rect.collidepoint(mx, my):
        player.recipe_book_page = min(_recipe_book_page_count() - 1, player.recipe_book_page + 1)


def _draw_recipe_book(screen, font, small_font, page):
    panel = RECIPE_BOOK_PANEL_RECT
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    pygame.draw.rect(screen, (205, 190, 150), panel)
    pygame.draw.rect(screen, (55, 45, 30), panel, 4)
    screen.blit(font.render("Recipe Book", True, (40, 35, 25)), (panel.left + 24, panel.top + 10))
    help_text = small_font.render("Ingredients and crafting grid size | Mouse wheel to browse", True, (60, 55, 45))
    screen.blit(help_text, (panel.left + 24, panel.top + 40))

    start = page * RECIPE_BOOK_PAGE_SIZE
    for row, (item_type, count, ingredients, grid_size) in enumerate(
        RECIPE_BOOK_ENTRIES[start:start + RECIPE_BOOK_PAGE_SIZE]
    ):
        row_y = panel.top + 72 + row * 46
        row_rect = pygame.Rect(panel.left + 16, row_y, panel.width - 32, 42)
        pygame.draw.rect(screen, (225, 214, 183) if row % 2 == 0 else (215, 202, 169), row_rect)
        draw_block_icon(screen, item_type, row_rect.left + 6, row_y + 6, 30, font)
        name = BLOCK_NAMES.get(item_type, "Unknown")
        name_text = small_font.render(f"{name} x{count}", True, (35, 35, 30))
        ingredient_text = small_font.render(ingredients, True, (55, 55, 48))
        grid_text = small_font.render(grid_size, True, (65, 50, 30))
        screen.blit(name_text, (row_rect.left + 44, row_y + 3))
        screen.blit(ingredient_text, (row_rect.left + 44, row_y + 22))
        screen.blit(grid_text, (row_rect.right - grid_text.get_width() - 8, row_y + 3))

    close_rect = pygame.Rect(panel.right - 82, panel.top + 10, 68, 28)
    previous_rect = pygame.Rect(panel.left + 28, panel.bottom - 42, 94, 28)
    next_rect = pygame.Rect(panel.right - 122, panel.bottom - 42, 94, 28)
    for button, label in ((close_rect, "Close"), (previous_rect, "Previous"), (next_rect, "Next")):
        pygame.draw.rect(screen, (125, 108, 76), button)
        pygame.draw.rect(screen, (55, 45, 30), button, 2)
        text = small_font.render(label, True, (255, 255, 240))
        screen.blit(text, text.get_rect(center=button.center))
    page_text = small_font.render(f"Page {page + 1}/{_recipe_book_page_count()}", True, (40, 35, 25))
    screen.blit(page_text, page_text.get_rect(center=(panel.centerx, previous_rect.centery)))


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
                        unlock_achievement(world, "first_craft")
                        for i in range(4):
                            if player.crafting_grid[i]:
                                player.crafting_grid[i]["count"] -= 1
                                if player.crafting_grid[i]["count"] <= 0: player.crafting_grid[i] = None
                        return
                    elif player.held_item["type"] == player.crafting_output["type"] and player.held_item["count"] + player.crafting_output["count"] <= 80:
                        player.held_item["count"] += player.crafting_output["count"]
                        player.crafting_output = None
                        unlock_achievement(world, "first_craft")
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
                        unlock_achievement(world, "first_craft")
                        for i in range(9):
                            if player.crafting_3x3[i]:
                                player.crafting_3x3[i]["count"] -= 1
                                if player.crafting_3x3[i]["count"] <= 0: player.crafting_3x3[i] = None
                        return
                    elif player.held_item["type"] == player.output_3x3["type"] and player.held_item["count"] + player.output_3x3["count"] <= 80:
                        player.held_item["count"] += player.output_3x3["count"]
                        player.output_3x3 = None
                        unlock_achievement(world, "first_craft")
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
                if i == 0 and t in (I_HELMET, D_HELMET): valid = True
                if i == 1 and t in (I_CHEST, D_CHEST): valid = True
                if i == 2 and t in (I_LEGS, D_LEGS): valid = True
                if i == 3 and t in (I_BOOTS, D_BOOTS): valid = True
            
            if valid:
                player.armor[i], player.held_item = player.held_item, player.armor[i]
            return

    # Check Offhand Slot
    ox, oy = inv_x - 50, inv_y + 4 * 44 + 10
    if ox <= mx <= ox + 40 and oy <= my <= oy + 40:
        player.offhand, player.held_item = player.held_item, player.offhand
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
        drop = DroppedItem(player.rect.centerx, player.rect.centery, player.held_item["type"], player.held_item["count"], player.held_item.get("durability"))
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
            elif i_type == COPPER_ORE: result_type = COPPER_INGOT
            elif i_type == SAND_BLOCK: result_type = GLASS
            elif i_type == CACTUS: result_type = GREEN_DYE
            elif i_type == RAW_BEEF: result_type = STEAK
            elif i_type == RAW_MUTTON: result_type = COOKED_MUTTON
            elif i_type == RAW_CHICKEN: result_type = COOKED_CHICKEN
            elif i_type == RAW_COD: result_type = COOKED_COD
            elif i_type == RAW_SALMON: result_type = COOKED_SALMON
            elif i_type in (OAK_LOG, BIRCH_LOG): result_type = CHARCOAL
            
            if result_type:
                can_smelt = True
                b_at_pos = world.data.get(pos)
                # Filtering
                if b_at_pos == SMOKER and i_type not in (RAW_BEEF, RAW_MUTTON, RAW_CHICKEN, RAW_COD, RAW_SALMON): can_smelt = False
                if b_at_pos == BLAST_FURNACE and i_type not in (IRON_BLOCK, COPPER_ORE, COBBLESTONE): can_smelt = False
                
                if data["output"] and (data["output"]["type"] != result_type or data["output"]["count"] >= 80):
                    can_smelt = False
        
        if can_smelt and data["fuel_time"] <= 0 and data["fuel"]:
            # Consume fuel
            f_type = data["fuel"]["type"]
            fuel_values = {
                COAL_BLOCK: 720, COAL_BLOCK_ITEM: 720, COAL: 80, CHARCOAL: 80, 
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

def save_game(world, player, filename):
    save_data = {
        "player_id": player.persistent_id,
        "seed": world.seed,
        "achievements": sorted(world.unlocked_achievements),
        "world_data": {f"{k[0]},{k[1]}": v for k, v in world.data.items()},
        "block_meta": {f"{k[0]},{k[1]}": v for k, v in world.block_meta.items()},
        "chest_data": {f"{k[0]},{k[1]}": v for k, v in world.chest_data.items()},
        "furnace_data": {f"{k[0]},{k[1]}": v for k, v in world.furnace_data.items()},
        "time": world.time,
        "weather_type": world.weather_type,
        "weather_timer": world.weather_timer,
        "weather_intensity": world.weather_intensity,
        "villages_generated": world.villages_generated,
        "village_generation_version": world.village_generation_version,
        "village_locations": world.village_locations,
        "player": {
            "x": player.rect.x, "y": player.rect.y,
            "health": player.health, "hunger": player.hunger,
            "h_timer": player.hunger_timer, "r_timer": player.regen_timer,
            "inventory": player.inventory, "armor": player.armor,
            "offhand": getattr(player, 'offhand', None),
            "name": getattr(player, "display_name", "Player")
        },
        "remote_players": world.remote_players_data,
        "mobs": [
            {
                "x": m.rect.x,
                "y": m.rect.y,
                "type": m.m_type,
                "hp": m.health,
                "sheared": m.sheared,
                "saddled": getattr(m, "saddled", False),
                "golem_angry": m.angry if m.m_type == "iron_golem" else False,
            }
            for m in world.mobs
        ]
    }
    with open(filename, "w") as f:
        json.dump(save_data, f)
    if Path(filename).resolve() == (WORLDS_DIR / "savegame.json").resolve():
        legacy_player_id_file = WORLDS_DIR / "player_id.json"
        if legacy_player_id_file.exists():
            try:
                legacy_player_id_file.unlink()
            except OSError as error:
                print(f"[SAVE] Could not remove migrated player ID file: {error}")
    return True

def load_game(world, player, filename):
    if not os.path.exists(filename): return
    try:
        with open(filename, "r") as f:
            sd = json.load(f)
            saved_player_id = sd.get("player_id")
            if isinstance(saved_player_id, str) and saved_player_id:
                player.persistent_id = saved_player_id
            world.seed = sd.get("seed", world.seed)
            world.rng = random.Random(world.seed)
            # Restore World
            world.chunks = {} # Clear existing
            world.unloaded_chunks = {}
            world.loaded_chunk_columns = None
            world.villages_generated = sd.get("villages_generated", False)
            world.village_generation_version = sd.get("village_generation_version", 0)
            world.village_locations = [
                tuple(location) for location in sd.get("village_locations", [])
            ]
            world.active_water.clear()
            world.water_cascade_removed.clear()
            world.falling_sand.clear()
            raw_world = sd.get("world_data", {})
            max_x = -1
            for k_str, v in raw_world.items():
                tx, ty = map(int, k_str.split(','))
                if tx > max_x: max_x = tx
                world.set_block(tx, ty, v)
                
            # Patch legacy saves (1000-block width)
            if 0 < max_x < WORLD_WIDTH - 1:
                print(f"Legacy save detected. Generating missing terrain from x={max_x+1} to {WORLD_WIDTH-1}...")
                for x in range(max_x + 1, WORLD_WIDTH):
                    h = world.rng.randint(10, 20)
                    for y in range(WORLD_HEIGHT):
                        if y > h: 
                            world.data[(x, y)] = STONE_BLOCK if y > h+4 else DIRT_BLOCK
                        elif y == h: 
                            world.data[(x, y)] = GRASS_BLOCK
                            if world.rng.random() < 0.2:
                                world.data[(x, y - 1)] = TALL_GRASS
            
            world.block_meta = {tuple(map(int, k.split(','))): v for k, v in sd.get("block_meta", {}).items()}
            world.chest_data = {tuple(map(int, k.split(','))): v for k, v in sd.get("chest_data", {}).items()}
            world.furnace_data = {tuple(map(int, k.split(','))): v for k, v in sd.get("furnace_data", {}).items()}
            world.time = sd.get("time", 0)
            world.active_water.clear()
            world.unlocked_achievements = set(sd.get("achievements", []))
            world.achievement_queue.clear()
            world.achievement_toast = None
            world.weather_type = sd.get("weather_type", "clear")
            world.weather_timer = sd.get("weather_timer", 0)
            world.weather_intensity = sd.get("weather_intensity", 0.0)
            if DIAMOND_ORE not in world.data.values():
                for _ in range(max(8, WORLD_WIDTH // 24)):
                    vx = world.rng.randint(0, WORLD_WIDTH - 1)
                    vy = world.rng.randint(80, WORLD_HEIGHT - 8)
                    for _ in range(world.rng.randint(3, 6)):
                        if (vx, vy) in world.data and world.data[(vx, vy)] == STONE_BLOCK:
                            world.data[(vx, vy)] = DIAMOND_ORE
                        vx = (vx + world.rng.choice([-1, 0, 1])) % WORLD_WIDTH
                        vy = max(80, min(WORLD_HEIGHT - 1, vy + world.rng.choice([-1, 0, 1])))
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
                m.sheared = m_data.get("sheared", False)
                m.saddled = m_data.get("saddled", False)
                if m.m_type == "iron_golem":
                    m.angry = m_data.get("golem_angry", False)
                world.mobs.append(m)
            if world.village_generation_version in (9, 10, 11):
                if world.villages_generated:
                    if world.village_generation_version == 9:
                        world._generate_hay_bales_for_existing_villages()
                    world._spawn_golems_for_existing_villages()
                    world._generate_natural_flowers()
                else:
                    world.generate_villages()
                world.village_generation_version = VILLAGE_GENERATION_VERSION
            elif world.village_generation_version < VILLAGE_GENERATION_VERSION:
                legacy_houses = {}
                if world.village_generation_version >= 8:
                    door_offset = 5
                    house_spacing = 16
                    bed_offsets = (2, 3)
                elif world.village_generation_version >= 6:
                    door_offset = 7
                    house_spacing = 16
                    bed_offsets = (1, 2)
                elif world.village_generation_version >= 3:
                    door_offset = 9
                    house_spacing = 16
                    bed_offsets = (4,)
                elif world.village_generation_version >= 2:
                    door_offset = 9
                    house_spacing = 14
                    bed_offsets = (4,)
                else:
                    door_offset = 4
                    house_spacing = 10
                    bed_offsets = (1,)
                for (tx, ty), block_type in world.data.items():
                    if (
                        block_type == DOOR
                        and world.get_block(tx, ty - 1) == DOOR_TOP
                    ):
                        house_x = (tx - door_offset) % WORLD_WIDTH
                        if any(
                            world.get_block(house_x + bed_offset, ty) == BED
                            and world.get_block(house_x + bed_offset + 1, ty) == BED_RIGHT
                            for bed_offset in bed_offsets
                        ):
                            legacy_houses[house_x] = ty + 1

                legacy_locations = []
                legacy_house_counts = []
                houses_to_clear = set()
                for region_start, region_end in ((24, 180), (420, WORLD_WIDTH - 44)):
                    region_houses = {
                        x: y for x, y in legacy_houses.items()
                        if region_start <= x < region_end
                    }
                    for house_x in sorted(region_houses):
                        if world.village_generation_version >= 3:
                            if house_x - house_spacing in region_houses:
                                continue
                            cluster = [house_x]
                            while cluster[-1] + house_spacing in region_houses:
                                cluster.append(cluster[-1] + house_spacing)
                            if len(cluster) < 4:
                                continue
                            houses_to_clear.update(cluster)
                            legacy_locations.append(
                                (house_x, max(region_houses[x] for x in cluster))
                            )
                            legacy_house_counts.append(len(cluster))
                        elif house_x + house_spacing in region_houses:
                            houses_to_clear.update(
                                (house_x, house_x + house_spacing)
                            )
                            legacy_locations.append(
                                (
                                    house_x,
                                    max(
                                        region_houses[house_x],
                                        region_houses[house_x + house_spacing],
                                    ),
                                )
                            )
                            legacy_house_counts.append(None)

                if legacy_locations:
                    old_house_blocks = {
                        PLANKS, GLASS_PANE, DOOR, DOOR_TOP, BED, BED_RIGHT,
                        OAK_LOG, W_STAIRS, CHEST,
                    }
                    for house_x in houses_to_clear:
                        floor_y = legacy_houses[house_x]
                        for x in range(house_x, house_x + 16):
                            for y in range(max(0, floor_y - 20), floor_y + 1):
                                if world.get_block(x, y) in old_house_blocks:
                                    if world.get_block(x, y) == CHEST:
                                        world.chest_data.pop((x, y), None)
                                    world.set_block(x, y, None)
                        for x in (
                            house_x, house_x + 1, house_x + 7, house_x + 10,
                        ):
                            for y in range(floor_y, min(WORLD_HEIGHT, floor_y + 16)):
                                if world.get_block(x, y) == OAK_LOG:
                                    world.set_block(x, y, None)
                        for x in range(house_x - 12, house_x):
                            for y in range(max(0, floor_y - 7), floor_y + 1):
                                if world.get_block(x, y) in (
                                    STONE_BLOCK, LADDER, FURNACE,
                                ):
                                    world.set_block(x, y, None)
                    world.villages_generated = False
                    world.mobs = [m for m in world.mobs if m.m_type != "villager"]
                    world.generate_villages(legacy_locations, legacy_house_counts)
                elif not world.villages_generated:
                    world.generate_villages()
                else:
                    world.village_generation_version = VILLAGE_GENERATION_VERSION
                    world._generate_natural_flowers()
            elif not world.villages_generated:
                world.generate_villages()
    except Exception as e:
        print(f"Load error: {e}")

def shear_saddled_camel(world, camel):
    if camel.m_type != "camel" or not getattr(camel, "saddled", False):
        return False
    camel.saddled = False
    world.dropped_items.append(
        DroppedItem(camel.rect.centerx, camel.rect.centery, SADDLE)
    )
    return True

def drop_mob_loot(world, mob):
    def spawn_drop(item_type, count=1):
        for _ in range(count):
            world.dropped_items.append(
                DroppedItem(mob.rect.centerx, mob.rect.centery, item_type)
            )

    if mob.m_type == "cow":
        spawn_drop(RAW_BEEF, random.randint(2, 4))
        spawn_drop(LEATHER, random.randint(1, 2))
    elif mob.m_type in ("zombie", "husk"):
        spawn_drop(ROTTEN_FLESH, random.randint(1, 2))
        spawn_drop(BONE, random.randint(1, 2))
    elif mob.m_type == "camel":
        if getattr(mob, "saddled", False):
            spawn_drop(SADDLE)
    elif mob.m_type == "enderman":
        spawn_drop(ENDER_PEARL, random.randint(1, 2))
    elif mob.m_type == "sheep":
        if not mob.sheared:
            spawn_drop(WOOL, random.randint(1, 2))
        spawn_drop(RAW_MUTTON, random.randint(1, 3))
    elif mob.m_type == "chicken":
        spawn_drop(RAW_CHICKEN, random.randint(1, 2))
        if random.random() < 0.65:
            spawn_drop(FEATHER, random.randint(1, 2))
    elif mob.m_type == "spider":
        spawn_drop(STRING_ITEM, random.randint(1, 3))
    elif mob.m_type == "iron_golem":
        spawn_drop(IRON_INGOT, random.randint(3, 5))
        spawn_drop(POPPY, random.randint(0, 2))

def anger_village_golem_for_villager(world, mob):
    if mob.m_type != "villager":
        return

    villager_x = mob.rect.centerx
    golems = []
    for candidate in world.mobs:
        if candidate.m_type != "iron_golem":
            continue
        dx = candidate.rect.centerx - villager_x
        if dx > WORLD_PIXELS / 2:
            dx -= WORLD_PIXELS
        elif dx < -WORLD_PIXELS / 2:
            dx += WORLD_PIXELS
        dy = candidate.rect.centery - mob.rect.centery
        distance = math.hypot(dx, dy)
        if distance <= VILLAGE_FOOTPRINT_WIDTH * TILE_SIZE:
            golems.append((distance, candidate))

    if golems:
        min(golems, key=lambda entry: entry[0])[1].angry = True

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

def drop_selected_item(player, world):
    slot = player.inventory[player.selected_slot]
    if not slot:
        return False
    drop = DroppedItem(
        player.rect.centerx,
        player.rect.centery,
        slot["type"],
        1,
        slot.get("durability"),
    )
    drop.vel_x = player.direction * 4
    drop.vel_y = -3
    world.dropped_items.append(drop)
    slot["count"] -= 1
    if slot["count"] <= 0:
        player.inventory[player.selected_slot] = None
    return True

def get_bed_partner(world, tx, ty, block_type):
    partner_type = {
        BED: BED_RIGHT,
        BED_RIGHT: BED,
        RED_BED: RED_BED_RIGHT,
        RED_BED_RIGHT: RED_BED,
        YELLOW_BED: YELLOW_BED_RIGHT,
        YELLOW_BED_RIGHT: YELLOW_BED,
        ORANGE_BED: ORANGE_BED_RIGHT,
        ORANGE_BED_RIGHT: ORANGE_BED,
        GREEN_BED: GREEN_BED_RIGHT,
        GREEN_BED_RIGHT: GREEN_BED,
        BLUE_BED: BLUE_BED_RIGHT,
        BLUE_BED_RIGHT: BLUE_BED,
        PURPLE_BED: PURPLE_BED_RIGHT,
        PURPLE_BED_RIGHT: PURPLE_BED,
        CYAN_BED: CYAN_BED_RIGHT,
        CYAN_BED_RIGHT: CYAN_BED,
    }[block_type]
    for neighbor_x in ((tx + 1) % WORLD_WIDTH, (tx - 1) % WORLD_WIDTH):
        if world.data.get((neighbor_x, ty)) == partner_type:
            return neighbor_x, ty
    return None

def _can_smelt_in_furnace(item_type):
    return item_type in (
        COBBLESTONE, IRON_BLOCK, COPPER_ORE, CACTUS, RAW_BEEF, RAW_MUTTON, RAW_CHICKEN, RAW_COD,
        RAW_SALMON, OAK_LOG, BIRCH_LOG, SAND_BLOCK
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
    
    choice = input("\nSelect option (1-4): ").strip() or "1"
    
    mode = "single"
    if choice == "2": mode = "host"
    elif choice == "3": mode = "join"
    elif choice == "4":
        return
    
    world_name = "default"
    world_seed = None
    if mode != "join":
        # List existing worlds
        saves = [f.name for f in WORLDS_DIR.iterdir() if f.is_file() and f.name.startswith("savegame") and f.name.endswith(".json")]
        if saves:
            print("\nExisting Worlds:")
            for s in saves:
                if s == "savegame.json": name = "default"
                elif s.startswith("savegame_"): name = s[9:-5]
                else: name = s[8:-5]
                print(f" - {name}")
        
        print("\n(Type a world name to load, 'create' for a new world, or enter a numeric seed)")
        world_name = input("Enter world name, 'create', or numeric seed [default]: ").strip() or "default"
        if world_name.lower() == "create":
            world_name = input("Enter name for new world: ").strip() or f"world_{int(time.time())}"
            seed_text = input("Enter world seed (leave blank for a random seed): ").strip()
            if seed_text:
                try:
                    world_seed = int(seed_text)
                except ValueError:
                    world_seed = seed_text
        else:
            try:
                world_seed = int(world_name)
            except ValueError:
                pass
            else:
                world_name = f"seed_{world_seed}"
    else:
        world_name = input("\nEnter World Name OR Host IP Address to Join: ").strip()
        if not world_name: return

    # Resolve filename
    if world_name == "default":
        save_filename = WORLDS_DIR / "savegame.json"
    else:
        # Check standard format first
        save_filename = WORLDS_DIR / f"savegame_{world_name}.json"
        if not save_filename.exists():
            # Fallback to no-underscore format if it exists
            alt_filename = WORLDS_DIR / f"savegame{world_name}.json"
            if alt_filename.exists():
                save_filename = alt_filename
    
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    recipe_font = pygame.font.SysFont(None, 18)

    if not play_loading_screens(screen):
        pygame.quit()
        return

    world, player = World(seed=world_seed), Player(player_name)
    
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

    print(f"[WORLD] Seed: {world.seed}")
    scroll_x = player.rect.centerx - SCREEN_WIDTH // 2
    scroll_y = player.rect.centery - SCREEN_HEIGHT // 2
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
            connected_players = net.get_player_data_snapshot() if net else {}
            for p_id, p_data in connected_players.items():
                if p_id == "host" or not isinstance(p_data, dict):
                    continue
                active_remote_ids.add(p_id)
                world.remote_players_data[p_id] = p_data.copy()
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
        world.update_loaded_chunks(scroll_x + SCREEN_WIDTH // 2)

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
                if event.key == pygame.K_r: player.respawn()
                if (
                    event.key == pygame.K_l
                    and not player.show_inventory
                    and sleep_anim_timer == 0
                    and sleep_wake_timer == 0
                ):
                    player.flying = not player.flying
                    player.vel_y = 0
                    player.highest_y = player.rect.y
                    if player.flying:
                        player.health = player.max_health
                if event.key == pygame.K_e and sleep_anim_timer == 0 and sleep_wake_timer == 0: 
                    player.show_inventory = not player.show_inventory
                    if not player.show_inventory: 
                        player.show_3x3 = False
                        player.recipe_book_open = False
                        player.active_furnace_pos = None
                        player.active_chest_pos = None
                
                if event.key == pygame.K_ESCAPE:
                    if player.recipe_book_open:
                        player.recipe_book_open = False
                    elif player.show_inventory:
                        player.show_inventory = False
                        player.show_3x3 = False
                        player.recipe_book_open = False
                        player.active_furnace_pos = None
                        player.active_chest_pos = None
                    else:
                        save_game(world, player, save_filename)
                        running = False
                
                if event.key == pygame.K_u: # Emergency Unlock Key
                    print("[DEBUG] Force Unlocking Player...")
                    player.show_inventory = False
                    player.show_3x3 = False
                    player.recipe_book_open = False
                    player.active_furnace_pos = None
                    player.active_chest_pos = None
                    world.find_safe_spawn(player)
                    sleep_anim_timer = 0
                    sleep_wake_timer = 0
                
                if not player.show_inventory and sleep_anim_timer == 0 and sleep_wake_timer == 0:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                        player.selected_slot = event.key - pygame.K_1
                    if event.key in (pygame.K_q, pygame.K_z):
                        drop_selected_item(player, world)

            if (
                event.type == pygame.MOUSEWHEEL
                and player.show_inventory
                and player.recipe_book_open
                and event.y != 0
            ):
                player.recipe_book_page = max(
                    0, min(_recipe_book_page_count() - 1, player.recipe_book_page - event.y)
                )

            if (
                event.type == pygame.MOUSEWHEEL
                and not player.show_inventory
                and sleep_anim_timer == 0
                and sleep_wake_timer == 0
                and event.y != 0
            ):
                player.selected_slot = (player.selected_slot - event.y) % 9
            
            if player.show_inventory:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    if player.recipe_book_open:
                        _handle_recipe_book_click(player, mx, my)
                    elif event.button == 1 and RECIPE_BOOK_BUTTON_RECT.collidepoint(mx, my):
                        player.recipe_book_open = True
                        player.recipe_book_page = min(
                            player.recipe_book_page, _recipe_book_page_count() - 1
                        )
                    else:
                        handle_inventory_click(player, mx, my, event.button, world)
                    update_crafting(player)
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_z):
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
            mining_targets = []
            mouse_target = None
            m_btns = [False, False, False]
        else:
            px, py = player.rect.centerx // TILE_SIZE, player.rect.centery // TILE_SIZE
            m_btns = pygame.mouse.get_pressed()
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_tile_x = int((scroll_x + mouse_x) // TILE_SIZE) % WORLD_WIDTH
            mouse_tile_y = int((scroll_y + mouse_y) // TILE_SIZE)
            player_tile_x = px % WORLD_WIDTH
            player_tile_y = py
            horizontal_distance = (
                mouse_tile_x - player_tile_x + WORLD_WIDTH // 2
            ) % WORLD_WIDTH - WORLD_WIDTH // 2
            mouse_target = None
            if (
                0 <= mouse_tile_y < WORLD_HEIGHT
                and abs(horizontal_distance) <= 5
                and abs(mouse_tile_y - player_tile_y) <= 5
            ):
                mouse_target = (mouse_tile_x, mouse_tile_y)
            mining_targets = (
                [mouse_target]
                if mouse_target is not None
                and mouse_target in world.data
                and world.data[mouse_target] not in (WATER, BEDROCK)
                else []
            )
        now = pygame.time.get_ticks()
        if m_btns[0] and mining_targets:
            # --- Mining Logic ---
            if player.breaking_block not in mining_targets:
                player.breaking_block = mining_targets[0]
                player.breaking_progress = 0.0
            
            if player.breaking_block:
                tx, ty = player.breaking_block
                b_type = world.data[(tx, ty)]
                
                # Tool Efficiency
                tool = player.inventory[player.selected_slot]
                t_type = tool["type"] if tool else None
                speed = 1.0
                if b_type == DIAMOND_ORE and t_type not in (I_PICK, D_PICK):
                    speed = 0.0
                elif t_type in (W_PICK, S_PICK, I_PICK, D_PICK) and b_type in (
                    STONE_BLOCK, DEEPSLATE, DIORITE, GRANITE, ANDESITE,
                    COAL_BLOCK, IRON_BLOCK, COPPER_ORE, DIAMOND_ORE,
                ):
                    if t_type == W_PICK: speed = 3.0
                    elif t_type == S_PICK: speed = 6.0
                    elif t_type == I_PICK: speed = 10.0
                    else: speed = 12.0 # Diamond
                elif t_type in (W_SHOVEL, S_SHOVEL, I_SHOVEL, D_SHOVEL) and b_type == GRAVEL:
                    speed = 3.0 if t_type == W_SHOVEL else (6.0 if t_type == S_SHOVEL else (10.0 if t_type == I_SHOVEL else 12.0))
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
                elif t_type == SHEARS and b_type in (OAK_LEAVES, BIRCH_LEAVES):
                    speed = 8.0
                
                hardness = BLOCK_HARDNESS.get(b_type, 1.0)
                if b_type == TALL_GRASS or b_type in (
                    WHEAT_STG3, CARROT_STG3, POTATO_STG3, BEETROOT_STG3
                ):
                    hardness = 0.01
                if player.flying:
                    speed = max(speed, 60 * hardness)
                player.breaking_progress += (1.0 / (60 * hardness)) * speed
                
                if player.breaking_progress >= 1.0:
                    player.last_action_time = now
                    for bx, by in mining_targets:
                        if (bx, by) in world.data and world.data[(bx, by)] not in (WATER, BEDROCK):
                            drop_type = world.data[(bx, by)]
                            unlock_achievement(world, "first_break")
                            if drop_type == DIAMOND_ORE:
                                unlock_achievement(world, "find_diamond")
                            to_remove = [(bx, by)]
                            extra_drops = []
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
                            elif drop_type in BED_BLOCKS:
                                bed_partner = get_bed_partner(world, bx, by, drop_type)
                                if bed_partner is not None:
                                    to_remove.append(bed_partner)
                                drop_type = (
                                    RED_BED if drop_type in (RED_BED, RED_BED_RIGHT)
                                    else YELLOW_BED if drop_type in (YELLOW_BED, YELLOW_BED_RIGHT)
                                    else ORANGE_BED if drop_type in (ORANGE_BED, ORANGE_BED_RIGHT)
                                    else GREEN_BED if drop_type in (GREEN_BED, GREEN_BED_RIGHT)
                                    else BLUE_BED if drop_type in (BLUE_BED, BLUE_BED_RIGHT)
                                    else PURPLE_BED if drop_type in (PURPLE_BED, PURPLE_BED_RIGHT)
                                    else CYAN_BED if drop_type in (CYAN_BED, CYAN_BED_RIGHT)
                                    else BED
                                )
                            if drop_type == TALL_GRASS:
                                if random.random() < 0.15: drop_type = SEEDS
                                else: drop_type = None # Usually nothing drops
                            elif drop_type == FIRE:
                                drop_type = None
                            elif drop_type == DEAD_BUSH:
                                drop_type = STICK
                                if random.random() < 0.5:
                                    world.dropped_items.append(DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, STICK))
                            elif drop_type in CROP_STAGE_TO_KIND:
                                crop_kind = CROP_STAGE_TO_KIND[drop_type]
                                is_mature = drop_type == CROP_STAGES[crop_kind][-1]
                                drop_type = None
                                if is_mature:
                                    if crop_kind == "wheat":
                                        unlock_achievement(world, "harvest_wheat")
                                extra_drops.extend(get_crop_drops(drop_type))
                            elif drop_type == GRASS_BLOCK: drop_type = DIRT_BLOCK
                            elif drop_type == COAL_BLOCK: drop_type = COAL
                            elif drop_type == DIAMOND_ORE: drop_type = DIAMOND
                            elif drop_type == GRAVEL and random.random() < 0.1: drop_type = FLINT
                            elif drop_type == STONE_BLOCK: drop_type = COBBLESTONE
                            
                            for pos in to_remove:
                                if pos in world.data:
                                    del world.data[pos]
                                    if pos in world.block_meta: del world.block_meta[pos]
                                    if net:
                                        net.send({"type": "BLOCK", "pos": f"{pos[0]},{pos[1]}", "b_type": None})
                            
                            if drop_type in (OAK_LEAVES, BIRCH_LEAVES) and tool and tool["type"] == SHEARS:
                                world.dropped_items.append(DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, drop_type))
                            elif drop_type in (OAK_LEAVES, BIRCH_LEAVES):
                                leaf_x = bx * TILE_SIZE + 8
                                leaf_y = by * TILE_SIZE + 8
                                if random.random() < 0.05:
                                    sapling = OAK_SAPLING if drop_type == OAK_LEAVES else BIRCH_SAPLING
                                    world.dropped_items.append(DroppedItem(leaf_x, leaf_y, sapling))
                                elif random.random() < 0.03:
                                    world.dropped_items.append(DroppedItem(leaf_x, leaf_y, STICK))
                                if drop_type == OAK_LEAVES and random.randrange(200) == 0:
                                    world.dropped_items.append(DroppedItem(leaf_x, leaf_y, APPLE))
                            elif drop_type and drop_type not in (OAK_LEAVES, BIRCH_LEAVES):
                                world.dropped_items.append(DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, drop_type))
                            for item_type, count in extra_drops:
                                world.dropped_items.append(
                                    DroppedItem(bx * TILE_SIZE + 8, by * TILE_SIZE + 8, item_type, count)
                                )
                        
                        # Durability Loss
                        if tool and tool["type"] in MAX_DURABILITY and tool["type"] != FLINT_STEEL:
                            if "durability" not in tool:
                                # Fallback: add durability if missing (legacy items)
                                tool["durability"] = MAX_DURABILITY.get(tool["type"], 60)
                            
                            tool["durability"] -= 1
                            if tool["durability"] <= 0:
                                player.inventory[player.selected_slot] = None
                                
                    player.breaking_block = None
                    player.breaking_progress = 0.0

        elif m_btns[0]:
            player.breaking_block = None
            player.breaking_progress = 0.0
        elif m_btns[2] and now - player.last_action_time > 120:
            # --- Placing/Interacting Logic ---
            action_taken = False
            slot = player.inventory[player.selected_slot]

            if slot and slot["type"] == WATER_BUCKET and mouse_target is not None:
                target_block = world.data.get(mouse_target)
                if target_block is None:
                    world.set_block(*mouse_target, WATER)
                    world.block_meta[mouse_target] = {"level": 7, "source": True}
                    world.active_water.add(mouse_target)
                    slot["type"] = BUCKET
                    if net:
                        net.send({"type": "BLOCK", "pos": f"{mouse_target[0]},{mouse_target[1]}", "b_type": WATER})
                    action_taken = True
            elif slot and slot["type"] == BUCKET and mouse_target is not None:
                if world.data.get(mouse_target) == WATER:
                    world.set_block(*mouse_target, None)
                    slot["type"] = WATER_BUCKET
                    unlock_achievement(world, "collect_water")
                    if net:
                        net.send({"type": "BLOCK", "pos": f"{mouse_target[0]},{mouse_target[1]}", "b_type": None})
                    action_taken = True

            if not action_taken and slot and slot["type"] == FLINT_STEEL and mouse_target is not None:
                fire_pos = ignite_fire(world, *mouse_target)
                if fire_pos is not None:
                    if net:
                        net.send({
                            "type": "BLOCK",
                            "pos": f"{fire_pos[0]},{fire_pos[1]}",
                            "b_type": FIRE,
                        })
                    slot["durability"] = slot.get("durability", MAX_DURABILITY[FLINT_STEEL]) - 1
                    if slot["durability"] <= 0:
                        player.inventory[player.selected_slot] = None
                    action_taken = True

            # Ender Pearl: throw toward the mouse cursor and teleport on landing.
            if not action_taken and slot and slot["type"] == ENDER_PEARL:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                world.projectiles.append(ThrownPearl(player.rect.centerx, player.rect.centery, target_x, target_y))
                slot["count"] -= 1
                if slot["count"] <= 0:
                    player.inventory[player.selected_slot] = None
                player.last_action_time = now
                action_taken = True
            elif not action_taken and slot and slot["type"] == ROCKET_LAUNCHER:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                world.rocket_projectiles.append(
                    RocketShot(player.rect.centerx, player.rect.centery, target_x, target_y)
                )
                action_taken = True
            elif not action_taken and slot and slot["type"] == EGG:
                mx, my = pygame.mouse.get_pos()
                target_x = (scroll_x + mx) % WORLD_PIXELS
                target_y = max(0, min(WORLD_HEIGHT * TILE_SIZE - 1, int(scroll_y + my)))
                world.egg_projectiles.append(EggShot(player.rect.centerx, player.rect.centery, target_x, target_y))
                slot["count"] -= 1
                if slot["count"] <= 0:
                    player.inventory[player.selected_slot] = None
                player.last_action_time = now
                action_taken = True
            elif not action_taken and slot and slot["type"] == BOW:
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
            elif not action_taken and slot and slot["type"] == FISHING_ROD:
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

            if not action_taken:
                mx, my = pygame.mouse.get_pos()
                world_click_x = (scroll_x + mx) % WORLD_PIXELS
                world_click_y = scroll_y + my
                clicked_camel = None
                for mob in world.mobs:
                    if mob.m_type == "camel":
                        for offset in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
                            m_rect = mob.rect.copy()
                            m_rect.x += offset
                            if m_rect.collidepoint(world_click_x, world_click_y):
                                clicked_camel = mob
                                break
                        if clicked_camel:
                            break
                
                if clicked_camel:
                    action_taken = True
                    player.last_action_time = now
                    if (
                        slot
                        and slot["type"] == SHEARS
                        and shear_saddled_camel(world, clicked_camel)
                    ):
                        slot["durability"] = slot.get("durability", MAX_DURABILITY[SHEARS]) - 1
                        if slot["durability"] <= 0:
                            player.inventory[player.selected_slot] = None
                    elif slot and slot["type"] == SADDLE:
                        if not getattr(clicked_camel, "saddled", False):
                            clicked_camel.saddled = True
                            clicked_camel.tamed = True
                            slot["count"] -= 1
                            if slot["count"] <= 0:
                                player.inventory[player.selected_slot] = None
                    else:
                        clicked_camel.tamed = True
                        player.riding_mob = clicked_camel
                elif slot and slot["type"] == SHEARS:
                    clicked_sheep = None
                    for mob in world.mobs:
                        if mob.m_type != "sheep" or mob.sheared:
                            continue
                        for offset in (-WORLD_PIXELS, 0, WORLD_PIXELS):
                            sheep_rect = mob.rect.copy()
                            sheep_rect.x += offset
                            if sheep_rect.collidepoint(world_click_x, world_click_y):
                                clicked_sheep = mob
                                break
                        if clicked_sheep:
                            break
                    if clicked_sheep:
                        clicked_sheep.sheared = True
                        unlock_achievement(world, "shear_sheep")
                        for _ in range(random.randint(1, 3)):
                            world.dropped_items.append(
                                DroppedItem(clicked_sheep.rect.centerx, clicked_sheep.rect.centery, WOOL)
                            )
                        slot["durability"] = slot.get("durability", MAX_DURABILITY[SHEARS]) - 1
                        if slot["durability"] <= 0:
                            player.inventory[player.selected_slot] = None
                        action_taken = True
                        player.last_action_time = now

            for tx, ty in ([] if action_taken or mouse_target is None else [mouse_target]):
                if (tx, ty) in world.data and world.data[(tx, ty)] == BOAT:
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
                    if (tx, ty) not in world.data or world.data.get((tx, ty)) == WATER:
                        boat_pos = (tx, ty)
                    elif ty > 0 and (tx, ty - 1) not in world.data:
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
                if slot and slot["type"] in (
                    APPLE, BREAD, RAW_BEEF, STEAK, ROTTEN_FLESH, RAW_MUTTON, COOKED_MUTTON,
                    RAW_COD, COOKED_COD, RAW_SALMON, COOKED_SALMON, MILK_BUCKET,
                    CARROT_ITEM, POTATO_ITEM, POISONOUS_POTATO, BEETROOT_ITEM,
                ):
                    if slot["type"] == MILK_BUCKET or player.hunger < player.max_hunger:
                        fill = {
                            APPLE: 4, BREAD: 5, RAW_BEEF: 3, STEAK: 8, ROTTEN_FLESH: 4,
                            RAW_MUTTON: 3, COOKED_MUTTON: 7, RAW_COD: 2,
                            COOKED_COD: 5, RAW_SALMON: 2, COOKED_SALMON: 6,
                            MILK_BUCKET: 2, CARROT_ITEM: 3, POTATO_ITEM: 2,
                            POISONOUS_POTATO: 1, BEETROOT_ITEM: 2,
                        }[slot["type"]]
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
                    if (tx, ty) in world.data and world.data[(tx, ty)] in (GRASS_BLOCK, DIRT_BLOCK):
                        world.data[(tx, ty)] = FARMLAND
                        world.block_meta[(tx, ty)] = {"moisture": 7}
                        if net:
                            net.send({
                                "type": "BLOCK",
                                "pos": f"{tx},{ty}",
                                "b_type": FARMLAND,
                                "meta": world.block_meta[(tx, ty)],
                            })
                        slot["durability"] -= 1
                        if slot["durability"] <= 0: player.inventory[player.selected_slot] = None
                        action_taken = True
                        break
                # Planting crop seeds and vegetables
                if slot and slot["type"] in CROP_PLANT_ITEMS:
                    if (tx, ty) in world.data and world.data[(tx, ty)] == FARMLAND:
                        if (tx, ty - 1) not in world.data:
                            crop_kind = CROP_PLANT_ITEMS[slot["type"]]
                            world.data[(tx, ty - 1)] = CROP_STAGES[crop_kind][0]
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
                elif (tx, ty) in world.data and world.data[(tx, ty)] in (DOOR, DOOR_TOP, DOOR_OPEN, DOOR_OPEN_TOP, TRAPDOOR, TRAPDOOR_OPEN, FENCE_GATE, FENCE_GATE_OPEN, *BED_BLOCKS):
                    b_type = world.data[(tx, ty)]
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
                    elif b_type == TRAPDOOR: world.data[(tx, ty)] = TRAPDOOR_OPEN
                    elif b_type == TRAPDOOR_OPEN: world.data[(tx, ty)] = TRAPDOOR
                    elif b_type == FENCE_GATE: world.data[(tx, ty)] = FENCE_GATE_OPEN
                    elif b_type == FENCE_GATE_OPEN: world.data[(tx, ty)] = FENCE_GATE
                    elif b_type in BED_BLOCKS:
                        sleep_anim_timer = sleep_anim_total
                        sleep_bed_pos = (tx, ty)
                        action_taken = True
                        break
                    action_taken = True
                    break
                elif (tx, ty) not in world.data or world.data.get((tx, ty)) == WATER:
                    slot = player.inventory[player.selected_slot]
                    if slot is not None and slot["type"] == DOOR:
                        if ty > 0 and (
                            (tx, ty - 1) not in world.data
                            or world.data.get((tx, ty - 1)) == WATER
                        ):
                            bottom_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            top_rect = pygame.Rect(tx * TILE_SIZE, (ty - 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            p_placement_rect = player.rect.inflate(-6, -6)
                            p_placement_rect.x %= WORLD_PIXELS
                            if not p_placement_rect.colliderect(bottom_rect) and not p_placement_rect.colliderect(top_rect):
                                world.data[(tx, ty)] = slot["type"]
                                world.data[(tx, ty - 1)] = DOOR_TOP
                                slot["count"] -= 1
                                action_taken = True
                                if slot["count"] <= 0:
                                    player.inventory[player.selected_slot] = None
                                    break
                    elif slot is not None and slot["type"] in BED_ITEMS:
                        bed_dx = 1 if player.direction > 0 else -1
                        tx2 = (tx + bed_dx) % WORLD_WIDTH
                        if (tx2, ty) not in world.data or world.data.get((tx2, ty)) == WATER:
                            bed_rect_1 = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            bed_rect_2 = pygame.Rect(tx2 * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            p_placement_rect = player.rect.inflate(-6, -6)
                            p_placement_rect.x %= WORLD_PIXELS
                            if not p_placement_rect.colliderect(bed_rect_1) and not p_placement_rect.colliderect(bed_rect_2):
                                bed_head = slot["type"]
                                bed_foot = {
                                    BED: BED_RIGHT,
                                    RED_BED: RED_BED_RIGHT,
                                    YELLOW_BED: YELLOW_BED_RIGHT,
                                    ORANGE_BED: ORANGE_BED_RIGHT,
                                    GREEN_BED: GREEN_BED_RIGHT,
                                    BLUE_BED: BLUE_BED_RIGHT,
                                    PURPLE_BED: PURPLE_BED_RIGHT,
                                    CYAN_BED: CYAN_BED_RIGHT,
                                }[bed_head]
                                world.data[(tx, ty)] = bed_head
                                world.data[(tx2, ty)] = bed_foot
                                if net:
                                    net.send({"type": "BLOCK", "pos": f"{tx},{ty}", "b_type": bed_head})
                                    net.send({"type": "BLOCK", "pos": f"{tx2},{ty}", "b_type": bed_foot})
                                slot["count"] -= 1
                                action_taken = True
                                if slot["count"] <= 0:
                                    player.inventory[player.selected_slot] = None
                                    break
                    elif slot is not None and slot["type"] in PLACEABLE_BLOCKS:
                        tr = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        p_placement_rect = player.rect.inflate(-6, -6)
                        p_placement_rect.x %= WORLD_PIXELS
                        can_place_plant = (
                            slot["type"] not in (OAK_SAPLING, BIRCH_SAPLING, POPPY, DANDELION, CORNFLOWER)
                            or world.get_block(tx, ty + 1) in (GRASS_BLOCK, DIRT_BLOCK)
                        )
                        if can_place_plant and not p_placement_rect.colliderect(tr):
                            world.data[(tx, ty)] = slot["type"]
                            unlock_achievement(world, "first_build")
                            if slot["type"] in (W_STAIRS, C_STAIRS, SS_STAIRS):
                                world.block_meta[(tx, ty)] = {"facing": player.direction}
                            elif slot["type"] == TORCH:
                                wall_facing = None
                                left_block = world.data.get(((tx - 1) % WORLD_WIDTH, ty))
                                right_block = world.data.get(((tx + 1) % WORLD_WIDTH, ty))
                                if left_block and left_block != AIR and left_block != WATER:
                                    wall_facing = 1
                                elif right_block and right_block != AIR and right_block != WATER:
                                    wall_facing = -1
                                if wall_facing is not None:
                                    world.block_meta[(tx, ty)] = {"facing": wall_facing}
                                elif (tx, ty + 1) in world.data and world.data[(tx, ty + 1)] not in (AIR, WATER, TALL_GRASS):
                                    world.block_meta[(tx, ty)] = {"facing": 0}
                            
                            if net:
                                net.send({"type": "BLOCK", "pos": f"{tx},{ty}", "b_type": slot["type"], "meta": world.block_meta.get((tx, ty))})
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
            if world.water_cascade_removed:
                if net:
                    for wx, wy in world.water_cascade_removed:
                        net.send({"type": "BLOCK", "pos": f"{wx},{wy}", "b_type": None})
                world.water_cascade_removed.clear()
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
            elif t_type in (COPPER_SPEAR, IRON_SPEAR): dmg = 5 if t_type == COPPER_SPEAR else 6
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
                            anger_village_golem_for_villager(world, mob)
                            if mob.m_type == "iron_golem":
                                mob.angry = True
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
                    if tool and tool["type"] in MAX_DURABILITY and tool["type"] != FLINT_STEEL:
                        tool["durability"] -= 1
                        if tool["durability"] <= 0:
                            player.inventory[player.selected_slot] = None

        sleeping_visual = sleep_anim_timer > 0 or sleep_wake_timer > 0
        if not sleeping_visual:
            player.update(world)
            update_furnaces(world)
            if world.time % 8 == 0:
                world.update_water()
            if world.time % 3 == 0:
                world.update_falling_sand()
            world.time = (world.time + 1) % 24000
            if world.time % 600 == 0:
                for pos, block_type, metadata in world.update_farmland_moisture():
                    if net:
                        net.send({
                            "type": "BLOCK",
                            "pos": f"{pos[0]},{pos[1]}",
                            "b_type": block_type,
                            "meta": metadata,
                        })
            world.update_weather()
            
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
            # Desert spawning: check if player is in desert biome (tile x 200-400)
            player_tile_x = (player.rect.centerx // TILE_SIZE) % WORLD_WIDTH
            in_desert = 200 <= player_tile_x < 400
            # Husks spawn at night in the desert (they don't burn)
            if in_desert and (t > 14000 or t < 1000) and len([m for m in world.mobs if m.m_type == "husk"]) < 5:
                if random.random() < 0.004:
                    world.mobs.append(Mob((player.rect.x + random.choice([-400, 400])) % WORLD_PIXELS, 50, "husk"))
            # Camels spawn during the day in the desert
            if in_desert and (2000 < t < 12000) and len([m for m in world.mobs if m.m_type == "camel"]) < 3:
                if random.random() < 0.002:
                    world.mobs.append(Mob((player.rect.x + random.choice([-500, 500])) % WORLD_PIXELS, 50, "camel"))
                
            for mob in world.mobs[:]:
                mob.update(world, player)
                if mob.health <= 0:
                    unlock_achievement(world, "first_hunt")
                    drop_mob_loot(world, mob)
                    world.mobs.remove(mob)
                    
            # --- Natural growth ---
            if random.random() < 0.01:
                for pos, block_type, metadata in world.update_natural_growth():
                    if net:
                        net.send({
                            "type": "BLOCK",
                            "pos": f"{pos[0]},{pos[1]}",
                            "b_type": block_type,
                            "meta": metadata,
                        })
                    
            # Auto-Save
            auto_save_timer += 1
            if auto_save_timer >= 1800: # 30 seconds
                # Update remote player data before saving (Host only)
                if mode == "host" and net:
                    for p_id, p_data in net.get_player_data_snapshot().items():
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

        for rocket in world.rocket_projectiles[:]:
            if rocket.update(world):
                world.rocket_projectiles.remove(rocket)
            else:
                rocket.draw(screen, scroll_x, scroll_y)

        for explosion in world.explosions[:]:
            if explosion.update():
                world.explosions.remove(explosion)
            else:
                explosion.draw(screen, scroll_x, scroll_y)

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
        if not player.show_inventory and mouse_target:
            for off in [-WORLD_PIXELS, 0, WORLD_PIXELS]:
                tx, ty = mouse_target
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
            pygame.draw.rect(screen, (105, 88, 58), RECIPE_BOOK_BUTTON_RECT)
            pygame.draw.rect(screen, (35, 30, 20), RECIPE_BOOK_BUTTON_RECT, 2)
            book_label = font.render("Recipe Book", True, (255, 245, 220))
            screen.blit(book_label, book_label.get_rect(center=RECIPE_BOOK_BUTTON_RECT.center))
            
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

            if player.recipe_book_open:
                _draw_recipe_book(screen, font, recipe_font, player.recipe_book_page)

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

            # --- Draw Bubbles (Air) ---
            if player.air < 10:
                for i in range(player.air):
                    hx, hy = 20 + i * 18, 80
                    pygame.draw.circle(screen, (0, 190, 255), (hx + 8, hy + 8), 6) # Bubble
                    pygame.draw.circle(screen, (200, 240, 255), (hx + 6, hy + 6), 2) # Highlight

            # --- Draw Coordinates ---
            cx, cy = player.rect.centerx // TILE_SIZE, player.rect.centery // TILE_SIZE
            coord_text = font.render(f"X: {cx}, Y: {cy}", True, COLOR_WHITE)
            screen.blit(coord_text, (SCREEN_WIDTH - coord_text.get_width() - 20, 20))
            
            # --- Save Message ---
            if save_msg_timer > 0:
                msg = font.render(save_msg_text, True, (100, 255, 100))
                screen.blit(msg, (SCREEN_WIDTH - msg.get_width() - 20, 45))
                save_msg_timer -= 1

            # --- Draw Death Messages ---
            if hasattr(world, 'death_messages'):
                world.death_messages = [m for m in world.death_messages if m["timer"] > 0]
                for idx, m in enumerate(world.death_messages):
                    m["timer"] -= 1
                    text_surf = font.render(m["text"], True, (255, 100, 100))
                    msg_y = 70 + idx * 25
                    bg_rect = pygame.Rect(SCREEN_WIDTH - text_surf.get_width() - 25, msg_y, text_surf.get_width() + 10, 22)
                    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                    bg_surf.fill((0, 0, 0, 160))
                    screen.blit(bg_surf, (bg_rect.x, bg_rect.y))
                    screen.blit(text_surf, (SCREEN_WIDTH - text_surf.get_width() - 20, msg_y + 2))

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

        draw_achievement_toast(screen, font, world)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
