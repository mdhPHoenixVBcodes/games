import socket
import threading
import json
import time

# Constants for Networking
PORT = 8080
DISCOVERY_PORT = 8081
BUFFER_SIZE = 4096

class NetworkManager:
    """Base class for handling socket communication."""
    def __init__(self):
        self.socket = None
        self.running = False
        self.messages = [] # Queue of received messages

    def send_json(self, conn, data):
        try:
            msg = json.dumps(data).encode('utf-8')
            conn.sendall(msg + b'|END|') # Delimiter for message parsing
        except:
            return False
        return True

class GameServer(NetworkManager):
    def __init__(self, world_name):
        super().__init__()
        self.world_name = world_name
        self.clients = {} # conn -> player_id
        self.player_data = {} # id -> data
        self.world_ref = None

    def send(self, data):
        """Unified send method for both Client and Server."""
        self.broadcast(data)

    def start(self, world):
        self.world_ref = world
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind(('', PORT))
            self.socket.listen(5)
            self.running = True
            threading.Thread(target=self.accept_clients, daemon=True).start()
            print(f"[SERVER] Started on port {PORT}")
            return True
        except Exception as e:
            print(f"[SERVER] Error: {e}")
            return False

    def accept_clients(self):
        while self.running:
            try:
                conn, addr = self.socket.accept()
                client_id = f"player_{int(time.time() * 1000)}"
                print(f"[SERVER] New connection from {addr} (ID: {client_id})")
                
                # Send initial world data
                initial_sync = {
                    "type": "INIT",
                    "id": client_id,
                    "world_data": {f"{k[0]},{k[1]}": v for k, v in self.world_ref.data.items()},
                    "time": self.world_ref.time
                }
                self.send_json(conn, initial_sync)
                
                self.clients[conn] = client_id
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except:
                break

    def handle_client(self, conn):
        client_id = self.clients[conn]
        buffer = b""
        while self.running:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data: break
                
                buffer += data
                while b'|END|' in buffer:
                    msg_raw, buffer = buffer.split(b'|END|', 1)
                    try:
                        msg = json.loads(msg_raw.decode('utf-8'))
                        self.process_message(client_id, msg, conn) # Pass conn to exclude it
                    except Exception as e:
                        print(f"[SERVER] Packet error: {e}")
                        continue
            except:
                break
        
        print(f"[SERVER] Client {client_id} disconnected")
        del self.clients[conn]
        if client_id in self.player_data:
            del self.player_data[client_id]
        self.broadcast({"type": "QUIT", "id": client_id})
        conn.close()

    def process_message(self, client_id, msg, sender_conn):
        msg["id"] = client_id 
        if msg["type"] == "POS":
            self.player_data[client_id] = msg
        elif msg["type"] == "BLOCK":
            pos = tuple(map(int, msg["pos"].split(',')))
            if msg["b_type"] is None:
                if pos in self.world_ref.data: del self.world_ref.data[pos]
            else:
                self.world_ref.data[pos] = msg["b_type"]
        
        # Relay to all OTHER clients
        self.broadcast(msg, exclude_conn=sender_conn)

    def broadcast(self, data, exclude_conn=None):
        for conn in list(self.clients.keys()):
            if conn != exclude_conn:
                self.send_json(conn, data)

class GameClient(NetworkManager):
    def __init__(self):
        super().__init__()
        self.client_id = None
        self.conn = None

    def connect(self, ip):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect((ip, PORT))
            self.running = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False

    def receive_loop(self):
        buffer = b""
        while self.running:
            try:
                data = self.conn.recv(BUFFER_SIZE)
                if not data: break
                
                buffer += data
                while b'|END|' in buffer:
                    msg_raw, buffer = buffer.split(b'|END|', 1)
                    try:
                        msg = json.loads(msg_raw.decode('utf-8'))
                        if msg["type"] == "INIT":
                            self.client_id = msg["id"]
                        self.messages.append(msg)
                    except:
                        continue
            except:
                break
        self.running = False

    def send(self, data):
        if self.running:
            return self.send_json(self.conn, data)
        return False
