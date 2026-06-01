import socket
import threading
import json
import os
import time
import math
import ursina
import ursina.prefabs.first_person_controller
import random
from ursina import *

game = Ursina()
sky = Sky(color=color.rgb(185/255, 207/255, 220/255))
player = ursina.prefabs.first_person_controller.FirstPersonController()

# ==============================================================================
# --- 1. INTERNAL SERVER LOGIC (Runs inside a background thread if hosting) ---
class Server:
    def __init__(self, host='localhost', port=5050):
        self.host = host
        self.port = port
        self.clients = []
        self.running = False
        self.server_socket = None

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server started on {self.host}:{self.port}")
        threading.Thread(target=self.accept_clients).start()

    def accept_clients(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            print(f"Client connected from {addr}")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                # Handle incoming data from clients here (e.g., update game state)
            except ConnectionResetError:
                break
        print("Client disconnected")
        client_socket.close()
        self.clients.remove(client_socket)

    def stop(self):
        self.running = False
        for client in self.clients:
            client.close()
        if self.server_socket:
            self.server_socket.close()

# ==============================================================================
# --- 2. GAME LOGIC (Runs in the main thread) ---

def shoot():
    bullet = Entity(model='sphere', color=color.black, scale=0.05, position=player.position + player.forward * 1.5, collider='box')
    bullet.velocity = player.forward * 50

    def update():
        bullet.position += bullet.velocity * time.dt
        if bullet.position.y < -10:
            destroy(bullet)
    bullet.update = update

def ads():
    player.camera = (0, 10, 0)
    player.camera_pivot = (0, 0, 0)

def input(key):
    if key == 'escape':
        mouse.locked = not mouse.locked
    if key == 'left mouse down':
        shoot()
    if key == 'right mouse down':
        ads()
    

if player.y > -10:
    player.position = (0, 1, 0)

player = Entity(model='cube', color=color.white, scale=(1, 2, 1), position=(0, 1, 0), collider='box')
env = Entity(model='cube', position=(0, 0, 0), scale=(100, 1, 100), color=color.green, collider='box')

game.run()