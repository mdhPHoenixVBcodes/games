from ursina import *
from pathlib import Path
import math
import random

import adventure_state as state
import adventure_world as world


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
        self.name_label = Text(parent=self, text='Chef', scale=10, color=color.orange, position=(0, 1), billboard=True, origin=(0, 0))
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))
        self.dialogue_ui = Text(text="Chef: Take my bow, right click to shoot!", position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)


chef = Chef()


class Manager(Entity):
    def __init__(self):
        super().__init__(model='sphere', color=color.green, scale=(2, 4, 2), position=(990, 1, 1010), collider='box')
        self.name_label = Text(parent=self, text='Manager', scale=10, color=color.green, position=(0, 1), billboard=True, origin=(0, 0))
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))
        self.dialogue_ui = Text(text="Manager: Welcome. The portal to Level 3 is open.", position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)


manager = Manager()


class Scientist(Entity):
    def __init__(self):
        super().__init__(model='sphere', color=color.azure, scale=(2, 4, 2), position=(3992, 1, 2238), collider='box')
        self.name_label = Text(parent=self, text='Scientist', scale=10, color=color.azure, position=(0, 1), billboard=True, origin=(0, 0))
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))
        self.dialogue_ui = Text(text="Scientist: ...", position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)


scientist = None


class Cannon(Entity):
    def __init__(self, position, fixed_fire_direction=None, fire_damage=15, fire_interval_range=(3.0, 5.0)):
        super().__init__(model='cube', color=color.red, scale=(2, 2, 2), position=position, collider='box')
        self.hp = 50
        self.fixed_fire_direction = fixed_fire_direction.normalized() if fixed_fire_direction is not None else None
        self.fire_damage = fire_damage
        self.fire_interval_range = fire_interval_range
        self.shoot_timer = random.uniform(*fire_interval_range)

    def take_damage(self, amount):
        self.hp -= amount
        DamageMarker(amount, self.world_position + (0, 1, 0))
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            if self in state.cannons:
                state.cannons.remove(self)
            destroy(self)

    def update(self):
        if state.player.is_teleporting or distance(self.position, state.player.position) > 100:
            return

        self.shoot_timer -= time.dt
        if self.shoot_timer <= 0:
            if self.fixed_fire_direction is not None:
                sphere = CannonSphere(
                    self.position + self.fixed_fire_direction * 1.5 + (0, 1, 0),
                    target=state.get_nearest_party_target(self.position),
                    fixed_direction=self.fixed_fire_direction,
                    damage=self.fire_damage,
                )
                state.cannon_spheres.append(sphere)
                self.shoot_timer = random.uniform(*self.fire_interval_range)
            else:
                target = state.get_nearest_party_target(self.position)
                sphere = CannonSphere(self.position + (0, 1, 0), target=target)
                state.cannon_spheres.append(sphere)
                self.shoot_timer = random.uniform(3.0, 5.0)


class CannonSphere(Entity):
    def __init__(self, position, target=None, fixed_direction=None, damage=15):
        self.target = target or state.player
        super().__init__(model='sphere', color=color.orange, scale=2.5, position=position)
        self.speed = 10
        self.fixed_direction = fixed_direction.normalized() if fixed_direction is not None else None
        self.damage = damage
        if self.fixed_direction is None:
            self.look_at_2d(self.target, 'y')
        self.lifetime = 8.0

    def take_damage(self, amount):
        DamageMarker(amount, self.world_position + (0, 1, 0))
        if self in state.cannon_spheres:
            state.cannon_spheres.remove(self)
        destroy(self)

    def update(self):
        if state.player.is_teleporting:
            return

        self.lifetime -= time.dt
        if self.lifetime <= 0:
            if self in state.cannon_spheres:
                state.cannon_spheres.remove(self)
            destroy(self)
            return

        if self.fixed_direction is not None:
            self.position += self.fixed_direction * self.speed * time.dt
        else:
            self.position += self.forward * self.speed * time.dt

        for target in state.get_active_party_targets():
            if distance(self.position, target.position) < 2.5:
                target.take_damage(self.damage)
                if self in state.cannon_spheres:
                    state.cannon_spheres.remove(self)
                destroy(self)
                return


