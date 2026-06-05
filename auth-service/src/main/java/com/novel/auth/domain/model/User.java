package com.novel.auth.domain.model;

import java.time.LocalDateTime;

/**
 * User domain entity — core identity aggregate root.
 */
public class User {

    private UserId id;
    private String username;
    private String email;
    private String passwordHash;
    private AccountStatus status;
    private LocalDateTime createdAt;

    public User() {}

    public User(UserId id, String username, String email, String passwordHash,
                AccountStatus status, LocalDateTime createdAt) {
        this.id = id;
        this.username = username;
        this.email = email;
        this.passwordHash = passwordHash;
        this.status = status;
        this.createdAt = createdAt;
    }

    // --- Getters & Setters ---

    public UserId getId() { return id; }
    public void setId(UserId id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }

    public AccountStatus getStatus() { return status; }
    public void setStatus(AccountStatus status) { this.status = status; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
