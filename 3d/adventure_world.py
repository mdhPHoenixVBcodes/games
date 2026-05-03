from ursina import *
import random

ground_1 = Entity(model='plane', color=color.green, collider='box', scale=(100, 1, 100), position=(0, 0, 0))
for _ in range(15):
    Entity(model='cube', color=color.brown, position=(random.uniform(-30, 30), 1, random.uniform(-30, 30)), scale=(2, 2, 2), collider='box')

ground_2 = Entity(model='plane', color=color.brown, collider='box', scale=(100, 1, 100), position=(1000, 0, 1000))
for _ in range(10):
    Entity(model='cube', color=color.yellow, position=(1000 + random.uniform(-30, 30), 1, 1000 + random.uniform(-30, 30)), scale=(2, 5, 2), collider='box')

wall_height = 10
Entity(model='cube', color=color.dark_gray, collider='box', scale=(100, wall_height, 1), position=(1000, wall_height/2, 1050))
Entity(model='cube', color=color.dark_gray, collider='box', scale=(100, wall_height, 1), position=(1000, wall_height/2, 950))
Entity(model='cube', color=color.dark_gray, collider='box', scale=(1, wall_height, 100), position=(1050, wall_height/2, 1000))
Entity(model='cube', color=color.dark_gray, collider='box', scale=(1, wall_height, 100), position=(950, wall_height/2, 1000))

ground_3 = Entity(model='cube', color=color.dark_gray, collider='box', scale=(20, 1, 200), position=(2000, 0, 2100))
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 200), position=(1990, 5, 2100))
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 200), position=(2010, 5, 2100))
Entity(model='cube', color=color.gray, collider='box', scale=(20, 10, 1), position=(2000, 5, 1999.5))

level_3_door = Entity(model='cube', color=color.orange, collider='box', scale=(20, 10, 1), position=(2000, 5, 2200.5))

ground_4 = Entity(model='cube', color=color.dark_gray, collider='box', scale=(60, 1, 60), position=(2000, 0, 2230))
Entity(model='cube', color=color.gray, collider='box', scale=(60, 10, 1), position=(2000, 5, 2260))
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 60), position=(1970, 5, 2230))
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 60), position=(2030, 5, 2230))

ground_5 = Entity(model='cube', color=color.white, collider='box', scale=(100, 1, 100), position=(3000, 0, 2230))
ground_6 = Entity(model='cube', color=color.gray, collider='box', scale=(150, 1, 150), position=(4000, 0, 2230))
