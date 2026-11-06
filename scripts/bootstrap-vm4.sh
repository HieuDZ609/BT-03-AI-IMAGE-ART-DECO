#!/usr/bin/env bash
# Bootstrap VM4 (core node) — cài Redis + PostgreSQL native (không Docker).
set -euo pipefail

REDIS_PASSWORD="${REDIS_PASSWORD:-B4Deco_Redis_2026!}"
PG_PASSWORD="${PG_PASSWORD:-B4Deco_Pg_2026!}"
TAILSCALE_IP="${TAILSCALE_IP:-100.70.241.87}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq redis-server redis-tools postgresql postgresql-contrib python3 python3-pip

# --- Redis ---
cp /etc/redis/redis.conf /etc/redis/redis.conf.bak 2>/dev/null || true
sed -i "s/^bind .*/bind 127.0.0.1 ${TAILSCALE_IP}/" /etc/redis/redis.conf
sed -i "s/^appendonly .*/appendonly yes/" /etc/redis/redis.conf
grep -q "^requirepass" /etc/redis/redis.conf || \
  sed -i "/^protected-mode yes/a requirepass ${REDIS_PASSWORD}" /etc/redis/redis.conf
systemctl enable --now redis-server

# --- PostgreSQL ---
PGCONF=/etc/postgresql/*/main/postgresql.conf
PGHBA=/etc/postgresql/*/main/pg_hba.conf
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = 'localhost,${TAILSCALE_IP}'/" $PGCONF
grep -q "100.0.0.0/8" $PGHBA || echo "host all all 100.0.0.0/8 scram-sha-256" >> $PGHBA
systemctl enable --now postgresql

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='bt03') THEN
    CREATE ROLE bt03 LOGIN PASSWORD '${PG_PASSWORD}';
  END IF;
END \$\$;
SELECT 'CREATE DATABASE bt03 OWNER bt03' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='bt03')\gexec
SQL
sudo -u postgres psql -d bt03 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo "=== DONE ==="
echo "Redis:    ${TAILSCALE_IP}:6379"
echo "Postgres: ${TAILSCALE_IP}:5432 (bt03)"
"