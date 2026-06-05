package com.novel.auth.application.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * API Key application service — CRUD for user API keys.
 */
@Service
public class ApiKeyAppService {

    private static final Logger log = LoggerFactory.getLogger(ApiKeyAppService.class);

    /**
     * Create a new API key for a user.
     *
     * @param userId the owner
     * @return the generated key string
     */
    public String createApiKey(String userId) {
        // TODO: generate key → save to DB → return plaintext (only shown once)
        log.info("CreateApiKey stub called for userId={}", userId);
        return "sk-stub-" + userId;
    }

    /**
     * Revoke (soft-delete) an API key.
     *
     * @param userId the owner
     * @param keyId  the key to revoke
     */
    public void revokeApiKey(String userId, String keyId) {
        // TODO: mark key as revoked in DB
        log.info("RevokeApiKey stub called for userId={}, keyId={}", userId, keyId);
    }
}
