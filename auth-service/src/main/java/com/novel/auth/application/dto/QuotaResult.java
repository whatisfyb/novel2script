package com.novel.auth.application.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * DTO returned by quota check operations.
 */
@Data
public class QuotaResult {

    private boolean allowed;
    private int remaining;
    private LocalDateTime resetAt;

    public QuotaResult() {}

    public QuotaResult(boolean allowed, int remaining, LocalDateTime resetAt) {
        this.allowed = allowed;
        this.remaining = remaining;
        this.resetAt = resetAt;
    }
}
