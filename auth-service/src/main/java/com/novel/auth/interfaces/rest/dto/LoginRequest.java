package com.novel.auth.interfaces.rest.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * Login request DTO.
 */
@Data
public class LoginRequest {

    @NotBlank(message = "Username is required")
    private String username;

    @NotBlank(message = "Password is required")
    private String password;
}
