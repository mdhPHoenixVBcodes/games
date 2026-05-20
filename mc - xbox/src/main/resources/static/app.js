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
  9: { name: "Sand", color: "#d8cb9f" },
  10: { name: "Leaves", color: "#4f9d4a" },
  11: { name: "Crafting Table", color: "#ad7a46" }
};

const state = {
  clientId: null,
  me: { x: 140, y: 220, vx: 0, vy: 0, name: "Player", onGround: false, dirt: 10, inventory: { 2: 10 } },
  players: [],
  keys: new Set(),
  joined: false,
  world: { width: 2048, height: 128, tileSize: TILE, chunkSize: 16, chunks: {}, blocks: {} },
  lastSend: 0,
  lastWorldSync: 0,
  cameraX: 0,
  cameraY: 0,
  selectedSlotIndex: 0,
  inventoryOpen: false,
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

function getInventorySlots() {
  return Object.entries(state.me.inventory || {})
    .map(([type, count]) => ({ type: Number(type), count: Number(count) || 0 }))
    .filter((item) => item.count > 0);
}

function getSelectedSlot() {
  const slots = getInventorySlots();
  if (!slots.length) {
    return null;
  }
  const index = clamp(state.selectedSlotIndex, 0, slots.length - 1);
  return { slots, slot: slots[index], index };
}

function getCraftingGrid() {
  const grid = Array.isArray(state.me.craftingGrid) ? state.me.craftingGrid : [];
  return [grid[0] ?? null, grid[1] ?? null, grid[2] ?? null, grid[3] ?? null];
}

function getCraftingOutput() {
  const grid = getCraftingGrid();
  const items = grid.filter((item) => item != null);
  if (items.length === 1 && items[0] === 7) {
    return { type: 6, count: 4 };
  }
  if (items.length === 4 && items.every((item) => item === 6)) {
    return { type: 11, count: 1 };
  }
  return null;
}

function inventoryLayout() {
  const slotSize = 36;
  const panelWidth = 420;
  const panelHeight = 220;
  const panelX = (canvas.width - panelWidth) / 2;
  const panelY = (canvas.height - panelHeight) / 2 - 20;
  return {
    slotSize,
    panelWidth,
    panelHeight,
    panelX,
    panelY,
    gridX: panelX + 42,
    gridY: panelY + 60,
    outputX: panelX + 214,
    outputY: panelY + 104,
    hotbarX: panelX + 42,
    hotbarY: panelY + 160
  };
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
  if (state.inventoryOpen) {
    return { left: false, right: false, jump: false, crouch: false, sprint: false };
  }
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
  ctx.fillRect(10, 10, 360, 200);
  ctx.fillStyle = "#ffffff";
  const selected = getSelectedSlot();
  ctx.fillText(`Block: ${selected ? (BLOCKS[selected.slot.type]?.name || "Block") : "None"}`, 20, 30);
  ctx.fillText(`Dirt: ${state.me.dirt ?? 0}`, 20, 44);
  ctx.fillText(`Mode: ${MINING_MODES[state.miningMode]}`, 20, 58);
  ctx.fillText("Move: A/D or arrows", 20, 72);
  ctx.fillText("Jump: W / Space / Up / A", 20, 86);
  ctx.fillText("Crouch: Shift / B", 20, 100);
  ctx.fillText("Sprint: Ctrl / L-stick click", 20, 114);
  ctx.fillText("Break: left click / RT", 20, 128);
  ctx.fillText("Place: right click / LT", 20, 142);
  ctx.fillText("Mine mode: F / Xbox X", 20, 156);
  ctx.fillText("E: inventory", 20, 170);
  ctx.fillText("Change: 1-9, wheel, LB/RB", 20, 184);
  ctx.fillText("Click world: lock mouse, Esc: unlock", 20, 198);

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
  const slots = getInventorySlots();
  const selected = getSelectedSlot();

  ctx.textAlign = "left";
  for (let i = 1; i <= 9; i++) {
    const x = startX + (i - 1) * (slotSize + gap);
    const slot = slots[i - 1] || null;
    const isSelected = !!selected && selected.index === i - 1;
    const block = slot ? BLOCKS[slot.type] : null;
    ctx.fillStyle = isSelected ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.45)";
    ctx.fillRect(x, y, slotSize, slotSize);
    if (block) {
      ctx.fillStyle = block.color;
      ctx.fillRect(x + 4, y + 4, slotSize - 8, slotSize - 8);
      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fillRect(x + 4, y + 4, slotSize - 8, (slotSize - 8) / 2);
    }
    ctx.strokeStyle = isSelected ? "#ffe08a" : "rgba(255,255,255,0.25)";
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.strokeRect(x + 1, y + 1, slotSize - 2, slotSize - 2);
    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.font = "12px Arial";
    ctx.fillText(String(i), x + 4, y + 14);
    const count = slot ? slot.count : 0;
    ctx.fillStyle = count > 0 ? "rgba(0, 0, 0, 0.45)" : "rgba(120, 120, 120, 0.4)";
    ctx.fillRect(x + slotSize - 16, y + slotSize - 16, 14, 14);
    ctx.fillStyle = count > 0 ? "#ffffff" : "rgba(255,255,255,0.75)";
    ctx.font = "10px Arial";
    ctx.textAlign = "center";
    ctx.fillText(count > 0 ? String(count) : "", x + slotSize - 9, y + slotSize - 5);
    ctx.textAlign = "left";
  }
}

