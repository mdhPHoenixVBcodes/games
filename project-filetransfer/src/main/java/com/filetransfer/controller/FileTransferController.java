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
import java.util.concurrent.ConcurrentHashMap;

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
}