package com.student.mcxbox.world;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

public class WorldState {
    private static final int WIDTH = 2048;
    private static final int HEIGHT = 128;
    private static final int TILE_SIZE = 32;
    private static final int CHUNK_SIZE = 16;
    private static final Path WORLD_DIR = Paths.get("worlds");
    private static final Path CHUNK_DIR = WORLD_DIR.resolve("chunks");
    private static final Path SAVE_FILE = WORLD_DIR.resolve("savegame.json");

    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, PlayerState> players = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Integer>> chunks = new ConcurrentHashMap<>();

    public WorldState() {
        try {
            Files.createDirectories(CHUNK_DIR);
            loadManifest();
        } catch (IOException e) {
            throw new IllegalStateException("Failed to initialize world storage", e);
        }
    }

    public Collection<PlayerState> players() {
        return players.values();
    }

    public PlayerState getOrCreatePlayer(String id, String name) {
        return players.compute(id, (key, existing) -> {
            if (existing == null) {
                return new PlayerState(id, name);
            }
            existing.name = name == null || name.isBlank() ? existing.name : name;
            return existing;
        });
    }

    public PlayerState getPlayer(String id) {
        return players.get(id);
    }

    public void removePlayer(String id) {
        players.remove(id);
    }

    public Map<String, Integer> blocks() {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (Map<String, Integer> chunk : chunks.values()) {
            out.putAll(chunk);
        }
        return out;
    }

    public Map<String, Map<String, Integer>> snapshotChunksAround(int centerTx, int centerTy, int radiusChunks) {
        int centerCx = toChunkX(centerTx);
        int centerCy = toChunkY(centerTy);
        for (int cx = centerCx - radiusChunks; cx <= centerCx + radiusChunks; cx++) {
            for (int cy = centerCy - radiusChunks; cy <= centerCy + radiusChunks; cy++) {
                ensureChunkLoaded(cx, cy);
            }
        }

        Map<String, Map<String, Integer>> snapshot = new LinkedHashMap<>();
        for (int cx = centerCx - radiusChunks; cx <= centerCx + radiusChunks; cx++) {
            for (int cy = centerCy - radiusChunks; cy <= centerCy + radiusChunks; cy++) {
                String key = chunkKey(cx, cy);
                Map<String, Integer> chunk = chunks.get(key);
                if (chunk != null && !chunk.isEmpty()) {
                    snapshot.put(key, new LinkedHashMap<>(chunk));
                }
            }
        }

        pruneFarChunks(centerCx, centerCy, radiusChunks);
        return snapshot;
    }

    public Integer getBlock(int x, int y) {
        if (!inBounds(x, y)) {
            return null;
        }
        int cx = toChunkX(x);
        int cy = toChunkY(y);
        ensureChunkLoaded(cx, cy);
        Map<String, Integer> chunk = chunks.get(chunkKey(cx, cy));
        if (chunk == null) {
            return null;
        }
        return chunk.get(tileKey(x, y));
    }

    public void setBlock(int x, int y, Integer type) {
        if (!inBounds(x, y)) {
            return;
        }
        int cx = toChunkX(x);
        int cy = toChunkY(y);
        String key = chunkKey(cx, cy);
        Map<String, Integer> chunk = ensureChunkLoaded(cx, cy);
        if (type == null) {
            chunk.remove(tileKey(x, y));
        } else {
            chunk.put(tileKey(x, y), type);
        }
        chunks.put(key, chunk);
    }

    public int getTileSize() {
        return TILE_SIZE;
    }

    public int getWidth() {
        return WIDTH;
    }

    public int getHeight() {
        return HEIGHT;
    }

    public int getChunkSize() {
        return CHUNK_SIZE;
    }

    public void saveAllLoadedChunks() {
        try {
            Files.createDirectories(CHUNK_DIR);
            for (Map.Entry<String, Map<String, Integer>> entry : chunks.entrySet()) {
                Path file = chunkFile(entry.getKey());
                mapper.writerWithDefaultPrettyPrinter().writeValue(file.toFile(), entry.getValue());
            }
            Map<String, Object> manifest = new LinkedHashMap<>();
            manifest.put("width", WIDTH);
            manifest.put("height", HEIGHT);
            manifest.put("tileSize", TILE_SIZE);
            manifest.put("chunkSize", CHUNK_SIZE);
            manifest.put("loadedChunks", chunks.keySet());
            mapper.writerWithDefaultPrettyPrinter().writeValue(SAVE_FILE.toFile(), manifest);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to save world chunks", e);
        }
    }

    private void loadManifest() throws IOException {
        if (Files.exists(SAVE_FILE)) {
            // The manifest is mostly informational; chunks load lazily from disk.
            mapper.readTree(SAVE_FILE.toFile());
        }
    }

