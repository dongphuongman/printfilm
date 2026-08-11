package com.printfilm.api.dto;

import com.printfilm.api.domain.UserStatus;
import jakarta.validation.constraints.Size;

public record UpdateUserRequest(
        UserStatus status,
        @Size(max = 100) String displayName
) {
}
