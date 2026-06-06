package com.novel.history.infrastructure.persistence.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ConversionHistory persistence object — maps to the "conversion_history" table.
 */
@Data
@TableName("conversion_history")
public class HistoryPO {

    @TableId(type = IdType.ASSIGN_UUID)
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
}
