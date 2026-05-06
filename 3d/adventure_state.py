from panda3d.core import loadPrcFileData, Filename
from ursina import Ursina, Entity, color, destroy, distance, window
from pathlib import Path
import os

APP_DIR = Path(__file__).resolve().parent
APP_ICON = Filename.fromOsSpecific(str(APP_DIR / 'Logo' / 'logo.ico'))
loadPrcFileData('', f'icon-filename {APP_ICON}')

app = Ursina(title='3D Adventure', icon=APP_ICON)
window.title = '3D Adventure'
SAVE_FILE = Path(__file__).with_name('savegame.json')
player_name = os.getenv('GAME_USERNAME', 'Player')

player = None
archer_companion = None
drone_companion = None
scientist_npc = None

enemies = []
cannons = []
cannon_spheres = []
level_6_pillars = []
level_6_sphere_drop = None


def get_active_party_targets():
    targets = [player]
    if archer_companion is not None and getattr(archer_companion, 'hp', 0) > 0:
        targets.append(archer_companion)
    if drone_companion is not None and getattr(drone_companion, 'hp', 0) > 0:
        targets.append(drone_companion)
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
        from adventure_entities import ArcherCompanion
        archer_companion = ArcherCompanion()
    return archer_companion


def spawn_drone_companion():
    global drone_companion
    if drone_companion is None:
        from adventure_entities import DroneCompanion
        drone_companion = DroneCompanion()
    return drone_companion


def spawn_scientist():
    global scientist_npc
    if scientist_npc is None:
        from adventure_entities import Scientist
        scientist_npc = Scientist()
    return scientist_npc


def dismiss_scientist():
    global scientist_npc
    if scientist_npc is not None:
        destroy(scientist_npc)
        scientist_npc = None


def dismiss_drone_companion():
    global drone_companion
    if drone_companion is not None:
        destroy(drone_companion)
        drone_companion = None


def clear_level_6_pillars():
    global level_6_pillars
    for pillar in level_6_pillars:
        destroy(pillar)
    level_6_pillars.clear()


def clear_level_6_sphere_drop():
    global level_6_sphere_drop
    if level_6_sphere_drop is not None:
        destroy(level_6_sphere_drop)
        level_6_sphere_drop = None


def spawn_level_6_sphere_enemy(position):
    from adventure_entities import SphereEnemy

    burst = Entity(
        model='sphere',
        color=color.rgba(255, 235, 120, 180),
        position=position,
        scale=0.5
    )
    burst.animate_scale(4, duration=0.18)
    burst.animate_color(color.rgba(255, 235, 120, 0), duration=0.18)
    destroy(burst, delay=0.22)

    sphere_enemy = SphereEnemy(target=player, spawn_pos=position)
    enemies.append(sphere_enemy)
    return sphere_enemy


def spawn_level_6_sphere_drop(position):
    global level_6_sphere_drop
    from adventure_entities import SphereDrop

    if level_6_sphere_drop is not None:
        return level_6_sphere_drop

    level_6_sphere_drop = SphereDrop(position=position)
    if player is not None:
        player.level_6_drop_spawned = True
        player.level_6_drop_x = position[0]
        player.level_6_drop_y = position[1]
        player.level_6_drop_z = position[2]
    return level_6_sphere_drop


def resolve_level_6_pillar_collision(entity, previous_position):
    if not level_6_pillars:
        return
    for pillar in level_6_pillars:
        if pillar.enabled and entity.intersects(pillar).hit:
            entity.position = previous_position
            if hasattr(pillar, 'touch_cooldown') and pillar.touch_cooldown <= 0 and entity is player:
                spawn_level_6_sphere_enemy(pillar.position + (0, 1.5, 0))
                pillar.touch_cooldown = 0.75
            return
