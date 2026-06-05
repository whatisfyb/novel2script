package com.novel.auth.domain.event;

/**
 * Domain event — fired when a user's quota reaches zero.
 */
public record QuotaExhaustedEvent(String userId, String action) {}
