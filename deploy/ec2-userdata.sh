#!/bin/bash
# EC2 초기 설정 스크립트 (venv + systemd 방식)
# Amazon Linux 2023 / Ubuntu 22.04 호환

set -euo pipefail

# ── 1. Python 3.11 + git 설치 ──
if [ -f /etc/amazon-linux-release ]; then
    yum update -y
    yum install -y python3.11 python3.11-pip python3.11-devel git gcc
else
    apt-get update -y
    apt-get install -y python3.11 python3.11-venv python3-pip git build-essential
fi

# ── 2. 프로젝트 클론 ──
PROJECT_DIR="/home/ubuntu/inbody-app"
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/sammy0329/InBody-Multi-Model-Technical-Support-Agent.git "$PROJECT_DIR"
    chown -R ubuntu:ubuntu "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
git pull origin main 2>/dev/null || true

# ── 3. 데이터 디렉토리 준비 ──
mkdir -p data/chroma data/manuals static/images

# ── 4. venv 생성 및 의존성 설치 ──
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3.11 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
    "$PROJECT_DIR/.venv/bin/pip" install .
fi

# ── 5. systemd 서비스 등록 ──
cp "$PROJECT_DIR/deploy/inbody-api.service" /etc/systemd/system/
cp "$PROJECT_DIR/deploy/inbody-ui.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable inbody-api inbody-ui

# ── 6. .env 확인 후 서비스 시작 ──
if [ -f "$PROJECT_DIR/.env" ]; then
    systemctl start inbody-api inbody-ui
    echo "InBody Tech-Master 서비스가 시작되었습니다."
else
    echo "[WARNING] .env 파일이 없습니다. 아래 파일들을 SCP로 복사 후 서비스를 시작하세요:"
    echo "  scp .env ubuntu@<EC2_IP>:~/inbody-app/.env"
    echo "  scp -r data/chroma/ ubuntu@<EC2_IP>:~/inbody-app/data/chroma/"
    echo "  scp data/inbody.db ubuntu@<EC2_IP>:~/inbody-app/data/inbody.db"
    echo ""
    echo "복사 후: sudo systemctl start inbody-api inbody-ui"
fi

chown -R ubuntu:ubuntu "$PROJECT_DIR"
echo "InBody Tech-Master deployment complete."
