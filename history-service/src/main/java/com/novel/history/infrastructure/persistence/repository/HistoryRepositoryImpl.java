package com.novel.history.infrastructure.persistence.repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.novel.history.domain.model.ConversionHistory;
import com.novel.history.domain.repository.HistoryRepository;
import com.novel.history.infrastructure.persistence.converter.HistoryConverter;
import com.novel.history.infrastructure.persistence.mapper.HistoryMapper;
import com.novel.history.infrastructure.persistence.po.HistoryPO;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * History repository implementation — delegates to MyBatis-Plus mapper.
 */
@Repository
public class HistoryRepositoryImpl implements HistoryRepository {

    private final HistoryMapper historyMapper;
    private final HistoryConverter historyConverter;

    public HistoryRepositoryImpl(HistoryMapper historyMapper, HistoryConverter historyConverter) {
        this.historyMapper = historyMapper;
        this.historyConverter = historyConverter;
    }

    @Override
    public Optional<ConversionHistory> findById(String id) {
        HistoryPO po = historyMapper.selectById(id);
        return Optional.ofNullable(historyConverter.toDomain(po));
    }

    @Override
    public Optional<ConversionHistory> findByRunId(String runId) {
        HistoryPO po = historyMapper.selectOne(
                new LambdaQueryWrapper<HistoryPO>().eq(HistoryPO::getRunId, runId));
        return Optional.ofNullable(historyConverter.toDomain(po));
    }

    @Override
    public List<ConversionHistory> findAll(int page, int size, String scriptType, String status) {
        LambdaQueryWrapper<HistoryPO> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(scriptType)) {
            wrapper.eq(HistoryPO::getScriptType, scriptType);
        }
        if (StringUtils.hasText(status)) {
            wrapper.eq(HistoryPO::getStatus, status);
        }
        wrapper.orderByDesc(HistoryPO::getCreatedAt);

        Page<HistoryPO> pageParam = new Page<>(page, size);
        Page<HistoryPO> result = historyMapper.selectPage(pageParam, wrapper);
        return result.getRecords().stream()
                .map(historyConverter::toDomain)
                .collect(Collectors.toList());
    }

    @Override
    public void save(ConversionHistory history) {
        HistoryPO po = historyConverter.toPO(history);
        if (po.getId() == null) {
            historyMapper.insert(po);
            history.setId(po.getId());
        } else {
            historyMapper.updateById(po);
        }
    }

    @Override
    public void deleteByRunId(String runId) {
        historyMapper.delete(
                new LambdaQueryWrapper<HistoryPO>().eq(HistoryPO::getRunId, runId));
    }

    @Override
    public long count(String scriptType, String status) {
        LambdaQueryWrapper<HistoryPO> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(scriptType)) {
            wrapper.eq(HistoryPO::getScriptType, scriptType);
        }
        if (StringUtils.hasText(status)) {
            wrapper.eq(HistoryPO::getStatus, status);
        }
        return historyMapper.selectCount(wrapper);
    }
}
