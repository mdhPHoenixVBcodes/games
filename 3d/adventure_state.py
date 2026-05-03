from ursina import Ursina, Entity, color, destroy, distance
from pathlib import Path

app = Ursina()
SAVE_FILE = Path(__file__).with_name('savegame.json')

player = None
archer_companion = None

enemies = []
cannons = []
cannon_spheres = []
level_6_pillars = []


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
        from adventure_entities import ArcherCompanion
        archer_companion = ArcherCompanion()
    return archer_companion


def clear_level_6_pillars():
    global level_6_pillars
    for pillar in level_6_pillars:
        destroy(pillar)
    level_6_pillars.clear()


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
