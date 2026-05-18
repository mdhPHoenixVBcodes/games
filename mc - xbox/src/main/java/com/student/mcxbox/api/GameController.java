package com.student.mcxbox.api;

import com.student.mcxbox.world.PlayerState;
import com.student.mcxbox.world.WorldState;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class GameController {
    private static final double GRAVITY = 0.45;
    private static final double MOVE_SPEED = 2.6;
    private static final double SPRINT_SPEED = 4.0;
    private static final double CROUCH_SPEED = 1.4;
    private static final double JUMP_SPEED = -8.2;
    private static final int TILE = 32;
    private static final int PLAYER_W = 24;
    private static final int PLAYER_H = 48;

    private final WorldState worldState = new WorldState();

    @GetMapping("/world")
    public Map<String, Object> world() {
        Map<String, Object> out = new HashMap<>();
        out.put("width", worldState.getWidth());
        out.put("height", worldState.getHeight());
        out.put("tileSize", worldState.getTileSize());
        out.put("blocks", worldState.blocks());
        out.put("players", worldState.players());
        return out;
    }

    @PostMapping("/join")
    public Map<String, Object> join(@RequestBody(required = false) Map<String, String> body) {
        String name = body == null ? null : body.get("name");
        String id = UUID.randomUUID().toString();
        PlayerState player = worldState.getOrCreatePlayer(id, name == null ? "Player" : name);
        spawnAtGround(player);
        Map<String, Object> out = new HashMap<>();
        out.put("id", id);
        out.put("player", player);
        out.put("world", world());
        return out;
    }

    @PostMapping("/move")
    public Map<String, Object> move(@RequestBody MoveRequest req) {
        PlayerState player = worldState.getPlayer(req.id);
        if (player == null) {
            throw new IllegalArgumentException("Unknown player id");
        }

        double vx = 0;
        double moveSpeed = MOVE_SPEED;
        if (req.crouch) {
            moveSpeed = CROUCH_SPEED;
        } else if (req.sprint) {
            moveSpeed = SPRINT_SPEED;
        }
        if (req.left) {
            vx -= moveSpeed;
            player.facingRight = false;
        }
        if (req.right) {
            vx += moveSpeed;
            player.facingRight = true;
        }

        player.vx = vx;
        if (req.jump && player.onGround) {
            player.vy = JUMP_SPEED;
            player.onGround = false;
        }

        stepPhysics(player);

        Map<String, Object> out = new HashMap<>();
        out.put("ok", true);
        out.put("player", player);
        out.put("players", worldState.players());
        return out;
    }

    @PostMapping("/block")
    public Map<String, Object> block(@RequestBody BlockRequest req) {
        if (req == null) {
            throw new IllegalArgumentException("Missing request");
        }

        if (req.type == null || req.type.isBlank()) {
            throw new IllegalArgumentException("Missing block action");
        }

        int x = req.x;
        int y = req.y;
        if ("break".equalsIgnoreCase(req.type)) {
            PlayerState player = worldState.getPlayer(req.playerId);
            if (player != null) {
                int[][] expectedTargets = placementTargets(player, req.miningMode);
                boolean match = false;
                for (int[] expected : expectedTargets) {
                    if (x == expected[0] && y == expected[1]) {
                        match = true;
                        break;
                    }
                }
                if (!match) {
                    throw new IllegalArgumentException("Can only break blocks at the active mining target");
                }
            }
            worldState.setBlock(x, y, null);
        } else if ("place".equalsIgnoreCase(req.type)) {
            PlayerState player = worldState.getPlayer(req.playerId);
            if (player == null) {
                throw new IllegalArgumentException("Unknown player id");
            }
            int[][] expectedTargets = placementTargets(player, req.miningMode);
            boolean match = false;
            for (int[] expected : expectedTargets) {
                if (x == expected[0] && y == expected[1]) {
                    match = true;
                    break;
                }
            }
            if (!match) {
                throw new IllegalArgumentException("Can only place blocks at the active mining target");
            }
            if (worldState.getBlock(x, y) == null) {
                worldState.setBlock(x, y, req.blockType == null ? 2 : req.blockType);
            }
        } else {
            throw new IllegalArgumentException("Unknown block action");
        }

        Map<String, Object> out = new HashMap<>();
        out.put("ok", true);
        out.put("blocks", worldState.blocks());
        return out;
    }

    @PostMapping("/leave")
    public Map<String, Object> leave(@RequestBody Map<String, String> body) {
        if (body != null && body.get("id") != null) {
            worldState.removePlayer(body.get("id"));
        }
        return Map.of("ok", true);
    }

    private void spawnAtGround(PlayerState player) {
        player.x = 4 * TILE;
        player.y = 47 * TILE - PLAYER_H;
        player.vx = 0;
        player.vy = 0;
        player.onGround = false;
    }

    private void stepPhysics(PlayerState player) {
        player.vy += GRAVITY;
        if (player.vy > 12) {
            player.vy = 12;
        }

        double nextX = player.x + player.vx;
        double nextY = player.y + player.vy;

        if (player.vx != 0) {
            double targetLeft = nextX;
            double targetRight = nextX + PLAYER_W;
            double top = player.y + 2;
            double bottom = player.y + PLAYER_H - 2;
            if (collides(targetLeft, top, targetLeft, bottom) && player.vx < 0) {
                nextX = ((int) Math.floor(targetLeft / TILE) + 1) * TILE;
            } else if (collides(targetRight, top, targetRight, bottom) && player.vx > 0) {
                nextX = ((int) Math.floor(targetRight / TILE)) * TILE - PLAYER_W;
            }
        }

        player.x = clamp(nextX, 0, worldState.getWidth() * TILE - PLAYER_W);

        player.onGround = false;
        if (player.vy != 0) {
            double left = player.x + 2;
            double right = player.x + PLAYER_W - 2;
            double top = nextY;
            double bottom = nextY + PLAYER_H;
            if (player.vy > 0 && collides(left, bottom, right, bottom)) {
                nextY = ((int) Math.floor(bottom / TILE)) * TILE - PLAYER_H;
                player.vy = 0;
                player.onGround = true;
            } else if (player.vy < 0 && collides(left, top, right, top)) {
                nextY = ((int) Math.floor(top / TILE) + 1) * TILE;
                player.vy = 0;
            }
        }

        player.y = clamp(nextY, 0, worldState.getHeight() * TILE - PLAYER_H);
    }

    private boolean collides(double left, double y1, double right, double y2) {
        int tx1 = (int) Math.floor(left / TILE);
        int tx2 = (int) Math.floor(right / TILE);
        int ty1 = (int) Math.floor(y1 / TILE);
        int ty2 = (int) Math.floor(y2 / TILE);
        for (int tx = tx1; tx <= tx2; tx++) {
            for (int ty = ty1; ty <= ty2; ty++) {
                if (worldState.getBlock(tx, ty) != null) {
                    return true;
                }
            }
        }
        return false;
    }

    private int frontTileX(PlayerState player) {
        if (player.facingRight) {
            return (int) Math.floor((player.x + PLAYER_W - 1) / TILE) + 1;
        }
        return (int) Math.floor(player.x / TILE) - 1;
    }

    private int frontTileY(PlayerState player) {
        double probe = player.y + PLAYER_H - 1;
        return (int) Math.floor(probe / TILE);
    }

    private int[][] placementTargets(PlayerState player, Integer miningMode) {
        int mode = miningMode == null ? 0 : miningMode;
        int frontX = frontTileX(player);
        int frontY = frontTileY(player);
        int headY = (int) Math.floor((player.y + 8) / TILE);
        int footY = (int) Math.floor((player.y + PLAYER_H - 1) / TILE);
        return switch (mode) {
            case 1 -> new int[][] { { frontX, headY } };
            case 2 -> new int[][] { { frontX, footY + 1 } };
            case 3 -> new int[][] { { frontX, headY - 1 } };
            case 4 -> new int[][] { { frontX, footY }, { frontX, headY } };
            default -> new int[][] { { frontX, frontY } };
        };
    }

    private double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    public static class MoveRequest {
        public String id;
        public boolean left;
        public boolean right;
        public boolean jump;
        public boolean crouch;
        public boolean sprint;
    }

    public static class BlockRequest {
        public String type;
        public int x;
        public int y;
        public Integer blockType;
        public String playerId;
        public Integer miningMode;
    }
}
