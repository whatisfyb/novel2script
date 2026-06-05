package com.novel.auth.infrastructure.persistence.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * API Key persistence object — maps to the "api_keys" table.
 */
@Data
@TableName("api_keys")
public class ApiKeyPO {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    private String userId;
    private String keyHash;
    private String name;
    private boolean revoked;
    private LocalDateTime createdAt;
    private LocalDateTime lastUsedAt;
}
