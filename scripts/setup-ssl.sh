#!/usr/bin/env bash
# ==============================================================================
# VĀSTU SPATIAL PLATFORM - ONE-CLICK SSL PROVISIONER FOR EC2
# ==============================================================================
set -euo pipefail

DOMAIN="${1:-vastu.krads.co.in}"
EMAIL="${2:-admin@krads.co.in}"

echo "=========================================================================="
echo "Configuring Let's Encrypt SSL for https://${DOMAIN}"
echo "=========================================================================="

echo "▶ 1. Installing Certbot..."
sudo apt-get update -qq
sudo apt-get install -y -qq certbot

echo "▶ 2. Locating ACME Webroot..."
# Locate the docker volume mount on host filesystem
WEBROOT_DIR="$(docker volume inspect vastu_certbot_var -f '{{.Mountpoint}}' 2>/dev/null || echo '/var/lib/docker/volumes/vastu_certbot_var/_data')"
sudo mkdir -p "${WEBROOT_DIR}"

echo "▶ 3. Requesting Certificate via Let's Encrypt (ACME HTTP-01)..."
sudo certbot certonly --webroot -w "${WEBROOT_DIR}" \
  -d "${DOMAIN}" --email "${EMAIL}" --agree-tos --non-interactive

echo "▶ 4. Linking certificate files..."
sudo ln -sf "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" /etc/letsencrypt/live/fullchain.pem
sudo ln -sf "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" /etc/letsencrypt/live/privkey.pem

echo "▶ 5. Switching Nginx Gateway to SSL (Port 443)..."
if [ -f .env ]; then
  sed -i.bak 's|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway-ssl.conf|' .env
  rm -f .env.bak
fi
if [ -f .env.production ]; then
  sed -i.bak 's|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway-ssl.conf|' .env.production
  rm -f .env.production.bak
fi

echo "▶ 6. Reloading Nginx Gateway..."
docker compose -f docker-compose.prod.yml up -d vastu-gateway

echo ""
echo "=========================================================================="
echo "✓ SSL ENABLED SUCCESSFULLY!"
echo "You can now securely access: https://${DOMAIN}/dashboard"
echo "=========================================================================="
