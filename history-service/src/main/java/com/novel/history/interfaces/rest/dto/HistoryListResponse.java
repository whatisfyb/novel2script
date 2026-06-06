package com.novel.history.interfaces.rest.dto;

import lombok.Data;

import java.util.List;

/**
 * History list response DTO — contains list of histories and total count.
 */
@Data
public class HistoryListResponse {

    private long total;
    private List<HistoryResponse> items;
}
