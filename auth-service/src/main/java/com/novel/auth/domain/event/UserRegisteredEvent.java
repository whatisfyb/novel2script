package com.novel.auth.domain.event;

/**
 * Domain event — fired when a new user registers.
 */
public record UserRegisteredEvent(String userId, String username, String email) {}
