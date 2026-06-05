package com.novel.auth.domain.model;

import java.util.Objects;
import java.util.UUID;

/**
 * User identity value object — wraps the raw UUID string.
 */
public record UserId(String value) {

    public UserId {
        Objects.requireNonNull(value, "UserId must not be null");
    }

    public static UserId generate() {
        return new UserId(UUID.randomUUID().toString().replace("-", ""));
    }

    @Override
    public String toString() {
        return value;
    }
}
