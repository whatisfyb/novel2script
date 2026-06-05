package com.novel.auth.interfaces.rest.dto;

import lombok.Data;

/**
 * Login response DTO — contains session token and basic user info.
 */
@Data
public class LoginResponse {

    private String token;
    private UserInfo userInfo;

    @Data
    public static class UserInfo {
        private String userId;
        private String username;
        private String email;
        private int plan;  // 0=free, 1=pro
    }
}
