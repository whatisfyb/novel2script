package com.novel.history.interfaces.rest.dto;

import lombok.Data;

/**
 * Update history request DTO — all fields are nullable (partial update).
 */
@Data
public class UpdateHistoryRequest {

    private String status;
    private Integer chapters;
    private Integer acts;
    private Integer scenes;
    private Integer characters;
    private String yaml;
    private String error;
}
