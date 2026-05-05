import socket
import threading
import json
import time

# Constants for Networking
PORT = 25565
DISCOVERY_PORT = 25566
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
        data["id"] = "host"
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
                # Just wait for the client to send a JOIN packet with their persistent ID
                print(f"[SERVER] New connection from {addr}, waiting for JOIN packet...")
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except:
                break

    def handle_client(self, conn):
        buffer = b""
        client_id = None
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
        if msg["type"] == "JOIN":
            p_id = msg["p_id"]
            print(f"[SERVER] Player {p_id} joined from {sender_conn.getpeername()}")
            self.clients[sender_conn] = p_id
            self.player_data[p_id] = msg.get("player_data", {})
            
            # Now send the INIT packet with their specific data
            p_save = self.world_ref.remote_players_data.get(p_id)
            if not p_save:
                p_save = msg.get("player_data", {})
                self.world_ref.remote_players_data[p_id] = p_save # Save it immediately
            init_msg = {
                "type": "INIT",
                "id": p_id,
                "world_data": {f"{k[0]},{k[1]}": v for k, v in self.world_ref.data.items()},
                "block_meta": {f"{k[0]},{k[1]}": v for k, v in self.world_ref.block_meta.items()},
                "time": self.world_ref.time,
                "player_data": p_save # Send back their saved inventory/pos
            }
            self.send_json(sender_conn, init_msg)
            return

        msg["id"] = client_id 
        if msg["type"] in ("POS", "SYNC"):
            if client_id not in self.player_data:
                self.player_data[client_id] = {}
            self.player_data[client_id].update(msg)
        elif msg["type"] == "BLOCK":
            pos = tuple(map(int, msg["pos"].split(',')))
            if msg["b_type"] is None:
                if pos in self.world_ref.data: del self.world_ref.data[pos]
                if pos in self.world_ref.block_meta: del self.world_ref.block_meta[pos]
            else:
                self.world_ref.data[pos] = msg["b_type"]
                if "meta" in msg and msg["meta"]:
                    self.world_ref.block_meta[pos] = msg["meta"]
        
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
            self.conn.settimeout(10.0) # 10 second timeout for connecting
            self.conn.connect((ip, PORT))
            self.conn.settimeout(None) # Back to blocking for threads
            self.running = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed to {ip}:{PORT} - Error: {e}")
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