class ShockwaveGrenade(Entity):
    def __init__(self, position, rotation):
        super().__init__(model='sphere', color=color.azure, scale=0.35, position=position, rotation=rotation)
        self.speed = 28
        self.life = 1.2
        self.exploded = False

    def update(self):
        if state.player.is_teleporting or self.exploded:
            return

        self.position += self.forward * self.speed * time.dt
        self.life -= time.dt

        if self.life <= 0:
            self.explode()
            return

        for enemy in state.enemies:
            if distance(self.position, enemy.position) < 1.6:
                self.explode()
                return

    def explode(self):
        if self.exploded:
            return

        self.exploded = True
        state.player.grenade_used = True
        state.player.mission_ui.text = 'Talk to the Manager.'
        state.player.mission_ui.color = color.cyan

        shockwave = Entity(
            model='sphere',
            color=color.rgba(120, 240, 255, 110),
            position=self.position,
            scale=1.0
        )
        shockwave.animate_scale(8, duration=0.35)
        shockwave.animate_color(color.rgba(120, 240, 255, 0), duration=0.35)
        destroy(shockwave, delay=0.4)

        for enemy in state.enemies:
            dist = distance(self.position, enemy.position)
            if dist <= state.player.grenade_shockwave_radius:
                push_dir = enemy.position - self.position
                push_dir.y = 0 # Ensure push is horizontal
                if push_dir.length() > 0.001:
                    push_dir = push_dir.normalized()
                else:
                    push_dir = self.forward
                    push_dir.y = 0
                push_strength = state.player.grenade_shockwave_push * max(0.35, 1 - dist / state.player.grenade_shockwave_radius)
                enemy.position += push_dir * push_strength
                enemy.stun_timer = 0.45

        destroy(self)


class Arrow(Entity):
    def __init__(self, position, rotation=None, direction=None, hit_party=False, hit_enemies=True, hit_cannons=True, hit_spheres=True, damage=10):
        super().__init__(model='cube', color=color.white, scale=(0.05, 0.05, 1.5), position=position, rotation=rotation or (0, 0, 0))
        self.speed = 60
        self.damage = damage
        self.direction = (direction.normalized() if direction is not None else self.forward)
        self.hit_party = hit_party
        self.hit_enemies = hit_enemies
        self.hit_cannons = hit_cannons
        self.hit_spheres = hit_spheres
        destroy(self, delay=2.0)

    def update(self):
        self.position += self.direction * self.speed * time.dt

        if self.hit_spheres:
            for s in state.cannon_spheres:
                if distance(self.position, s.position) < 2.5:
                    s.take_damage(self.damage)
                    destroy(self)
                    return

        if self.hit_cannons:
            for c in state.cannons:
                if distance(self.position, c.position) < 2.0:
                    c.take_damage(self.damage)
                    destroy(self)
                    return

        if self.hit_enemies:
            for e in state.enemies:
                if distance(self.position, e.position) < 2.5:
                    e.take_damage(self.damage)
                    destroy(self)
                    return

        if self.hit_party:
            for target in state.get_active_party_targets():
                if distance(self.position, target.position) < 2.2:
                    target.take_damage(self.damage)
                    destroy(self)
                    return


class Rocket(Entity):
    def __init__(self, position, direction=None, damage=35, explosion_radius=6):
        super().__init__(model='sphere', color=color.orange, scale=0.28, position=position, collider='box')
        self.speed = 42
        self.damage = damage
        self.explosion_radius = explosion_radius
        self.direction = (direction.normalized() if direction is not None else self.forward)
        self.life = 3.0
        self.exploded = False
        destroy(self, delay=4.0)

    def update(self):
        if self.exploded or state.player.is_teleporting:
            return

        self.position += self.direction * self.speed * time.dt
        self.life -= time.dt

        for enemy in state.enemies:
            if distance(self.position, enemy.position) <= 1.4:
                self.explode()
                return

        for cannon in state.cannons:
            if distance(self.position, cannon.position) <= 1.6:
                self.explode()
                return

        for sphere in state.cannon_spheres:
            if distance(self.position, sphere.position) <= 1.8:
                self.explode()
                return

        if self.life <= 0:
            self.explode()

    def explode(self):
        if self.exploded:
            return

        self.exploded = True
        flash = Entity(
            model='sphere',
            color=color.rgba(255, 230, 160, 150),
            position=self.position,
            scale=0.35
        )
        flash.animate_scale(1.8, duration=0.18)
        flash.animate_color(color.rgba(255, 230, 160, 0), duration=0.18)
        destroy(flash, delay=0.2)

        blast = Entity(
            model='sphere',
            color=color.rgba(255, 180, 70, 140),
            position=self.position,
            scale=0.8
        )
        blast.animate_scale(self.explosion_radius * 0.8, duration=0.25)
        blast.animate_color(color.rgba(255, 180, 70, 0), duration=0.25)
        destroy(blast, delay=0.3)

        for enemy in list(state.enemies):
            if distance(self.position, enemy.position) <= self.explosion_radius:
                DamageMarker(self.damage, enemy.world_position + (0, 1.5, 0))
                enemy.take_damage(self.damage)

        for cannon in list(state.cannons):
            if distance(self.position, cannon.position) <= self.explosion_radius:
                DamageMarker(self.damage, cannon.world_position + (0, 1, 0))
                cannon.take_damage(self.damage)

        for sphere in list(state.cannon_spheres):
            if distance(self.position, sphere.position) <= self.explosion_radius:
                DamageMarker(self.damage, sphere.world_position + (0, 1, 0))
                sphere.take_damage(self.damage)

        destroy(self)


