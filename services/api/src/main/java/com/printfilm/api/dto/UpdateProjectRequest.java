package com.printfilm.api.dto;

import com.printfilm.api.domain.ProjectType;
import jakarta.validation.constraints.Size;

public record UpdateProjectRequest(
        @Size(max = 200) String name,
        ProjectType type,
        @Size(max = 1000) String description
) {}
