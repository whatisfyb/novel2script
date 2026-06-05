package com.novel.auth.infrastructure.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.novel.auth.infrastructure.persistence.po.QuotaPO;
import org.apache.ibatis.annotations.Mapper;

/**
 * MyBatis-Plus mapper for the user_quota table.
 */
@Mapper
public interface QuotaMapper extends BaseMapper<QuotaPO> {
}
