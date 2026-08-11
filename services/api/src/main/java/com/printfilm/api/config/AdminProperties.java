package com.printfilm.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "printfilm.admin")
public record AdminProperties(
        String email,
        String password,
        String displayName,
        boolean autoCreate
) {
}
