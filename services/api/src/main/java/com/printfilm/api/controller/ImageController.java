package com.printfilm.api.controller;

import com.printfilm.api.common.ApiResponse;
import com.printfilm.api.dto.CreateImageGenerationRequest;
import com.printfilm.api.dto.ImageGenerationResponse;
import com.printfilm.api.dto.ImageModelResponse;
import com.printfilm.api.service.ImageGenerationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/image")
public class ImageController {

    public static final String API_KEY_HEADER = "X-Tokenfree-Api-Key";

    private final ImageGenerationService imageGenerationService;

    public ImageController(ImageGenerationService imageGenerationService) {
        this.imageGenerationService = imageGenerationService;
    }

    @GetMapping("/models")
    public ApiResponse<List<ImageModelResponse>> listModels(
            @RequestHeader(value = API_KEY_HEADER, required = false) String apiKey) {
        return ApiResponse.ok(imageGenerationService.listModels(apiKey));
    }

    @PostMapping("/generations")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<ImageGenerationResponse> create(
            @RequestHeader(value = API_KEY_HEADER, required = false) String apiKey,
            @Valid @RequestBody CreateImageGenerationRequest request) {
        return ApiResponse.ok(imageGenerationService.create(request, apiKey));
    }

    @GetMapping("/generations/{id}")
    public ApiResponse<ImageGenerationResponse> get(@PathVariable UUID id) {
        return ApiResponse.ok(imageGenerationService.get(id));
    }
}