    private Map<String, Integer> ensureChunkLoaded(int cx, int cy) {
        String key = chunkKey(cx, cy);
        Map<String, Integer> existing = chunks.get(key);
        if (existing != null) {
            return existing;
        }
        Map<String, Integer> loaded = loadChunkFromDisk(key);
        if (loaded == null) {
            loaded = generateChunk(cx, cy);
        }
        chunks.put(key, loaded);
        return loaded;
    }

    private Map<String, Integer> loadChunkFromDisk(String key) {
        Path file = chunkFile(key);
        if (!Files.exists(file)) {
            return null;
        }
        try {
            return mapper.readValue(file.toFile(), new TypeReference<>() {});
        } catch (IOException e) {
            throw new IllegalStateException("Failed to load chunk " + key, e);
        }
    }

    private void pruneFarChunks(int centerCx, int centerCy, int radiusChunks) {
        for (String key : chunks.keySet()) {
            int[] coords = parseChunkKey(key);
            int dx = Math.abs(coords[0] - centerCx);
            int dy = Math.abs(coords[1] - centerCy);
            if (dx > radiusChunks || dy > radiusChunks) {
                Map<String, Integer> chunk = chunks.remove(key);
                if (chunk != null) {
                    saveChunkToDisk(key, chunk);
                }
            }
        }
    }

    private void saveChunkToDisk(String key, Map<String, Integer> chunk) {
        try {
            Files.createDirectories(CHUNK_DIR);
            mapper.writerWithDefaultPrettyPrinter().writeValue(chunkFile(key).toFile(), chunk);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to save chunk " + key, e);
        }
    }

    private Map<String, Integer> generateChunk(int cx, int cy) {
        Map<String, Integer> chunk = new LinkedHashMap<>();
        int startX = cx * CHUNK_SIZE;
        int startY = cy * CHUNK_SIZE;
        for (int lx = 0; lx < CHUNK_SIZE; lx++) {
            int x = startX + lx;
            if (x < 0 || x >= WIDTH) {
                continue;
            }
            int surface = surfaceHeight(x);
            maybeGenerateTree(chunk, x, surface);
            for (int ly = 0; ly < CHUNK_SIZE; ly++) {
                int y = startY + ly;
                if (y < 0 || y >= HEIGHT) {
                    continue;
                }
                if (y > surface + 4) {
                    chunk.put(tileKey(x, y), 3);
                } else if (y > surface) {
                    chunk.put(tileKey(x, y), 2);
                } else if (y == surface) {
                    chunk.put(tileKey(x, y), 1);
                }
            }
        }
        return chunk;
    }

    private void maybeGenerateTree(Map<String, Integer> chunk, int x, int surface) {
        Random rng = new Random(0x9E3779B97F4A7C15L ^ (long) x * 341873128712L);
        if (surface < 18 || surface > HEIGHT - 8) {
            return;
        }
        if (rng.nextDouble() > 0.08) {
            return;
        }

        int trunkHeight = 3 + rng.nextInt(3);
        for (int dy = 1; dy <= trunkHeight; dy++) {
            int ty = surface - dy;
            if (ty >= 0) {
                chunk.put(tileKey(x, ty), 7);
            }
        }

        int crownY = surface - trunkHeight - 1;
        for (int dx = -2; dx <= 2; dx++) {
            for (int dy = -2; dy <= 1; dy++) {
                int tx = x + dx;
                int ty = crownY + dy;
                if (tx < 0 || tx >= WIDTH || ty < 0 || ty >= HEIGHT) {
                    continue;
                }
                if (Math.abs(dx) + Math.abs(dy) <= 3) {
                    chunk.put(tileKey(tx, ty), 1);
                }
            }
        }
    }

    private int surfaceHeight(int x) {
        double wave = Math.sin(x * 0.07) * 4.0 + Math.cos(x * 0.021) * 3.0;
        int height = 48 + (int) Math.round(wave);
        return Math.max(28, Math.min(HEIGHT - 8, height));
    }

    private boolean inBounds(int x, int y) {
        return x >= 0 && x < WIDTH && y >= 0 && y < HEIGHT;
    }

    private int toChunkX(int tx) {
        return tx / CHUNK_SIZE;
    }

    private int toChunkY(int ty) {
        return ty / CHUNK_SIZE;
    }

    private String chunkKey(int cx, int cy) {
        return cx + "," + cy;
    }

    private String tileKey(int x, int y) {
        return x + "," + y;
    }

    private int[] parseChunkKey(String key) {
        String[] parts = key.split(",", 2);
        return new int[] { Integer.parseInt(parts[0]), Integer.parseInt(parts[1]) };
    }

    private Path chunkFile(String chunkKey) {
        return CHUNK_DIR.resolve("chunk_" + chunkKey.replace(',', '_') + ".json");
    }
}
