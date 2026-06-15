# =============================================================================
# OpenCode container — full dev environment + opencode CLI in serve mode
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ---------- System dependencies ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    unzip \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python 3.10 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 --version

# ---------- JDK 21 (Eclipse Temurin) ----------
RUN wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public \
    | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb jammy main" \
    > /etc/apt/sources.list.d/adoptium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends temurin-21-jdk \
    && rm -rf /var/lib/apt/lists/* \
    && java --version

# ---------- Node.js 21 ----------
RUN curl -fsSL https://deb.nodesource.com/setup_21.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npm --version

# ---------- Gradle 8.7 ----------
ENV GRADLE_VERSION=8.7
RUN wget -q "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" \
    -O /tmp/gradle.zip \
    && unzip -q /tmp/gradle.zip -d /opt \
    && ln -s "/opt/gradle-${GRADLE_VERSION}/bin/gradle" /usr/local/bin/gradle \
    && rm /tmp/gradle.zip \
    && gradle --version

# ---------- opencode CLI via npm ----------
# --omit=optional skips platform-specific binaries (Windows, macOS, ARM, musl)
RUN npm install -g opencode-ai@latest --omit=optional \
    && opencode --version

# ---------- Copy default config ----------
COPY docker/opencode/opencode.json /root/.config/opencode/opencode.json

# ---------- Prepare mount points ----------
RUN mkdir -p /opencode

# ---------- Workspace ----------
WORKDIR /workspace

ENV DEBIAN_FRONTEND=

EXPOSE 4096

# Start opencode in headless server mode
CMD ["opencode", "serve", "--port", "4096", "--hostname", "0.0.0.0"]
