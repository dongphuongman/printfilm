package com.printfilm.api.dto;

import jakarta.validation.constraints.NotBlank;

public record UpdateCanvasRequest(
        @NotBlank String canvasData
) {}