class PurpleOrb(Entity):
    def __init__(self, position, direction=None, damage=25, explosion_radius=6, stun_duration=3.0):
        super().__init__(model='sphere', color=color.violet, scale=0.32, position=position, collider='box')
        self.speed = 38
        self.damage = damage
        self.explosion_radius = explosion_radius
        self.stun_duration = stun_duration
        self.direction = (direction.normalized() if direction is not None else self.forward)
        self.life = 3.5
        self.exploded = False
        destroy(self, delay=4.5)

    def update(self):
        if self.exploded or state.player.is_teleporting:
            return

        self.position += self.direction * self.speed * time.dt
        self.life -= time.dt

        for enemy in state.enemies:
            if distance(self.position, enemy.position) <= 1.4:
                self.explode()
                return

        if self.life <= 0:
            self.explode()

    def explode(self):
        if self.exploded:
            return

        self.exploded = True
        flash = Entity(
            model='sphere',
            color=color.rgba(210, 120, 255, 160),
            position=self.position,
            scale=0.35
        )
        flash.animate_scale(1.9, duration=0.18)
        flash.animate_color(color.rgba(210, 120, 255, 0), duration=0.18)
        destroy(flash, delay=0.2)

        blast = Entity(
            model='sphere',
            color=color.rgba(180, 80, 255, 140),
            position=self.position,
            scale=0.9
        )
        blast.animate_scale(self.explosion_radius * 0.85, duration=0.25)
        blast.animate_color(color.rgba(180, 80, 255, 0), duration=0.25)
        destroy(blast, delay=0.3)

        for enemy in list(state.enemies):
            if distance(self.position, enemy.position) <= self.explosion_radius:
                DamageMarker(self.damage, enemy.world_position + (0, 1.5, 0))
                enemy.take_damage(self.damage)
                enemy.stun_timer = max(enemy.stun_timer, self.stun_duration)

        destroy(self)


class ArcherCompanion(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.azure,
            scale=(0.9, 1.8, 0.9),
            position=state.player.position + (2, 0, -2),
            collider='box'
        )
        self.max_hp = 150
        self.hp = self.max_hp
        self.speed = 7
        self.follow_distance = 2.8
        self.attack_range = 16
        self.attack_cooldown = 0
        self.y_velocity = 0
        self.gravity = 25
        self.jump_force = 12
        self.grounded = False
        self.dash_cooldown = 0
        self.dash_max_cooldown = 0.8
        self.dash_duration = 0.15
        self.dash_speed = 45
        self.is_dashing = False
        self.health_bar = Entity(parent=self, y=1.1, model='cube', color=color.green, scale=(1.2, 0.12, 0.12))
        self.bow = Entity(parent=self, model='cube', color=color.brown, scale=(0.12, 0.8, 0.12), position=(0.55, 0.05, 0.25), rotation=(0, 0, 25))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.2
        self.color = color.white
        invoke(setattr, self, 'color', color.azure, delay=0.1)
        if self.hp <= 0:
            # Notify player to start respawn timer, then destroy
            if hasattr(state.player, 'archer_respawn_timer'):
                state.player.archer_respawn_timer = 30.0
                state.player.mission_ui.text = 'Archer KO! Respawning in 30s...'
                state.player.mission_ui.color = color.orange
            state.set_control_mode('player')
            state.dismiss_archer_companion()

    def shoot_arrow(self):
        if self.attack_cooldown > 0:
            return

        self.attack_cooldown = 0.5
        spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.5
        ray = raycast(camera.world_position, camera.forward, distance=500, ignore=(self,))
        if ray.hit:
            target_point = ray.world_point
        else:
            target_point = camera.world_position + (camera.forward * 500)
        shot_direction = (target_point - spawn_pos).normalized()
        Arrow(position=spawn_pos, rotation=self.rotation, direction=shot_direction, damage=15)

    def perform_dash(self):
        self.dash_cooldown = self.dash_max_cooldown
        self.is_dashing = True
        dash_dir = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        if dash_dir.length() <= 0.001:
            dash_dir = self.forward
        else:
            dash_dir = dash_dir.normalized()

        self.animate_position(self.position + dash_dir * 8, duration=self.dash_duration, curve=curve.out_expo)
        invoke(setattr, self, 'is_dashing', False, delay=self.dash_duration)

    def snap_to_ground(self):
        ground_ray = raycast(self.position + (0, 2, 0), direction=(0, -1, 0), ignore=(self, state.player), distance=8)
        if ground_ray.hit:
            self.y = ground_ray.world_point[1] + (self.scale_y / 2)
            self.y_velocity = 0
            self.grounded = True
            return True
        return False

    def input(self, key):
        if state.control_mode != 'archer':
            return

        if key == 'f':
            state.handle_story_interaction(self)

    def update(self):
        if state.player.is_teleporting:
            return

        if state.control_mode == 'archer':
            if self.attack_cooldown > 0:
                self.attack_cooldown -= time.dt
            if self.dash_cooldown > 0:
                self.dash_cooldown -= time.dt

            current_speed = self.speed
            target_fov = 90
            if held_keys['left control']:
                current_speed *= 1.6
                target_fov = 110
            camera.fov = lerp(camera.fov, target_fov, 5 * time.dt)

            if not self.is_dashing:
                direction = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
                self.position += direction * current_speed * time.dt

            previous_position = self.position
            if getattr(state.player, 'current_level', None) == 7:
                state.player.resolve_level_7_pillar_collision(self, previous_position)

            if not self.snap_to_ground():
                self.grounded = False
                self.y_velocity -= self.gravity * time.dt
            self.y += self.y_velocity * time.dt
            self.snap_to_ground()

            self.rotation_y += mouse.velocity[0] * 150
            camera.rotation_x = clamp(camera.rotation_x - mouse.velocity[1] * 150, -25, 45)

            if held_keys['space'] and self.grounded:
                self.y_velocity = self.jump_force
            if (held_keys['left shift'] or held_keys['shift']) and self.dash_cooldown <= 0:
                self.perform_dash()
            if held_keys['right mouse'] and self.attack_cooldown <= 0:
                self.shoot_arrow()
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        follow_target = state.player.position + state.player.right * 1.5 - state.player.forward * 2.5
        follow_target.y = self.y
        to_follow = follow_target - self.position
        to_follow.y = 0
        previous_position = self.position
        if to_follow.length() > self.follow_distance:
            self.position += to_follow.normalized() * self.speed * time.dt
            state.resolve_level_6_pillar_collision(self, previous_position)

        self.snap_to_ground()

        if self.attack_cooldown <= 0 and len(state.enemies) > 0:
            target = min(state.enemies, key=lambda enemy: distance(self.position, enemy.position))
            if distance(self.position, target.position) <= self.attack_range:
                self.look_at(target.position + (0, 0.5, 0))
                Arrow(position=self.position + self.forward * 1.3 + (0, 1.0, 0), rotation=self.rotation, direction=self.forward, hit_party=False, hit_enemies=True, hit_cannons=True, hit_spheres=True, damage=15)
                self.attack_cooldown = 0.9


