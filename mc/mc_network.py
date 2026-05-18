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
        except Exception as e:
            print(f"[NET] Send failed: {e}")
            return False
        return True

class GameServer(NetworkManager):
    def __init__(self, world_name):
        super().__init__()
        self.world_name = world_name
        self.clients = {} # conn -> player_id
        self.player_data = {} # id -> data
        self.world_ref = None
        self.pending_world_updates = []
        self.pending_world_updates_lock = threading.Lock()

    def _extract_player_snapshot(self, msg):
        return {
            k: v for k, v in msg.items()
            if k not in ("type", "id")
        }

    def send(self, data):
        """Unified send method for both Client and Server."""
        data["id"] = "host"
        self.broadcast(data)
        return True

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
            except OSError as e:
                if self.running:
                    print(f"[SERVER] Accept loop stopped: {e}")
                break
            except Exception as e:
                print(f"[SERVER] Accept error: {e}")
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
                        new_client_id = self.process_message(client_id, msg, conn) # Pass conn to exclude it
                        if new_client_id is not None:
                            client_id = new_client_id
                    except Exception as e:
                        print(f"[SERVER] Packet error: {e}")
                        continue
            except Exception as e:
                print(f"[SERVER] Client loop error: {e}")
                break
        
        print(f"[SERVER] Client {client_id} disconnected")
        if conn in self.clients:
            del self.clients[conn]
        if client_id in self.player_data:
            del self.player_data[client_id]
        if self.world_ref is not None and client_id in self.world_ref.remote_players_data:
            del self.world_ref.remote_players_data[client_id]
        self.broadcast({"type": "QUIT", "id": client_id})
        try:
            conn.close()
        except Exception:
            pass

    def process_message(self, client_id, msg, sender_conn):
        msg_type = msg.get("type")
        if msg_type == "JOIN":
            p_id = msg["p_id"]
            print(f"[SERVER] Player {p_id} joined from {sender_conn.getpeername()}")
            self.clients[sender_conn] = p_id
            self.player_data[p_id] = msg.get("player_data", {})
            if "name" not in self.player_data[p_id]:
                self.player_data[p_id]["name"] = msg.get("name", p_id)
            
            # Now send the INIT packet with their specific data
            p_save = self.world_ref.remote_players_data.get(p_id)
            if not p_save:
                p_save = msg.get("player_data", {})
            self.world_ref.remote_players_data[p_id] = p_save.copy() if isinstance(p_save, dict) else p_save
            if isinstance(self.world_ref.remote_players_data[p_id], dict) and "name" not in self.world_ref.remote_players_data[p_id]:
                self.world_ref.remote_players_data[p_id]["name"] = msg.get("name", p_id)
            init_msg = {
                "type": "INIT",
                "id": p_id,
                "world_data": {f"{pos[0]},{pos[1]}": b_type for chunk in self.world_ref.chunks.values() for pos, b_type in chunk.items()},
                "block_meta": {f"{k[0]},{k[1]}": v for k, v in self.world_ref.block_meta.items()},
                "time": self.world_ref.time,
                "player_data": p_save # Send back their saved inventory/pos
            }
            self.send_json(sender_conn, init_msg)
            return p_id

        msg["id"] = client_id 
        if msg_type in ("POS", "SYNC"):
            if client_id not in self.player_data:
                self.player_data[client_id] = {}
            self.player_data[client_id].update(msg)
            if "name" in msg:
                self.player_data[client_id]["name"] = msg["name"]
            if self.world_ref is not None:
                snapshot = self._extract_player_snapshot(msg)
                if snapshot:
                    self.world_ref.remote_players_data[client_id] = snapshot
        elif msg_type == "BLOCK":
            with self.pending_world_updates_lock:
                self.pending_world_updates.append(msg.copy())
        elif msg_type == "CHAT":
            print(f"[CHAT] {msg.get('name', client_id)}: {msg.get('text', '')}")
        
        # Relay to all OTHER clients
        self.broadcast(msg, exclude_conn=sender_conn)
        return client_id

    def broadcast(self, data, exclude_conn=None):
        for conn in list(self.clients.keys()):
            if conn != exclude_conn:
                if not self.send_json(conn, data):
                    try:
                        conn.close()
                    except Exception:
                        pass
                    if conn in self.clients:
                        del self.clients[conn]

    def drain_world_updates(self):
        if not self.pending_world_updates or self.world_ref is None:
            return

        with self.pending_world_updates_lock:
            updates = self.pending_world_updates[:]
            self.pending_world_updates.clear()
        for msg in updates:
            pos = tuple(map(int, msg["pos"].split(',')))
            if msg["b_type"] is None:
                if pos in self.world_ref.data:
                    del self.world_ref.data[pos]
                if pos in self.world_ref.block_meta:
                    del self.world_ref.block_meta[pos]
            else:
                self.world_ref.data[pos] = msg["b_type"]
                if "meta" in msg and msg["meta"]:
                    self.world_ref.block_meta[pos] = msg["meta"]

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
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
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
                    except Exception as e:
                        print(f"[CLIENT] Packet error: {e}")
                        continue
            except Exception as e:
                print(f"[CLIENT] Receive loop error: {e}")
                break
        self.running = False
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = None

    def send(self, data):
        if self.running:
            return self.send_json(self.conn, data)
        return False
