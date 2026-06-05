package com.novel.auth.infrastructure.persistence.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * Quota persistence object — maps to the "user_quota" table.
 */
@Data
@TableName("user_quota")
public class QuotaPO {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    private String userId;
    private int plan;
    private int remaining;
    private LocalDateTime resetAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
