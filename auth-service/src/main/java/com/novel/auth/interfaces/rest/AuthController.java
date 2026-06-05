package com.novel.auth.interfaces.rest;

import com.novel.auth.application.service.AuthAppService;
import com.novel.auth.common.result.R;
import com.novel.auth.interfaces.rest.dto.LoginRequest;
import com.novel.auth.interfaces.rest.dto.LoginResponse;
import com.novel.auth.interfaces.rest.dto.RegisterRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

/**
 * Auth REST controller — handles /api/auth/* endpoints.
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthAppService authAppService;

    public AuthController(AuthAppService authAppService) {
        this.authAppService = authAppService;
    }

    @PostMapping("/register")
    public R<Void> register(@Valid @RequestBody RegisterRequest request) {
        authAppService.register(request);
        return R.ok();
    }

    @PostMapping("/login")
    public R<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authAppService.login(request);
        return R.ok(response);
    }

    @PostMapping("/logout")
    public R<Void> logout() {
        authAppService.logout();
        return R.ok();
    }
}
