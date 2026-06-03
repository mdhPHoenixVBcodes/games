package com.filetransfer.config;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class SecurityConfig {

    private static final Map<String, SessionToken> activeTokens = new ConcurrentHashMap<>();
    private static final SecureRandom random = new SecureRandom();

    public static String generateToken(String username) {
        byte[] randomBytes = new byte[32];
        random.nextBytes(randomBytes);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
        
        activeTokens.put(token, new SessionToken(username, System.currentTimeMillis() + 3600000)); // 1 hour
        return token;
    }

    public static boolean validateToken(String token, String username) {
        SessionToken sessionToken = activeTokens.get(token);
        if (sessionToken == null) return false;
        
        if (System.currentTimeMillis() > sessionToken.expiryTime) {
            activeTokens.remove(token);
            return false;
        }
        
        return sessionToken.username.equals(username);
    }

    public static void invalidateToken(String token) {
        activeTokens.remove(token);
    }

    private static class SessionToken {
        String username;
        long expiryTime;

        SessionToken(String username, long expiryTime) {
            this.username = username;
            this.expiryTime = expiryTime;
        }
    }
}