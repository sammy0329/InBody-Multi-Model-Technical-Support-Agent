#!/bin/bash
# T075: EC2 초기 설정 스크립트
# Amazon Linux 2023 / Ubuntu 22.04 호환

set -euo pipefail

# ── 1. Docker 설치 ──
if ! command -v docker &>/dev/null; then
    if [ -f /etc/amazon-linux-release ]; then
        yum update -y
        yum install -y docker git
        systemctl enable docker
        systemctl start docker
    else
        apt-get update -y
        apt-get install -y docker.io docker-compose-plugin git
        systemctl enable docker
        systemctl start docker
    fi
fi

# ── 2. Docker Compose 설치 (standalone) ──
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    COMPOSE_VERSION="v2.24.0"
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# ── 3. 사용자를 docker 그룹에 추가 ──
usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true

# ── 4. 프로젝트 클론 ──
PROJECT_DIR="/home/ec2-user/inbody-app"
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/sammy0329/InBody-Multi-Model-Technical-Support-Agent.git "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
git pull origin main 2>/dev/null || true

# ── 5. 데이터 디렉토리 준비 ──
mkdir -p data/chroma data/manuals static/images

# ── 6. Docker Compose 빌드 및 실행 ──
docker compose build
docker compose up -d

# ── 7. 초기 데이터 시딩 (최초 1회) ──
SEED_FLAG="/home/ec2-user/.inbody-seeded"
if [ ! -f "$SEED_FLAG" ]; then
    sleep 10  # 서비스 안정화 대기
    docker compose exec -T api python scripts/seed_structured_data.py 2>/dev/null || true
    docker compose exec -T api python scripts/ingest_manuals.py 2>/dev/null || true
    touch "$SEED_FLAG"
fi

echo "InBody Tech-Master deployment complete."
