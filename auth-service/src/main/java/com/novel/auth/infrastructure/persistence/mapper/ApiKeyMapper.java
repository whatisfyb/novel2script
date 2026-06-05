package com.novel.auth.infrastructure.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.novel.auth.infrastructure.persistence.po.ApiKeyPO;
import org.apache.ibatis.annotations.Mapper;

/**
 * MyBatis-Plus mapper for the api_keys table.
 */
@Mapper
public interface ApiKeyMapper extends BaseMapper<ApiKeyPO> {
}
