from panda3d.core import loadPrcFileData, Filename
from ursina import Ursina, Entity, color, destroy, distance, window, camera, mouse, invoke
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
soldier_companion = None
scientist_npc = None
control_mode = 'player'

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
    if soldier_companion is not None and getattr(soldier_companion, 'hp', 0) > 0:
        targets.append(soldier_companion)
    return targets


def get_nearest_party_target(origin):
    if control_mode == 'archer' and archer_companion is not None and getattr(archer_companion, 'hp', 0) > 0:
        return archer_companion
    if control_mode == 'drone' and drone_companion is not None and getattr(drone_companion, 'hp', 0) > 0:
        return drone_companion
    if control_mode == 'soldier' and soldier_companion is not None and getattr(soldier_companion, 'hp', 0) > 0:
        return soldier_companion
    targets = get_active_party_targets()
    return min(targets, key=lambda target: distance(origin, target.position)) if targets else None


def dismiss_archer_companion():
    global archer_companion
    if archer_companion is not None:
        if control_mode == 'archer':
            set_control_mode('player')
        destroy(archer_companion)
        archer_companion = None


def set_control_mode(mode):
    global control_mode
    mode = mode if mode in ('player', 'archer', 'drone', 'soldier') else 'player'
    if mode == 'archer' and (archer_companion is None or getattr(archer_companion, 'hp', 0) <= 0):
        mode = 'player'
    if mode == 'drone' and (drone_companion is None or getattr(drone_companion, 'hp', 0) <= 0):
        mode = 'player'
    if mode == 'soldier' and (soldier_companion is None or getattr(soldier_companion, 'hp', 0) <= 0):
        mode = 'player'
    control_mode = mode

    target = player
    if mode == 'archer' and archer_companion is not None:
        target = archer_companion
    elif mode == 'drone' and drone_companion is not None:
        target = drone_companion
    elif mode == 'soldier' and soldier_companion is not None:
        target = soldier_companion
    if target is not None:
        camera.parent = target
        camera.position = (0, 3, -7)
        camera.rotation_x = 15
        mouse.locked = True
    return control_mode


