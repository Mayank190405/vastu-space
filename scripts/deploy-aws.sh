#!/usr/bin/env bash
# ==============================================================================
# VĀSTU SPATIAL COMPUTING PLATFORM - AWS EC2 PRODUCTION DEPLOYMENT SCRIPT
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}"
echo "=========================================================================="
echo "          VĀSTU / NAMMA SPACE - AWS EC2 PRODUCTION DEPLOYMENT             "
echo "=========================================================================="
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# 1. System Requirements & Dependency Check
# ------------------------------------------------------------------------------
echo -e "${BLUE}▶ Checking system requirements and dependencies...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Installing Docker on Ubuntu/Debian...${NC}"
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}✓ Docker installed successfully.${NC}"
else
    echo -e "${GREEN}✓ Docker is installed ($(docker --version))${NC}"
fi

# Verify Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: 'docker compose' (v2 plugin) is required.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose plugin available ($(docker compose version))${NC}"

# ------------------------------------------------------------------------------
# 2. Swap Space Provisioning (Vital for EC2 instances < 8GB RAM)
# ------------------------------------------------------------------------------
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
SWAP_EXISTS=$(swapon --show | wc -l)

if [ "${SWAP_EXISTS}" -le 1 ] && [ "${TOTAL_RAM_MB}" -lt 8000 ]; then
    echo -e "${YELLOW}Notice: RAM is ${TOTAL_RAM_MB}MB. Adding 4GB swapfile for 3D photogrammetry stability...${NC}"
    if [ ! -f /swapfile ]; then
        sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
        echo -e "${GREEN}✓ 4GB Swap successfully enabled.${NC}"
    fi
else
    echo -e "${GREEN}✓ Memory profile verified (${TOTAL_RAM_MB}MB RAM)${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Environment Configuration Check
# ------------------------------------------------------------------------------
ENV_FILE="${PROJECT_ROOT}/.env.production"

if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${YELLOW}Warning: ${ENV_FILE} not found.${NC}"
    echo -e "${BLUE}Generating a secure .env.production template with randomized secrets...${NC}"

    cp "${PROJECT_ROOT}/infrastructure/environments/production.env.template" "${ENV_FILE}"

    # Auto-generate secure 32-byte cryptographic random passwords
    GEN_PG_PASS=$(openssl rand -hex 24)
    GEN_REDIS_PASS=$(openssl rand -hex 24)
    GEN_MINIO_PASS=$(openssl rand -hex 24)
    GEN_JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n')

    sed -i.bak "s/CHANGE_ME_GENERATE_SECURE_PASSWORD_32_CHARS/${GEN_PG_PASS}/g" "${ENV_FILE}"
    sed -i.bak "s/CHANGE_ME_GENERATE_SECURE_REDIS_PASSWORD_32_CHARS/${GEN_REDIS_PASS}/g" "${ENV_FILE}"
    sed -i.bak "s/CHANGE_ME_GENERATE_MINIO_PASSWORD_32_CHARS/${GEN_MINIO_PASS}/g" "${ENV_FILE}"
    sed -i.bak "s|CHANGE_ME_GENERATE_64_CHAR_CRYPTOGRAPHIC_JWT_KEY|${GEN_JWT_SECRET}|g" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"

    echo -e "${GREEN}✓ Created .env.production with cryptographically secure random credentials.${NC}"
    echo -e "${YELLOW}Please review .env.production and set your APP_URL and SMTP credentials if needed.${NC}"
fi

# ------------------------------------------------------------------------------
# 4. Optional Domain & SSL Configuration
# ------------------------------------------------------------------------------
ENABLE_SSL="${ENABLE_SSL:-false}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

if [ "${1:-}" == "--ssl" ] || [ "${ENABLE_SSL}" == "true" ]; then
    if [ -z "${DOMAIN_NAME}" ]; then
        read -rp "Enter your fully qualified domain name (e.g. vastu.example.com): " DOMAIN_NAME
    fi
    if [ -z "${CERTBOT_EMAIL}" ]; then
        read -rp "Enter contact email for Let's Encrypt SSL renewal alerts: " CERTBOT_EMAIL
    fi

    echo -e "${BLUE}Configuring Let's Encrypt SSL for ${DOMAIN_NAME}...${NC}"

    # Step 1: Start gateway on HTTP for ACME challenge
    sed -i.bak "s|APP_URL=.*|APP_URL=https://${DOMAIN_NAME}|g" "${ENV_FILE}"
    sed -i.bak "s|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway.conf|g" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"

    docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE}" up -d vastu-gateway

    echo "Requesting SSL certificate..."
    sudo apt-get install -y certbot || true
    sudo certbot certonly --webroot -w /var/lib/docker/volumes/vastu_certbot_var/_data \
        -d "${DOMAIN_NAME}" --email "${CERTBOT_EMAIL}" --agree-tos --non-interactive || true

    # Step 2: Switch to SSL Gateway configuration
    sed -i.bak "s|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway-ssl.conf|g" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"
    echo -e "${GREEN}✓ SSL configured for ${DOMAIN_NAME}.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. Build & Launch Microservices Stack
# ------------------------------------------------------------------------------
echo -e "${BLUE}▶ Building and launching VĀSTU production stack...${NC}"

docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE}" down --remove-orphans || true
docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE}" build --parallel
docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE}" up -d

# ------------------------------------------------------------------------------
# 6. Post-Deployment Health Check & Verification
# ------------------------------------------------------------------------------
echo -e "${BLUE}▶ Waiting for services to become healthy...${NC}"

MAX_RETRIES=15
COUNTER=0
HEALTHY=false

while [ $COUNTER -lt $MAX_RETRIES ]; do
    sleep 3
    COUNTER=$((COUNTER + 1))
    
    GATEWAY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || true)
    BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/health || curl -s -o /dev/null -w "%{http_code}" http://localhost/health || true)

    if [ "${GATEWAY_STATUS}" == "200" ]; then
        HEALTHY=true
        break
    fi
    echo -n "."
done
echo ""

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}${BOLD}=========================================================================="
    echo "✓ VĀSTU PRODUCTION DEPLOYMENT COMPLETE & HEALTHY"
    echo "==========================================================================${NC}"
    echo ""
    echo -e "Web Gateway / Frontend:  ${BOLD}http://localhost${NC} (or your EC2 Public IP / Domain)"
    echo -e "Backend Control Plane:   ${BOLD}http://localhost/api/v1${NC}"
    echo -e "FastAPI Spatial Engine:  ${BOLD}http://localhost/py/ (Docs at /docs)${NC}"
    echo -e "MinIO S3 Storage API:    ${BOLD}http://localhost/vastu-artifacts/${NC}"
    echo -e "MinIO Web Console:       ${BOLD}http://localhost/minio-console/${NC}"
    echo ""
    echo -e "${BLUE}Useful Management Commands:${NC}"
    echo -e "  View live logs:        docker compose -f docker-compose.prod.yml logs -f"
    echo -e "  Check service status:  docker compose -f docker-compose.prod.yml ps"
    echo -e "  Restart all services:  docker compose -f docker-compose.prod.yml restart"
    echo -e "  Stop stack:            docker compose -f docker-compose.prod.yml down"
else
    echo -e "${YELLOW}Notice: Gateway is starting up or completing migrations.${NC}"
    echo -e "Check live service status with: ${BOLD}docker compose -f docker-compose.prod.yml ps${NC}"
fi
