package com.novel.auth.infrastructure.persistence.repository;

import com.novel.auth.infrastructure.persistence.mapper.ApiKeyMapper;
import org.springframework.stereotype.Repository;

/**
 * API Key repository implementation.
 */
@Repository
public class ApiKeyRepositoryImpl {

    private final ApiKeyMapper apiKeyMapper;

    public ApiKeyRepositoryImpl(ApiKeyMapper apiKeyMapper) {
        this.apiKeyMapper = apiKeyMapper;
    }

    // TODO: implement CRUD methods delegating to apiKeyMapper
}
