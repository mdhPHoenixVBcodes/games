package com.student.mcxbox.world;

import java.util.LinkedHashMap;
import java.util.Map;

public class PlayerState {
    public String id;
    public String name;
    public String color;
    public double x;
    public double y;
    public double vx;
    public double vy;
    public boolean onGround;
    public boolean facingRight = true;
    public boolean jumping;
    public int dirt = 10;
    public Map<Integer, Integer> inventory = new LinkedHashMap<>();

    public PlayerState() {
        resetInventory();
    }

    public PlayerState(String id, String name) {
        resetInventory();
        this.id = id;
        this.name = name;
        this.x = 100;
        this.y = 100;
    }

    public void resetInventory() {
        inventory = new LinkedHashMap<>();
        for (int blockType = 1; blockType <= 9; blockType++) {
            inventory.put(blockType, 0);
        }
        inventory.put(2, 10);
        dirt = 10;
    }

    public int getBlockCount(int blockType) {
        return inventory.getOrDefault(blockType, 0);
    }

    public void addBlock(int blockType) {
        inventory.put(blockType, getBlockCount(blockType) + 1);
        if (blockType == 2) {
            dirt = getBlockCount(2);
        }
    }

    public void consumeBlock(int blockType) {
        int next = Math.max(0, getBlockCount(blockType) - 1);
        inventory.put(blockType, next);
        if (blockType == 2) {
            dirt = next;
        }
    }
}
