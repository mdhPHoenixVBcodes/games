package com.student.mcxbox.world;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class WorldState {
    private final Map<String, PlayerState> players = new ConcurrentHashMap<>();
    private final Map<String, Integer> blocks = new ConcurrentHashMap<>();
    private final int width = 120;
    private final int height = 60;
    private final int tileSize = 32;

    public WorldState() {
        generateSpawnArea();
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
        return new LinkedHashMap<>(blocks);
    }

    public Integer getBlock(int x, int y) {
        return blocks.get(key(x, y));
    }

    public void setBlock(int x, int y, Integer type) {
        String key = key(x, y);
        if (type == null) {
            blocks.remove(key);
        } else {
            blocks.put(key, type);
        }
    }

    public int getTileSize() {
        return tileSize;
    }

    public int getWidth() {
        return width;
    }

    public int getHeight() {
        return height;
    }

    private String key(int x, int y) {
        return x + "," + y;
    }

    private void generateSpawnArea() {
        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                if (y >= 48) {
                    blocks.put(key(x, y), 3);
                } else if (y == 47) {
                    blocks.put(key(x, y), 1);
                }
            }
        }
        for (int x = 8; x < 14; x++) {
            blocks.put(key(x, 46), 4);
        }
        for (int x = 18; x < 22; x++) {
            blocks.put(key(x, 45), 5);
        }
        for (int x = 28; x < 31; x++) {
            blocks.put(key(x, 44), 4);
        }
    }
}
