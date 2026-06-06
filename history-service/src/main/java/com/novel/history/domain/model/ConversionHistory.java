package com.novel.history.domain.model;

import java.time.LocalDateTime;

/**
 * ConversionHistory domain entity — represents a novel-to-script conversion record.
 */
public class ConversionHistory {

    private String id;
    private String runId;
    private String userId;
    private String filename;
    private String title;
    private String scriptType;
    private String language;
    private String status;
    private Integer chapters;
    private Integer acts;
    private Integer scenes;
    private Integer characters;
    private String yaml;
    private String error;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public ConversionHistory() {}

    // --- Getters & Setters ---

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getRunId() { return runId; }
    public void setRunId(String runId) { this.runId = runId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getFilename() { return filename; }
    public void setFilename(String filename) { this.filename = filename; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getScriptType() { return scriptType; }
    public void setScriptType(String scriptType) { this.scriptType = scriptType; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Integer getChapters() { return chapters; }
    public void setChapters(Integer chapters) { this.chapters = chapters; }

    public Integer getActs() { return acts; }
    public void setActs(Integer acts) { this.acts = acts; }

    public Integer getScenes() { return scenes; }
    public void setScenes(Integer scenes) { this.scenes = scenes; }

    public Integer getCharacters() { return characters; }
    public void setCharacters(Integer characters) { this.characters = characters; }

    public String getYaml() { return yaml; }
    public void setYaml(String yaml) { this.yaml = yaml; }

    public String getError() { return error; }
    public void setError(String error) { this.error = error; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