function drawInventoryOverlay() {
  if (!state.inventoryOpen) {
    return;
  }

  const layout = inventoryLayout();
  const slotSize = layout.slotSize;
  const grid = getCraftingGrid();
  const output = getCraftingOutput();

  ctx.save();
  ctx.fillStyle = "rgba(0, 0, 0, 0.58)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(18, 25, 38, 0.96)";
  ctx.fillRect(layout.panelX, layout.panelY, layout.panelWidth, layout.panelHeight);
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 2;
  ctx.strokeRect(layout.panelX + 1, layout.panelY + 1, layout.panelWidth - 2, layout.panelHeight - 2);

  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.font = "18px Arial";
  ctx.fillText("Inventory", layout.panelX + 18, layout.panelY + 30);
  ctx.font = "13px Arial";
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.fillText("E to close", layout.panelX + 18, layout.panelY + 48);
  ctx.fillText("Click a hotbar item, then click the grid to add it.", layout.panelX + 150, layout.panelY + 30);
  ctx.fillText("Right click a grid slot to take it back.", layout.panelX + 150, layout.panelY + 48);
  ctx.fillText("Click the result slot to craft.", layout.panelX + 150, layout.panelY + 66);

  ctx.fillStyle = "#ffffff";
  ctx.font = "14px Arial";
  ctx.fillText("Crafting", layout.panelX + 42, layout.panelY + 92);

  for (let i = 0; i < 4; i++) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const sx = layout.gridX + col * 44;
    const sy = layout.gridY + row * 44;
    const blockType = grid[i];
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(sx, sy, slotSize, slotSize);
    ctx.strokeStyle = "rgba(255,255,255,0.22)";
    ctx.lineWidth = 2;
    ctx.strokeRect(sx + 1, sy + 1, slotSize - 2, slotSize - 2);
    if (blockType != null) {
      const block = BLOCKS[blockType] || BLOCKS[2];
      ctx.fillStyle = block.color;
      ctx.fillRect(sx + 4, sy + 4, slotSize - 8, slotSize - 8);
      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fillRect(sx + 4, sy + 4, slotSize - 8, (slotSize - 8) / 2);
      ctx.fillStyle = "rgba(255,255,255,0.92)";
      ctx.font = "12px Arial";
      ctx.fillText(BLOCKS[blockType]?.name || "Item", sx + 4, sy + slotSize + 14);
    }
  }

  ctx.fillStyle = "rgba(255,255,255,0.9)";
  ctx.font = "14px Arial";
  ctx.fillText("=", layout.outputX - 18, layout.outputY + 24);
  ctx.fillStyle = "rgba(255,255,255,0.08)";
  ctx.fillRect(layout.outputX, layout.outputY, slotSize, slotSize);
  ctx.strokeStyle = output ? "#ffe08a" : "rgba(255,255,255,0.22)";
  ctx.lineWidth = 2;
  ctx.strokeRect(layout.outputX + 1, layout.outputY + 1, slotSize - 2, slotSize - 2);
  if (output) {
    const block = BLOCKS[output.type] || BLOCKS[2];
    ctx.fillStyle = block.color;
    ctx.fillRect(layout.outputX + 4, layout.outputY + 4, slotSize - 8, slotSize - 8);
    ctx.fillStyle = "rgba(255,255,255,0.12)";
    ctx.fillRect(layout.outputX + 4, layout.outputY + 4, slotSize - 8, (slotSize - 8) / 2);
    ctx.fillStyle = "#ffffff";
    ctx.font = "10px Arial";
    ctx.fillText(String(output.count), layout.outputX + slotSize - 9, layout.outputY + slotSize - 5);
  }

  const inventorySlots = getInventorySlots();
  const hotbarX = layout.hotbarX;
  const hotbarY = layout.hotbarY;
  for (let i = 0; i < 9; i++) {
    const x = hotbarX + i * 40;
    const slot = inventorySlots[i] || null;
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(x, hotbarY, slotSize, slotSize);
    ctx.strokeStyle = slot && i === getSelectedSlot()?.index ? "#ffe08a" : "rgba(255,255,255,0.18)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 1, hotbarY + 1, slotSize - 2, slotSize - 2);
    if (slot) {
      const block = BLOCKS[slot.type] || BLOCKS[2];
      ctx.fillStyle = block.color;
      ctx.fillRect(x + 4, hotbarY + 4, slotSize - 8, slotSize - 8);
      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fillRect(x + 4, hotbarY + 4, slotSize - 8, (slotSize - 8) / 2);
      ctx.fillStyle = "#ffffff";
      ctx.font = "10px Arial";
      ctx.textAlign = "center";
      ctx.fillText(String(slot.count), x + slotSize - 9, hotbarY + slotSize - 5);
    }
  }

  ctx.restore();
}

