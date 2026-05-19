const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const joinBtn = document.getElementById("join");
const nameInput = document.getElementById("name");

const TILE = 32;
const PLAYER_W = 24;
const PLAYER_H = 64;

const BLOCKS = {
  1: { name: "Grass", color: "#6dbb4f" },
  2: { name: "Dirt", color: "#8a5a36" },
  3: { name: "Stone", color: "#8f96a6" },
  4: { name: "Coal", color: "#333333" },
  5: { name: "Iron", color: "#d8c0aa" },
  6: { name: "Planks", color: "#c49a6c" },
  7: { name: "Wood", color: "#8f6a43" },
  8: { name: "Brick", color: "#b66a5a" },
  9: { name: "Sand", color: "#d8cb9f" }
};

const state = {
  clientId: null,
  me: { x: 140, y: 220, vx: 0, vy: 0, name: "Player", onGround: false },
  players: [],
  keys: new Set(),
  joined: false,
  world: { width: 2048, height: 128, tileSize: TILE, chunkSize: 16, chunks: {}, blocks: {} },
  lastSend: 0,
  lastWorldSync: 0,
  cameraX: 0,
  cameraY: 0,
  selectedBlock: 2,
  miningMode: 0,
  mouse: { x: 0, y: 0, downLeft: false, downRight: false },
  gamepad: {
    connected: false,
    prevButtons: [],
    prevLeftTrigger: false,
    prevRightTrigger: false
  }
};

const MINING_MODES = [
  "Front",
  "Head",
  "Down",
  "Up",
  "Both"
];

function setStatus(text) {
  statusEl.textContent = text;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

async function api(path, method = "GET", body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

function blockAt(tx, ty) {
  const chunkSize = state.world.chunkSize || 16;
  const cx = Math.floor(tx / chunkSize);
  const cy = Math.floor(ty / chunkSize);
  const chunk = state.world.chunks?.[`${cx},${cy}`];
  if (chunk && Object.prototype.hasOwnProperty.call(chunk, `${tx},${ty}`)) {
    return chunk[`${tx},${ty}`];
  }
  return state.world.blocks[`${tx},${ty}`] ?? null;
}

function mergeChunkSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return;
  }
  if (snapshot.chunkSize) {
    state.world.chunkSize = snapshot.chunkSize;
  }
  if (snapshot.width) {
    state.world.width = snapshot.width;
  }
  if (snapshot.height) {
    state.world.height = snapshot.height;
  }
  if (!state.world.chunks) {
    state.world.chunks = {};
  }
  if (snapshot.chunks && typeof snapshot.chunks === "object") {
    for (const [chunkKey, chunkBlocks] of Object.entries(snapshot.chunks)) {
      state.world.chunks[chunkKey] = { ...chunkBlocks };
    }
  }
  if (snapshot.blocks && typeof snapshot.blocks === "object") {
    state.world.blocks = { ...snapshot.blocks };
  } else if (snapshot.chunks && typeof snapshot.chunks === "object") {
    const flat = {};
    for (const chunkBlocks of Object.values(state.world.chunks)) {
      Object.assign(flat, chunkBlocks);
    }
    state.world.blocks = flat;
  }
}

function pruneChunksAroundPlayer(radiusChunks = 4) {
  if (!state.world.chunks) return;
  const chunkSize = state.world.chunkSize || 16;
  const centerTx = Math.floor((state.me.x + PLAYER_W / 2) / TILE);
  const centerTy = Math.floor((state.me.y + PLAYER_H / 2) / TILE);
  const centerCx = Math.floor(centerTx / chunkSize);
  const centerCy = Math.floor(centerTy / chunkSize);

  for (const key of Object.keys(state.world.chunks)) {
    const [cx, cy] = key.split(",").map(Number);
    if (Math.abs(cx - centerCx) > radiusChunks || Math.abs(cy - centerCy) > radiusChunks) {
      delete state.world.chunks[key];
    }
  }

  for (const key of Object.keys(state.world.blocks)) {
    const [tx, ty] = key.split(",").map(Number);
    const cx = Math.floor(tx / chunkSize);
    const cy = Math.floor(ty / chunkSize);
    if (Math.abs(cx - centerCx) > radiusChunks || Math.abs(cy - centerCy) > radiusChunks) {
      delete state.world.blocks[key];
    }
  }
}

