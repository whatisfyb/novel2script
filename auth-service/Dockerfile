# Stage 1: Build
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
COPY ../proto ./proto
RUN mvn package -DskipTests -B

# Stage 2: Runtime
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
RUN addgroup -S novel && adduser -S novel -G novel
COPY --from=builder /build/target/*.jar app.jar
RUN chown -R novel:novel /app
USER novel
EXPOSE 8080 9090
ENTRYPOINT ["java", "-jar", "app.jar"]
