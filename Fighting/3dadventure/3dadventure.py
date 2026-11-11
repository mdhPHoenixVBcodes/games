import os

player_name = input('Enter your username: ').strip() or 'Player'
os.environ['GAME_USERNAME'] = player_name

from adventure_game import player, state
from adventure_entities import *
from adventure_world import *
from adventure_state import app

app.run()