function frontTileForPlayer() {
  const facingRight = state.me.facingRight !== false;
  const tx = facingRight
    ? Math.floor((state.me.x + PLAYER_W - 1) / TILE) + 1
    : Math.floor(state.me.x / TILE) - 1;
  const ty = Math.floor((state.me.y + PLAYER_H - 1) / TILE);
  return { x: tx, y: ty };
}

function playerColumnTileX() {
  return Math.floor((state.me.x + PLAYER_W / 2) / TILE);
}

function getMiningTargets() {
  const front = frontTileForPlayer();
  const centerX = playerColumnTileX();
  const headY = Math.floor((state.me.y + 8) / TILE);
  const footY = Math.floor((state.me.y + PLAYER_H - 1) / TILE);
  switch (state.miningMode) {
    case 1:
      return [{ x: front.x, y: headY }];
    case 2:
      return [{ x: centerX, y: footY + 1 }];
    case 3:
      return [{ x: centerX, y: headY - 1 }];
    case 4:
      return [
        { x: front.x, y: footY },
        { x: front.x, y: headY }
      ];
    case 0:
    default:
      return [front];
  }
}

function tileFromScreen(px, py) {
  return {
    x: Math.floor((px + state.cameraX) / TILE),
    y: Math.floor((py + state.cameraY) / TILE)
  };
}

function getMoveIntent() {
  const intent = { left: false, right: false, jump: false, crouch: false, sprint: false };
  if (state.keys.has("ArrowLeft") || state.keys.has("a")) intent.left = true;
  if (state.keys.has("ArrowRight") || state.keys.has("d")) intent.right = true;
  if (state.keys.has("ArrowUp") || state.keys.has("w") || state.keys.has(" ")) intent.jump = true;
  if (state.keys.has("Shift")) intent.crouch = true;
  if (state.keys.has("Control")) intent.sprint = true;

  const pad = navigator.getGamepads ? navigator.getGamepads()[0] : null;
  if (pad) {
    state.gamepad.connected = true;
    const ax = pad.axes[0] || 0;
    const ay = pad.axes[1] || 0;
    if (ax < -0.25) intent.left = true;
    if (ax > 0.25) intent.right = true;
    if (ay < -0.35) intent.jump = true;
    if (pad.buttons[0] && pad.buttons[0].pressed) intent.jump = true;
    if (pad.buttons[1] && pad.buttons[1].pressed) intent.crouch = true;
    if (pad.buttons[10] && pad.buttons[10].pressed) intent.sprint = true;
  } else {
    state.gamepad.connected = false;
  }

  return intent;
}

function getGamepadEdgeState() {
  const pad = navigator.getGamepads ? navigator.getGamepads()[0] : null;
  const result = {
    breakPressed: false,
    placePressed: false,
    prevBlockPressed: false,
    nextBlockPressed: false,
    unlockPressed: false,
    modeNextPressed: false
  };

  if (!pad) {
    state.gamepad.connected = false;
    state.gamepad.prevButtons = [];
    state.gamepad.prevLeftTrigger = false;
    state.gamepad.prevRightTrigger = false;
    return result;
  }

  state.gamepad.connected = true;
  const prev = state.gamepad.prevButtons;
  const buttons = pad.buttons || [];

  const isPressed = (index) => !!(buttons[index] && (buttons[index].pressed || buttons[index].value > 0.5));
  const justPressed = (index) => isPressed(index) && !prev[index];

  result.jumpPressed = justPressed(0);
  const ltPressed = !!(buttons[6] && buttons[6].value > 0.5);
  const rtPressed = !!(buttons[7] && buttons[7].value > 0.5);
  result.placePressed = ltPressed && !state.gamepad.prevLeftTrigger;
  result.breakPressed = rtPressed && !state.gamepad.prevRightTrigger;
  result.prevBlockPressed = justPressed(4);
  result.nextBlockPressed = justPressed(5);
  result.unlockPressed = justPressed(11);
  result.modeNextPressed = justPressed(2);

  state.gamepad.prevButtons = buttons.map((btn) => !!btn.pressed);
  state.gamepad.prevLeftTrigger = ltPressed;
  state.gamepad.prevRightTrigger = rtPressed;
  return result;
}

