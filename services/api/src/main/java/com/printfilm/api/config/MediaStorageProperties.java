package com.printfilm.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "printfilm.media")
public record MediaStorageProperties(
        String storagePath,
        String publicBaseUrl,
        String uploadPath,
        String uploadPublicBaseUrl
) {
}
