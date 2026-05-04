from ursina import *
from pathlib import Path
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


class Cannon(Entity):
    def __init__(self, position):
        super().__init__(model='cube', color=color.red, scale=(2, 2, 2), position=position, collider='box')
        self.hp = 50
        self.shoot_timer = random.uniform(3.0, 5.0)

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
            target = state.get_nearest_party_target(self.position)
            sphere = CannonSphere(self.position + (0, 1, 0), target=target)
            state.cannon_spheres.append(sphere)
            self.shoot_timer = random.uniform(3.0, 5.0)


class CannonSphere(Entity):
    def __init__(self, position, target=None):
        self.target = target or state.player
        super().__init__(model='sphere', color=color.orange, scale=2.5, position=position)
        self.speed = 10
        self.look_at_2d(self.target, 'y')
        self.lifetime = 8.0

    def take_damage(self, amount):
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

        self.position += self.forward * self.speed * time.dt

        for target in state.get_active_party_targets():
            if distance(self.position, target.position) < 2.5:
                target.take_damage(15)
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
    def __init__(self, position, rotation=None, direction=None, hit_party=False, hit_enemies=True, hit_cannons=True, hit_spheres=True):
        super().__init__(model='cube', color=color.white, scale=(0.05, 0.05, 1.5), position=position, rotation=rotation or (0, 0, 0))
        self.speed = 60
        self.damage = 10
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
        self.health_bar = Entity(parent=self, y=1.1, model='cube', color=color.green, scale=(1.2, 0.12, 0.12))
        self.bow = Entity(parent=self, model='cube', color=color.brown, scale=(0.12, 0.8, 0.12), position=(0.55, 0.05, 0.25), rotation=(0, 0, 25))

    def take_damage(self, amount):
        self.hp -= amount
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.2
        self.color = color.white
        invoke(setattr, self, 'color', color.azure, delay=0.1)
        if self.hp <= 0:
            state.dismiss_archer_companion()

    def update(self):
        if state.player.is_teleporting:
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

        ray = raycast(self.position + (0, 2, 0), direction=(0, -1, 0), ignore=(self,), distance=4)
        if ray.hit:
            self.y = ray.world_point[1] + (self.scale_y / 2)

        if self.attack_cooldown <= 0 and len(state.enemies) > 0:
            target = min(state.enemies, key=lambda enemy: distance(self.position, enemy.position))
            if distance(self.position, target.position) <= self.attack_range:
                self.look_at(target.position + (0, 0.5, 0))
                Arrow(position=self.position + self.forward * 1.3 + (0, 1.0, 0), rotation=self.rotation, direction=self.forward, hit_party=True, hit_enemies=False, hit_cannons=False, hit_spheres=False)
                self.attack_cooldown = 0.9


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
            color=color.gray,
            scale=1.2,
            position=spawn_pos,
            collider='box'
        )
        self.target = target
        self.speed = 9.0
        self.max_hp = 120
        self.hp = self.max_hp
        self.attack_range = 22
        self.attack_damage = 12
        self.attack_cooldown = 0
        self.health_bar = Entity(parent=self, y=0.9, model='cube', color=color.green, scale=(1.1, 0.1, 0.1))

    def take_damage(self, amount):
        self.hp -= amount
        DamageMarker(amount, self.world_position + (0, 1, 0))
        self.health_bar.scale_x = max(self.hp / self.max_hp, 0) * 1.1
        self.color = color.white
        invoke(setattr, self, 'color', color.red, delay=0.1)
        if self.hp <= 0:
            if self in state.enemies:
                state.enemies.remove(self)
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
            self.look_at(target.position + (0, 0.5, 0))
            Arrow(position=self.position + self.forward * 1.2 + (0, 0.9, 0), rotation=self.rotation, direction=self.forward)
            self.attack_cooldown = 1.1


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


black_screen = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0), scale=(3, 3), z=-10)
controls_ui = Text(text='8 - Save\n9 - Load\n0 - Pause\nE - Shockwave', position=(-0.82, -0.35), scale=2.5, color=color.white, background=True)


class DamageMarker(Text):
    def __init__(self, amount, position):
        super().__init__(
            text=str(int(amount)),
            position=position,
            scale=1.5,
            color=color.red,
            origin=(0, 0),
            billboard=True,
            background=True
        )
        self.animate_y(self.y + 2, duration=0.6)
        self.animate_color(color.clear, duration=0.5, delay=0.1)
        destroy(self, delay=0.7)


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
