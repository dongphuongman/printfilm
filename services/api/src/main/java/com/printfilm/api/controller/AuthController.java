package com.printfilm.api.controller;

import com.printfilm.api.common.ApiResponse;
import com.printfilm.api.dto.AuthResponse;
import com.printfilm.api.dto.CreationStatsResponse;
import com.printfilm.api.dto.LoginRequest;
import com.printfilm.api.dto.RegisterRequest;
import com.printfilm.api.dto.UpdateArkKeyRequest;
import com.printfilm.api.dto.UpdateTokenfreeKeyRequest;
import com.printfilm.api.dto.UserResponse;
import com.printfilm.api.service.AuthService;
import com.printfilm.api.service.CreationStatsService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final CreationStatsService creationStatsService;

    public AuthController(AuthService authService, CreationStatsService creationStatsService) {
        this.authService = authService;
        this.creationStatsService = creationStatsService;
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ApiResponse.ok(authService.register(request));
    }

    @PostMapping("/login")
    public ApiResponse<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.ok(authService.login(request));
    }

    @GetMapping("/me")
    public ApiResponse<UserResponse> me() {
        return ApiResponse.ok(authService.me());
    }

    @GetMapping("/me/creation-stats")
    public ApiResponse<CreationStatsResponse> creationStats() {
        return ApiResponse.ok(creationStatsService.todayStats());
    }

    @PutMapping("/me/tokenfree-key")
    public ApiResponse<UserResponse> updateTokenfreeKey(@Valid @RequestBody UpdateTokenfreeKeyRequest request) {
        return ApiResponse.ok(authService.updateTokenfreeKey(request));
    }

    @PutMapping("/me/ark-key")
    public ApiResponse<UserResponse> updateArkKey(@Valid @RequestBody UpdateArkKeyRequest request) {
        return ApiResponse.ok(authService.updateArkKey(request));
    }
}
