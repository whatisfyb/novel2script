package com.novel.auth.infrastructure.persistence.converter;

import com.novel.auth.domain.model.AccountStatus;
import com.novel.auth.domain.model.User;
import com.novel.auth.domain.model.UserId;
import com.novel.auth.infrastructure.persistence.po.UserPO;
import org.springframework.stereotype.Component;

/**
 * Converter — maps between User domain entity and UserPO persistence object.
 */
@Component
public class UserConverter {

    public User toDomain(UserPO po) {
        if (po == null) return null;
        User user = new User();
        user.setId(new UserId(po.getId()));
        user.setUsername(po.getUsername());
        user.setEmail(po.getEmail());
        user.setPasswordHash(po.getPasswordHash());
        user.setStatus(AccountStatus.valueOf(po.getStatus()));
        user.setCreatedAt(po.getCreatedAt());
        return user;
    }

    public UserPO toPO(User user) {
        if (user == null) return null;
        UserPO po = new UserPO();
        po.setId(user.getId() != null ? user.getId().value() : null);
        po.setUsername(user.getUsername());
        po.setEmail(user.getEmail());
        po.setPasswordHash(user.getPasswordHash());
        po.setStatus(user.getStatus() != null ? user.getStatus().name() : null);
        po.setCreatedAt(user.getCreatedAt());
        return po;
    }
}
