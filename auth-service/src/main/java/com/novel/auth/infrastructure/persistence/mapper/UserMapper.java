package com.novel.auth.infrastructure.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.novel.auth.infrastructure.persistence.po.UserPO;
import org.apache.ibatis.annotations.Mapper;

/**
 * MyBatis-Plus mapper for the users table.
 */
@Mapper
public interface UserMapper extends BaseMapper<UserPO> {
}
