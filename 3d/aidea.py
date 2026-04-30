from ursina import *
import json
import os
import random
from pathlib import Path

# Initialize the Ursina application
app = Ursina()

# 1. Create the Environments
# --- Level 1 ---
ground_1 = Entity(model='plane', color=color.green, collider='box', scale=(100, 1, 100), position=(0, 0, 0))
for i in range(15):
    Entity(model='cube', color=color.brown, position=(random.uniform(-30, 30), 1, random.uniform(-30, 30)), scale=(2, 2, 2), collider='box')

# --- Level 2 (Far away) ---
ground_2 = Entity(model='plane', color=color.brown, collider='box', scale=(100, 1, 100), position=(1000, 0, 1000))
for i in range(10):
    Entity(model='cube', color=color.yellow, position=(1000 + random.uniform(-30, 30), 1, 1000 + random.uniform(-30, 30)), scale=(2, 5, 2), collider='box')

# Walls around Level 2
wall_height = 10
Entity(model='cube', color=color.dark_gray, collider='box', scale=(100, wall_height, 1), position=(1000, wall_height/2, 1050)) 
Entity(model='cube', color=color.dark_gray, collider='box', scale=(100, wall_height, 1), position=(1000, wall_height/2, 950))  
Entity(model='cube', color=color.dark_gray, collider='box', scale=(1, wall_height, 100), position=(1050, wall_height/2, 1000)) 
Entity(model='cube', color=color.dark_gray, collider='box', scale=(1, wall_height, 100), position=(950, wall_height/2, 1000))  

# --- Level 3 (Long Hallway) ---
ground_3 = Entity(model='cube', color=color.dark_gray, collider='box', scale=(20, 1, 200), position=(2000, 0, 2100))
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 200), position=(1990, 5, 2100)) # Left Wall
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 200), position=(2010, 5, 2100)) # Right Wall
Entity(model='cube', color=color.gray, collider='box', scale=(20, 10, 1), position=(2000, 5, 1999.5)) # Back Wall (Start)

# The Door at the end of the hallway
level_3_door = Entity(model='cube', color=color.orange, collider='box', scale=(20, 10, 1), position=(2000, 5, 2200.5)) 

# Level 4 (Final Arena)
ground_4 = Entity(model='cube', color=color.dark_gray, collider='box', scale=(60, 1, 60), position=(2000, 0, 2230))
Entity(model='cube', color=color.gray, collider='box', scale=(60, 10, 1), position=(2000, 5, 2260)) # Far wall
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 60), position=(1970, 5, 2230)) # Arena Left wall
Entity(model='cube', color=color.gray, collider='box', scale=(1, 10, 60), position=(2030, 5, 2230)) # Arena Right wall

# Level 5 (White Arena)
ground_5 = Entity(model='cube', color=color.white, collider='box', scale=(100, 1, 100), position=(3000, 0, 2230))

# Level 6 (Gray Arena)
ground_6 = Entity(model='cube', color=color.gray, collider='box', scale=(150, 1, 150), position=(4000, 0, 2230))


# Global tracking lists
enemies = []
cannons = []
cannon_spheres = []
archer_companion = None


def get_active_party_targets():
    targets = [player]
    if archer_companion is not None and getattr(archer_companion, 'hp', 0) > 0:
        targets.append(archer_companion)
    return targets


def get_nearest_party_target(origin):
    targets = get_active_party_targets()
    return min(targets, key=lambda target: distance(origin, target.position)) if targets else None


def dismiss_archer_companion():
    global archer_companion
    if archer_companion is not None:
        destroy(archer_companion)
        archer_companion = None


def spawn_archer_companion():
    global archer_companion
    if archer_companion is None:
        archer_companion = ArcherCompanion()
    return archer_companion

# 2. Portals, NPCs, Cannons, Projectiles, and UI
class Portal(Entity):
    def __init__(self):
        super().__init__(model='sphere', color=color.cyan, scale=(3, 4, 3), position=(0, 1.5, 0), enabled=False)
    def update(self):
        self.rotation_y += 75 * time.dt

portal = Portal()
portal_2 = Portal()
portal_3 = Portal()
portal_4 = Portal()

class Chef(Entity):
    def __init__(self):
        super().__init__(model='sphere', color=color.orange, scale=(2, 4, 2), position=(1000, 1, 1000), collider='box')
        self.exclamation = Text(parent=self, text='Chef', scale=10, color=color.orange, position=(0, 1), billboard=True, origin=(0, 0))
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))
        self.dialogue_ui = Text(text="Chef: Take my bow, right click to shoot!", position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)

chef = Chef()

class Manager(Entity):
    def __init__(self):
        super().__init__(model='sphere', color=color.green, scale=(2, 4, 2), position=(990, 1, 1010), collider='box')
        self.exclamation = Text(parent=self, text='Manager', scale=10, color=color.green, position=(0, 1), billboard=True, origin=(0, 0))
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))
        self.dialogue_ui = Text(text="Manager: Welcome. The portal to Level 3 is open.", position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)

manager = Manager()