function drawBackground() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const sky = ctx.createLinearGradient(0, 0, 0, canvas.height * 0.6);
  sky.addColorStop(0, "#79c9ff");
  sky.addColorStop(1, "#d9f1ff");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function drawBlock(tx, ty, type) {
  const x = tx * TILE - state.cameraX;
  const y = ty * TILE - state.cameraY;
  const block = BLOCKS[type] || BLOCKS[2];
  ctx.fillStyle = block.color;
  ctx.fillRect(x, y, TILE, TILE);
}

function drawWorld() {
  const startX = clamp(Math.floor(state.cameraX / TILE) - 1, 0, state.world.width - 1);
  const endX = clamp(Math.ceil((state.cameraX + canvas.width) / TILE) + 1, 0, state.world.width - 1);
  const startY = clamp(Math.floor(state.cameraY / TILE) - 1, 0, state.world.height - 1);
  const endY = clamp(Math.ceil((state.cameraY + canvas.height) / TILE) + 1, 0, state.world.height - 1);

  for (let y = startY; y <= endY; y++) {
    for (let x = startX; x <= endX; x++) {
      const type = blockAt(x, y);
      if (type != null) {
        drawBlock(x, y, type);
      }
    }
  }
}

function drawPlayer(p, isLocal) {
  const x = Math.round(p.x - state.cameraX);
  const y = Math.round(p.y - state.cameraY);
  ctx.fillStyle = getPlayerColor(p, isLocal);
  ctx.fillRect(x, y, PLAYER_W, PLAYER_H);
  ctx.fillStyle = "#102030";
  ctx.fillRect(x + (p.facingRight ? 16 : 4), y + 10, 4, 4);
  ctx.fillRect(x + (p.facingRight ? 4 : 16), y + 10, 4, 4);
  ctx.fillStyle = "#ffffff";
  ctx.font = "14px Arial";
  ctx.textAlign = "center";
  ctx.fillText(p.name || "Player", x + PLAYER_W / 2, y - 6);
}

function getPlayerColor(p, isLocal) {
  return p.color || colorFromName(p.name) || (isLocal ? "#ffcf5a" : "#2b6cff");
}

function drawHud() {
  ctx.textAlign = "left";
  ctx.font = "14px Arial";
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(10, 10, 360, 110);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(`Block: ${BLOCKS[state.selectedBlock]?.name || "Dirt"}`, 20, 30);
  ctx.fillText(`Mode: ${MINING_MODES[state.miningMode]}`, 20, 44);
  ctx.fillText("Move: A/D or arrows", 20, 58);
  ctx.fillText("Jump: W / Space / Up / A", 20, 72);
  ctx.fillText("Crouch: Shift / B", 20, 86);
  ctx.fillText("Sprint: Ctrl / L-stick click", 20, 100);
  ctx.fillText("Break: left click / RT", 20, 114);
  ctx.fillText("Place: right click / LT", 20, 128);
  ctx.fillText("Mine mode: F / Xbox X", 20, 142);
  ctx.fillText("Change: 1-9, wheel, LB/RB", 20, 156);
  ctx.fillText("Click world: lock mouse, Esc: unlock", 20, 170);

  if (!state.me.onGround) {
    ctx.fillText("Airborne", canvas.width - 100, 35);
  }
  if (state.gamepad.connected) {
    ctx.fillText("Controller connected", canvas.width - 180, 55);
  }

  ctx.textAlign = "right";
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(canvas.width - 150, 10, 140, 44);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(`X: ${Math.floor(state.me.x / TILE)}`, canvas.width - 20, 30);
  ctx.fillText(`Y: ${Math.floor(state.me.y / TILE)}`, canvas.width - 20, 44);
  ctx.textAlign = "left";
}

