package com.novel.auth.domain.repository;

import com.novel.auth.domain.model.User;
import com.novel.auth.domain.model.UserId;

import java.util.Optional;

/**
 * User repository interface — defined in domain layer, implemented in infrastructure.
 */
public interface UserRepository {

    Optional<User> findById(UserId id);

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    void save(User user);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);
}
