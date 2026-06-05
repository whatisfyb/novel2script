package com.novel.auth.application.service;

import com.novel.auth.domain.model.Quota;
import com.novel.auth.domain.repository.QuotaRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * Quota application service — manages user quota checking and consumption.
 */
@Service
public class QuotaAppService {

    private static final Logger log = LoggerFactory.getLogger(QuotaAppService.class);

    private static final int FREE_PLAN_DEFAULT_QUOTA = 10;
    private static final int PRO_PLAN_DEFAULT_QUOTA = 1000;

    private final QuotaRepository quotaRepository;

    public QuotaAppService(QuotaRepository quotaRepository) {
        this.quotaRepository = quotaRepository;
    }

    /**
     * Check whether a user is allowed to perform an action.
     *
     * @param userId the user ID
     * @param action the action type ("convert", "export")
     * @return true if quota allows the action
     */
    public boolean checkQuota(String userId, String action) {
        Optional<Quota> quotaOpt = quotaRepository.findByUserId(userId);
        if (quotaOpt.isEmpty()) {
            // No quota record — create default free plan quota
            Quota defaultQuota = new Quota(0, FREE_PLAN_DEFAULT_QUOTA,
                    LocalDateTime.now().plusMonths(1));
            quotaRepository.save(userId, defaultQuota);
            log.info("Created default quota for userId={}", userId);
            return true;
        }

        Quota quota = quotaOpt.get();

        // Check if quota has reset
        if (quota.getResetAt().isBefore(LocalDateTime.now())) {
            int newRemaining = quota.getPlan() == 0 ? FREE_PLAN_DEFAULT_QUOTA : PRO_PLAN_DEFAULT_QUOTA;
            quotaRepository.updateRemaining(userId, newRemaining);
            log.info("Quota reset for userId={}, newRemaining={}", userId, newRemaining);
            return true;
        }

        boolean allowed = quota.getRemaining() > 0;
        log.info("CheckQuota userId={}, action={}, remaining={}, allowed={}",
                userId, action, quota.getRemaining(), allowed);
        return allowed;
    }

    /**
     * Record usage after a successful action — deducts quota.
     *
     * @param userId            the user ID
     * @param action            the action type
     * @param chaptersProcessed number of chapters processed
     * @param tokensUsed        LLM tokens consumed
     */
    @Transactional
    public void recordUsage(String userId, String action, int chaptersProcessed, long tokensUsed) {
        Optional<Quota> quotaOpt = quotaRepository.findByUserId(userId);
        if (quotaOpt.isEmpty()) {
            log.warn("No quota found for userId={}, skipping recordUsage", userId);
            return;
        }

        Quota quota = quotaOpt.get();
        int newRemaining = Math.max(0, quota.getRemaining() - 1);
        quotaRepository.updateRemaining(userId, newRemaining);

        log.info("RecordUsage userId={}, action={}, chapters={}, tokens={}, newRemaining={}",
                userId, action, chaptersProcessed, tokensUsed, newRemaining);
    }
}
