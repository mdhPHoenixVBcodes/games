from ursina import *
import json
import os
import random

import adventure_state as state
import adventure_entities as ent
import adventure_world as world


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
        self.boss_music = None
        self.safezone_music = None
        self.low_health_music = Audio('lowhealth.mp3', loop=True, autoplay=False)
        self.dash_cooldown = 0
        self.dash_duration = 0.15
        self.dash_speed = 45

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
        self.autosave_interval = 30.0
        self.autosave_timer = self.autosave_interval
        self.grenade_cooldown = 0
        self.grenade_shockwave_radius = 7
        self.grenade_shockwave_push = 28
        self.crosshair = Text(parent=camera.ui, text='+', origin=(0, 0), position=(0, 0.19), scale=2, color=color.white, enabled=False)
        
        # --- Ability HUD ---
        self.grenade_max_cooldown = 1.25
        self.grenade_icon = Entity(parent=camera.ui, model='quad', texture='image.png', color=color.white, scale=(0.14, 0.14), position=(0.62, -0.4), enabled=False)
        self.grenade_overlay = Entity(parent=self.grenade_icon, model='quad', color=color.black66, scale=(1, 0), z=-0.1, origin_y=-0.5)
        
        self.dash_max_cooldown = 0.8
        self.dash_icon = Entity(parent=camera.ui, model='quad', texture='image2.png', color=color.white, scale=(0.14, 0.14), position=(0.44, -0.4), enabled=True)
        self.dash_overlay = Entity(parent=self.dash_icon, model='quad', color=color.black66, scale=(1, 0), z=-0.1, origin_y=-0.5)
        
        self.attack_max_cooldown = 0.5
        self.bow_icon = Entity(parent=camera.ui, model='quad', texture='image1.png', color=color.white, scale=(0.14, 0.14), position=(0.8, -0.4), enabled=False)
        self.bow_overlay = Entity(parent=self.bow_icon, model='quad', color=color.black66, scale=(1, 0), z=-0.1, origin_y=-0.5)
        
        mouse.locked = True

        camera.parent = self
        camera.position = (0, 3, -7)
        camera.rotation_x = 15
        camera.fov = 90

        self.sword = Entity(parent=self, model='cube', color=color.light_gray, scale=(0.1, 1.2, 0.2), position=(0.7, 0.2, 0.5), rotation=(30, 0, 0))
        self.crossguard = Entity(parent=self.sword, model='cube', color=color.gold, scale=(4, 0.1, 1.5), position=(0, -0.4, 0))

    def take_damage(self, amount):
        if self.is_teleporting:
            return

        self.hp -= amount
        ent.DamageMarker(amount, self.world_position + (0, 2, 0))
        self.color = color.red
        invoke(setattr, self, 'color', color.azure, delay=0.2)
        self.health_ui.text = f'HP: {int(self.hp)} / {self.max_hp}'

        if self.hp <= 0:
            if self.low_health_music and self.low_health_music.playing:
                self.low_health_music.stop()
            print("You died!")
            if state.SAVE_FILE.exists():
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
            ent.portal.position = self.position + self.forward * 4
            ent.portal.y = 1.5
            ent.portal.enabled = True
        elif self.spawn_point == (0, 1, 0):
            self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'

    def enter_portal(self):
        self.is_teleporting = True
        ent.portal.enabled = False
        self.save_game()
        ent.black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_2, delay=1.0)

    def enter_portal_2(self):
        self.is_teleporting = True
        ent.portal_2.enabled = False
        self.save_game()
        ent.black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_3, delay=1.0)

    def enter_portal_3(self):
        self.is_teleporting = True
        ent.portal_3.enabled = False
        self.save_game()
        ent.black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        invoke(self.teleport_to_level_4, delay=1.0)

    def enter_portal_4(self):
        self.is_teleporting = True
        ent.portal_4.enabled = False
        self.save_game()
        ent.black_screen.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)
        if self.level_6_portal_open or (self.teammate_unlocked and self.level_5_cleared):
            invoke(self.teleport_to_level_6, delay=1.0)
        elif self.level_5_cleared:
            invoke(self.teleport_to_level_2, delay=1.0)
        elif self.level_5_portal_open:
            invoke(self.teleport_to_level_5, delay=1.0)
        else:
            invoke(self.teleport_to_level_2, delay=1.0)

    def clear_all_entities(self):
        for enemy in state.enemies:
            destroy(enemy)
        state.enemies.clear()
        for c in state.cannons:
            destroy(c)
        state.cannons.clear()
        for s in state.cannon_spheres:
            destroy(s)
        state.cannon_spheres.clear()
        state.clear_level_6_pillars()

    def teleport_to_level_2(self):
        self.spawn_point = (1000, 1, 990)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.clear_all_entities()
        self.level_3_phase = 0

        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        if self.boss_music:
            self.boss_music.stop()
        if not self.safezone_music or not self.safezone_music.playing:
            if self.safezone_music: self.safezone_music.stop()
            self.safezone_music = Audio('safezone.mp3', loop=True, autoplay=True, volume=0.5)
        
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        if not self.has_bow:
            self.mission_ui.text = 'Talk to chef'
            self.mission_ui.color = color.cyan
            self.crosshair.enabled = False
        elif not self.level_3_cleared:
            self.mission_ui.text = 'Talk to the Manager'
            self.mission_ui.color = color.yellow
            self.crosshair.enabled = True
        elif self.level_4_portal_open and not self.level_4_cleared:
            self.mission_ui.text = 'Enter the portal!'
            self.mission_ui.color = color.magenta
            self.crosshair.enabled = True
        elif self.level_4_cleared and not self.has_grenade:
            self.mission_ui.text = 'Talk to chef'
            self.mission_ui.color = color.cyan
            self.crosshair.enabled = True
        elif self.level_5_cleared:
            if self.teammate_unlocked:
                self.mission_ui.text = 'Go with the archer.'
                self.mission_ui.color = color.yellow
            else:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.yellow
            self.crosshair.enabled = True
            self.bow_icon.enabled = True
            if self.has_grenade:
                self.grenade_icon.enabled = True
        elif self.level_5_portal_open:
            self.mission_ui.text = 'Enter the portal!'
            self.mission_ui.color = color.magenta
            self.crosshair.enabled = True
        else:
            self.mission_ui.text = 'Talk to the Manager'
            self.mission_ui.color = color.yellow
            self.crosshair.enabled = True

    def setup_level_3_cannons(self):
        self.clear_all_entities()
        state.cannons.append(ent.Cannon(position=(2000, 1.5, 2060)))
        state.cannons.append(ent.Cannon(position=(1995, 1.5, 2120)))
        state.cannons.append(ent.Cannon(position=(2005, 1.5, 2180)))
        world.level_3_door.y = 5
        self.level_3_cleared = False
        ent.portal.enabled = False
        ent.portal_3.enabled = False

    def setup_level_4_arena(self):
        self.clear_all_entities()
        self.level_4_cleared = False
        ent.portal_3.enabled = False
        enemy_positions = [
            (1992, 1, 2218),
            (2008, 1, 2218),
            (1988, 1, 2238),
            (2012, 1, 2238),
            (1996, 1, 2250),
            (2004, 1, 2250),
        ]
        for pos in enemy_positions:
            state.enemies.append(ent.Enemy(target=self, spawn_pos=pos))

    def setup_level_5_arena(self):
        self.clear_all_entities()
        state.enemies.append(ent.BossCube(target=self, spawn_pos=(3000, 1, 2240)))

    def teleport_to_level_3(self):
        self.spawn_point = (2000, 1, 2010)
        self.position = self.spawn_point
        self.y_velocity = 0

        self.level_3_phase = 1
        self.setup_level_3_cannons()
        
        if self.safezone_music:
            self.safezone_music.stop()

        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
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
        
        if self.safezone_music:
            self.safezone_music.stop()

        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Defeat the boss!'
        self.mission_ui.color = color.red

    def teleport_to_level_4(self):
        self.spawn_point = (2000, 1, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        if not self.level_4_cleared:
            self.setup_level_4_arena()
        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

    def teleport_to_level_5(self):
        self.spawn_point = (3000, 1, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.level_3_phase = 0
        self.level_5_portal_open = True
        self.level_5_cleared = False
        world.ground_4.color = color.dark_gray
        self.setup_level_5_arena()
        
        if self.safezone_music:
            self.safezone_music.stop()

        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Defeat The Iron Revenant'
        self.mission_ui.color = color.white
        
        if self.boss_music:
            self.boss_music.stop()
        self.boss_music = Audio('boss.mp3', loop=True, autoplay=True, volume=0.6)

    def setup_level_6_arena(self):
        self.clear_all_entities()
        state.clear_level_6_pillars()
        self.level_6_portal_open = True
        world.ground_6.enabled = True
        world.ground_6.position = (4000, 0, 2230)
        world.ground_6.scale = (150, 1, 150)
        world.ground_6.collider = 'box'
        for _ in range(18):
            pillar_x = random.uniform(3930, 4070)
            pillar_z = random.uniform(2160, 2300)
            pillar_height = random.uniform(8, 20)
            pillar = Entity(
                model='cube',
                color=color.brown,
                collider='box',
                scale=(1.0, pillar_height, 1.0),
                position=(pillar_x, pillar_height / 2, pillar_z)
            )
            pillar.touch_cooldown = 0
            state.level_6_pillars.append(pillar)

    def teleport_to_level_6(self):
        self.spawn_point = (4000, 2, 2230)
        self.position = self.spawn_point
        self.y_velocity = 0
        self.grounded = True
        self.level_3_phase = 0
        self.level_6_portal_open = True
        self.setup_level_6_arena()

        if self.teammate_unlocked:
            companion = state.spawn_archer_companion()
            companion.position = self.position + (2, 0, -2)
            companion.y = self.y + (companion.scale_y / 2) - 1
            companion.hp = max(1, min(companion.hp, companion.max_hp))
            companion.health_bar.scale_x = max(companion.hp / companion.max_hp, 0) * 1.2

        if not self.level_6_broadcast_shown:
            ent.chef.dialogue_ui.text = 'Chef: What is this place?'
            ent.chef.dialogue_ui.enabled = True
            invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            self.level_6_broadcast_shown = True

        if self.safezone_music:
            self.safezone_music.stop()

        ent.black_screen.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        invoke(setattr, self, 'is_teleporting', False, delay=1.0)

        self.mission_ui.text = 'Investigate a pillar'
        self.mission_ui.color = color.gray

    def reset_mission(self):
        self.enemies_killed = 0
        self.mission_ui.color = color.yellow
        self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'
        ent.portal.enabled = False
        ent.portal_2.enabled = False
        ent.portal_3.enabled = False
        ent.portal_4.enabled = False

    def reset_game_state(self):
        self.position = self.spawn_point
        self.hp = self.max_hp
        self.health_ui.text = f'HP: {self.hp} / {self.max_hp}'
        if self.low_health_music and self.low_health_music.playing:
            self.low_health_music.stop()
        self.y_velocity = 0
        if self.boss_music:
            self.boss_music.stop()
        if hasattr(self, 'safezone_music') and self.safezone_music:
            self.safezone_music.stop()
        if hasattr(self, 'low_health_music') and self.low_health_music:
            self.low_health_music.stop()
            
        self.crosshair.position = (0, 0.19)
        self.clear_all_entities()

        if self.spawn_point == (0, 1, 0):
            self.has_bow = False
            self.has_grenade = False
            self.grenade_used = False
            self.teammate_unlocked = False
            state.dismiss_archer_companion()
            ent.chef.exclamation.enabled = True
            ent.manager.exclamation.enabled = True
            self.level_3_phase = 0
            self.level_3_cleared = False
            self.level_4_portal_open = False
            self.level_4_cleared = False
            self.level_5_portal_open = False
            self.level_5_cleared = False
            self.level_6_portal_open = False
            self.level_6_broadcast_shown = False
            self.crosshair.enabled = False
            self.bow_icon.enabled = False
            self.grenade_icon.enabled = False
            self.dash_icon.enabled = True
            self.reset_mission()
        elif self.spawn_point == (1000, 1, 990):
            self.level_3_phase = 0
            if not self.has_bow:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.cyan
                self.crosshair.enabled = False
            elif self.level_5_portal_open:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
                self.crosshair.enabled = True
            elif self.level_4_cleared:
                self.mission_ui.text = 'Talk to the Manager'
                self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
            elif self.level_4_portal_open:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
                self.crosshair.enabled = True
            else:
                self.mission_ui.text = 'Find the Manager'
                self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
        elif self.spawn_point == (2000, 1, 2010):
            self.mission_ui.text = 'Destroy the Cannons!'
            self.mission_ui.color = color.red
            self.crosshair.enabled = True
            self.level_3_phase = 1
            self.setup_level_3_cannons()
        elif self.spawn_point == (2000, 1, 2230):
            self.level_3_phase = 0
            self.level_3_cleared = True
            self.level_4_portal_open = True
            self.setup_level_4_arena()
            self.mission_ui.text = 'Defeat the boss!'
            self.mission_ui.color = color.red
            self.crosshair.enabled = True
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
            self.crosshair.enabled = True

    def update(self):
        if self.is_teleporting:
            return

        if ent.portal.enabled and distance(self.position, ent.portal.position) < 2.5:
            self.enter_portal()
        if ent.portal_2.enabled and distance(self.position, ent.portal_2.position) < 2.5:
            self.enter_portal_2()
        if ent.portal_3.enabled and distance(self.position, ent.portal_3.position) < 2.5:
            self.enter_portal_3()
        if ent.portal_4.enabled and distance(self.position, ent.portal_4.position) < 2.5:
            self.enter_portal_4()

        if self.y < self.spawn_point[1] - 20:
            self.take_damage(self.max_hp)

        if self.level_3_phase == 1 and len(state.cannons) == 0:
            self.level_3_phase = 2
            self.mission_ui.text = 'Enter the arena!'
            self.mission_ui.color = color.green
            world.level_3_door.animate_y(-5, duration=2.0)
            state.cannons.append(ent.Cannon(position=(1980, 1.5, 2250)))
            state.cannons.append(ent.Cannon(position=(2020, 1.5, 2250)))

        if self.level_3_phase == 2 and len(state.cannons) == 0 and len(state.enemies) == 0 and len(state.cannon_spheres) == 0 and not self.level_3_cleared:
            self.level_3_cleared = True
            self.mission_ui.text = 'Hallway portal open!'
            self.mission_ui.color = color.magenta
            self.level_4_portal_open = True
            ent.portal_3.position = self.position + self.forward * 4
            ent.portal_3.y = 1.5
            ent.portal_3.enabled = True

        if self.spawn_point == (2000, 1, 2230) and not self.level_4_cleared and len(state.enemies) == 0:
            self.level_4_cleared = True
            self.mission_ui.text = 'Return portal open! Talk to the chef.'
            self.mission_ui.color = color.cyan
            ent.portal.position = self.position + self.forward * 4
            ent.portal.y = 1.5
            ent.portal.enabled = True
            ent.chef.exclamation.enabled = True

        if self.spawn_point == (3000, 1, 2230) and not self.level_5_cleared and len(state.enemies) == 0:
            self.level_5_cleared = True
            self.level_5_portal_open = False
            self.mission_ui.text = 'Boss defeated! Talk to the chef.'
            self.mission_ui.color = color.cyan
            ent.portal_4.position = self.position + self.forward * 4
            ent.portal_4.y = 1.5
            ent.portal_4.enabled = True
            ent.chef.exclamation.enabled = True
            if self.boss_music:
                self.boss_music.fade_out(duration=2)
            self.crosshair.position = (0, 0)

        if self.spawn_point == (0, 1, 0) or (self.level_3_phase == 2 and len(state.cannons) > 0):
            self.spawn_timer -= time.dt
            if self.spawn_timer <= 0:
                if len(state.enemies) < 15:
                    if self.spawn_point == (0, 1, 0):
                        spawn_x = self.x + random.uniform(-20, 20)
                        spawn_z = self.z + random.uniform(-20, 20)
                    else:
                        spawn_x = random.uniform(1980, 2020)
                        spawn_z = random.uniform(2210, 2250)

                    new_enemy = ent.Enemy(target=self, spawn_pos=(spawn_x, self.spawn_point[1], spawn_z))
                    state.enemies.append(new_enemy)
                self.spawn_timer = random.uniform(2.0, 5.0)

        previous_position = self.position
        
        # Sprinting and FOV
        current_speed = self.speed
        target_fov = 90
        if held_keys['left control']:
            current_speed *= 1.6
            target_fov = 110
        
        camera.fov = lerp(camera.fov, target_fov, 5 * time.dt)
        
        direction = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        self.position += direction * current_speed * time.dt
        if self.spawn_point == (4000, 2, 2230) or self.level_6_portal_open:
            state.resolve_level_6_pillar_collision(self, previous_position)

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
        if self.level_5_cleared:
            camera.rotation_x = clamp(camera.rotation_x - mouse.velocity[1] * 150, -25, 45)
        else:
            camera.rotation_x = 15

        if held_keys['space'] and self.grounded:
            self.y_velocity = self.jump_force
        if self.dash_cooldown > 0:
            self.dash_cooldown -= time.dt
        elif held_keys['left shift'] and self.grounded:
            self.perform_dash()

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt
        elif held_keys['left mouse']:
            self.perform_attack()
        if self.grenade_cooldown > 0:
            self.grenade_cooldown -= time.dt
        if self.level_6_portal_open:
            for pillar in state.level_6_pillars:
                if hasattr(pillar, 'touch_cooldown') and pillar.touch_cooldown > 0:
                    pillar.touch_cooldown -= time.dt
        if self.autosave_timer <= 0 and not self.is_teleporting:
            self.save_game()
            self.autosave_timer = self.autosave_interval

        # Update HUD
        if self.has_bow:
            self.bow_icon.enabled = True
            if self.attack_cooldown > 0:
                self.bow_overlay.scale_y = self.attack_cooldown / self.attack_max_cooldown
                self.bow_icon.color = color.gray
            else:
                self.bow_overlay.scale_y = 0
                self.bow_icon.color = color.white
        
        if self.has_grenade:
            self.grenade_icon.enabled = True
            if self.grenade_cooldown > 0:
                self.grenade_overlay.scale_y = self.grenade_cooldown / self.grenade_max_cooldown
                self.grenade_icon.color = color.gray
            else:
                self.grenade_overlay.scale_y = 0
                self.grenade_icon.color = color.white

            if self.dash_cooldown > 0:
                self.dash_overlay.scale_y = self.dash_cooldown / self.dash_max_cooldown
                self.dash_icon.color = color.gray
            else:
                self.dash_overlay.scale_y = 0
                self.dash_icon.color = color.white

        # Hub (Level 2) logic: Regeneration and safe zone music overrides
        is_hub = self.spawn_point == (1000, 1, 990)
        
        if is_hub:
            if self.hp < self.max_hp:
                self.hp += 15 * time.dt
                if self.hp > self.max_hp:
                    self.hp = self.max_hp
                self.health_ui.text = f'HP: {int(self.hp)} / {self.max_hp}'
        
        # Low Health Music Management
        should_play_low_health = self.hp > 0 and self.hp <= 35 and not is_hub
        
        if should_play_low_health:
            self.health_ui.color = color.red
            if self.low_health_music and not self.low_health_music.playing:
                self.low_health_music.play()
        else:
            self.health_ui.color = color.white
            if self.low_health_music and self.low_health_music.playing:
                self.low_health_music.stop()

    def perform_dash(self):
        self.dash_cooldown = 0.8
        dash_dir = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        if dash_dir.length() <= 0.001:
            dash_dir = self.forward
        else:
            dash_dir = dash_dir.normalized()
            
        self.animate_position(self.position + dash_dir * 8, duration=self.dash_duration, curve=curve.out_expo)
        self.color = color.white
        invoke(setattr, self, 'color', color.azure, delay=0.2)

    def perform_attack(self):
        self.attack_cooldown = 0.4
        self.sword.animate_rotation((120, 0, 0), duration=0.1)
        invoke(self.sword.animate_rotation, (30, 0, 0), duration=0.2, delay=0.15)

        for enemy in state.enemies:
            if distance(self.position, enemy.position) <= self.attack_range:
                enemy.take_damage(self.attack_damage)

        for c in state.cannons:
            if distance(self.position, c.position) <= self.attack_range:
                c.take_damage(self.attack_damage)

    def shoot_arrow(self):
        self.attack_cooldown = 0.5
        spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.5
        
        # Precision aiming: Find what the crosshair is looking at
        ray = raycast(camera.world_position, camera.forward, distance=500, ignore=(self,))
        if ray.hit:
            target_point = ray.world_point
        else:
            target_point = camera.world_position + (camera.forward * 500)
            
        # Before Level 5 boss is defeated, keep shots horizontal for traditional feel
        if not self.level_5_cleared:
            target_point.y = spawn_pos.y
            
        shot_direction = (target_point - spawn_pos).normalized()
        ent.Arrow(position=spawn_pos, rotation=self.rotation, direction=shot_direction)

    def throw_grenade(self):
        self.grenade_cooldown = 1.25
        spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.3
        ent.ShockwaveGrenade(position=spawn_pos, rotation=self.rotation)

    def save_game(self):
        save_data = {
            'x': self.x, 'y': self.y, 'z': self.z,
            'hp': self.hp,
            'spawn_x': self.spawn_point[0], 'spawn_y': self.spawn_point[1], 'spawn_z': self.spawn_point[2],
            'enemies_killed': self.enemies_killed,
            'portal_enabled': ent.portal.enabled, 'portal_x': ent.portal.x, 'portal_y': ent.portal.y, 'portal_z': ent.portal.z,
            'portal_2_enabled': ent.portal_2.enabled, 'portal_2_x': ent.portal_2.x, 'portal_2_y': ent.portal_2.y, 'portal_2_z': ent.portal_2.z,
            'portal_3_enabled': ent.portal_3.enabled, 'portal_3_x': ent.portal_3.x, 'portal_3_y': ent.portal_3.y, 'portal_3_z': ent.portal_3.z,
            'portal_4_enabled': ent.portal_4.enabled, 'portal_4_x': ent.portal_4.x, 'portal_4_y': ent.portal_4.y, 'portal_4_z': ent.portal_4.z,
            'has_bow': self.has_bow,
            'has_grenade': self.has_grenade,
            'grenade_used': self.grenade_used,
            'exclamation_enabled': ent.chef.exclamation.enabled,
            'manager_exclamation_enabled': ent.manager.exclamation.enabled,
            'level_3_phase': self.level_3_phase,
            'level_3_cleared': self.level_3_cleared,
            'level_4_portal_open': self.level_4_portal_open,
            'level_4_cleared': self.level_4_cleared,
            'level_5_portal_open': self.level_5_portal_open,
            'level_5_cleared': self.level_5_cleared,
            'level_6_portal_open': self.level_6_portal_open,
            'level_6_broadcast_shown': self.level_6_broadcast_shown,
            'teammate_unlocked': self.teammate_unlocked,
            'teammate_hp': getattr(state.archer_companion, 'hp', 150),
            'teammate_x': getattr(state.archer_companion, 'x', self.x),
            'teammate_y': getattr(state.archer_companion, 'y', self.y),
            'teammate_z': getattr(state.archer_companion, 'z', self.z),
            'door_y': world.level_3_door.y
        }
        tmp_file = state.SAVE_FILE.with_suffix('.json.tmp')
        with open(tmp_file, 'w') as f:
            json.dump(save_data, f)
        os.replace(tmp_file, state.SAVE_FILE)
        self.autosave_timer = self.autosave_interval
        print("Game Saved!")

    def load_game(self):
        if not state.SAVE_FILE.exists() or state.SAVE_FILE.stat().st_size == 0:
            print("No valid save file found; starting fresh.")
            return

        try:
            with open(state.SAVE_FILE, 'r') as f:
                save_data = json.load(f)
        except json.JSONDecodeError:
            print("Save file is empty or corrupted; starting fresh.")
            return

        self.x, self.y, self.z = save_data['x'], save_data['y'], save_data['z']
        if 'hp' in save_data:
            self.hp = save_data['hp']
            self.health_ui.text = f'HP: {int(self.hp)} / {self.max_hp}'
        if 'spawn_x' in save_data:
            self.spawn_point = (save_data['spawn_x'], save_data['spawn_y'], save_data['spawn_z'])

        if 'enemies_killed' in save_data:
            self.enemies_killed = save_data['enemies_killed']

        if 'portal_enabled' in save_data:
            ent.portal.enabled = save_data['portal_enabled']
            ent.portal.position = (save_data['portal_x'], save_data['portal_y'], save_data['portal_z'])
        if 'portal_2_enabled' in save_data:
            ent.portal_2.enabled = save_data['portal_2_enabled']
            ent.portal_2.position = (save_data['portal_2_x'], save_data['portal_2_y'], save_data['portal_2_z'])
        if 'portal_3_enabled' in save_data:
            ent.portal_3.enabled = save_data['portal_3_enabled']
            ent.portal_3.position = (save_data['portal_3_x'], save_data['portal_3_y'], save_data['portal_3_z'])
        if 'portal_4_enabled' in save_data:
            ent.portal_4.enabled = save_data['portal_4_enabled']
            ent.portal_4.position = (save_data['portal_4_x'], save_data['portal_4_y'], save_data['portal_4_z'])

        self.has_bow = save_data.get('has_bow', False)
        self.has_grenade = save_data.get('has_grenade', False)
        self.grenade_used = save_data.get('grenade_used', False)
        self.crosshair.enabled = self.has_bow
        self.bow_icon.enabled = self.has_bow
        self.grenade_icon.enabled = self.has_grenade
        ent.chef.exclamation.enabled = save_data.get('exclamation_enabled', True)
        ent.manager.exclamation.enabled = save_data.get('manager_exclamation_enabled', True)
        self.level_3_phase = save_data.get('level_3_phase', 0)
        self.level_3_cleared = save_data.get('level_3_cleared', False)
        self.level_4_portal_open = save_data.get('level_4_portal_open', False)
        self.level_4_cleared = save_data.get('level_4_cleared', False)
        self.level_5_portal_open = save_data.get('level_5_portal_open', False)
        self.level_5_cleared = save_data.get('level_5_cleared', False)
        self.level_6_portal_open = save_data.get('level_6_portal_open', False)
        self.level_6_broadcast_shown = save_data.get('level_6_broadcast_shown', False)
        self.teammate_unlocked = save_data.get('teammate_unlocked', False)
        world.level_3_door.y = save_data.get('door_y', 5)

        if self.teammate_unlocked:
            companion = state.spawn_archer_companion()
            companion.hp = save_data.get('teammate_hp', companion.max_hp)
            companion.health_bar.scale_x = max(companion.hp / companion.max_hp, 0) * 1.2
            companion.position = (
                save_data.get('teammate_x', self.x + 2),
                save_data.get('teammate_y', self.y),
                save_data.get('teammate_z', self.z - 2),
            )
        else:
            state.dismiss_archer_companion()

        if self.spawn_point == (0, 1, 0):
            if self.enemies_killed >= self.mission_target:
                self.mission_ui.text = 'Portal Opened Nearby!'
                self.mission_ui.color = color.magenta
            else:
                self.mission_ui.text = f'Defeat enemies: {self.enemies_killed} / {self.mission_target}'
                self.mission_ui.color = color.yellow
        elif self.spawn_point == (1000, 1, 990):
            if not self.safezone_music or not self.safezone_music.playing:
                if self.safezone_music: self.safezone_music.stop()
                self.safezone_music = Audio('safezone.mp3', loop=True, autoplay=True, volume=0.5)

            if not self.has_bow:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.cyan
                self.crosshair.enabled = False
            elif not self.level_3_cleared:
                self.mission_ui.text = 'Talk to the Manager'
                self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
            elif self.level_4_portal_open and not self.level_4_cleared:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
                self.crosshair.enabled = True
            elif self.level_4_cleared and not self.has_grenade:
                self.mission_ui.text = 'Talk to chef'
                self.mission_ui.color = color.cyan
                self.crosshair.enabled = True
            elif self.level_5_cleared:
                if self.teammate_unlocked:
                    self.mission_ui.text = 'Go with the archer.'
                    self.mission_ui.color = color.yellow
                else:
                    self.mission_ui.text = 'Talk to chef'
                    self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
            elif self.level_5_portal_open:
                self.mission_ui.text = 'Enter the portal!'
                self.mission_ui.color = color.magenta
                self.crosshair.enabled = True
            else:
                self.mission_ui.text = 'Talk to the Manager'
                self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
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
                ent.portal.position = self.position + (0, 0.5, 4)
                ent.portal.enabled = True
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
        elif self.spawn_point == (4000, 2, 2230):
            self.mission_ui.text = 'Investigate a pillar'
            self.mission_ui.color = color.gray

        self.y_velocity = 0
        self.crosshair.position = (0, 0) if self.level_5_cleared else (0, 0.19)
        self.crosshair.scale = 2
        self.crosshair.enabled = self.has_bow
        self.autosave_timer = self.autosave_interval
        print("Game Loaded!")

    def input(self, key):
        if key == '8':
            self.save_game()
        elif key == '9':
            self.load_game()
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
            if distance(self.position, ent.chef.position) < 5.0 and not self.has_bow:
                ent.chef.dialogue_ui.enabled = True
                ent.chef.exclamation.enabled = False
                self.has_bow = True
                self.mission_ui.text = 'Find the Manager'
                self.mission_ui.color = color.yellow
                self.crosshair.enabled = True
                self.bow_icon.enabled = True
                invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, ent.chef.position) < 5.0 and self.level_4_cleared and not self.has_grenade:
                ent.chef.dialogue_ui.text = 'Chef: Here take this shockwave grenade, press E to use it'
                ent.chef.dialogue_ui.enabled = True
                ent.chef.exclamation.enabled = False
                self.has_grenade = True
                self.mission_ui.text = 'Use the shockwave grenade'
                self.mission_ui.color = color.yellow
                self.grenade_icon.enabled = True
                invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, ent.chef.position) < 5.0 and self.level_5_cleared and not self.teammate_unlocked:
                ent.chef.dialogue_ui.text = 'Chef: This is my friend, the archer, he will help.'
                ent.chef.dialogue_ui.enabled = True
                ent.chef.exclamation.enabled = False
                self.teammate_unlocked = True
                teammate = state.spawn_archer_companion()
                teammate.hp = teammate.max_hp
                teammate.health_bar.scale_x = 1.2
                teammate.position = self.position + (2, 0, -2)
                self.mission_ui.text = 'Talk to the Manager'
                self.mission_ui.color = color.yellow
                invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, ent.chef.position) < 5.0:
                ent.chef.dialogue_ui.text = 'Chef: Good luck out there!'
                ent.chef.dialogue_ui.enabled = True
                invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            elif distance(self.position, ent.manager.position) < 5.0:
                if not self.has_bow:
                    ent.manager.dialogue_ui.text = "Manager: Talk to the Chef first, you need a weapon!"
                    ent.manager.dialogue_ui.enabled = True
                    invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)
                elif not self.level_3_cleared:
                    ent.manager.dialogue_ui.text = "Manager: The portal is open."
                    ent.manager.dialogue_ui.enabled = True
                    ent.manager.exclamation.enabled = False
                    self.mission_ui.text = 'Enter the portal!'
                    self.mission_ui.color = color.magenta

                    ent.portal_2.position = ent.manager.position + ent.manager.forward * 4
                    ent.portal_2.y = 1.5
                    ent.portal_2.enabled = True

                    invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)
                else:
                    if self.teammate_unlocked and self.level_5_cleared:
                        ent.manager.dialogue_ui.text = "Manager: Great. The Level 6 portal is open."
                        self.mission_ui.text = 'Enter Level 6!'
                        self.level_5_portal_open = False
                        self.level_6_portal_open = True
                    else:
                        ent.manager.dialogue_ui.text = "Manager: Great. The boss arena is open."
                        self.mission_ui.text = 'Enter the portal!'
                        self.level_5_portal_open = True
                        self.level_6_portal_open = False
                    ent.manager.dialogue_ui.enabled = True
                    ent.manager.exclamation.enabled = False
                    world.ground_4.color = color.dark_gray
                    ent.portal_4.position = ent.manager.position + ent.manager.forward * 4
                    ent.portal_4.y = 1.5
                    ent.portal_4.enabled = True
                    self.mission_ui.color = color.magenta
                    invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)

        # Removed application.quit() from here as it's now in PauseHandler


player = ThirdPersonPlayer()
state.player = player

for _ in range(2):
    new_enemy = ent.Enemy(target=player, spawn_pos=(random.uniform(-10, 10), 1, random.uniform(-10, 10)))
    state.enemies.append(new_enemy)