class DroneCompanion(Entity):
    def __init__(self):
        super().__init__(
            model='sphere',
            color=color.cyan,
            scale=1.15,
            position=state.player.position + (-2, 1.5, -2),
            collider='box'
        )
        self.max_hp = 120
        self.hp = self.max_hp
        self.speed = 8.5
        self.follow_distance = 3.0
        self.attack_range = 24
        self.attack_cooldown = 0
        self.y_velocity = 0
        self.gravity = 25
        self.jump_force = 12
        self.grounded = False
        self.dash_cooldown = 0
        self.dash_duration = 0.15
        self.dash_speed = 45
        self.is_dashing = False
        self.health_bar = Entity(parent=self, y=0.9, model='cube', color=color.green, scale=(1.1, 0.1, 0.1))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.1
        self.color = color.white
        invoke(setattr, self, 'color', color.cyan, delay=0.1)
        if self.hp <= 0:
            if hasattr(state.player, 'drone_respawn_timer'):
                state.player.drone_respawn_timer = 30.0
                state.player.mission_ui.text = 'Drone KO! Respawning in 30s...'
                state.player.mission_ui.color = color.orange
            state.set_control_mode('player')
            state.dismiss_drone_companion()

    def snap_to_ground(self):
        ground_ray = raycast(self.position + (0, 2, 0), direction=(0, -1, 0), ignore=(self, state.player, state.archer_companion), distance=8)
        if ground_ray.hit:
            self.y = ground_ray.world_point[1] + (self.scale_y / 2)
            self.y_velocity = 0
            self.grounded = True
            return True
        return False

    def perform_dash(self):
        self.dash_cooldown = self.dash_duration
        self.is_dashing = True
        dash_dir = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        if dash_dir.length() <= 0.001:
            dash_dir = self.forward
        else:
            dash_dir = dash_dir.normalized()

        self.animate_position(self.position + dash_dir * 8, duration=self.dash_duration, curve=curve.out_expo)
        invoke(setattr, self, 'is_dashing', False, delay=self.dash_duration)

    def input(self, key):
        if state.control_mode != 'drone':
            return
        if key == 'f':
            state.handle_story_interaction(self)

    def update(self):
        if state.player.is_teleporting:
            return

        if state.control_mode == 'drone':
            if self.attack_cooldown > 0:
                self.attack_cooldown -= time.dt

            current_speed = self.speed
            target_fov = 90
            if held_keys['left control']:
                current_speed *= 1.6
                target_fov = 110
            camera.fov = lerp(camera.fov, target_fov, 5 * time.dt)

            if not self.is_dashing:
                direction = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
                self.position += direction * current_speed * time.dt

            vertical_direction = 0
            if held_keys['space']:
                vertical_direction += 1
            if held_keys['left shift'] or held_keys['shift']:
                vertical_direction -= 1
            if vertical_direction != 0:
                self.position += self.up * vertical_direction * current_speed * time.dt

            previous_position = self.position
            if getattr(state.player, 'current_level', None) == 7:
                state.player.resolve_level_7_pillar_collision(self, previous_position)

            self.y_velocity = 0
            self.grounded = False

            self.rotation_y += mouse.velocity[0] * 150
            camera.rotation_x = clamp(camera.rotation_x - mouse.velocity[1] * 150, -25, 45)

            if held_keys['right mouse'] and self.attack_cooldown <= 0:
                self.attack_cooldown = 0.5
                spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.5
                ray = raycast(camera.world_position, camera.forward, distance=500, ignore=(self,))
                if ray.hit:
                    target_point = ray.world_point
                else:
                    target_point = camera.world_position + (camera.forward * 500)
                shot_direction = (target_point - spawn_pos).normalized()
                Arrow(position=spawn_pos, rotation=self.rotation, direction=shot_direction, damage=10)
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        follow_target = state.player.position - state.player.right * 1.8 - state.player.forward * 3.0
        follow_target.y = self.y
        to_follow = follow_target - self.position
        to_follow.y = 0
        previous_position = self.position
        if to_follow.length() > self.follow_distance:
            self.position += to_follow.normalized() * self.speed * time.dt
            if getattr(state.player, 'current_level', None) == 7:
                state.player.resolve_level_7_pillar_collision(self, previous_position)

        self.snap_to_ground()

        if self.attack_cooldown <= 0 and len(state.enemies) > 0:
            target = min(state.enemies, key=lambda enemy: distance(self.position, enemy.position))
            if distance(self.position, target.position) <= self.attack_range:
                loS_target = target.position + (0, 0.5, 0)
                loS_origin = self.position + (0, 1.0, 0)
                los = raycast(loS_origin, (loS_target - loS_origin).normalized(), distance=distance(loS_origin, loS_target), ignore=(self, target))
                if getattr(state.player, 'current_level', None) == 7 and los.hit and los.entity in getattr(state.player, 'level_7_pillars', []):
                    return
                self.look_at(target.position + (0, 0.5, 0))
                Arrow(position=self.position + self.forward * 1.2 + (0, 1.0, 0), rotation=self.rotation, direction=self.forward, hit_party=False, hit_enemies=True, hit_cannons=True, hit_spheres=True, damage=10)
                self.attack_cooldown = 1.8


