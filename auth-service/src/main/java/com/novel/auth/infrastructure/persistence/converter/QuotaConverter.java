package com.novel.auth.infrastructure.persistence.converter;

import com.novel.auth.domain.model.Quota;
import com.novel.auth.infrastructure.persistence.po.QuotaPO;
import org.springframework.stereotype.Component;

/**
 * Converter — maps between Quota domain value object and QuotaPO persistence object.
 */
@Component
public class QuotaConverter {

    public Quota toDomain(QuotaPO po) {
        if (po == null) return null;
        return new Quota(po.getPlan(), po.getRemaining(), po.getResetAt());
    }

    public QuotaPO toPO(Quota quota, String userId) {
        if (quota == null) return null;
        QuotaPO po = new QuotaPO();
        po.setUserId(userId);
        po.setPlan(quota.getPlan());
        po.setRemaining(quota.getRemaining());
        po.setResetAt(quota.getResetAt());
        return po;
    }
}