function drawHotbar() {
  const slotSize = 36;
  const gap = 4;
  const totalWidth = 9 * slotSize + 8 * gap;
  const startX = (canvas.width - totalWidth) / 2;
  const y = canvas.height - 46;

  ctx.textAlign = "left";
  for (let i = 1; i <= 9; i++) {
    const x = startX + (i - 1) * (slotSize + gap);
    const selected = i === state.selectedBlock;
    ctx.fillStyle = selected ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.45)";
    ctx.fillRect(x, y, slotSize, slotSize);
    ctx.strokeStyle = selected ? "#ffe08a" : "rgba(255,255,255,0.25)";
    ctx.lineWidth = selected ? 3 : 2;
    ctx.strokeRect(x + 1, y + 1, slotSize - 2, slotSize - 2);
    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.font = "12px Arial";
    ctx.fillText(String(i), x + 4, y + 14);
  }
}

function drawCrosshair() {
  if (!state.joined || document.pointerLockElement !== canvas) {
    return;
  }
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  ctx.strokeStyle = "rgba(0,0,0,0.7)";
  ctx.beginPath();
  ctx.moveTo(cx - 8, cy);
  ctx.lineTo(cx - 2, cy);
  ctx.moveTo(cx + 2, cy);
  ctx.lineTo(cx + 8, cy);
  ctx.moveTo(cx, cy - 8);
  ctx.lineTo(cx, cy - 2);
  ctx.moveTo(cx, cy + 2);
  ctx.lineTo(cx, cy + 8);
  ctx.stroke();
  ctx.strokeStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(cx - 7, cy);
  ctx.lineTo(cx - 3, cy);
  ctx.moveTo(cx + 3, cy);
  ctx.lineTo(cx + 7, cy);
  ctx.moveTo(cx, cy - 7);
  ctx.lineTo(cx, cy - 3);
  ctx.moveTo(cx, cy + 3);
  ctx.lineTo(cx, cy + 7);
  ctx.stroke();
}

function drawPlacementOutline() {
  const targets = getMiningTargets();
  ctx.save();
  ctx.strokeStyle = "rgba(255, 230, 120, 0.95)";
  ctx.lineWidth = 3;
  for (const tile of targets) {
    const sx = tile.x * TILE - state.cameraX;
    const sy = tile.y * TILE - state.cameraY;
    ctx.strokeRect(sx + 1.5, sy + 1.5, TILE - 3, TILE - 3);
    ctx.strokeStyle = "rgba(0, 0, 0, 0.5)";
    ctx.lineWidth = 1;
    ctx.strokeRect(sx + 4.5, sy + 4.5, TILE - 9, TILE - 9);
    ctx.strokeStyle = "rgba(255, 230, 120, 0.95)";
    ctx.lineWidth = 3;
  }
  ctx.restore();
}

async function syncMove() {
  const intent = getMoveIntent();
  const now = performance.now();
  if (now - state.lastSend < 50) return;
  state.lastSend = now;

  try {
    const result = await api("/api/move", "POST", {
      id: state.clientId,
      left: intent.left,
      right: intent.right,
      jump: intent.jump,
      crouch: intent.crouch,
      sprint: intent.sprint
    });
    if (result.player) {
      state.me = result.player;
    }
    state.players = Array.isArray(result.players) ? result.players : state.players;
    mergeChunkSnapshot(result.world);
  } catch (err) {
    setStatus(`Network error: ${err.message}`);
  }
}