class SoldierCompanion(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.rgb(90, 120, 90),
            scale=(1.0, 2.0, 1.0),
            position=state.player.position + (3, 0, -2),
            collider='box'
        )
        self.max_hp = 170
        self.hp = self.max_hp
        self.speed = 7.5
        self.follow_distance = 2.6
        self.attack_range = 20
        self.attack_cooldown = 0
        self.melee_range = 3.0
        self.melee_damage = 18
        self.special_max_cooldown = 8.0
        self.special_cooldown = 0.0
        self.y_velocity = 0
        self.gravity = 25
        self.jump_force = 12
        self.grounded = False
        self.dash_cooldown = 0
        self.dash_duration = 0.15
        self.is_dashing = False
        self.health_bar = Entity(parent=self, y=1.0, model='cube', color=color.green, scale=(1.25, 0.12, 0.12))
        self.weapon = Entity(parent=self, model='cube', color=color.dark_gray, scale=(0.12, 0.9, 0.12), position=(0.55, 0.1, 0.2), rotation=(0, 0, 20))
        self.dialogue_ui = Text(text='Soldier: ...', position=(0, -0.35), origin=(0, 0), scale=2, color=color.white, background=True, enabled=False)
        self.exclamation = Text(parent=self, text='!', scale=50, color=color.yellow, position=(0, 1.2), billboard=True, origin=(0, 0))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.25
        self.color = color.white
        invoke(setattr, self, 'color', color.rgb(90, 120, 90), delay=0.1)
        if self.hp <= 0:
            state.set_control_mode('player')
            state.dismiss_soldier_companion()

    def snap_to_ground(self):
        ground_ray = raycast(self.position + (0, 2, 0), direction=(0, -1, 0), ignore=(self, state.player, state.archer_companion, state.drone_companion), distance=8)
        if ground_ray.hit:
            self.y = ground_ray.world_point[1] + (self.scale_y / 2)
            self.y_velocity = 0
            self.grounded = True
            return True
        return False

    def input(self, key):
        if state.control_mode != 'soldier':
            return
        if key == 'f':
            state.handle_story_interaction(self)

    def perform_melee_attack(self):
        if self.attack_cooldown > 0:
            return
        hit_target = None
        hit_distance = self.melee_range
        for enemy in state.enemies:
            dist = distance(self.position, enemy.position)
            if dist <= hit_distance:
                hit_target = enemy
                hit_distance = dist
        if hit_target is not None:
            self.look_at(hit_target.position + (0, 0.5, 0))
            hit_target.take_damage(self.melee_damage)
            self.attack_cooldown = 0.45
        else:
            self.attack_cooldown = 0.2

    def start_special_attack(self):
        if self.special_cooldown > 0 or state.control_mode != 'soldier':
            return
        self.special_cooldown = self.special_max_cooldown
        self.attack_cooldown = max(self.attack_cooldown, 0.1)

        dash_dir = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
        if dash_dir.length() <= 0.001:
            dash_dir = self.forward
        else:
            dash_dir = dash_dir.normalized()

        self.is_dashing = True
        dash_target = self.position + dash_dir * 9.5
        self.animate_position(dash_target, duration=0.18, curve=curve.out_expo)
        invoke(setattr, self, 'is_dashing', False, delay=0.18)
        invoke(self.slice_and_dice, delay=0.06)

    def slice_and_dice(self):
        pulse_delays = (0.0, 0.09, 0.18)
        for delay in pulse_delays:
            invoke(self._slice_pulse, delay=delay)

    def _slice_pulse(self):
        if state.control_mode != 'soldier' or self.hp <= 0:
            return

        hit_any = False
        slash_radius = 3.6
        slash_damage = 16
        for enemy in list(state.enemies):
            if distance(self.position, enemy.position) <= slash_radius:
                enemy.take_damage(slash_damage)
                hit_any = True

        if hit_any:
            self.color = color.white
            invoke(setattr, self, 'color', color.rgb(90, 120, 90), delay=0.08)
        self.attack_cooldown = max(self.attack_cooldown, 0.12)

    def update(self):
        if state.player.is_teleporting:
            return

        if state.control_mode == 'soldier':
            if self.attack_cooldown > 0:
                self.attack_cooldown -= time.dt
            if self.special_cooldown > 0:
                self.special_cooldown -= time.dt
            if self.dash_cooldown > 0:
                self.dash_cooldown -= time.dt

            current_speed = self.speed
            target_fov = 90
            if held_keys['left control']:
                current_speed *= 1.55
                target_fov = 108
            camera.fov = lerp(camera.fov, target_fov, 5 * time.dt)

            if not self.is_dashing:
                direction = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
                self.position += direction * current_speed * time.dt

            previous_position = self.position
            if getattr(state.player, 'current_level', None) == 7:
                state.player.resolve_level_7_pillar_collision(self, previous_position)

            if not self.snap_to_ground():
                self.grounded = False
                self.y_velocity -= self.gravity * time.dt
            self.y += self.y_velocity * time.dt
            self.snap_to_ground()

            self.rotation_y += mouse.velocity[0] * 150
            camera.rotation_x = clamp(camera.rotation_x - mouse.velocity[1] * 150, -25, 45)

            if held_keys['space'] and self.grounded:
                self.y_velocity = self.jump_force
            if (held_keys['left shift'] or held_keys['shift']) and self.dash_cooldown <= 0:
                self.dash_cooldown = 0.8
                self.is_dashing = True
                dash_dir = self.forward * (held_keys['w'] - held_keys['s']) + self.right * (held_keys['d'] - held_keys['a'])
                if dash_dir.length() <= 0.001:
                    dash_dir = self.forward
                else:
                    dash_dir = dash_dir.normalized()
                self.animate_position(self.position + dash_dir * 8, duration=0.15, curve=curve.out_expo)
                invoke(setattr, self, 'is_dashing', False, delay=0.15)
            if held_keys['right mouse'] and self.attack_cooldown <= 0:
                self.attack_cooldown = 0.45
                spawn_pos = self.position + (0, 1.2, 0) + self.forward * 1.4
                ray = raycast(camera.world_position, camera.forward, distance=500, ignore=(self,))
                if ray.hit:
                    target_point = ray.world_point
                else:
                    target_point = camera.world_position + (camera.forward * 500)
                shot_direction = (target_point - spawn_pos).normalized()
                Arrow(position=spawn_pos, rotation=self.rotation, direction=shot_direction, damage=12)
            if held_keys['left mouse'] and self.attack_cooldown <= 0:
                self.perform_melee_attack()
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        if getattr(state.player, 'soldier_teammate_unlocked', False):
            follow_target = state.player.position + state.player.right * 1.5 - state.player.forward * 2.2
            follow_target.y = self.y
            to_follow = follow_target - self.position
            to_follow.y = 0
            previous_position = self.position
            if to_follow.length() > self.follow_distance:
                self.position += to_follow.normalized() * self.speed * time.dt
            if getattr(state.player, 'current_level', None) == 7:
                state.player.resolve_level_7_pillar_collision(self, previous_position)

            self.snap_to_ground()

            if self.attack_cooldown <= 0 and len(state.enemies) > 0:
                target = min(state.enemies, key=lambda enemy: distance(self.position, enemy.position))
                if distance(self.position, target.position) <= self.attack_range:
                    self.look_at(target.position + (0, 0.5, 0))
                    Arrow(position=self.position + self.forward * 1.3 + (0, 1.0, 0), rotation=self.rotation, direction=self.forward, hit_party=False, hit_enemies=True, hit_cannons=True, hit_spheres=True, damage=12)
                    self.attack_cooldown = 1.2


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
        DamageMarker(amount, self.world_position + (0, 1.5, 0))
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.2
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            if self in state.enemies:
                state.enemies.remove(self)
            self.target.add_kill()
            destroy(self)

    def update(self):
        if self.target.is_teleporting:
            return

        target = state.get_nearest_party_target(self.position) or self.target

        if self.stun_timer > 0:
            self.stun_timer -= time.dt
            return

        dist = distance(self.position, target.position)
        for other in state.enemies:
            if other != self and distance(self.position, other.position) < 1.5:
                self.position += (self.position - other.position).normalized() * self.speed * 0.5 * time.dt

        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt
        if dist > self.attack_range:
            self.look_at_2d(target, 'y')
            self.position += self.forward * self.speed * time.dt
        elif self.attack_cooldown <= 0:
            target.take_damage(self.attack_damage)
            self.attack_cooldown = 2.0


