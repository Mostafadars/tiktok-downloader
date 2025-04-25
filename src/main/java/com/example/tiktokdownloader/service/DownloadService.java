package com.example.tiktokdownloader.service;

import com.example.tiktokdownloader.dto.DownloadRequest;
import com.example.tiktokdownloader.exception.DownloadException;
import org.springframework.stereotype.Service;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class DownloadService {

    public String downloadVideo(DownloadRequest request) throws DownloadException {
        String url = request.getUrl().trim();
        String saveLocation = request.getSaveLocation();

        if (url.isEmpty()) {
            throw new DownloadException("Please enter a TikTok URL");
        }

        if (!url.contains("tiktok.com")) {
            throw new DownloadException("Invalid TikTok URL");
        }

        try {
            // Step 1: Get the actual video URL
            String videoUrl = getVideoUrl(url);

            if (videoUrl == null || videoUrl.isEmpty()) {
                throw new DownloadException("Could not extract video URL");
            }

            // Ensure URL is complete
            if (videoUrl.startsWith("//")) {
                videoUrl = "https:" + videoUrl;
            } else if (videoUrl.startsWith("/")) {
                videoUrl = "https://www.tiktok.com" + videoUrl;
            }

            // Step 2: Prepare filename
            Pattern pattern = Pattern.compile("/video/(\\d+)");
            Matcher matcher = pattern.matcher(url);
            String videoId = matcher.find() ? matcher.group(1) : "video";
            String filename = "tiktok_" + videoId + ".mp4";
            Path savePath = Paths.get(saveLocation, filename);

            // Step 3: Download the video
            URL videoURL = new URL(videoUrl);
            URLConnection connection = videoURL.openConnection();
            connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");
            connection.setRequestProperty("Referer", "https://www.tiktok.com/");

            try (InputStream in = connection.getInputStream();
                 BufferedInputStream bis = new BufferedInputStream(in);
                 FileOutputStream fos = new FileOutputStream(savePath.toFile());
                 BufferedOutputStream bos = new BufferedOutputStream(fos)) {

                byte[] buffer = new byte[8192];
                int bytesRead;

                while ((bytesRead = bis.read(buffer)) != -1) {
                    bos.write(buffer, 0, bytesRead);
                }
            }

            return savePath.toString();

        } catch (Exception e) {
            throw new DownloadException("Failed to download video: " + e.getMessage());
        }
    }

    public String getVideoUrl(String tiktokUrl) throws DownloadException {
        try {
            // First try using tikwm API
            String apiUrl = "https://www.tikwm.com/api/?url=" + tiktokUrl;
            String apiResponse = sendGetRequest(apiUrl);

            if (apiResponse.contains("\"code\":0")) {
                int playIndex = apiResponse.indexOf("\"play\":\"") + 8;
                int endIndex = apiResponse.indexOf("\"", playIndex);
                return apiResponse.substring(playIndex, endIndex).replace("\\/", "/");
            }

            // Fallback to HTML parsing if API fails
            String html = sendGetRequest(tiktokUrl);

            // Look for video tag
            int videoTagIndex = html.indexOf("<video");
            if (videoTagIndex != -1) {
                int srcIndex = html.indexOf("src=\"", videoTagIndex) + 5;
                int srcEndIndex = html.indexOf("\"", srcIndex);
                return html.substring(srcIndex, srcEndIndex);
            }

            throw new DownloadException("Could not find video URL");
        } catch (Exception e) {
            throw new DownloadException("Error extracting video URL: " + e.getMessage());
        }
    }

    private String sendGetRequest(String urlString) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");
        connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");

        try (BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()))) {
            String inputLine;
            StringBuilder response = new StringBuilder();

            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }

            return response.toString();
        }
    }
}