class Cannon(Entity):
    def __init__(self, position):
        super().__init__(model='cube', color=color.red, scale=(2, 2, 2), position=position, collider='box')
        self.hp = 100
        self.shoot_timer = random.uniform(3.0, 5.0)

    def take_damage(self, amount):
        self.hp -= amount
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            if self in cannons: cannons.remove(self)
            destroy(self)

    def update(self):
        if player.is_teleporting or distance(self.position, player.position) > 100:
            return 
        
        self.shoot_timer -= time.dt
        if self.shoot_timer <= 0:
            target = get_nearest_party_target(self.position)
            sphere = CannonSphere(self.position + (0, 1, 0), target=target)
            cannon_spheres.append(sphere)
            self.shoot_timer = random.uniform(3.0, 5.0)

class CannonSphere(Entity):
    def __init__(self, position, target=None):
        self.target = target or player
        super().__init__(model='sphere', color=color.orange, scale=2.5, position=position)
        self.speed = 10
        self.look_at_2d(self.target, 'y') 
        self.lifetime = 8.0 # Track lifespan manually

    def take_damage(self, amount):
        if self in cannon_spheres: cannon_spheres.remove(self)
        destroy(self)

    def update(self):
        if player.is_teleporting: return 
        
        # Countdown and cleanly remove from the list if it misses
        self.lifetime -= time.dt
        if self.lifetime <= 0:
            if self in cannon_spheres: cannon_spheres.remove(self)
            destroy(self)
            return

        self.position += self.forward * self.speed * time.dt
        
        for target in get_active_party_targets():
            if distance(self.position, target.position) < 2.5:
                target.take_damage(15) 
                if self in cannon_spheres: cannon_spheres.remove(self)
                destroy(self)
                return

class ShockwaveGrenade(Entity):
    def __init__(self, position, rotation):
        super().__init__(model='sphere', color=color.azure, scale=0.35, position=position, rotation=rotation)
        self.speed = 28
        self.life = 1.2
        self.exploded = False

    def update(self):
        if player.is_teleporting or self.exploded:
            return

        self.position += self.forward * self.speed * time.dt
        self.life -= time.dt

        if self.life <= 0:
            self.explode()
            return

        for enemy in enemies:
            if distance(self.position, enemy.position) < 1.6:
                self.explode()
                return

    def explode(self):
        if self.exploded:
            return

        self.exploded = True
        player.grenade_used = True
        player.mission_ui.text = 'Talk to the Manager.'
        player.mission_ui.color = color.cyan

        shockwave = Entity(
            model='sphere',
            color=color.rgba(120, 240, 255, 110),
            position=self.position,
            scale=1.0
        )
        shockwave.animate_scale(8, duration=0.35)
        shockwave.animate_color(color.rgba(120, 240, 255, 0), duration=0.35)
        destroy(shockwave, delay=0.4)

        for enemy in enemies:
            dist = distance(self.position, enemy.position)
            if dist <= player.grenade_shockwave_radius:
                push_dir = enemy.position - self.position
                if push_dir.length() > 0.001:
                    push_dir = push_dir.normalized()
                else:
                    push_dir = self.forward
                push_strength = player.grenade_shockwave_push * max(0.35, 1 - dist / player.grenade_shockwave_radius)
                enemy.position += push_dir * push_strength
                enemy.stun_timer = 0.45

        destroy(self)

class Arrow(Entity):
    def __init__(self, position, rotation):
        super().__init__(model='cube', color=color.white, scale=(0.05, 0.05, 1.5), position=position, rotation=rotation)
        self.speed = 60 
        self.damage = 25
        destroy(self, delay=2.0) 

    def update(self):
        self.position += self.forward * self.speed * time.dt
        
        for s in cannon_spheres:
            if distance(self.position, s.position) < 2.5:
                s.take_damage(self.damage)
                destroy(self)
                return
                
        for c in cannons:
            if distance(self.position, c.position) < 2.0:
                c.take_damage(self.damage)
                destroy(self)
                return
                
        for e in enemies:
            if distance(self.position, e.position) < 2.5:
                e.take_damage(self.damage)
                destroy(self)
                return 


class ArcherCompanion(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.azure,
            scale=(0.9, 1.8, 0.9),
            position=player.position + (2, 0, -2),
            collider='box'
        )
        self.max_hp = 150
        self.hp = self.max_hp
        self.speed = 7
        self.follow_distance = 2.8
        self.attack_range = 16
        self.attack_cooldown = 0
        self.health_bar = Entity(parent=self, y=1.1, model='cube', color=color.green, scale=(1.2, 0.12, 0.12))
        self.bow = Entity(parent=self, model='cube', color=color.brown, scale=(0.12, 0.8, 0.12), position=(0.55, 0.05, 0.25), rotation=(0, 0, 25))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.2
        self.color = color.white
        invoke(setattr, self, 'color', color.azure, delay=0.1)
        if self.hp <= 0:
            dismiss_archer_companion()

    def update(self):
        if player.is_teleporting:
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        follow_target = player.position + player.right * 1.5 - player.forward * 2.5
        follow_target.y = self.y
        to_follow = follow_target - self.position
        to_follow.y = 0
        if to_follow.length() > self.follow_distance:
            self.position += to_follow.normalized() * self.speed * time.dt

        ray = raycast(self.position + (0, 2, 0), direction=(0, -1, 0), ignore=(self,), distance=4)
        if ray.hit:
            self.y = ray.world_point[1] + (self.scale_y / 2)

        if self.attack_cooldown <= 0 and len(enemies) > 0:
            target = min(enemies, key=lambda enemy: distance(self.position, enemy.position))
            if distance(self.position, target.position) <= self.attack_range:
                self.look_at_2d(target, 'y')
                Arrow(position=self.position + self.forward * 1.3 + (0, 0.8, 0), rotation=self.rotation)
                self.attack_cooldown = 0.9

