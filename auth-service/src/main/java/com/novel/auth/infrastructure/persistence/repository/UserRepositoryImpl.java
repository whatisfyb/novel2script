package com.novel.auth.infrastructure.persistence.repository;

import com.novel.auth.domain.model.User;
import com.novel.auth.domain.model.UserId;
import com.novel.auth.domain.repository.UserRepository;
import com.novel.auth.infrastructure.persistence.converter.UserConverter;
import com.novel.auth.infrastructure.persistence.mapper.UserMapper;
import com.novel.auth.infrastructure.persistence.po.UserPO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * User repository implementation — delegates to MyBatis-Plus mapper.
 */
@Repository
public class UserRepositoryImpl implements UserRepository {

    private final UserMapper userMapper;
    private final UserConverter userConverter;

    public UserRepositoryImpl(UserMapper userMapper, UserConverter userConverter) {
        this.userMapper = userMapper;
        this.userConverter = userConverter;
    }

    @Override
    public Optional<User> findById(UserId id) {
        UserPO po = userMapper.selectById(id.value());
        return Optional.ofNullable(userConverter.toDomain(po));
    }

    @Override
    public Optional<User> findByUsername(String username) {
        UserPO po = userMapper.selectOne(
                new LambdaQueryWrapper<UserPO>().eq(UserPO::getUsername, username));
        return Optional.ofNullable(userConverter.toDomain(po));
    }

    @Override
    public Optional<User> findByEmail(String email) {
        UserPO po = userMapper.selectOne(
                new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email));
        return Optional.ofNullable(userConverter.toDomain(po));
    }

    @Override
    public void save(User user) {
        UserPO po = userConverter.toPO(user);
        // Check if user exists by ID
        UserPO existing = userMapper.selectById(po.getId());
        if (existing == null) {
            userMapper.insert(po);
        } else {
            userMapper.updateById(po);
        }
    }

    @Override
    public boolean existsByUsername(String username) {
        return userMapper.selectCount(
                new LambdaQueryWrapper<UserPO>().eq(UserPO::getUsername, username)) > 0;
    }

    @Override
    public boolean existsByEmail(String email) {
        return userMapper.selectCount(
                new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email)) > 0;
    }
}
