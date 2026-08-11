package com.printfilm.api.dto;

public record AuthResponse(
        String token,
        UserResponse user
) {
}
