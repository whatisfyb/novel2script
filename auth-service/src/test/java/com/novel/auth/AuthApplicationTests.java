package com.novel.auth;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

/**
 * Basic smoke test — verifies Spring context loads.
 */
@SpringBootTest
@ActiveProfiles("test")
class AuthApplicationTests {

    @Test
    void contextLoads() {
        // Context loads successfully if no exceptions are thrown
    }
}
