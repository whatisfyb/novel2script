package com.novel.history.interfaces.rest.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * Create history request DTO.
 */
@Data
public class CreateHistoryRequest {

    @NotBlank(message = "Run ID is required")
    private String runId;

    private String userId;

    @NotBlank(message = "Filename is required")
    private String filename;

    private String title;

    @NotBlank(message = "Script type is required")
    private String scriptType;

    @NotBlank(message = "Language is required")
    private String language;
}
