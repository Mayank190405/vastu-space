#!/usr/bin/env bash
# ==============================================================================
# VĀSTU SPATIAL PLATFORM - ONE-CLICK SSL PROVISIONER FOR EC2
# ==============================================================================
set -euo pipefail

DOMAIN="${1:-vastu.krads.co.in}"
EMAIL="${2:-admin@krads.co.in}"
SSL_DIR="./infrastructure/ssl"

echo "=========================================================================="
echo "Configuring Let's Encrypt SSL for https://${DOMAIN}"
echo "=========================================================================="

echo "▶ 1. Installing Certbot..."
sudo apt-get update -qq
sudo apt-get install -y -qq certbot

echo "▶ 2. Locating ACME Webroot..."
WEBROOT_DIR="$(docker volume inspect vastu_certbot_var -f '{{.Mountpoint}}' 2>/dev/null || echo '/var/lib/docker/volumes/vastu_certbot_var/_data')"
sudo mkdir -p "${WEBROOT_DIR}"

echo "▶ 3. Ensuring Certificate exists..."
if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo "Requesting Certificate via Let's Encrypt..."
    sudo certbot certonly --webroot -w "${WEBROOT_DIR}" \
      -d "${DOMAIN}" --email "${EMAIL}" --agree-tos --non-interactive
fi

echo "▶ 4. Copying dereferenced certificates to ${SSL_DIR}..."
mkdir -p "${SSL_DIR}"
sudo cp -L "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/fullchain.pem"
sudo cp -L "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${SSL_DIR}/privkey.pem"
sudo chmod 644 "${SSL_DIR}/fullchain.pem"
sudo chmod 644 "${SSL_DIR}/privkey.pem"
sudo chown -R "${USER}:${USER}" "${SSL_DIR}"

echo "▶ 5. Switching Nginx Gateway to SSL configuration..."
if [ -f .env ]; then
  sed -i.bak 's|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway-ssl.conf|' .env
  rm -f .env.bak
fi
if [ -f .env.production ]; then
  sed -i.bak 's|NGINX_CONF_PATH=.*|NGINX_CONF_PATH=./infrastructure/nginx/gateway-ssl.conf|' .env.production
  rm -f .env.production.bak
fi

echo "▶ 6. Recreating Nginx Gateway with SSL..."
docker compose -f docker-compose.prod.yml up -d --force-recreate vastu-gateway

echo ""
echo "=========================================================================="
echo "✓ SSL ENABLED SUCCESSFULLY!"
echo "Visit: https://${DOMAIN}/dashboard"
echo "=========================================================================="
