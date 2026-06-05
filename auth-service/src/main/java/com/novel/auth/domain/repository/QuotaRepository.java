package com.novel.auth.domain.repository;

import com.novel.auth.domain.model.Quota;

import java.util.Optional;

/**
 * Quota repository interface — defined in domain layer, implemented in infrastructure.
 */
public interface QuotaRepository {

    Optional<Quota> findByUserId(String userId);

    void save(String userId, Quota quota);

    void updateRemaining(String userId, int remaining);
}