function getControllerAimTile() {
  return getMiningTargets()[0];
}

function getFrontTile() {
  return getControllerAimTile();
}

function cycleBlock(delta) {
  const next = ((state.selectedBlock - 1 + delta + 9) % 9) + 1;
  state.selectedBlock = next;
}

function cycleMiningMode(delta) {
  state.miningMode = (state.miningMode + delta + MINING_MODES.length) % MINING_MODES.length;
}

async function syncWorld() {
  if (!state.joined) return;
  const now = performance.now();
  if (now - state.lastWorldSync < 1000) return;
  state.lastWorldSync = now;
  try {
    const centerX = Math.floor(state.me.x + PLAYER_W / 2);
    const centerY = Math.floor(state.me.y + PLAYER_H / 2);
    const world = await api(`/api/world?centerX=${centerX}&centerY=${centerY}&radius=4`);
    mergeChunkSnapshot(world);
    state.players = Array.isArray(world.players)
      ? world.players.map((player) => ({
          ...player,
          color: player.color || colorFromName(player.name)
        }))
      : state.players;
    pruneChunksAroundPlayer(4);
  } catch (err) {
    setStatus(`World sync error: ${err.message}`);
  }
}

async function updateBlock(type, tx, ty) {
  try {
    const payload = {
      type,
      x: tx,
      y: ty,
      blockType: state.selectedBlock,
      playerId: state.clientId,
      miningMode: state.miningMode
    };
    const result = await api("/api/block", "POST", payload);
    mergeChunkSnapshot(result.world || result);
  } catch (err) {
    setStatus(`Block error: ${err.message}`);
  }
}

async function applyMiningAction(type) {
  const targets = getMiningTargets();
  for (const tile of targets) {
    await updateBlock(type, tile.x, tile.y);
  }
}

async function placeActiveTarget() {
  const targets = getMiningTargets();
  for (const tile of targets) {
    await updateBlock("place", tile.x, tile.y);
  }
}

function updateCamera() {
  const targetX = state.me.x + PLAYER_W / 2 - canvas.width / 2;
  const targetY = state.me.y + PLAYER_H / 2 - canvas.height / 2;
  const maxX = state.world.width * TILE - canvas.width;
  const maxY = state.world.height * TILE - canvas.height;
  state.cameraX = clamp(targetX, 0, Math.max(0, maxX));
  state.cameraY = clamp(targetY, 0, Math.max(0, maxY));
}

async function tick() {
  if (state.joined) {
    await syncMove();
    const edges = getGamepadEdgeState();
    if (edges.unlockPressed && document.pointerLockElement === canvas) {
      document.exitPointerLock();
    }
    if (edges.prevBlockPressed) {
      cycleBlock(-1);
    }
    if (edges.nextBlockPressed) {
      cycleBlock(1);
    }
    if (edges.modeNextPressed) {
      cycleMiningMode(1);
    }
    if (edges.breakPressed || edges.placePressed) {
      if (edges.breakPressed && state.miningMode !== 2) {
        await applyMiningAction("break");
      }
      if (edges.placePressed && state.miningMode !== 2) {
        await placeActiveTarget();
      }
    }
    await syncWorld();
    updateCamera();
  }

  drawBackground();
  drawWorld();

  for (const p of state.players) {
    drawPlayer(p, p.id === state.clientId);
  }

  drawHud();
  drawCrosshair();
  drawPlacementOutline();
  drawHotbar();
  requestAnimationFrame(tick);
}

