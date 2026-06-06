package com.novel.history.infrastructure.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.novel.history.infrastructure.persistence.po.HistoryPO;
import org.apache.ibatis.annotations.Mapper;

/**
 * MyBatis-Plus mapper for the conversion_history table.
 */
@Mapper
public interface HistoryMapper extends BaseMapper<HistoryPO> {
}
