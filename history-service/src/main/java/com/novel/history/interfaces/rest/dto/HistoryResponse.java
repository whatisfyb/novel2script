package com.novel.history.interfaces.rest.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * History response DTO — all fields from ConversionHistory.
 */
@Data
public class HistoryResponse {

    private String id;
    private String runId;
    private String userId;
    private String filename;
    private String title;
    private String scriptType;
    private String language;
    private String status;
    private Integer chapters;
    private Integer acts;
    private Integer scenes;
    private Integer characters;
    private String yaml;
    private String error;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
