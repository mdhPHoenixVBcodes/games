package com.filetransfer.controller;

import com.filetransfer.config.SecurityConfig;
import com.filetransfer.config.TransferWebSocketHandler;
import jakarta.annotation.PostConstruct;
import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.*;
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
    private final Map<String, ChunkedUpload> chunkedUploads = new ConcurrentHashMap<>();

    public FileTransferController() {
        this.baseDir = Paths.get(System.getProperty("java.io.tmpdir"), "file-transfer");
    }

    @PostConstruct
    public void init() throws IOException {
        if (!Files.exists(baseDir)) Files.createDirectories(baseDir);
    }

    // Generate session token
    @PostMapping("/token")
    public ResponseEntity<Map<String, String>> generateToken(@RequestParam String username) {
        String token = SecurityConfig.generateToken(username);
        Map<String, String> response = new HashMap<>();
        response.put("token", token);
        response.put("username", username);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/register")
    public ResponseEntity<String> register(@RequestParam String username, 
                                           @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, username)) {
            return ResponseEntity.status(401).body("Invalid or expired token");
        }
        
        registry.put(username, "waiting");
        TransferWebSocketHandler.sendMessage(username, "{\"type\":\"registered\",\"username\":\"" + username + "\"}");
        return ResponseEntity.ok("Registered");
    }

    @PostMapping("/connect")
    public ResponseEntity<String> connect(@RequestParam String sender, 
                                          @RequestParam String receiver,
                                          @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, sender)) {
            return ResponseEntity.status(401).body("Invalid or expired token");
        }
        
        if (registry.containsKey(receiver) && "waiting".equals(registry.get(receiver))) {
            registry.put(receiver, "connected");
            registry.put(sender, "connected");
            
            // Notify both users via WebSocket
            TransferWebSocketHandler.sendMessage(receiver, "{\"type\":\"connected\",\"from\":\"" + sender + "\"}");
            TransferWebSocketHandler.sendMessage(sender, "{\"type\":\"connected\",\"to\":\"" + receiver + "\"}");
            
            return ResponseEntity.ok("Connection established");
        }
        return ResponseEntity.status(404).body("User not found or not waiting");
    }

    @GetMapping("/status/{username}")
    public ResponseEntity<String> status(@PathVariable String username) {
        return ResponseEntity.ok(registry.getOrDefault(username, "unknown"));
    }

    // Chunked upload - initialize
    @PostMapping("/upload/chunk/init")
    public ResponseEntity<Map<String, String>> initChunkedUpload(@RequestParam String filename,
                                                                   @RequestParam long totalSize,
                                                                   @RequestParam String target,
                                                                   @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, target)) {
            return ResponseEntity.status(401).body(Map.of("error", "Invalid token"));
        }

        String uploadId = UUID.randomUUID().toString();
        Path tempDir = baseDir.resolve("temp").resolve(uploadId);
        
        try {
            Files.createDirectories(tempDir);
            chunkedUploads.put(uploadId, new ChunkedUpload(filename, totalSize, target, tempDir));
            
            Map<String, String> response = new HashMap<>();
            response.put("uploadId", uploadId);
            return ResponseEntity.ok(response);
        } catch (IOException e) {
            return ResponseEntity.status(500).body(Map.of("error", "Failed to initialize upload"));
        }
    }

    // Chunked upload - upload chunk
    @PostMapping("/upload/chunk")
    public ResponseEntity<String> uploadChunk(@RequestParam String uploadId,
                                               @RequestParam int chunkIndex,
                                               @RequestParam("file") MultipartFile chunk,
                                               @RequestParam(required = false) String token) {
        ChunkedUpload upload = chunkedUploads.get(uploadId);
        if (upload == null) {
            return ResponseEntity.status(404).body("Upload session not found");
        }

        try {
            Path chunkPath = upload.tempDir.resolve("chunk_" + chunkIndex);
            chunk.transferTo(chunkPath.toFile());
            
            // Check if all chunks received
            if (upload.markChunkReceived(chunkIndex)) {
                // Assemble file
                Path finalPath = baseDir.resolve(upload.target).resolve(upload.filename);
                Files.createDirectories(finalPath.getParent());
                
                try (OutputStream os = Files.newOutputStream(finalPath)) {
                    int i = 0;
                    Path chunkFile;
                    while ((chunkFile = upload.tempDir.resolve("chunk_" + i)).toFile().exists()) {
                        Files.copy(chunkFile, os);
                        Files.delete(chunkFile);
                        i++;
                    }
                }
                
                chunkedUploads.remove(uploadId);
                Files.deleteIfExists(upload.tempDir);
                
                // Notify receiver via WebSocket
                TransferWebSocketHandler.sendMessage(upload.target, 
                    "{\"type\":\"fileReceived\",\"filename\":\"" + upload.filename + "\"}");
                
                return ResponseEntity.ok("Upload complete");
            }
            
            return ResponseEntity.ok("Chunk uploaded");
        } catch (IOException e) {
            return ResponseEntity.status(500).body("Upload failed: " + e.getMessage());
        }
    }

    // Regular upload (for small files)
    @PostMapping("/upload")
    public ResponseEntity<String> upload(@RequestParam("file") MultipartFile file,
                                         @RequestParam String target,
                                         @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, target)) {
            return ResponseEntity.status(401).body("Invalid or expired token");
        }
        
        try {
            Path targetDir = baseDir.resolve(target);
            Files.createDirectories(targetDir);
            Path filePath = targetDir.resolve(file.getOriginalFilename());
            
            // Use streaming for memory efficiency
            try (InputStream is = file.getInputStream();
                 OutputStream os = Files.newOutputStream(filePath)) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {
                    os.write(buffer, 0, bytesRead);
                }
            }
            
            // Notify receiver via WebSocket
            TransferWebSocketHandler.sendMessage(target, 
                "{\"type\":\"fileReceived\",\"filename\":\"" + file.getOriginalFilename() + "\"}");
            
            return ResponseEntity.ok("File uploaded");
        } catch (IOException e) {
            return ResponseEntity.status(500).body("Upload failed: " + e.getMessage());
        }
    }

    @GetMapping("/files/{username}")
    public ResponseEntity<List<Map<String, String>>> listFiles(@PathVariable String username,
                                                                @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, username)) {
            return ResponseEntity.status(401).body(Collections.emptyList());
        }
        
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
    public ResponseEntity<Resource> download(@PathVariable String username,
                                             @PathVariable String filename,
                                             @RequestParam(required = false) String token) throws IOException {
        if (token != null && !SecurityConfig.validateToken(token, username)) {
            return ResponseEntity.status(401).build();
        }
        
        Path filePath = baseDir.resolve(username).resolve(filename);
        if (!Files.exists(filePath)) return ResponseEntity.notFound().build();
        
        // Delete file after download (auto-cleanup)
        Files.delete(filePath);
        
        Resource resource = new InputStreamResource(Files.newInputStream(filePath));
        String contentType = "application/octet-stream";
        try { contentType = Files.probeContentType(filePath); } catch (IOException ignored) {}
        
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(MediaType.parseMediaType(contentType))
                .contentLength(Files.size(filePath))
                .body(resource);
    }

    // Delete file manually
    @DeleteMapping("/file/{username}/{filename:.+}")
    public ResponseEntity<String> deleteFile(@PathVariable String username,
                                             @PathVariable String filename,
                                             @RequestParam(required = false) String token) {
        if (token != null && !SecurityConfig.validateToken(token, username)) {
            return ResponseEntity.status(401).body("Invalid token");
        }
        
        Path filePath = baseDir.resolve(username).resolve(filename);
        try {
            if (Files.exists(filePath)) {
                Files.delete(filePath);
                return ResponseEntity.ok("File deleted");
            }
            return ResponseEntity.status(404).body("File not found");
        } catch (IOException e) {
            return ResponseEntity.status(500).body("Delete failed: " + e.getMessage());
        }
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024) + " KB";
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024.0));
        return String.format("%.1f GB", bytes / (1024.0 * 1024.0 * 1024.0));
    }

    // Inner class for chunked uploads
    private static class ChunkedUpload {
        String filename;
        long totalSize;
        String target;
        Path tempDir;
        Set<Integer> receivedChunks = ConcurrentHashMap.newKeySet();
        int totalChunks;

        ChunkedUpload(String filename, long totalSize, String target, Path tempDir) {
            this.filename = filename;
            this.totalSize = totalSize;
            this.target = target;
            this.tempDir = tempDir;
            this.totalChunks = (int) Math.ceil((double) totalSize / (5 * 1024 * 1024)); // 5MB chunks
        }

        boolean markChunkReceived(int chunkIndex) {
            receivedChunks.add(chunkIndex);
            return receivedChunks.size() >= totalChunks;
        }
    }
}