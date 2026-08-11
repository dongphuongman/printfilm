package com.printfilm.api.dramaforge.controller;

import com.printfilm.api.dramaforge.dto.DramaForgeDtos.AgentChatRequest;
import com.printfilm.api.dramaforge.dto.DramaForgeDtos.AgentChatResponse;
import com.printfilm.api.dramaforge.service.DramaForgeAgentService;
import com.printfilm.api.dramaforge.service.DramaForgeService;
import com.printfilm.api.common.ApiResponse;
import com.printfilm.api.controller.ImageController;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/dramaforge/projects/{projectId}")
public class DramaForgeAgentController {

    private final DramaForgeAgentService agentService;
    private final DramaForgeService dramaForgeService;

    public DramaForgeAgentController(DramaForgeAgentService agentService, DramaForgeService dramaForgeService) {
        this.agentService = agentService;
        this.dramaForgeService = dramaForgeService;
    }

    @PostMapping("/agent/chat")
    public ApiResponse<AgentChatResponse> chat(
            @PathVariable UUID projectId,
            @Valid @RequestBody AgentChatRequest request,
            @RequestHeader(value = ImageController.API_KEY_HEADER, required = false) String apiKey) {
        dramaForgeService.ensureConfig(projectId);
        return ApiResponse.ok(agentService.chat(projectId, request, apiKey));
    }
}
