package com.filetransfer;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.ConcurrentHashMap;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class FileTransferController {

    // Maps username -> status ("waiting" or "connected")
    private final ConcurrentHashMap<String, String> activeUsers = new ConcurrentHashMap<>();

    // Maps username -> their connected peer's username
    private final ConcurrentHashMap<String, String> peerConnections = new ConcurrentHashMap<>();

    private final Path baseDir;

    public FileTransferController() {
        this.baseDir = Paths.get(System.getProperty("java.io.tmpdir"), "file-transfer").toAbsolutePath().normalize();
    }

    @PostConstruct
    public void init() throws IOException {
        if (!Files.exists(baseDir)) Files.createDirectories(baseDir);
    }

    // Validates that a given name segment is safe (no path traversal)
    private boolean isSafeName(String name) {
        if (name == null || name.isBlank()) return false;
        // Reject any path separators or traversal sequences
        if (name.contains("..") || name.contains("/") || name.contains("\\")) return false;
        // Reject absolute paths or other suspicious characters
        if (name.startsWith(".") || name.contains(":")) return false;
        return true;
    }

    // Validates that the resolved path is still within baseDir
    private boolean isWithinBaseDir(Path resolved) {
        return resolved.toAbsolutePath().normalize().startsWith(baseDir);
    }

    @PostMapping("/register")
    public ResponseEntity<String> register(@RequestParam String username) {
        if (!isSafeName(username)) {
            return ResponseEntity.badRequest().body("Invalid username");
        }
        activeUsers.put(username, "waiting");
        return ResponseEntity.ok("Registered");
    }

    @PostMapping("/connect")
    public ResponseEntity<String> connect(@RequestParam String sender, @RequestParam String receiver) {
        if (!isSafeName(sender) || !isSafeName(receiver)) {
            return ResponseEntity.badRequest().body("Invalid username");
        }
        if (activeUsers.containsKey(receiver) && "waiting".equals(activeUsers.get(receiver))) {
            // Mark both as connected
            activeUsers.put(receiver, "connected");
            activeUsers.put(sender, "connected");
            // Map peers to each other (bidirectional)
            peerConnections.put(sender, receiver);
            peerConnections.put(receiver, sender);
            return ResponseEntity.ok("Connection established");
        }
        return ResponseEntity.status(404).body("User not found or not waiting");
    }

    @GetMapping("/status/{username}")
    public ResponseEntity<String> status(@PathVariable String username) {
        if (!isSafeName(username)) {
            return ResponseEntity.badRequest().body("Invalid username");
        }
        return ResponseEntity.ok(activeUsers.getOrDefault(username, "unknown"));
    }

    // NEW: Returns the peer username for a connected user
    @GetMapping("/connections/{username}")
    public ResponseEntity<String> getPeer(@PathVariable String username) {
        if (!isSafeName(username)) {
            return ResponseEntity.badRequest().body("Invalid username");
        }
        String peer = peerConnections.get(username);
        if (peer == null) {
            return ResponseEntity.status(404).body("No peer found");
        }
        return ResponseEntity.ok(peer);
    }

    @PostMapping("/upload")
    public ResponseEntity<String> upload(@RequestParam("file") MultipartFile file,
                                          @RequestParam String target) {
        // Validate target username
        if (!isSafeName(target)) {
            return ResponseEntity.badRequest().body("Invalid target username");
        }

        // Validate file name
        String originalName = file.getOriginalFilename();
        if (originalName == null || !isSafeName(originalName)) {
            return ResponseEntity.badRequest().body("Invalid file name");
        }

        try {
            Path targetDir = baseDir.resolve(target).normalize();
            // Security check: ensure targetDir is within baseDir
            if (!isWithinBaseDir(targetDir)) {
                return ResponseEntity.badRequest().body("Invalid target path");
            }

            Files.createDirectories(targetDir);
            Path filePath = targetDir.resolve(originalName).normalize();

            // Security check: ensure final file path is within targetDir
            if (!isWithinBaseDir(filePath)) {
                return ResponseEntity.badRequest().body("Invalid file path");
            }

            file.transferTo(filePath.toFile());
            return ResponseEntity.ok("File uploaded");
        } catch (IOException e) {
            return ResponseEntity.status(500).body("Upload failed: " + e.getMessage());
        }
    }

    @GetMapping("/download/{username}/{filename:.+}")
    public ResponseEntity<Resource> download(@PathVariable String username,
                                              @PathVariable String filename) {
        // Validate username and filename
        if (!isSafeName(username) || !isSafeName(filename)) {
            return ResponseEntity.badRequest().build();
        }

        Path filePath = baseDir.resolve(username).resolve(filename).normalize();

        // Security check: ensure file path is within baseDir
        if (!isWithinBaseDir(filePath)) {
            return ResponseEntity.badRequest().build();
        }

        if (!Files.exists(filePath)) return ResponseEntity.notFound().build();

        Resource resource = new FileSystemResource(filePath);
        String contentType = "application/octet-stream";
        try { contentType = Files.probeContentType(filePath); } catch (IOException ignored) {}
        if (contentType == null) contentType = "application/octet-stream";

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .header(HttpHeaders.CONTENT_TYPE, contentType)
                .body(resource);
    }
}