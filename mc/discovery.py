import socket
import threading
import time

DISCOVERY_PORT = 8081
MAGIC_WORD = "MC2D_DISCOVERY"

class DiscoveryBroadcaster:
    """Background thread that broadcasts the world name via UDP."""
    def __init__(self, world_name):
        self.world_name = world_name
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = f"{MAGIC_WORD}|{self.world_name}".encode('utf-8')
        print(f"[DISCOVERY] Broadcasting world: {self.world_name}")
        
        while self.running:
            try:
                # Send to common broadcast addresses
                sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
                sock.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
            except:
                pass
            time.sleep(2)
        sock.close()

class DiscoveryListener:
    """Utility to find a host on the local network by world name."""
    @staticmethod
    def find_host(target_name, timeout=5, screen=None, font=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', DISCOVERY_PORT))
        sock.settimeout(0.5)
        
        print(f"[DISCOVERY] Searching for world: {target_name}...")
        start_time = time.time()
        
        import pygame
        while time.time() - start_time < timeout:
            # Prevent "Not Responding"
            pygame.event.pump()
            if screen and font:
                screen.fill((15, 15, 30))
                txt = font.render(f"Searching for World: {target_name}...", True, (255, 255, 255))
                screen.blit(txt, (400 - txt.get_width()//2, 300))
                pygame.display.flip()

            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode('utf-8')
                if msg.startswith(MAGIC_WORD):
                    _, world_name = msg.split('|', 1)
                    if world_name.strip() == target_name.strip():
                        print(f"[DISCOVERY] Found host {addr[0]} for world {world_name}")
                        sock.close()
                        return addr[0]
            except (socket.timeout, socket.error):
                continue
            except Exception as e:
                print(f"[DISCOVERY] Error: {e}")
                break
        
        sock.close()
        return None
