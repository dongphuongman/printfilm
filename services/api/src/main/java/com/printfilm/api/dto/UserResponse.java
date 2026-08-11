package com.printfilm.api.dto;

import com.printfilm.api.domain.User;
import com.printfilm.api.domain.UserRole;
import com.printfilm.api.domain.UserStatus;

import java.time.Instant;
import java.util.UUID;

public record UserResponse(
        UUID id,
        String email,
        String displayName,
        UserRole role,
        UserStatus status,
        boolean hasTokenfreeApiKey,
        boolean hasArkApiKey,
        Instant createdAt,
        Instant updatedAt
) {
    public static UserResponse from(User user) {
        return new UserResponse(
                user.getId(),
                user.getEmail(),
                user.getDisplayName(),
                user.getRole(),
                user.getStatus(),
                user.getTokenfreeApiKey() != null && !user.getTokenfreeApiKey().isBlank(),
                user.getArkApiKey() != null && !user.getArkApiKey().isBlank(),
                user.getCreatedAt(),
                user.getUpdatedAt()
        );
    }
}