joinBtn.addEventListener("click", async () => {
  try {
    const name = nameInput.value.trim() || "Player";
    const result = await api("/api/join", "POST", { name });
    state.clientId = result.id;
    state.me = result.player;
    state.me.color = state.me.color || colorFromName(name);
    state.joined = true;
    state.players = [result.player].map((player) => ({
      ...player,
      color: player.color || colorFromName(player.name)
    }));
    if (result.world) {
      mergeChunkSnapshot(result.world);
    }
    setStatus(`Joined as ${name}`);
  } catch (err) {
    setStatus(`Join failed: ${err.message}`);
  }
});

function colorFromName(name) {
  const raw = String(name || "").trim();
  if (!raw) return "#ffcf5a";
  const ch = raw[0].toLowerCase();
  const palette = {
    a: "#ff5b5b",
    b: "#ff9a3c",
    c: "#ffe45c",
    d: "#6bd96b",
    e: "#ffffff",
    f: "#4ea6ff",
    g: "#c56bff",
    h: "#ff6bb5",
    i: "#9bf6ff",
    j: "#c2b280",
    k: "#8a5a36",
    l: "#7d7d7d",
    m: "#ffd166",
    n: "#06d6a0",
    o: "#f4a261",
    p: "#e76f51",
    q: "#90be6d",
    r: "#577590",
    s: "#f94144",
    t: "#f3722c",
    u: "#f9c74f",
    v: "#43aa8b",
    w: "#4895ef",
    x: "#b5179e",
    y: "#adb5bd",
    z: "#f8961e"
  };
  return palette[ch] || "#ffcf5a";
}

document.addEventListener("keydown", (e) => {
  if (state.joined) {
    if (e.ctrlKey || e.metaKey || e.altKey) {
      e.preventDefault();
    }
    if (["Tab", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"].includes(e.key)) {
      e.preventDefault();
    }
  }
  state.keys.add(e.key);
  if (e.key >= "1" && e.key <= "9") {
    state.selectedBlock = Number(e.key);
  }
  if (e.key.toLowerCase() === "f") {
    cycleMiningMode(1);
  }
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", " ", "Shift", "Control", "Alt", "Meta", "Tab"].includes(e.key)) {
    e.preventDefault();
  }
}, true);

document.addEventListener("keyup", (e) => state.keys.delete(e.key), true);

window.addEventListener("wheel", (e) => {
  if (!state.joined) return;
  e.preventDefault();
  if (e.deltaY > 0) {
    cycleBlock(1);
  } else if (e.deltaY < 0) {
    cycleBlock(-1);
  }
}, { passive: false });

canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  state.mouse.x = ((e.clientX - rect.left) / rect.width) * canvas.width;
  state.mouse.y = ((e.clientY - rect.top) / rect.height) * canvas.height;
});

canvas.addEventListener("contextmenu", (e) => e.preventDefault());

canvas.addEventListener("click", async () => {
  if (!state.joined) return;
  if (document.pointerLockElement !== canvas) {
    canvas.requestPointerLock();
  }
});

document.addEventListener("pointerlockchange", () => {
  if (document.pointerLockElement === canvas) {
    setStatus("Mouse locked. Press Esc to unlock.");
  } else if (state.joined) {
    setStatus("Mouse unlocked.");
  }
});

canvas.addEventListener("mousedown", async (e) => {
  if (!state.joined) return;
  if (document.pointerLockElement !== canvas) {
    return;
  }
  if (e.button === 0) {
    await applyMiningAction("break");
  } else if (e.button === 2) {
    await placeActiveTarget();
  }
});

window.addEventListener("gamepadconnected", () => {
  state.gamepad.connected = true;
  setStatus("Gamepad connected");
});

window.addEventListener("gamepaddisconnected", () => {
  state.gamepad.connected = false;
  state.gamepad.prevButtons = [];
  setStatus("Gamepad disconnected");
});

window.addEventListener("beforeunload", () => {
  if (!state.clientId) return;
  const payload = new Blob([JSON.stringify({ id: state.clientId })], {
    type: "application/json"
  });
  navigator.sendBeacon("/api/leave", payload);
});

drawBackground();
requestAnimationFrame(tick);