function hitTestInventory(px, py) {
  if (!state.inventoryOpen) {
    return null;
  }

  const layout = inventoryLayout();
  const slotSize = layout.slotSize;
  const localX = px;
  const localY = py;

  const outputRect = {
    x: layout.outputX,
    y: layout.outputY,
    w: slotSize,
    h: slotSize
  };
  if (localX >= outputRect.x && localX < outputRect.x + outputRect.w && localY >= outputRect.y && localY < outputRect.y + outputRect.h) {
    return { kind: "output" };
  }

  for (let i = 0; i < 4; i++) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = layout.gridX + col * 44;
    const y = layout.gridY + row * 44;
    if (localX >= x && localX < x + slotSize && localY >= y && localY < y + slotSize) {
      return { kind: "grid", index: i };
    }
  }

  for (let i = 0; i < 9; i++) {
    const x = layout.hotbarX + i * 40;
    const y = layout.hotbarY;
    if (localX >= x && localX < x + slotSize && localY >= y && localY < y + slotSize) {
      return { kind: "hotbar", index: i };
    }
  }

  return null;
}

async function inventoryAction(action, payload) {
  try {
    const result = await api("/api/inventory", "POST", {
      action,
      playerId: state.clientId,
      ...payload
    });
    if (result.player) {
      state.me = result.player;
    }
    if (result.world) {
      mergeChunkSnapshot(result.world);
    }
  } catch (err) {
    setStatus(`Inventory error: ${err.message}`);
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
  if (state.inventoryOpen) {
    return;
  }
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
  const slots = getInventorySlots();
  if (!slots.length) {
    state.selectedSlotIndex = 0;
    return;
  }
  state.selectedSlotIndex = (state.selectedSlotIndex + delta + slots.length) % slots.length;
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
    const selected = getSelectedSlot();
    if (type === "place" && (!selected || selected.slot.count <= 0)) {
      throw new Error("No blocks selected");
    }
    const payload = {
      type,
      x: tx,
      y: ty,
      blockType: selected ? selected.slot.type : 2,
      playerId: state.clientId,
      miningMode: state.miningMode
    };
    const result = await api("/api/block", "POST", payload);
    if (result.player) {
      state.me = result.player;
    }
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
    if (!state.inventoryOpen) {
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
    } else {
      getGamepadEdgeState();
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
  if (!state.inventoryOpen) {
    drawCrosshair();
    drawPlacementOutline();
  }
  drawHotbar();
  drawInventoryOverlay();
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
    state.inventoryOpen = false;
    state.players = [result.player].map((player) => ({
      ...player,
      color: player.color || colorFromName(player.name)
    }));
    state.selectedSlotIndex = 0;
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
  if (e.key.toLowerCase() === "e") {
    state.inventoryOpen = !state.inventoryOpen;
    if (state.inventoryOpen && document.pointerLockElement === canvas) {
      document.exitPointerLock();
    }
    setStatus(state.inventoryOpen ? "Inventory open." : "Inventory closed.");
    e.preventDefault();
    return;
  }
  if (state.inventoryOpen && e.key === "Escape") {
    state.inventoryOpen = false;
    setStatus("Inventory closed.");
    e.preventDefault();
    return;
  }
  if (e.key >= "1" && e.key <= "9") {
    const index = Number(e.key) - 1;
    if (index < getInventorySlots().length) {
      state.selectedSlotIndex = index;
    }
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
  if (!getInventorySlots().length) return;
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
  if (state.inventoryOpen) return;
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
  if (state.inventoryOpen) {
    const hit = hitTestInventory(state.mouse.x, state.mouse.y);
    if (!hit) {
      return;
    }
    if (hit.kind === "hotbar") {
      state.selectedSlotIndex = hit.index;
      return;
    }
    if (hit.kind === "grid") {
      const selected = getSelectedSlot();
      if (e.button === 0 && selected) {
        await inventoryAction("place", {
          slot: hit.index,
          blockType: selected.slot.type
        });
      } else if (e.button === 2) {
        await inventoryAction("remove", { slot: hit.index });
      }
      return;
    }
    if (hit.kind === "output" && e.button === 0) {
      await inventoryAction("craft", {});
      return;
    }
    return;
  }
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
