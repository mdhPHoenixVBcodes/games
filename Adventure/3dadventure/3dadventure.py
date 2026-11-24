import os
from pathlib import Path

from ursina import Entity, camera, color, destroy, invoke

player_name = input('Enter your username: ').strip() or 'Player'
os.environ['GAME_USERNAME'] = player_name

from adventure_game import player, state
from adventure_entities import *
from adventure_world import *
from adventure_state import app

APP_DIR = Path(__file__).resolve().parent
FADE_DURATION = 0.75


def create_loading_image(filename):
    image = Entity(
        parent=camera.ui,
        model='quad',
        texture=str(APP_DIR / filename),
        scale=(camera.aspect_ratio * 2, 2),
        color=color.rgba(255, 255, 255, 0),
        transparency=True,
    )
    image.animate_color(color.white, duration=FADE_DURATION)
    return image


def fade_out_loading_image(image):
    image.animate_color(color.rgba(255, 255, 255, 0), duration=FADE_DURATION)
    destroy(image, delay=FADE_DURATION)


def show_loading_sequence():
    first_image = create_loading_image('loading1.png')

    def show_second_image():
        second_image = create_loading_image('loading2.png')
        fade_out_loading_image(first_image)
        invoke(fade_out_loading_image, second_image, delay=3)

    invoke(show_second_image, delay=3)


show_loading_sequence()
app.run()
