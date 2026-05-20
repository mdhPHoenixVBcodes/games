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
    public Integer[] craftingGrid = new Integer[4];

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
        inventory.put(2, 10);
        dirt = 10;
        craftingGrid = new Integer[4];
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

    public void placeCraftingItem(int slot, int blockType) {
        if (slot < 0 || slot >= craftingGrid.length) {
            throw new IllegalArgumentException("Invalid crafting slot");
        }
        if (craftingGrid[slot] != null) {
            throw new IllegalArgumentException("Crafting slot already occupied");
        }
        if (blockType != 6 && blockType != 7) {
            throw new IllegalArgumentException("That item cannot be used in the crafting grid");
        }
        if (getBlockCount(blockType) <= 0) {
            throw new IllegalArgumentException("No blocks left");
        }
        craftingGrid[slot] = blockType;
        consumeBlock(blockType);
    }

    public void removeCraftingItem(int slot) {
        if (slot < 0 || slot >= craftingGrid.length) {
            throw new IllegalArgumentException("Invalid crafting slot");
        }
        Integer blockType = craftingGrid[slot];
        if (blockType == null) {
            return;
        }
        craftingGrid[slot] = null;
        addBlock(blockType);
    }

    public void clearCraftingGrid() {
        for (int i = 0; i < craftingGrid.length; i++) {
            craftingGrid[i] = null;
        }
    }
}
