package com.novel.auth.interfaces.grpc;

import com.novel.auth.application.service.QuotaAppService;
import com.novel.auth.infrastructure.grpc.proto.AuthServiceGrpc;
import com.novel.auth.infrastructure.grpc.proto.CheckQuotaRequest;
import com.novel.auth.infrastructure.grpc.proto.CheckQuotaResponse;
import com.novel.auth.infrastructure.grpc.proto.RecordUsageRequest;
import com.novel.auth.infrastructure.grpc.proto.RecordUsageResponse;
import com.novel.auth.infrastructure.grpc.proto.VerifyTokenRequest;
import com.novel.auth.infrastructure.grpc.proto.VerifyTokenResponse;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * gRPC service implementation — exposes auth/quota RPCs to pipeline-service.
 */
@GrpcService
public class AuthGrpcService extends AuthServiceGrpc.AuthServiceImplBase {

    private static final Logger log = LoggerFactory.getLogger(AuthGrpcService.class);

    private final QuotaAppService quotaAppService;

    public AuthGrpcService(QuotaAppService quotaAppService) {
        this.quotaAppService = quotaAppService;
    }

    @Override
    public void verifyToken(VerifyTokenRequest request,
                            StreamObserver<VerifyTokenResponse> responseObserver) {
        log.info("gRPC VerifyToken called for token={}", request.getToken().substring(0, Math.min(8, request.getToken().length())));
        // TODO: validate Sa-Token → extract user info
        VerifyTokenResponse response = VerifyTokenResponse.newBuilder()
                .setValid(true)
                .setUserId("stub-user-id")
                .setUsername("stub-user")
                .setPlan(0)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void checkQuota(CheckQuotaRequest request,
                           StreamObserver<CheckQuotaResponse> responseObserver) {
        log.info("gRPC CheckQuota called for userId={}, action={}", request.getUserId(), request.getAction());
        boolean allowed = quotaAppService.checkQuota(request.getUserId(), request.getAction());
        CheckQuotaResponse response = CheckQuotaResponse.newBuilder()
                .setAllowed(allowed)
                .setRemaining(100)
                .setResetAt("2026-07-01T00:00:00Z")
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void recordUsage(RecordUsageRequest request,
                            StreamObserver<RecordUsageResponse> responseObserver) {
        log.info("gRPC RecordUsage called for userId={}, action={}", request.getUserId(), request.getAction());
        quotaAppService.recordUsage(
                request.getUserId(),
                request.getAction(),
                request.getChaptersProcessed(),
                request.getTokensUsed()
        );
        RecordUsageResponse response = RecordUsageResponse.newBuilder()
                .setSuccess(true)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }
}
