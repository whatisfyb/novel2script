package com.novel.auth.domain.model;

import java.time.LocalDateTime;

/**
 * Quota value object — tracks a user's remaining usage allowance.
 */
public class Quota {

    private int plan;           // 0=free, 1=pro
    private int remaining;
    private LocalDateTime resetAt;

    public Quota() {}

    public Quota(int plan, int remaining, LocalDateTime resetAt) {
        this.plan = plan;
        this.remaining = remaining;
        this.resetAt = resetAt;
    }

    public int getPlan() { return plan; }
    public void setPlan(int plan) { this.plan = plan; }

    public int getRemaining() { return remaining; }
    public void setRemaining(int remaining) { this.remaining = remaining; }

    public LocalDateTime getResetAt() { return resetAt; }
    public void setResetAt(LocalDateTime resetAt) { this.resetAt = resetAt; }
}
