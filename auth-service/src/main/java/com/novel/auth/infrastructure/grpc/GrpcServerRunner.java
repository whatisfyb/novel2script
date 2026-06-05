package com.novel.auth.infrastructure.grpc;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * gRPC server lifecycle hook — runs after Spring context starts.
 * The actual gRPC server is managed by grpc-server-spring-boot-starter;
 * this runner is for any post-startup initialization.
 */
@Component
public class GrpcServerRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(GrpcServerRunner.class);

    @Override
    public void run(ApplicationArguments args) {
        log.info("Auth gRPC server started on port 9090");
    }
}
