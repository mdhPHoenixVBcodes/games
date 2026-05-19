package com.student.mcxbox.world;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
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
    private static final int WORLD_FORMAT_VERSION = 1;
    private static final int WORLD_MAGIC = 0x4D435842;
    private static final int WIDTH = 2048;
    private static final int HEIGHT = 128;
    private static final int TILE_SIZE = 32;
    private static final int CHUNK_SIZE = 16;
    private static final Path WORLD_DIR = Paths.get("worlds");
    private static final Path WORLD_FILE = WORLD_DIR.resolve("world.db");

    private final Map<String, PlayerState> players = new ConcurrentHashMap<>();
    private final Map<Integer, Integer> blocks = new ConcurrentHashMap<>();

    public WorldState() {
        try {
            Files.createDirectories(WORLD_DIR);
            if (!loadWorldFromDisk()) {
                generateWorld();
            }
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
        for (Map.Entry<Integer, Integer> entry : blocks.entrySet()) {
            int x = unpackX(entry.getKey());
            int y = unpackY(entry.getKey());
            out.put(tileKey(x, y), entry.getValue());
        }
        return out;
    }

    public Map<String, Map<String, Integer>> snapshotChunksAround(int centerTx, int centerTy, int radiusChunks) {
        int centerCx = toChunkX(centerTx);
        int centerCy = toChunkY(centerTy);
        Map<String, Map<String, Integer>> snapshot = new LinkedHashMap<>();
        int startX = Math.max(0, (centerCx - radiusChunks) * CHUNK_SIZE);
        int endX = Math.min(WIDTH - 1, (centerCx + radiusChunks + 1) * CHUNK_SIZE - 1);
        int startY = Math.max(0, (centerCy - radiusChunks) * CHUNK_SIZE);
        int endY = Math.min(HEIGHT - 1, (centerCy + radiusChunks + 1) * CHUNK_SIZE - 1);

        for (int x = startX; x <= endX; x++) {
            for (int y = startY; y <= endY; y++) {
                Integer type = getBlock(x, y);
                if (type == null) {
                    continue;
                }
                String chunkKey = chunkKey(toChunkX(x), toChunkY(y));
                snapshot.computeIfAbsent(chunkKey, key -> new LinkedHashMap<>())
                        .put(tileKey(x, y), type);
            }
        }
        return snapshot;
    }

    public Integer getBlock(int x, int y) {
        if (!inBounds(x, y)) {
            return null;
        }
        return blocks.get(packKey(x, y));
    }

    public void setBlock(int x, int y, Integer type) {
        if (!inBounds(x, y)) {
            return;
        }
        int key = packKey(x, y);
        if (type == null) {
            blocks.remove(key);
        } else {
            blocks.put(key, type);
        }
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
        saveWorldToDisk();
    }

    private boolean loadWorldFromDisk() {
        if (!Files.exists(WORLD_FILE)) {
            return false;
        }

        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(WORLD_FILE)))) {
            int magic = in.readInt();
            int version = in.readInt();
            int width = in.readInt();
            int height = in.readInt();
            int tileSize = in.readInt();
            int chunkSize = in.readInt();
            if (magic != WORLD_MAGIC || version != WORLD_FORMAT_VERSION) {
                return false;
            }
            if (width != WIDTH || height != HEIGHT || tileSize != TILE_SIZE || chunkSize != CHUNK_SIZE) {
                return false;
            }

            int count = in.readInt();
            blocks.clear();
            for (int i = 0; i < count; i++) {
                int key = in.readInt();
                int type = in.readInt();
                blocks.put(key, type);
            }
            return true;
        } catch (IOException e) {
            throw new IllegalStateException("Failed to load world database", e);
        }
    }

    private void saveWorldToDisk() {
        try {
            Files.createDirectories(WORLD_DIR);
            Map<Integer, Integer> snapshot = new LinkedHashMap<>(blocks);
            try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(WORLD_FILE)))) {
                out.writeInt(WORLD_MAGIC);
                out.writeInt(WORLD_FORMAT_VERSION);
                out.writeInt(WIDTH);
                out.writeInt(HEIGHT);
                out.writeInt(TILE_SIZE);
                out.writeInt(CHUNK_SIZE);
                out.writeInt(snapshot.size());
                for (Map.Entry<Integer, Integer> entry : snapshot.entrySet()) {
                    out.writeInt(entry.getKey());
                    out.writeInt(entry.getValue());
                }
            }
        } catch (IOException e) {
            throw new IllegalStateException("Failed to save world database", e);
        }
    }

    private void generateWorld() {
        blocks.clear();

        int[] surfaceHeights = new int[WIDTH];
        int[] soilDepths = new int[WIDTH];
        for (int x = 0; x < WIDTH; x++) {
            surfaceHeights[x] = surfaceHeight(x);
            soilDepths[x] = topSoilDepth(x, surfaceHeights[x]);
        }

        for (int x = 0; x < WIDTH; x++) {
            int surface = surfaceHeights[x];
            int topSoilDepth = soilDepths[x];
            for (int y = 0; y < HEIGHT; y++) {
                int depth = y - surface;
                int stoneDepth = stoneDepth(x, surface);
                boolean rocky = isRockyTerrain(x, surface);
                if (depth > topSoilDepth + stoneDepth) {
                    putBlock(x, y, 3);
                } else if (depth > topSoilDepth) {
                    putBlock(x, y, rocky ? 3 : 2);
                } else if (y == surface) {
                    putBlock(x, y, rocky ? 3 : 1);
                } else if (depth > 0) {
                    putBlock(x, y, rocky ? 3 : 2);
                }
            }
        }

        for (int x = 0; x < WIDTH; x++) {
            maybeGenerateTree(x, surfaceHeights[x]);
        }
    }

    private void maybeGenerateTree(int x, int surface) {
        if (surface < 24 || surface > HEIGHT - 10) {
            return;
        }
        if (isRockyTerrain(x, surface)) {
            return;
        }

        double forest = noise01(x, 0.024, 811L);
        double grove = noise01(x, 0.0065, 1123L);
        double canopy = ridgeNoise01(x, 0.019, 1427L);
        double treeChance = 0.05 + forest * 0.11 + grove * 0.07;
        if (canopy < 0.18 || forest < 0.52 || grove < 0.34) {
            return;
        }

        Random rng = new Random(0x9E3779B97F4A7C15L ^ (long) x * 341873128712L);
        if (rng.nextDouble() > treeChance) {
            return;
        }

        int trunkHeight = 4 + rng.nextInt(3);
        int trunkBase = surface;
        for (int dy = 1; dy <= trunkHeight; dy++) {
            int ty = trunkBase - dy;
            if (ty >= 0) {
                putBlock(x, ty, 7);
            }
        }

        int crownY = trunkBase - trunkHeight - 1;
        int crownRadius = 2 + rng.nextInt(2);
        for (int dx = -crownRadius; dx <= crownRadius; dx++) {
            for (int dy = -crownRadius; dy <= 1; dy++) {
                int tx = x + dx;
                int ty = crownY + dy;
                if (tx < 0 || tx >= WIDTH || ty < 0 || ty >= HEIGHT) {
                    continue;
                }
                int distance = Math.abs(dx) + Math.abs(dy);
                if (distance <= crownRadius + 1) {
                    putBlock(tx, ty, 10);
                }
            }
        }

        if (rng.nextDouble() > 0.5) {
            int topY = trunkBase - trunkHeight - crownRadius - 1;
            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    int tx = x + dx;
                    int ty = topY + dy;
                    if (tx >= 0 && tx < WIDTH && ty >= 0 && ty < HEIGHT) {
                        putBlock(tx, ty, 10);
                    }
                }
            }
        }
    }

    private int surfaceHeight(int x) {
        double plains = signedNoise(x, 0.016, 11L) * 3.0
                + signedNoise(x, 0.006, 17L) * 7.0
                + signedNoise(x, 0.0018, 23L) * 4.0;
        double mountainField = noise01(x, 0.0016, 41L);
        double mountainMask = smoothStep(0.46, 0.74, mountainField);
        double mountainRidges = ridgeNoise01(x, 0.009, 73L) * 26.0;
        double mountainJagged = ridgeNoise01(x, 0.028, 97L) * 7.0;
        double mountainDrop = noise01(x, 0.004, 131L) * 9.0;
        int height = 56 + (int) Math.round(plains + mountainMask * (mountainRidges + mountainJagged + 8.0 - mountainDrop));
        return Math.max(28, Math.min(HEIGHT - 8, height));
    }

    private int stoneDepth(int x, int surface) {
        double mountainField = noise01(x, 0.0016, 41L);
        double mountainMask = smoothStep(0.46, 0.74, mountainField);
        int depth = 3 + (int) Math.round(mountainMask * 5.0);
        if (surface < 40) {
            depth += 2;
        }
        return Math.max(3, Math.min(10, depth));
    }

    private int topSoilDepth(int x, int surface) {
        double plains = noise01(x, 0.008, 211L);
        int depth = 3 + (int) Math.round(plains * 2.0);
        if (surface < 40) {
            depth = 2 + (int) Math.round(plains);
        }
        return Math.max(2, Math.min(5, depth));
    }

    private boolean isRockyTerrain(int x, int surface) {
        int left = surfaceHeight(clampX(x - 1));
        int right = surfaceHeight(clampX(x + 1));
        int slope = Math.max(Math.abs(surface - left), Math.abs(surface - right));
        return surface < 40 || slope >= 5;
    }

    private void putBlock(int x, int y, int type) {
        if (inBounds(x, y)) {
            blocks.put(packKey(x, y), type);
        }
    }

    private int packKey(int x, int y) {
        return (x << 7) | y;
    }

    private int unpackX(int key) {
        return key >>> 7;
    }

    private int unpackY(int key) {
        return key & 0x7F;
    }

    private int clampX(int x) {
        return Math.max(0, Math.min(WIDTH - 1, x));
    }

    private double smoothStep(double edge0, double edge1, double value) {
        if (edge0 == edge1) {
            return value < edge0 ? 0.0 : 1.0;
        }
        double t = (value - edge0) / (edge1 - edge0);
        t = Math.max(0.0, Math.min(1.0, t));
        return t * t * (3.0 - 2.0 * t);
    }

    private double noise01(int x, double frequency, long seed) {
        double scaled = x * frequency;
        int x0 = (int) Math.floor(scaled);
        int x1 = x0 + 1;
        double t = scaled - x0;
        double v0 = hash01(x0, seed);
        double v1 = hash01(x1, seed);
        double u = t * t * (3.0 - 2.0 * t);
        return v0 + (v1 - v0) * u;
    }

    private double signedNoise(int x, double frequency, long seed) {
        return noise01(x, frequency, seed) * 2.0 - 1.0;
    }

    private double ridgeNoise01(int x, double frequency, long seed) {
        return 1.0 - Math.abs(signedNoise(x, frequency, seed));
    }

    private double hash01(int value, long seed) {
        long n = value * 341873128712L + seed * 132897987541L;
        n = (n << 13) ^ n;
        long nn = (n * (n * n * 15731L + 789221L) + 1376312589L) & 0x7fffffffL;
        return nn / (double) 0x7fffffffL;
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
}