class SphereEnemy(Entity):
    def __init__(self, target, spawn_pos):
        super().__init__(
            model='sphere',
            color=color.red,
            scale=1.2,
            position=spawn_pos,
            collider='box'
        )
        self.target = target
        self.speed = 9.0
        self.max_hp = 120
        self.hp = self.max_hp
        self.attack_range = 22
        self.attack_damage = 5
        self.attack_cooldown = 0
        self.health_bar = Entity(parent=self, y=0.9, model='cube', color=color.green, scale=(1.1, 0.1, 0.1))

    def take_damage(self, amount):
        self.hp -= amount
        DamageMarker(amount, self.world_position + (0, 1, 0))
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.1
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            drop_position = self.position + (0, 0.6, 0)
            if self in state.enemies:
                state.enemies.remove(self)
            if getattr(state.player, 'current_level', None) == 6 and state.level_6_sphere_drop is None:
                state.spawn_level_6_sphere_drop(drop_position)
            destroy(self)

    def update(self):
        if self.target.is_teleporting:
            return

        target = state.get_nearest_party_target(self.position) or self.target
        dist = distance(self.position, target.position)
        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        if dist > self.attack_range:
            self.look_at(target.position + (0, 0.5, 0))
            self.position += self.forward * self.speed * time.dt
        elif self.attack_cooldown <= 0:
            loS_target = target.position + (0, 0.5, 0)
            loS_origin = self.position + (0, 0.9, 0)
            los = raycast(loS_origin, (loS_target - loS_origin).normalized(), distance=dist, ignore=(self, target))
            if getattr(state.player, 'current_level', None) == 7 and los.hit and los.entity in getattr(state.player, 'level_7_pillars', []):
                return
            self.look_at(target.position + (0, 0.5, 0))
            Arrow(position=self.position + self.forward * 1.2 + (0, 0.9, 0), rotation=self.rotation, direction=self.forward, hit_party=True, hit_enemies=False, hit_cannons=False, hit_spheres=False, damage=5)
            self.attack_cooldown = 2.25


