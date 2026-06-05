package com.novel.auth.domain.service;

import com.novel.auth.domain.model.Quota;
import org.springframework.stereotype.Service;

/**
 * Quota domain service — enforces plan-based usage limits.
 */
@Service
public class QuotaDomainService {

    private static final int FREE_MONTHLY_LIMIT = 10;
    private static final int PRO_MONTHLY_LIMIT = 500;

    /**
     * Determine whether the quota allows a new action.
     */
    public boolean isAllowed(Quota quota) {
        return quota != null && quota.getRemaining() > 0;
    }

    /**
     * Get the monthly limit for a given plan.
     */
    public int getMonthlyLimit(int plan) {
        return plan >= 1 ? PRO_MONTHLY_LIMIT : FREE_MONTHLY_LIMIT;
    }
}
