package com.novel.history.application.service;

import com.novel.history.common.exception.BusinessException;
import com.novel.history.domain.model.ConversionHistory;
import com.novel.history.domain.model.ConversionStatus;
import com.novel.history.domain.repository.HistoryRepository;
import com.novel.history.interfaces.rest.dto.CreateHistoryRequest;
import com.novel.history.interfaces.rest.dto.HistoryListResponse;
import com.novel.history.interfaces.rest.dto.HistoryResponse;
import com.novel.history.interfaces.rest.dto.UpdateHistoryRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * History application service — orchestrates conversion history CRUD use cases.
 */
@Service
public class HistoryAppService {

    private static final Logger log = LoggerFactory.getLogger(HistoryAppService.class);

    private final HistoryRepository historyRepository;

    public HistoryAppService(HistoryRepository historyRepository) {
        this.historyRepository = historyRepository;
    }

    /**
     * Create a new conversion history record.
     *
     * @param request creation form
     * @return created history response
     */
    @Transactional
    public HistoryResponse create(CreateHistoryRequest request) {
        // Check if runId already exists
        historyRepository.findByRunId(request.getRunId())
                .ifPresent(h -> {
                    throw new BusinessException("Run ID already exists: " + request.getRunId());
                });

        ConversionHistory history = new ConversionHistory();
        history.setRunId(request.getRunId());
        history.setUserId(request.getUserId());
        history.setFilename(request.getFilename());
        history.setTitle(request.getTitle());
        history.setScriptType(request.getScriptType());
        history.setLanguage(request.getLanguage());
        history.setStatus(ConversionStatus.PROCESSING.name());
        history.setChapters(0);
        history.setActs(0);
        history.setScenes(0);
        history.setCharacters(0);
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());

        historyRepository.save(history);
        log.info("Conversion history created: runId={}", request.getRunId());

        return toResponse(history);
    }

    /**
     * Get a conversion history by runId.
     *
     * @param runId conversion run ID
     * @return history response
     */
    public HistoryResponse getByRunId(String runId) {
        ConversionHistory history = historyRepository.findByRunId(runId)
                .orElseThrow(() -> new BusinessException(404, "History not found: " + runId));
        return toResponse(history);
    }

    /**
     * List conversion histories with pagination and optional filters.
     *
     * @param page       page number (1-indexed)
     * @param size       page size
     * @param scriptType optional filter by script type
     * @param status     optional filter by status
     * @return paginated history list
     */
    public HistoryListResponse list(int page, int size, String scriptType, String status) {
        List<ConversionHistory> histories = historyRepository.findAll(page, size, scriptType, status);
        long total = historyRepository.count(scriptType, status);

        List<HistoryResponse> responses = histories.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());

        HistoryListResponse listResponse = new HistoryListResponse();
        listResponse.setTotal(total);
        listResponse.setItems(responses);
        return listResponse;
    }

    /**
     * Update a conversion history by runId.
     *
     * @param runId   conversion run ID
     * @param request update form (nullable fields)
     * @return updated history response
     */
    @Transactional
    public HistoryResponse update(String runId, UpdateHistoryRequest request) {
        ConversionHistory history = historyRepository.findByRunId(runId)
                .orElseThrow(() -> new BusinessException(404, "History not found: " + runId));

        if (request.getStatus() != null) {
            history.setStatus(request.getStatus());
        }
        if (request.getChapters() != null) {
            history.setChapters(request.getChapters());
        }
        if (request.getActs() != null) {
            history.setActs(request.getActs());
        }
        if (request.getScenes() != null) {
            history.setScenes(request.getScenes());
        }
        if (request.getCharacters() != null) {
            history.setCharacters(request.getCharacters());
        }
        if (request.getYaml() != null) {
            history.setYaml(request.getYaml());
        }
        if (request.getError() != null) {
            history.setError(request.getError());
        }
        history.setUpdatedAt(LocalDateTime.now());

        historyRepository.save(history);
        log.info("Conversion history updated: runId={}", runId);

        return toResponse(history);
    }

    /**
     * Delete a conversion history by runId.
     *
     * @param runId conversion run ID
     */
    @Transactional
    public void delete(String runId) {
        historyRepository.findByRunId(runId)
                .orElseThrow(() -> new BusinessException(404, "History not found: " + runId));
        historyRepository.deleteByRunId(runId);
        log.info("Conversion history deleted: runId={}", runId);
    }

    /**
     * Convert domain entity to response DTO.
     */
    private HistoryResponse toResponse(ConversionHistory history) {
        HistoryResponse response = new HistoryResponse();
        response.setId(history.getId());
        response.setRunId(history.getRunId());
        response.setUserId(history.getUserId());
        response.setFilename(history.getFilename());
        response.setTitle(history.getTitle());
        response.setScriptType(history.getScriptType());
        response.setLanguage(history.getLanguage());
        response.setStatus(history.getStatus());
        response.setChapters(history.getChapters());
        response.setActs(history.getActs());
        response.setScenes(history.getScenes());
        response.setCharacters(history.getCharacters());
        response.setYaml(history.getYaml());
        response.setError(history.getError());
        response.setCreatedAt(history.getCreatedAt());
        response.setUpdatedAt(history.getUpdatedAt());
        return response;
    }
}