class SphereDrop(Entity):
    def __init__(self, position):
        super().__init__(
            model='cube',
            color=color.gold,
            scale=0.7,
            position=position,
            collider='box'
        )
        self.base_y = self.y
        self.spin_speed = random.uniform(90, 140)
        self.float_phase = random.uniform(0, 6.28)
        self.float_timer = 0
        self.fall_speed = 18
        self.landed = False
        self.pickup_range = 2.2

    def update(self):
        if state.player is None or state.player.is_teleporting:
            return

        self.rotation_y += self.spin_speed * time.dt

        if not self.landed:
            self.y -= self.fall_speed * time.dt
            ground_hit = raycast(self.world_position + (0, 1, 0), direction=(0, -1, 0), distance=20, ignore=(self,))
            if ground_hit.hit:
                target_y = ground_hit.world_point[1] + (self.scale_y / 2)
                if self.y <= target_y:
                    self.y = target_y
                    self.base_y = self.y
                    self.landed = True
            return

        self.float_timer += time.dt * 2.5
        self.y = self.base_y + math.sin(self.float_timer + self.float_phase) * 0.15

        if distance(self.position, state.player.position) <= self.pickup_range:
            state.player.collect_level_6_sphere_drop(self.position)
            state.clear_level_6_sphere_drop()


class BossCube(Entity):
    def __init__(self, target, spawn_pos):
        super().__init__(
            model='cube',
            texture='Logo/boss_texture1.png',
            color=color.white,
            scale=4.5,
            position=spawn_pos,
            collider='box'
        )
        self.target = target
        self.speed = 1.2
        self.max_hp = 300
        self.hp = self.max_hp
        self.attack_range = 5.0
        self.attack_damage = 25
        self.attack_cooldown = 0
        self.shoot_timer = random.uniform(2.5, 4.0)
        self.health_bar = Entity(parent=self, y=0.6, model='cube', color=color.green, scale=(1.2, 0.08, 0.08))

    def take_damage(self, amount):
        self.hp -= amount
        DamageMarker(amount, self.world_position + (0, 2, 0))
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 2.2
        self.color = color.gray
        invoke(setattr, self, 'color', color.white, delay=0.1)
        if self.hp <= 0:
            if self in state.enemies:
                state.enemies.remove(self)
            destroy(self)

    def update(self):
        if self.target.is_teleporting:
            return

        target = state.get_nearest_party_target(self.position) or self.target
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
            state.cannon_spheres.append(sphere)
            self.shoot_timer = random.uniform(2.5, 4.0)


