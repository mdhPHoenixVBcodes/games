package com.filetransfer.controller;

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
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class FileTransferController {

    private final ConcurrentHashMap<String, String> registry = new ConcurrentHashMap<>();
    private final Path baseDir;

    public FileTransferController() {
        this.baseDir = Paths.get(System.getProperty("java.io.tmpdir"), "file-transfer");
    }

    @PostConstruct
    public void init() throws IOException {
        if (!Files.exists(baseDir)) Files.createDirectories(baseDir);
    }

    @PostMapping("/register")
    public ResponseEntity<String> register(@RequestParam String username) {
        registry.put(username, "waiting");
        return ResponseEntity.ok("Registered");
    }

    @PostMapping("/connect")
    public ResponseEntity<String> connect(@RequestParam String sender, @RequestParam String receiver) {
        if (registry.containsKey(receiver) && "waiting".equals(registry.get(receiver))) {
            registry.put(receiver, "connected");
            registry.put(sender, "connected");
            return ResponseEntity.ok("Connection established");
        }
        return ResponseEntity.status(404).body("User not found or not waiting");
    }

    @GetMapping("/status/{username}")
    public ResponseEntity<String> status(@PathVariable String username) {
        return ResponseEntity.ok(registry.getOrDefault(username, "unknown"));
    }

    @PostMapping("/upload")
    public ResponseEntity<String> upload(@RequestParam("file") MultipartFile file, @RequestParam String target) {
        try {
            Path targetDir = baseDir.resolve(target);
            Files.createDirectories(targetDir);
            Path filePath = targetDir.resolve(file.getOriginalFilename());
            file.transferTo(filePath.toFile());
            return ResponseEntity.ok("File uploaded");
        } catch (IOException e) {
            return ResponseEntity.status(500).body("Upload failed: " + e.getMessage());
        }
    }

    @GetMapping("/files/{username}")
    public ResponseEntity<List<Map<String, String>>> listFiles(@PathVariable String username) {
        Path userDir = baseDir.resolve(username);
        if (!Files.exists(userDir)) {
            return ResponseEntity.ok(Collections.emptyList());
        }
        
        try (Stream<Path> paths = Files.list(userDir)) {
            List<Map<String, String>> files = paths
                .filter(Files::isRegularFile)
                .map(path -> {
                    Map<String, String> fileInfo = new HashMap<>();
                    fileInfo.put("name", path.getFileName().toString());
                    try {
                        long size = Files.size(path);
                        fileInfo.put("size", formatSize(size));
                        fileInfo.put("sizeBytes", String.valueOf(size));
                    } catch (IOException e) {
                        fileInfo.put("size", "Unknown");
                        fileInfo.put("sizeBytes", "0");
                    }
                    return fileInfo;
                })
                .collect(Collectors.toList());
            return ResponseEntity.ok(files);
        } catch (IOException e) {
            return ResponseEntity.status(500).body(Collections.emptyList());
        }
    }

    @GetMapping("/download/{username}/{filename:.+}")
    public ResponseEntity<Resource> download(@PathVariable String username, @PathVariable String filename) {
        Path filePath = baseDir.resolve(username).resolve(filename);
        if (!Files.exists(filePath)) return ResponseEntity.notFound().build();
        Resource resource = new FileSystemResource(filePath);
        String contentType = "application/octet-stream";
        try { contentType = Files.probeContentType(filePath); } catch (IOException ignored) {}
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .header(HttpHeaders.CONTENT_TYPE, contentType)
                .body(resource);
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024) + " KB";
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024.0));
        return String.format("%.1f GB", bytes / (1024.0 * 1024.0 * 1024.0));
    }
}