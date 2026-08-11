package com.printfilm.api.dto;

import com.printfilm.api.domain.GenerationJob;
import com.printfilm.api.domain.GenerationStatus;

import java.time.Instant;
import java.util.UUID;

public record VideoGenerationResponse(
        UUID id,
        UUID projectId,
        String nodeId,
        String providerTaskId,
        String model,
        String prompt,
        GenerationStatus status,
        Integer progress,
        String outputUrl,
        String errorMessage,
        Instant createdAt,
        Instant updatedAt
) {
    public static VideoGenerationResponse from(GenerationJob job) {
        return new VideoGenerationResponse(
                job.getId(),
                job.getProjectId(),
                job.getNodeId(),
                job.getProviderTaskId(),
                job.getModel(),
                job.getPrompt(),
                job.getStatus(),
                job.getProgress(),
                job.getOutputUrl(),
                job.getErrorMessage(),
                job.getCreatedAt(),
                job.getUpdatedAt()
        );
    }
}
