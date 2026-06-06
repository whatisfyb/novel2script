package com.novel.history.infrastructure.persistence.converter;

import com.novel.history.domain.model.ConversionHistory;
import com.novel.history.infrastructure.persistence.po.HistoryPO;
import org.springframework.stereotype.Component;

/**
 * Converter — maps between ConversionHistory domain entity and HistoryPO persistence object.
 */
@Component
public class HistoryConverter {

    public ConversionHistory toDomain(HistoryPO po) {
        if (po == null) return null;
        ConversionHistory history = new ConversionHistory();
        history.setId(po.getId());
        history.setRunId(po.getRunId());
        history.setUserId(po.getUserId());
        history.setFilename(po.getFilename());
        history.setTitle(po.getTitle());
        history.setScriptType(po.getScriptType());
        history.setLanguage(po.getLanguage());
        history.setStatus(po.getStatus());
        history.setChapters(po.getChapters());
        history.setActs(po.getActs());
        history.setScenes(po.getScenes());
        history.setCharacters(po.getCharacters());
        history.setYaml(po.getYaml());
        history.setError(po.getError());
        history.setCreatedAt(po.getCreatedAt());
        history.setUpdatedAt(po.getUpdatedAt());
        return history;
    }

    public HistoryPO toPO(ConversionHistory history) {
        if (history == null) return null;
        HistoryPO po = new HistoryPO();
        po.setId(history.getId());
        po.setRunId(history.getRunId());
        po.setUserId(history.getUserId());
        po.setFilename(history.getFilename());
        po.setTitle(history.getTitle());
        po.setScriptType(history.getScriptType());
        po.setLanguage(history.getLanguage());
        po.setStatus(history.getStatus());
        po.setChapters(history.getChapters());
        po.setActs(history.getActs());
        po.setScenes(history.getScenes());
        po.setCharacters(history.getCharacters());
        po.setYaml(history.getYaml());
        po.setError(history.getError());
        po.setCreatedAt(history.getCreatedAt());
        po.setUpdatedAt(history.getUpdatedAt());
        return po;
    }
}