def handle_story_interaction(actor):
    import adventure_entities as ent
    import adventure_world as world

    player_obj = globals()['player']

    if scientist_npc is not None and distance(actor.position, scientist_npc.position) < 5.0:
        if not player_obj.scientist_inspected:
            scientist_npc.dialogue_ui.text = "Scientist: I need to check this thing out. Maybe it will be useful."
            player_obj.scientist_inspected = True
            player_obj.mission_ui.text = 'Talk to the Manager'
            player_obj.mission_ui.color = color.yellow
        else:
            scientist_npc.dialogue_ui.text = "Scientist: I used that special battery to make this drone for you. It's friendly."
            player_obj.scientist_talked = True
            player_obj.drone_teammate_unlocked = True
            player_obj.mission_ui.text = 'Talk to the Manager'
            player_obj.mission_ui.color = color.cyan
            drone = spawn_drone_companion()
            drone.position = player_obj.position + (-2, 1, -2)
            drone.y = player_obj.y + 1.5
            drone.hp = drone.max_hp
            drone.health_bar.scale_x = 1.1
        scientist_npc.dialogue_ui.enabled = True
        scientist_npc.exclamation.enabled = False
        invoke(setattr, scientist_npc.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if distance(actor.position, ent.chef.position) < 5.0 and not player_obj.has_bow:
        ent.chef.dialogue_ui.enabled = True
        ent.chef.exclamation.enabled = False
        player_obj.has_bow = True
        player_obj.mission_ui.text = 'Find the Manager'
        player_obj.mission_ui.color = color.yellow
        player_obj.crosshair.enabled = True
        player_obj.bow_icon.enabled = True
        invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if distance(actor.position, ent.chef.position) < 5.0 and player_obj.level_4_cleared and not player_obj.has_grenade:
        ent.chef.dialogue_ui.text = 'Chef: Here take this shockwave grenade, press E to use it'
        ent.chef.dialogue_ui.enabled = True
        ent.chef.exclamation.enabled = False
        player_obj.has_grenade = True
        player_obj.mission_ui.text = 'Use the shockwave grenade'
        player_obj.mission_ui.color = color.yellow
        player_obj.grenade_icon.enabled = True
        invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if distance(actor.position, ent.chef.position) < 5.0 and player_obj.level_5_cleared and not player_obj.teammate_unlocked:
        ent.chef.dialogue_ui.text = 'Chef: This is my friend, the archer, he will help.'
        ent.chef.dialogue_ui.enabled = True
        ent.chef.exclamation.enabled = False
        player_obj.teammate_unlocked = True
        teammate = spawn_archer_companion()
        teammate.hp = teammate.max_hp
        teammate.health_bar.scale_x = 1.2
        teammate.position = player_obj.position + (2, 0, -2)
        player_obj.mission_ui.text = 'Talk to the Manager'
        player_obj.mission_ui.color = color.yellow
        invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if distance(actor.position, ent.chef.position) < 5.0 and player_obj.level_8_cleared and not player_obj.level_9_cleared and not player_obj.level_9_portal_open:
        ent.chef.dialogue_ui.text = 'Chef: I heard a survivor is still surviving in an area, where is he?'
        ent.chef.dialogue_ui.enabled = True
        ent.chef.exclamation.enabled = False
        player_obj.level_9_portal_open = True
        player_obj.mission_ui.text = 'Enter Level 9!'
        player_obj.mission_ui.color = color.magenta

        ent.portal_4.position = ent.chef.position + ent.chef.forward * 4
        ent.portal_4.y = 1.5
        ent.portal_4.enabled = True

        manager_exit_point = ent.portal_4.position + ent.portal_4.forward * 1.25
        ent.manager.position = ent.portal_4.position
        ent.manager.y = 1.0
        ent.manager.enabled = True
        ent.manager.dialogue_ui.text = 'Manager: HELP'
        ent.manager.dialogue_ui.enabled = True
        ent.manager.look_at_2d(ent.portal_4.position, 'y')
        ent.manager.animate_position(manager_exit_point, duration=1.1)

        def chef_followup():
            ent.chef.dialogue_ui.text = 'Chef: Where did he go? Go save him!'
            ent.chef.dialogue_ui.enabled = True
            invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)

        invoke(chef_followup, delay=2.0)
        invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=0.8)
        invoke(setattr, ent.manager, 'enabled', False, delay=1.15)
        invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if getattr(player_obj, 'level_9_cleared', False) and distance(actor.position, ent.chef.position) < 5.0:
        if not getattr(player_obj, 'soldier_spawned', False):
            ent.chef.dialogue_ui.text = 'Chef: I found another survivor. Go meet the soldier.'
            ent.chef.dialogue_ui.enabled = True
            ent.chef.exclamation.enabled = False
            player_obj.soldier_spawned = True
            player_obj.mission_ui.text = 'Talk to soldier'
            player_obj.mission_ui.color = color.yellow
            soldier = spawn_soldier_companion()
            soldier.position = player_obj.position + (3, 0, -2)
            soldier.y = player_obj.y + 0.9
            soldier.hp = soldier.max_hp
            soldier.health_bar.scale_x = 1.25
            player_obj.soldier_x = soldier.x
            player_obj.soldier_y = soldier.y
            player_obj.soldier_z = soldier.z
            invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            return True
        if not getattr(player_obj, 'soldier_teammate_unlocked', False):
            ent.chef.dialogue_ui.text = 'Chef: Talk to the soldier. He can join you.'
            ent.chef.dialogue_ui.enabled = True
            player_obj.mission_ui.text = 'Talk to soldier'
            player_obj.mission_ui.color = color.yellow
            invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
            return True

    if distance(actor.position, ent.chef.position) < 5.0:
        ent.chef.dialogue_ui.text = 'Chef: Good luck out there!'
        ent.chef.dialogue_ui.enabled = True
        invoke(setattr, ent.chef.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if getattr(player_obj, 'soldier_spawned', False) and soldier_companion is not None and distance(actor.position, soldier_companion.position) < 5.0:
        if not getattr(player_obj, 'soldier_teammate_unlocked', False):
            soldier_companion.dialogue_ui.text = 'Soldier: I am in. Press J to control me.'
            soldier_companion.dialogue_ui.enabled = True
            soldier_companion.exclamation.enabled = False
            player_obj.soldier_teammate_unlocked = True
            player_obj.mission_ui.text = 'Press J to control soldier'
            player_obj.mission_ui.color = color.cyan
            player_obj.soldier_hud_hint = True
            invoke(setattr, soldier_companion.dialogue_ui, 'enabled', False, delay=4.0)
            return True
        soldier_companion.dialogue_ui.text = 'Soldier: Press J if you want me to lead.'
        soldier_companion.dialogue_ui.enabled = True
        invoke(setattr, soldier_companion.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    if distance(actor.position, ent.manager.position) < 5.0:
        if not player_obj.has_bow:
            ent.manager.dialogue_ui.text = "Manager: Talk to the Chef first, you need a weapon!"
            ent.manager.dialogue_ui.enabled = True
            invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)
        elif not player_obj.level_3_cleared and not player_obj.level_8_cleared and not player_obj.level_9_portal_open:
            ent.manager.dialogue_ui.text = "Manager: The portal is open."
            ent.manager.dialogue_ui.enabled = True
            ent.manager.exclamation.enabled = False
            player_obj.mission_ui.text = 'Enter the portal!'
            player_obj.mission_ui.color = color.magenta

            ent.portal_2.position = ent.manager.position + ent.manager.forward * 4
            ent.portal_2.y = 1.5
            ent.portal_2.enabled = True

            invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)
        else:
            if player_obj.level_8_cleared and not player_obj.level_9_portal_open:
                player_obj.mission_ui.text = 'Talk to chef'
                player_obj.mission_ui.color = color.yellow
                player_obj.crosshair.enabled = True
                return True
            elif player_obj.drone_teammate_unlocked and not player_obj.level_8_cleared:
                ent.manager.dialogue_ui.text = "Manager: The Level 8 portal is open."
                player_obj.level_8_portal_open = True
                player_obj.level_7_portal_open = False
                player_obj.level_6_portal_open = False
                player_obj.mission_ui.text = 'Enter Level 8!'
                player_obj.mission_ui.color = color.magenta
            elif player_obj.scientist_inspected and not player_obj.level_7_cleared:
                ent.manager.dialogue_ui.text = "Manager: The Level 7 arena is open."
                player_obj.level_7_portal_open = True
                player_obj.level_6_portal_open = False
                player_obj.mission_ui.text = 'Enter Level 7!'
                player_obj.mission_ui.color = color.magenta
            elif player_obj.level_7_cleared and not player_obj.scientist_talked:
                ent.manager.dialogue_ui.text = "Manager: Talk to the scientist."
                player_obj.mission_ui.text = 'Talk to scientist'
                player_obj.mission_ui.color = color.white
                player_obj.level_7_portal_open = False
            elif player_obj.teammate_unlocked and player_obj.level_5_cleared and not player_obj.drone_teammate_unlocked:
                ent.manager.dialogue_ui.text = "Manager: Great. The Level 6 portal is open."
                player_obj.mission_ui.text = 'Enter Level 6!'
                player_obj.level_5_portal_open = False
                player_obj.level_6_portal_open = True
            else:
                ent.manager.dialogue_ui.text = "Manager: Great. The boss arena is open."
                player_obj.mission_ui.text = 'Enter the portal!'
                player_obj.level_5_portal_open = True
                player_obj.level_6_portal_open = False
            ent.manager.dialogue_ui.enabled = True
            ent.manager.exclamation.enabled = False
            world.ground_4.color = color.dark_gray
            ent.portal_4.position = ent.manager.position + ent.manager.forward * 4
            ent.portal_4.y = 1.5
            ent.portal_4.enabled = True
            player_obj.mission_ui.color = color.magenta
            invoke(setattr, ent.manager.dialogue_ui, 'enabled', False, delay=4.0)
        return True

    return False


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


def spawn_soldier_companion():
    global soldier_companion
    if soldier_companion is None:
        from adventure_entities import SoldierCompanion
        soldier_companion = SoldierCompanion()
    return soldier_companion


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
        if control_mode == 'drone':
            set_control_mode('player')
        destroy(drone_companion)
        drone_companion = None


def dismiss_soldier_companion():
    global soldier_companion
    if soldier_companion is not None:
        if control_mode == 'soldier':
            set_control_mode('player')
        destroy(soldier_companion)
        soldier_companion = None


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
