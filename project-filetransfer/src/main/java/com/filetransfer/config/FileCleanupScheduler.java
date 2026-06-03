package com.filetransfer.config;

import jakarta.annotation.PostConstruct;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.FileTime;
import java.time.Instant;

@Component
@EnableScheduling
public class FileCleanupScheduler {

    private final Path baseDir;

    public FileCleanupScheduler() {
        this.baseDir = Paths.get(System.getProperty("java.io.tmpdir"), "file-transfer");
    }

    @PostConstruct
    public void init() throws IOException {
        if (!Files.exists(baseDir)) Files.createDirectories(baseDir);
    }

    // Run every 10 minutes
    @Scheduled(fixedRate = 600000)
    public void cleanupOldFiles() {
        try {
            long oneHourAgo = System.currentTimeMillis() - 3600000;
            
            Files.list(baseDir).forEach(userDir -> {
                if (Files.isDirectory(userDir)) {
                    try {
                        Files.list(userDir).forEach(file -> {
                            try {
                                FileTime lastModified = Files.getLastModifiedTime(file);
                                if (lastModified.toMillis() < oneHourAgo) {
                                    Files.delete(file);
                                    System.out.println("Deleted old file: " + file.getFileName());
                                }
                            } catch (IOException e) {
                                e.printStackTrace();
                            }
                        });
                        
                        // Delete empty user directories
                        if (Files.list(userDir).count() == 0) {
                            Files.delete(userDir);
                            System.out.println("Deleted empty directory: " + userDir.getFileName());
                        }
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }
            });
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}