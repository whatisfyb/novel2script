package com.novel.auth.infrastructure.persistence.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * User persistence object — maps to the "users" table.
 */
@Data
@TableName("users")
public class UserPO {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    private String username;
    private String email;
    private String passwordHash;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
