package com.novel.auth.infrastructure.persistence.repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.novel.auth.domain.model.Quota;
import com.novel.auth.domain.repository.QuotaRepository;
import com.novel.auth.infrastructure.persistence.converter.QuotaConverter;
import com.novel.auth.infrastructure.persistence.mapper.QuotaMapper;
import com.novel.auth.infrastructure.persistence.po.QuotaPO;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * Quota repository implementation — delegates to MyBatis-Plus mapper.
 */
@Repository
public class QuotaRepositoryImpl implements QuotaRepository {

    private final QuotaMapper quotaMapper;
    private final QuotaConverter quotaConverter;

    public QuotaRepositoryImpl(QuotaMapper quotaMapper, QuotaConverter quotaConverter) {
        this.quotaMapper = quotaMapper;
        this.quotaConverter = quotaConverter;
    }

    @Override
    public Optional<Quota> findByUserId(String userId) {
        QuotaPO po = quotaMapper.selectOne(
                new LambdaQueryWrapper<QuotaPO>().eq(QuotaPO::getUserId, userId));
        return Optional.ofNullable(quotaConverter.toDomain(po));
    }

    @Override
    public void save(String userId, Quota quota) {
        QuotaPO po = quotaConverter.toPO(quota, userId);
        QuotaPO existing = quotaMapper.selectOne(
                new LambdaQueryWrapper<QuotaPO>().eq(QuotaPO::getUserId, userId));
        if (existing == null) {
            quotaMapper.insert(po);
        } else {
            po.setId(existing.getId());
            quotaMapper.updateById(po);
        }
    }

    @Override
    public void updateRemaining(String userId, int remaining) {
        quotaMapper.update(null,
                new LambdaUpdateWrapper<QuotaPO>()
                        .eq(QuotaPO::getUserId, userId)
                        .set(QuotaPO::getRemaining, remaining)
                        .set(QuotaPO::getUpdatedAt, LocalDateTime.now()));
    }
}
