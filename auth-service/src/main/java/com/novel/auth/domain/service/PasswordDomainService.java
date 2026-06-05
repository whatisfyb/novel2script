package com.novel.auth.domain.service;

import at.favre.lib.crypto.bcrypt.BCrypt;
import com.novel.auth.common.exception.BusinessException;
import org.springframework.stereotype.Service;

/**
 * Password domain service — handles password hashing and validation rules.
 */
@Service
public class PasswordDomainService {

    private static final int MIN_LENGTH = 8;
    private static final int BCRYPT_COST = 12;

    /**
     * Hash a plaintext password.
     *
     * @param rawPassword the plaintext password
     * @return the hashed password
     * @throws BusinessException if password fails validation
     */
    public String hash(String rawPassword) {
        if (rawPassword == null || rawPassword.length() < MIN_LENGTH) {
            throw new BusinessException("密码长度不能少于8位");
        }
        return BCrypt.withDefaults().hashToString(BCRYPT_COST, rawPassword.toCharArray());
    }

    /**
     * Verify a plaintext password against a hash.
     */
    public boolean verify(String rawPassword, String hashedPassword) {
        if (rawPassword == null || hashedPassword == null) {
            return false;
        }
        BCrypt.Result result = BCrypt.verifyer()
                .verify(rawPassword.toCharArray(), hashedPassword.toCharArray());
        return result.verified;
    }
}
