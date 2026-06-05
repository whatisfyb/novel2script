package com.novel.auth.interfaces.rest.assembler;

import com.novel.auth.domain.model.User;
import com.novel.auth.interfaces.rest.dto.LoginResponse;
import org.springframework.stereotype.Component;

/**
 * Assembler — converts domain entities to interface DTOs.
 */
@Component
public class AuthAssembler {

    /**
     * Build a LoginResponse.UserInfo from a User domain entity.
     */
    public LoginResponse.UserInfo toUserInfo(User user) {
        LoginResponse.UserInfo info = new LoginResponse.UserInfo();
        info.setUserId(user.getId().value());
        info.setUsername(user.getUsername());
        info.setEmail(user.getEmail());
        // TODO: derive plan from quota
        info.setPlan(0);
        return info;
    }
}