black_screen = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(3, 3), z=-10)
controls_ui = Text(text='8 - Save\n9 - Load\n0 - Pause\nE - Shockwave', position=(-0.75, -0.38), scale=1.5, color=color.white, background=True)

class PauseHandler(Entity):
    def __init__(self):
        super().__init__(ignore_paused=True)
        self.pause_text = Text(text='PAUSED', origin=(0, 0), scale=5, color=color.yellow, background=True, enabled=False)

    def input(self, key):
        if key == '0':
            application.paused = not application.paused
            self.pause_text.enabled = application.paused

pause_handler = PauseHandler()


# 3. Define the Player Class
class ThirdPersonPlayer(Entity):
    def __init__(self):
        super().__init__(model='cube', color=color.azure, scale=(1, 2, 1), position=(0, 1, 0), collider='box')
        self.speed = 10
        self.spawn_point = (0, 1, 0) 
        self.has_bow = False 
        self.has_grenade = False
        self.grenade_used = False
        self.y_velocity = 0
        self.gravity = 25
        self.jump_force = 12
        self.grounded = False
        self.is_teleporting = False 
        
        # Phase 0 = Off, Phase 1 = Hallway, Phase 2 = Arena
        self.level_3_phase = 0 
        self.level_3_cleared = False
        self.level_4_portal_open = False
        self.level_4_cleared = False
        self.level_5_portal_open = False
        self.level_5_cleared = False
        self.level_6_portal_open = False
        self.level_6_broadcast_shown = False
        self.teammate_unlocked = False
        
        self.max_hp = 100
        self.hp = self.max_hp
        self.health_ui = Text(text=f'HP: {self.hp} / {self.max_hp}', position=(-0.85, 0.45), scale=2, color=color.white, background=True)

        self.enemies_killed = 0
        self.mission_target = 5
        self.mission_ui = Text(text=f'Defeat enemies: {self.enemies_killed} / {self.mission_target}', position=(0.85, 0.45), origin=(0.5, 0.5), scale=2, color=color.yellow, background=True)

        self.attack_cooldown = 0  
        self.attack_damage = 25 
        self.attack_range = 3.5 
        self.spawn_timer = 2.0 
        self.grenade_cooldown = 0
        self.grenade_shockwave_radius = 7
        self.grenade_shockwave_push = 12
        mouse.locked = True

        camera.parent = self
        camera.position = (0, 3, -7)  
        camera.rotation_x = 15        
        camera.fov = 90 

        self.sword = Entity(parent=self, model='cube', color=color.light_gray, scale=(0.1, 1.2, 0.2), position=(0.7, 0.2, 0.5), rotation=(30, 0, 0))
        self.crossguard = Entity(parent=self.sword, model='cube', color=color.gold, scale=(4, 0.1, 1.5), position=(0, -0.4, 0))

    def take_damage(self, amount):
        if self.is_teleporting: return 
        
        self.hp -= amount
        self.color = color.red
        invoke(setattr, self, 'color', color.azure, delay=0.2)
        self.health_ui.text = f'HP: {self.hp} / {self.max_hp}'
        
        if self.hp <= 0:
            print("You died!")
            if os.path.exists('savegame.json'):
                print("Loading last save...")
                self.load_game()
            else:
                print("No save file found! Resetting...")
                self.reset_game_state()

    def add_kill(self):
        if self.spawn_point != (0, 1, 0):
            return

        self.enemies_killed += 1
        
        if self.enemies_killed == self.mission_target and self.spawn_point == (0, 1, 0):
            self.mission_ui.text = 'Portal Opened Nearby!'
            self.mission_ui.color = color.magenta
            portal.position = self.position + self.forward * 4
            portal.y = 1.5 
            portal.enabled = True
        elif self.spawn_point == (0, 1, 0):
            self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'

    def enter_portal(self):
        self.is_teleporting = True
        portal.enabled = False 
        black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_2, delay=1.0)

    def enter_portal_2(self):
        self.is_teleporting = True
        portal_2.enabled = False 
        black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_3, delay=1.0)

    def enter_portal_3(self):
        self.is_teleporting = True
        portal_3.enabled = False
        black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_2, delay=1.0)

    def enter_portal_4(self):
        self.is_teleporting = True
        portal_4.enabled = False
        black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        if self.level_6_portal_open:
            invoke(self.teleport_to_level_6, delay=1.0)
        elif self.level_5_cleared:
            invoke(self.teleport_to_level_2, delay=1.0)
        else:
            invoke(self.teleport_to_level_5, delay=1.0)

    def clear_all_entities(self):
        global enemies, cannons, cannon_spheres
        for enemy in enemies: destroy(enemy)
        enemies.clear()
        for c in cannons: destroy(c)
        cannons.clear()
        for s in cannon_spheres: destroy(s)
        cannon_spheres.clear()

    def teleport_to_level_2(self):
        self.spawn_point = (1000, 1, 990)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.clear_all_entities()
        self.level_3_phase = 0
        
        black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)
        
        if not self.has_bow:
            self.mission_ui.text = 'Talk to chef'
            self.mission_ui.color = color.cyan
        elif not self.has_grenade:
            self.mission_ui.text = 'Talk to chef'
            self.mission_ui.color = color.cyan
        elif self.level_5_cleared:
            if self.teammate_unlocked:
                self.mission_ui.text = 'Go with the archer.'
                self.mission_ui.color = color.yellow
            else:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.yellow
        elif self.level_5_portal_open:
            self.mission_ui.text = 'Enter the portal!'
            self.mission_ui.color = color.magenta
        elif self.level_4_cleared:
            self.mission_ui.text = 'Talk to the Manager'
            self.mission_ui.color = color.yellow
        elif self.level_4_portal_open:
            self.mission_ui.text = 'Enter the portal!'
            self.mission_ui.color = color.magenta
        else:
            self.mission_ui.text = 'Talk to the Manager'
            self.mission_ui.color = color.yellow

    def setup_level_3_cannons(self):
        self.clear_all_entities()
        cannons.append(Cannon(position=(2000, 1.5, 2060)))
        cannons.append(Cannon(position=(1995, 1.5, 2120)))
        cannons.append(Cannon(position=(2005, 1.5, 2180)))
        level_3_door.y = 5 
        self.level_3_cleared = False
        portal.enabled = False
        portal_3.enabled = False

    def setup_level_4_arena(self):
        self.clear_all_entities()
        self.level_4_cleared = False
        enemy_positions = [
            (1992, 1, 2218),
            (2008, 1, 2218),
            (1988, 1, 2238),
            (2012, 1, 2238),
            (1996, 1, 2250),
            (2004, 1, 2250),
        ]
        for pos in enemy_positions:
            enemies.append(Enemy(target=self, spawn_pos=pos))

    def setup_level_5_arena(self):
        self.clear_all_entities()
        enemies.append(BossCube(target=self, spawn_pos=(3000, 1, 2240)))

    def teleport_to_level_3(self):
        self.spawn_point = (2000, 1, 2010)
        self.position = self.spawn_point
        self.y_velocity = 0
        
        self.level_3_phase = 1
        self.setup_level_3_cannons()
        
        black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)
        
        self.mission_ui.text = 'Destroy the Cannons!'
        self.mission_ui.color = color.red

    def teleport_to_level_4(self):
        self.spawn_point = (2000, 1, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.level_3_phase = 0
        self.level_3_cleared = True
        self.level_4_portal_open = True
        self.setup_level_4_arena()

        black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Defeat the boss!'
        self.mission_ui.color = color.red

    def teleport_to_level_5(self):
        self.spawn_point = (3000, 1, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.level_3_phase = 0
        self.level_5_portal_open = True
        self.level_5_cleared = False
        ground_4.color = color.dark_gray
        self.setup_level_5_arena()

        black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Defeat the robo-guy'
        self.mission_ui.color = color.white

    def setup_level_6_arena(self):
        self.clear_all_entities()
        self.level_6_portal_open = True
        ground_6.enabled = True
        ground_6.position = (4000, 0, 2230)
        ground_6.scale = (150, 1, 150)
        ground_6.collider = 'box'
        for _ in range(18):
            pillar_x = random.uniform(3930, 4070)
            pillar_z = random.uniform(2160, 2300)
            pillar_height = random.uniform(8, 20)
            Entity(
                model='cube',
                color=color.brown,
                collider='box',
                scale=(1.0, pillar_height, 1.0),
                position=(pillar_x, pillar_height / 2, pillar_z)
            )

    def teleport_to_level_6(self):
        self.spawn_point = (4000, 2, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.grounded = True
        self.level_3_phase = 0
        self.level_6_portal_open = True
        self.setup_level_6_arena()

        if self.teammate_unlocked:
            companion = spawn_archer_companion()
            companion.position = self.position + (2, 0, -2)
            companion.y = self.y + (companion.scale_y / 2) - 1
            companion.hp = max(1, min(companion.hp, companion.max_hp))
            companion.health_bar.scale_x = max(companion.hp / companion.max_hp, 0) * 1.2

        if not self.level_6_broadcast_shown:
            chef.dialogue_ui.text = 'Chef: What is this place?'
            chef.dialogue_ui.enabled = True
            invoke(setattr, chef.dialogue_ui, 'enabled', False, delay=4.0)
            self.level_6_broadcast_shown = True

        black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Explore Level 6'
        self.mission_ui.color = color.gray

    def reset_mission(self):
        self.enemies_killed = 0
        self.mission_ui.color = color.yellow
        self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'
        portal.enabled = False
        portal_2.enabled = False
        portal_3.enabled = False
        portal_4.enabled = False

    def reset_game_state(self):
        self.position = self.spawn_point
        self.hp = self.max_hp
        self.health_ui.text = f'HP: {self.hp} / {self.max_hp}'
        self.y_velocity = 0
        self.clear_all_entities()
        
        if self.spawn_point == (0, 1, 0):
            self.has_bow = False
            self.has_grenade = False
            self.grenade_used = False
            self.teammate_unlocked = False
            dismiss_archer_companion()
            chef.exclamation.enabled = True
            manager.exclamation.enabled = True
            self.level_3_phase = 0
            self.level_3_cleared = False
            self.level_4_portal_open = False
            self.level_4_cleared = False
            self.level_5_portal_open = False
            self.level_5_cleared = False
            self.level_6_portal_open = False
            self.level_6_broadcast_shown = False
            self.reset_mission()
        elif self.spawn_point == (1000, 1, 990):
            self.level_3_phase = 0
            if not self.has_bow:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.cyan
            elif self.level_5_portal_open:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
            elif self.level_4_cleared:
                self.mission_ui.text = 'Talk to the Manager'
                self.mission_ui.color = color.yellow
            elif self.level_4_portal_open:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
            else:
                self.mission_ui.text = 'Find the Manager'
                self.mission_ui.color = color.yellow
        elif self.spawn_point == (2000, 1, 2010):
            self.mission_ui.text = 'Destroy the Cannons!'
            self.mission_ui.color = color.red
            self.level_3_phase = 1
            self.setup_level_3_cannons()
        elif self.spawn_point == (2000, 1, 2230):
            self.level_3_phase = 0
            self.level_3_cleared = True
            self.level_4_portal_open = True
            self.setup_level_4_arena()
            self.mission_ui.text = 'Defeat the boss!'
            self.mission_ui.color = color.red
        elif self.spawn_point == (3000, 1, 2230):
            self.level_3_phase = 0
            self.level_5_portal_open = True
            self.setup_level_5_arena()
            if self.level_5_cleared:
                self.mission_ui.text = 'Boss defeated! Return portal open.'
                self.mission_ui.color = color.cyan
            else:
                self.level_5_cleared = False
                self.mission_ui.text = 'Defeat the boss!'
                self.mission_ui.color = color.white
            
    def update(self):
        if self.is_teleporting: return 

        if portal.enabled and distance(self.position, portal.position) < 2.5: self.enter_portal()
        if portal_2.enabled and distance(self.position, portal_2.position) < 2.5: self.enter_portal_2()
        if portal_3.enabled and distance(self.position, portal_3.position) < 2.5: self.enter_portal_3()
        if portal_4.enabled and distance(self.position, portal_4.position) < 2.5: self.enter_portal_4()

        if self.y < self.spawn_point[1] - 20:
            self.take_damage(self.max_hp)

        # Trigger Arena Phase
        if self.level_3_phase == 1 and len(cannons) == 0:
            self.level_3_phase = 2
            self.mission_ui.text = 'Enter the arena!'
            self.mission_ui.color = color.green
            
            level_3_door.animate_y(-5, duration=2.0)
            
            cannons.append(Cannon(position=(1980, 1.5, 2250)))
            cannons.append(Cannon(position=(2020, 1.5, 2250)))

        if self.level_3_phase == 2 and len(cannons) == 0 and len(enemies) == 0 and len(cannon_spheres) == 0 and not self.level_3_cleared:
            self.level_3_cleared = True
            self.mission_ui.text = 'Hallway portal open!'
            self.mission_ui.color = color.magenta
            self.level_4_portal_open = True
            portal_3.position = self.position + self.forward * 4
            portal_3.y = 1.5
            portal_3.enabled = True

        if self.spawn_point == (2000, 1, 2230) and not self.level_4_cleared and len(enemies) == 0:
            self.level_4_cleared = True
            self.mission_ui.text = 'Return portal open! Talk to the chef.'
            self.mission_ui.color = color.cyan
            portal.position = self.position + self.forward * 4
            portal.y = 1.5
            portal.enabled = True

        if self.spawn_point == (3000, 1, 2230) and not self.level_5_cleared and len(enemies) == 0:
            self.level_5_cleared = True
            self.level_5_portal_open = False
            self.mission_ui.text = 'Boss defeated! Return portal open.'
            self.mission_ui.color = color.cyan
            portal_4.position = self.position + self.forward * 4
            portal_4.y = 1.5
            portal_4.enabled = True

        # Spawning only happens in Level 1 OR in Level 3 Arena while Cannons are still alive
        if self.spawn_point == (0, 1, 0) or (self.level_3_phase == 2 and len(cannons) > 0): 
            self.spawn_timer -= time.dt
            if self.spawn_timer <= 0:
                if len(enemies) < 15:
                    if self.spawn_point == (0, 1, 0):
                        spawn_x = self.x + random.uniform(-20, 20)
                        spawn_z = self.z + random.uniform(-20, 20)
                    else:
                        spawn_x = random.uniform(1980, 2020)
                        spawn_z = random.uniform(2210, 2250)

                    new_enemy = Enemy(target=self, spawn_pos=(spawn_x, self.spawn_point[1], spawn_z))
                    enemies.append(new_enemy)
                self.spawn_timer = random.uniform(2.0, 5.0)

        direction = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        self.position += direction * self.speed * time.dt
        
        ray = raycast(self.position, direction=(0, -1, 0), ignore=(self,), distance=1.1)
        if ray.hit and self.y_velocity <= 0:
            self.grounded = True
            self.y_velocity = 0
            self.y = ray.world_point[1] + (self.scale_y / 2)
        else:
            self.grounded = False
            self.y_velocity -= self.gravity * time.dt
        self.y += self.y_velocity * time.dt
        
        self.rotation_y += mouse.velocity[0] * 150

        if held_keys['space'] and self.grounded: self.y_velocity = self.jump_force
        if self.attack_cooldown > 0: self.attack_cooldown -= time.dt
        elif held_keys['left mouse']: self.perform_attack()
        if self.grenade_cooldown > 0: self.grenade_cooldown -= time.dt

    def perform_attack(self):
        self.attack_cooldown = 0.4 
        self.sword.animate_rotation((120, 0, 0), duration=0.1)
        invoke(self.sword.animate_rotation, (30, 0, 0), duration=0.2, delay=0.15)
        
        for enemy in enemies:
            if distance(self.position, enemy.position) <= self.attack_range:
                enemy.take_damage(self.attack_damage)
                
        for c in cannons:
            if distance(self.position, c.position) <= self.attack_range:
                c.take_damage(self.attack_damage)

    def shoot_arrow(self):
        self.attack_cooldown = 0.5 
        spawn_pos = self.position + (0, 1, 0) + self.forward * 1.5
        Arrow(position=spawn_pos, rotation=self.rotation)

    def throw_grenade(self):
        self.grenade_cooldown = 1.25
        spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.3
        ShockwaveGrenade(position=spawn_pos, rotation=self.rotation)

    def save_game(self):
        save_data = {
            'x': self.x, 'y': self.y, 'z': self.z, 
            'hp': self.hp, 
            'spawn_x': self.spawn_point[0], 'spawn_y': self.spawn_point[1], 'spawn_z': self.spawn_point[2],
            'enemies_killed': self.enemies_killed,
            'portal_enabled': portal.enabled, 'portal_x': portal.x, 'portal_y': portal.y, 'portal_z': portal.z,
            'portal_2_enabled': portal_2.enabled, 'portal_2_x': portal_2.x, 'portal_2_y': portal_2.y, 'portal_2_z': portal_2.z,
            'portal_3_enabled': portal_3.enabled, 'portal_3_x': portal_3.x, 'portal_3_y': portal_3.y, 'portal_3_z': portal_3.z,
            'portal_4_enabled': portal_4.enabled, 'portal_4_x': portal_4.x, 'portal_4_y': portal_4.y, 'portal_4_z': portal_4.z,
            'has_bow': self.has_bow,
            'has_grenade': self.has_grenade,
            'grenade_used': self.grenade_used,
            'exclamation_enabled': chef.exclamation.enabled,
            'manager_exclamation_enabled': manager.exclamation.enabled,
            'level_3_phase': self.level_3_phase,
            'level_3_cleared': self.level_3_cleared,
            'level_4_portal_open': self.level_4_portal_open,
            'level_4_cleared': self.level_4_cleared,
            'level_5_portal_open': self.level_5_portal_open,
            'level_5_cleared': self.level_5_cleared,
            'level_6_portal_open': self.level_6_portal_open,
            'level_6_broadcast_shown': self.level_6_broadcast_shown,
            'teammate_unlocked': self.teammate_unlocked,
            'teammate_hp': getattr(archer_companion, 'hp', 150),
            'teammate_x': getattr(archer_companion, 'x', self.x),
            'teammate_y': getattr(archer_companion, 'y', self.y),
            'teammate_z': getattr(archer_companion, 'z', self.z),
            'door_y': level_3_door.y
        }
        with open('savegame.json', 'w') as f: json.dump(save_data, f)
        print("Game Saved!")

    def load_game(self):
        if os.path.exists('savegame.json'):
            with open('savegame.json', 'r') as f: save_data = json.load(f)
            
            self.x, self.y, self.z = save_data['x'], save_data['y'], save_data['z']
            if 'hp' in save_data:
                self.hp = save_data['hp']
                self.health_ui.text = f'HP: {self.hp} / {self.max_hp}'
            if 'spawn_x' in save_data:
                self.spawn_point = (save_data['spawn_x'], save_data['spawn_y'], save_data['spawn_z'])
            
            if 'enemies_killed' in save_data: self.enemies_killed = save_data['enemies_killed']
            
            if 'portal_enabled' in save_data:
                portal.enabled = save_data['portal_enabled']
                portal.position = (save_data['portal_x'], save_data['portal_y'], save_data['portal_z'])
            if 'portal_2_enabled' in save_data:
                portal_2.enabled = save_data['portal_2_enabled']
                portal_2.position = (save_data['portal_2_x'], save_data['portal_2_y'], save_data['portal_2_z'])
            if 'portal_3_enabled' in save_data:
                portal_3.enabled = save_data['portal_3_enabled']
                portal_3.position = (save_data['portal_3_x'], save_data['portal_3_y'], save_data['portal_3_z'])
            if 'portal_4_enabled' in save_data:
                portal_4.enabled = save_data['portal_4_enabled']
                portal_4.position = (save_data['portal_4_x'], save_data['portal_4_y'], save_data['portal_4_z'])

            self.has_bow = save_data.get('has_bow', False)
            self.has_grenade = save_data.get('has_grenade', False)
            self.grenade_used = save_data.get('grenade_used', False)
            chef.exclamation.enabled = save_data.get('exclamation_enabled', True)
            manager.exclamation.enabled = save_data.get('manager_exclamation_enabled', True)
            self.level_3_phase = save_data.get('level_3_phase', 0)
            self.level_3_cleared = save_data.get('level_3_cleared', False)
            self.level_4_portal_open = save_data.get('level_4_portal_open', False)
            self.level_4_cleared = save_data.get('level_4_cleared', False)
            self.level_5_portal_open = save_data.get('level_5_portal_open', False)
            self.level_5_cleared = save_data.get('level_5_cleared', False)
            self.level_6_portal_open = save_data.get('level_6_portal_open', False)
            self.level_6_broadcast_shown = save_data.get('level_6_broadcast_shown', False)
            self.teammate_unlocked = save_data.get('teammate_unlocked', False)
            level_3_door.y = save_data.get('door_y', 5)

            if self.teammate_unlocked:
                companion = spawn_archer_companion()
                companion.hp = save_data.get('teammate_hp', companion.max_hp)
                companion.health_bar.scale_x = max(companion.hp / companion.max_hp, 0) * 1.2
                companion.position = (
                    save_data.get('teammate_x', self.x + 2),
                    save_data.get('teammate_y', self.y),
                    save_data.get('teammate_z', self.z - 2),
                )
            else:
                dismiss_archer_companion()

            if self.spawn_point == (0, 1, 0):
                if self.enemies_killed >= self.mission_target:
                    self.mission_ui.text = 'Portal Opened Nearby!'
                    self.mission_ui.color = color.magenta
                else:
                    self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'
                    self.mission_ui.color = color.yellow
            elif self.spawn_point == (1000, 1, 990):
                if self.has_bow:
                    if not self.has_grenade:
                        self.mission_ui.text = 'Talk to chef'
                        self.mission_ui.color = color.cyan
                    elif self.level_5_cleared and not self.teammate_unlocked:
                        self.mission_ui.text = 'Talk to chef'
                        self.mission_ui.color = color.yellow
                    elif self.teammate_unlocked:
                        self.mission_ui.text = 'Travel with the archer.'
                        self.mission_ui.color = color.yellow
                    elif self.level_5_portal_open:
                        self.mission_ui.text = 'Enter the portal!'
                        self.mission_ui.color = color.magenta
                    elif self.level_4_cleared:
                        self.mission_ui.text = 'Talk to the Manager'
                        self.mission_ui.color = color.yellow
                    else:
                        self.mission_ui.text = 'Find the Manager'
                        self.mission_ui.color = color.yellow
                else:
                    self.mission_ui.text = 'Talk to chef'
                    self.mission_ui.color = color.cyan
            elif self.spawn_point == (2000, 1, 2010):
                if self.level_3_phase == 1:
                    self.mission_ui.text = 'Destroy the Cannons!'
                    self.mission_ui.color = color.red
                elif self.level_3_phase == 2:
                    self.mission_ui.text = 'Enter the arena!'
                    self.mission_ui.color = color.green
            elif self.spawn_point == (2000, 1, 2230):
                if self.level_4_cleared:
                    self.mission_ui.text = 'Return portal open! Talk to the chef.'
                    self.mission_ui.color = color.cyan
                else:
                    self.setup_level_4_arena()
                    self.mission_ui.text = 'Defeat the boss cube!'
                    self.mission_ui.color = color.red
            elif self.spawn_point == (3000, 1, 2230):
                if self.level_5_cleared:
                    self.mission_ui.text = 'Boss defeated! Return portal open.'
                    self.mission_ui.color = color.cyan
                else:
                    self.mission_ui.text = 'Defeat the boss!'
                    self.mission_ui.color = color.white

            self.y_velocity = 0 
            print("Game Loaded!")
        else:
            print("No save file found!")

    def input(self, key):
        if key == '8': self.save_game()
        elif key == '9': self.load_game()
        elif key == '/': 
            self.spawn_point = (0, 1, 0) 
            self.reset_game_state()
            
        elif key == 'right mouse down':
            if self.has_bow and self.attack_cooldown <= 0:
                self.shoot_arrow()

        elif key == 'e':
            if self.has_grenade and self.grenade_cooldown <= 0 and not self.is_teleporting:
                self.throw_grenade()
            
        elif key == 'f':
            if distance(self.position, chef.position) < 3.5 and not self.has_bow:
                chef.dialogue_ui.enabled = True
                chef.exclamation.enabled = False 
                self.has_bow = True 
                self.mission_ui.text = 'Find the Manager'
                self.mission_ui.color = color.yellow
                invoke(setattr, chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, chef.position) < 3.5 and self.has_bow and not self.has_grenade:
                chef.dialogue_ui.text = 'Chef: Here take this shockwave grenade, press E to use it'
                chef.dialogue_ui.enabled = True
                chef.exclamation.enabled = False
                self.has_grenade = True
                self.mission_ui.text = 'Use the shockwave grenade'
                self.mission_ui.color = color.yellow
                invoke(setattr, chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, chef.position) < 3.5 and self.level_5_cleared and not self.teammate_unlocked:
                chef.dialogue_ui.text = 'Chef: This is my friend, the archer, he will help.'
                chef.dialogue_ui.enabled = True
                chef.exclamation.enabled = False
                self.teammate_unlocked = True
                teammate = spawn_archer_companion()
                teammate.hp = teammate.max_hp
                teammate.health_bar.scale_x = 1.2
                teammate.position = self.position + (2, 0, -2)
                self.mission_ui.text = 'Travel with the archer.'
                self.mission_ui.color = color.yellow
                invoke(setattr, chef.dialogue_ui, 'enabled', False, delay=4.0)
            
            elif distance(self.position, manager.position) < 3.5:
                if not self.has_bow:
                    manager.dialogue_ui.text = "Manager: Talk to the Chef first, you need a weapon!"
                    manager.dialogue_ui.enabled = True
                    invoke(setattr, manager.dialogue_ui, 'enabled', False, delay=4.0)
                elif not self.level_3_cleared:
                    manager.dialogue_ui.text = "Manager: The portal is open."
                    manager.dialogue_ui.enabled = True
                    manager.exclamation.enabled = False
                    self.mission_ui.text = 'Enter the portal!'
                    self.mission_ui.color = color.magenta

                    portal_2.position = manager.position + manager.forward * 4
                    portal_2.y = 1.5
                    portal_2.enabled = True

                    invoke(setattr, manager.dialogue_ui, 'enabled', False, delay=4.0)

                else:
                    manager.dialogue_ui.text = "Manager: Great. The portal is open."
                    manager.dialogue_ui.enabled = True
                    manager.exclamation.enabled = False
                    self.mission_ui.text = 'Enter the portal!'
                    self.mission_ui.color = color.magenta
                    
                    ground_4.color = color.dark_gray
                    portal_4.position = manager.position + manager.forward * 4
                    portal_4.y = 1.5
                    portal_4.enabled = True
                    self.level_6_portal_open = True
                    
                    invoke(setattr, manager.dialogue_ui, 'enabled', False, delay=4.0)

        if key == 'escape': application.quit()

# 4. Define the Enemy Class
class Enemy(Entity):
    def __init__(self, target, spawn_pos):
        super().__init__(model='cube', color=color.red, scale=(1, 2, 1), position=spawn_pos, collider='box')
        self.target = target
        self.speed = 4
        self.max_hp = 50
        self.hp = self.max_hp
        self.attack_range = 2.0
        self.attack_damage = 10
        self.attack_cooldown = 0
        self.stun_timer = 0
        self.health_bar = Entity(parent=self, y=0.6, model='cube', color=color.green, scale=(1.2, 0.1, 0.1))
        
    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.2
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            if self in enemies: enemies.remove(self) 
            self.target.add_kill() 
            destroy(self)          

    def update(self):
        if self.target.is_teleporting: return 

        target = get_nearest_party_target(self.position) or self.target

        if self.stun_timer > 0:
            self.stun_timer -= time.dt
            return

        dist = distance(self.position, target.position)
        for other in enemies:
            if other != self and distance(self.position, other.position) < 1.5:
                self.position += (self.position - other.position).normalized() * self.speed * 0.5 * time.dt
        
        if self.attack_cooldown > 0: self.attack_cooldown -= time.dt
        if dist > self.attack_range:
            self.look_at_2d(target, 'y')
            self.position += self.forward * self.speed * time.dt
        elif self.attack_cooldown <= 0:
            target.take_damage(self.attack_damage)
            self.attack_cooldown = 2.0 

class BossCube(Entity):
    def __init__(self, target, spawn_pos):
        super().__init__(
            model=load_model('boss_cube.bam', folder=Path(__file__).parent),
            texture=load_texture('boss_texture1.png', folder=Path(__file__).parent),
            color=color.white,
            scale=2.5,
            position=spawn_pos,
            collider='box'
        )
        self.target = target
        self.speed = 1.2
        self.max_hp = 300
        self.hp = self.max_hp
        self.attack_range = 3.5
        self.attack_damage = 20
        self.attack_cooldown = 0
        self.shoot_timer = random.uniform(2.5, 4.0)
        self.health_bar = Entity(parent=self, y=1.4, model='cube', color=color.green, scale=(2.2, 0.15, 0.15))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 2.2
        self.color = color.gray
        invoke(setattr, self, 'color', color.white, delay=0.1)
        if self.hp <= 0:
            if self in enemies: enemies.remove(self)
            destroy(self)

    def update(self):
        if self.target.is_teleporting:
            return

        target = get_nearest_party_target(self.position) or self.target
        dist = distance(self.position, target.position)
        self.shoot_timer -= time.dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        if dist > self.attack_range:
            self.look_at_2d(target, 'y')
            self.position += self.forward * self.speed * time.dt
        elif self.attack_cooldown <= 0:
            target.take_damage(self.attack_damage)
            self.attack_cooldown = 2.0

        if dist < 80 and self.shoot_timer <= 0:
            sphere = CannonSphere(self.position + (0, 1.2, 0), target=target)
            sphere.scale = 1.8
            sphere.color = color.red
            cannon_spheres.append(sphere)
            self.shoot_timer = random.uniform(2.5, 4.0)

player = ThirdPersonPlayer()

for i in range(2):
    new_enemy = Enemy(target=player, spawn_pos=(random.uniform(-10, 10), 1, random.uniform(-10, 10)))
    enemies.append(new_enemy)

app.run()
