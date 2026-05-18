package com.student.mcxbox.world;

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

    public PlayerState() {
    }

    public PlayerState(String id, String name) {
        this.id = id;
        this.name = name;
        this.x = 100;
        this.y = 100;
    }
}
