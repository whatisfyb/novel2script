package com.novel.auth.infrastructure.config;

import org.springframework.context.annotation.Configuration;

/**
 * gRPC server configuration.
 *
 * Actual port and settings are configured via application.yml:
 *   grpc.server.port=9090
 */
@Configuration
public class GrpcConfig {
    // gRPC server is auto-configured by grpc-server-spring-boot-starter.
    // Add custom interceptors or security config here as needed.
}
