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
import gltf._converter

game = Ursina()
sky = Sky(color=color.rgb(185/255, 207/255, 220/255))
player = ursina.prefabs.first_person_controller.FirstPersonController()

# ==============================================================================
# --- 1. INTERNAL SERVER LOGIC (Runs inside a background thread if hosting)

def patched_get_next_time_index(currtime: float, time_buffer: list[float]) -> int:
    nextidx = 1
    if nextidx >= len(time_buffer): return len(time_buffer) - 1
    nexttime = time_buffer[nextidx]
    while currtime > nexttime:
        nextidx += 1
        if nextidx >= len(time_buffer): return len(time_buffer) - 1
        nexttime = time_buffer[nextidx]
    return nextidx

gltf._converter.get_next_time_index = patched_get_next_time_index

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
    if key == 'r':
        gun_actor.play('reload')
    if key == 'z':
        player.position = (0, 5, 0)


if player.y > -10:
    player.position = (0, 5, 0)

env = Entity(model='cube', position=(0, 0, 0), scale=(100, 1, 100), color=color.green, collider='box')

from direct.actor.Actor import Actor
from ursina import *
# 1. Create a standard Ursina Entity attached to the camera
# This gives the weapon full shaders, lighting, and coordinate systems!
gun_holder = Entity(parent=camera)
# 2. Load the animated GLB model as a raw Actor and reparent it to our Entity
gun_actor = Actor('gun.glb')
gun_actor.reparent_to(gun_holder)
# 3. Position the gun relative to the camera using Ursina coordinates:
# X = right (+0.5), Y = down (-0.4), Z = forward (+0.8)
gun_holder.position = (0.5, 1, 5)
# 4. Scale it UP (10x) so it becomes a realistic 1.25-meter visual size!
gun_holder.scale = 10.0
# 5. Rotate it slightly to point forward if needed (Blender to Ursina rotation offset)
gun_holder.rotation = (0, 0, 0)  # You can adjust this if it points the wrong way!
# 6. Play the reload animation anytime!
gun_actor.play('reload')

game.run()