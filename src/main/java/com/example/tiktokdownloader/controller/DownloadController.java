package com.example.tiktokdownloader.controller;

import com.example.tiktokdownloader.dto.DownloadRequest;
import com.example.tiktokdownloader.exception.DownloadException;
import com.example.tiktokdownloader.service.DownloadService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.InputStream;
import java.net.URL;
import java.net.URLConnection;

@Controller
public class DownloadController {

    private final DownloadService downloadService;

    public DownloadController(DownloadService downloadService) {
        this.downloadService = downloadService;
    }

    @GetMapping("/")
    public String index() {
        return "index";
    }

    @PostMapping("/download")
    public ResponseEntity<StreamingResponseBody> downloadVideo(
            @RequestParam String url,
            HttpServletResponse response) throws DownloadException {

        // Get video URL from TikTok
        String videoUrl = downloadService.getVideoUrl(url);

        if (videoUrl == null || videoUrl.isEmpty()) {
            throw new DownloadException("Could not extract video URL");
        }

        // Set up filename
        String filename = "tiktok_" + System.currentTimeMillis() + ".mp4";

        // Set response headers
        response.setContentType("video/mp4");
        response.setHeader("Content-Disposition", "attachment; filename=\"" + filename + "\"");

        // Stream the video directly to response
        StreamingResponseBody stream = outputStream -> {
            try {
                URL videoURL = new URL(videoUrl);
                URLConnection connection = videoURL.openConnection();
                connection.setRequestProperty("User-Agent", "Mozilla/5.0...");
                connection.setRequestProperty("Referer", "https://www.tiktok.com/");

                try (InputStream inputStream = connection.getInputStream()) {
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = inputStream.read(buffer)) != -1) {
                        outputStream.write(buffer, 0, bytesRead);
                    }
                }
            } catch (Exception e) {
                try {
                    throw new DownloadException("Download failed: " + e.getMessage());
                } catch (DownloadException ex) {
                    throw new RuntimeException(ex);
                }
            }
        };

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(stream);
    }
}