class SphereBoss(Entity):
    def __init__(self, target, spawn_pos):
        super().__init__(
            model='sphere',
            texture='Logo/boss_texture2.png',
            color=color.white,
            scale=(5.5, 7.0, 5.5),
            position=spawn_pos,
            collider='box'
        )
        self.target = target
        self.speed = 1.3
        self.max_hp = 500
        self.hp = self.max_hp
        self.attack_range = 5.5
        self.attack_damage = 22
        self.attack_cooldown = 0
        self.shoot_timer = random.uniform(1.2, 2.4)
        self.health_bar = Entity(parent=self, y=0.8, model='cube', color=color.green, scale=(1.4, 0.08, 0.08))

    def take_damage(self, amount):
        self.hp -= amount
        DamageMarker(amount, self.world_position + (0, 2, 0))
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 2.2
        self.color = color.gray
        invoke(setattr, self, 'color', color.white, delay=0.1)
        if self.hp <= 0:
            if self in state.enemies:
                state.enemies.remove(self)
            destroy(self)

    def update(self):
        if self.target.is_teleporting:
            return

        target = state.player
        dist = distance(self.position, target.position)
        self.shoot_timer -= time.dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= time.dt

        if dist > self.attack_range:
            self.look_at_2d(target, 'y')
            self.position += self.forward * self.speed * time.dt
        elif self.attack_cooldown <= 0:
            target.take_damage(self.attack_damage)
            self.attack_cooldown = 1.5

        if dist < 90 and self.shoot_timer <= 0:
            arrow_start = self.position + (0, 2.0, 0) + self.forward * 2.8
            shot_dir = (target.position + (0, 1.0, 0) - arrow_start).normalized()
            Arrow(
                position=arrow_start,
                rotation=self.rotation,
                direction=shot_dir,
                hit_party=True,
                hit_enemies=False,
                hit_cannons=False,
                hit_spheres=False,
                damage=14,
            )
            self.shoot_timer = random.uniform(1.5, 2.8)


black_screen = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(3, 3), z=-10)
controls_ui = Text(text='8 - Save\n9 - Load\n0 - Pause', position=(-0.82, -0.35), scale=2.5, color=color.white, background=True)


class DamageMarker(Text):
    def __init__(self, amount, position):
        super().__init__(
            text=str(int(amount)),
            position=position,
            scale=2.2,
            color=color.white,
            origin=(0, 0),
            billboard=True,
            background=False
        )
        self.shadow = Text(
            parent=self,
            text=str(int(amount)),
            position=(0.04, -0.04),
            scale=2.2,
            color=color.black,
            origin=(0, 0),
            billboard=True,
            background=False
        )
        self.animate_y(self.y + 2.6, duration=0.55, curve=curve.out_expo)
        self.animate_scale(2.7, duration=0.12)
        self.animate_color(color.rgb(255, 245, 120), duration=0.08)
        self.shadow.animate_y(self.shadow.y + 2.6, duration=0.55, curve=curve.out_expo)
        self.shadow.animate_scale(2.7, duration=0.12)
        self.shadow.animate_color(color.rgba(0, 0, 0, 0), duration=0.45, delay=0.08)
        self.animate_color(color.rgba(255, 245, 120, 0), duration=0.45, delay=0.08)
        destroy(self.shadow, delay=0.6)
        destroy(self, delay=0.6)


class PauseHandler(Entity):
    def __init__(self):
        super().__init__(ignore_paused=True)
        self.pause_menu = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 150), scale=(2, 2), enabled=False)
        self.pause_text = Text(parent=self.pause_menu, text='PAUSED', origin=(0, 0), position=(0, 0.2), scale=4, color=color.yellow)
        
        self.resume_btn = Button(parent=self.pause_menu, text='Resume', scale=(0.3, 0.08), position=(0, 0), color=color.azure)
        self.resume_btn.on_click = self.toggle_pause
        
        self.quit_btn = Button(parent=self.pause_menu, text='Quit', scale=(0.3, 0.08), position=(0, -0.1), color=color.red)
        self.quit_btn.on_click = application.quit

    def input(self, key):
        if key == 'escape' or key == 'p' or key == '0':
            self.toggle_pause()

    def toggle_pause(self):
        application.paused = not application.paused
        self.pause_menu.enabled = application.paused
        mouse.locked = not application.paused
        mouse.visible = application.paused


pause_handler = PauseHandler()
