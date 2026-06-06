package com.novel.history.domain.repository;

import com.novel.history.domain.model.ConversionHistory;

import java.util.List;
import java.util.Optional;

/**
 * History repository interface — defined in domain layer, implemented in infrastructure.
 */
public interface HistoryRepository {

    Optional<ConversionHistory> findById(String id);

    Optional<ConversionHistory> findByRunId(String runId);

    List<ConversionHistory> findAll(int page, int size, String scriptType, String status);

    void save(ConversionHistory history);

    void deleteByRunId(String runId);

    long count(String scriptType, String status);
}
