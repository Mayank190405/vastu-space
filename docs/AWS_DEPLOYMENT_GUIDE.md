# VĀSTU Spatial Computing Platform - AWS Production Deployment Guide

This guide provides the complete, step-by-step production deployment procedure for running the **VĀSTU (Namma Space)** platform on **Amazon Web Services (AWS)** using a single high-performance EC2 instance, Docker Compose, unified Nginx reverse proxy, and self-hosted MinIO object storage.

---

## 1. Architecture Overview

```
                 Internet / Browser (HTTPS / Port 443)
                                 │
                                 ▼
                     AWS Route 53 / Elastic IP
                                 │
                                 ▼
         ┌─────────────────────────────────────────────────────────┐
         │                    AWS EC2 Host                         │
         │                                                         │
         │   ┌─────────────────────────────────────────────────┐   │
         │   │       VĀSTU Unified Nginx Gateway (Port 80/443)  │   │
         │   └───────┬──────────────┬─────────────┬────────────┘   │
         │           │              │             │                │
         │  / (Web App)      /api/v1 (API)  /vastu-* (S3)          │
         │           ▼              ▼             ▼                │
         │     ┌───────────┐  ┌───────────┐ ┌───────────┐          │
         │     │ Frontend  │  │  Backend  │ │   MinIO   │          │
         │     │  (React)  │  │ (Golang)  │ │   (S3)    │          │
         │     └───────────┘  └─────┬─────┘ └─────┬─────┘          │
         │                          │             │                │
         │               ┌──────────┴─────────────┴────┐           │
         │               │     Isolated Docker Network │           │
         │               │                             │           │
         │               │  ┌───────────────────────┐  │           │
         │               │  │ PostGIS Database (16) │  │           │
         │               │  └───────────────────────┘  │           │
         │               │  ┌───────────────────────┐  │           │
         │               │  │ Redis 7 Data Store    │  │           │
         │               │  └───────────────────────┘  │           │
         │               │  ┌───────────────────────┐  │           │
         │               │  │ 9-Stage Worker Engine │  │           │
         │               │  └───────────────────────┘  │           │
         │               └─────────────────────────────┘           │
         └─────────────────────────────────────────────────────────┘
```

---

## 2. Recommended AWS EC2 Instance Sizing

| Workload Type | AWS EC2 Instance | vCPU | RAM | Storage (EBS gp3) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Production** *(Recommended)* | `t3.large` or `t3.xlarge` | 2 - 4 | 8 - 16 GB | 100 GB gp3 | Optimal for API, Web Viewer, and standard photogrammetry reconstruction. |
| **High-Throughput / GPU** | `g4dn.xlarge` | 4 | 16 GB + 16GB GPU | 200 GB gp3 | Provides NVIDIA T4 GPU for ultra-fast dense point cloud & meshing pipelines. |
| **Staging / Testing** | `t3.medium` | 2 | 4 GB | 50 GB gp3 | Automated 4GB swap space will be provisioned by the deploy script. |

> [!TIP]
> Operating System: **Ubuntu Server 24.04 LTS (HVM)** or **Ubuntu Server 22.04 LTS**.

---

## 3. AWS Security Group Configuration

In the AWS EC2 Management Console, configure your instance's **Inbound Security Group Rules**:

| Type | Protocol | Port Range | Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | `My IP` (or Admin VPN) | Secure terminal access |
| **HTTP** | TCP | `80` | `0.0.0.0/0` | Let's Encrypt validation & Web redirects |
| **HTTPS** | TCP | `443` | `0.0.0.0/0` | Secure SSL web viewer & API traffic |

> [!IMPORTANT]
> Keep database ports (`5432`), Redis (`6379`), and internal MinIO (`9000`/`9001`) **CLOSED** from the public internet. The Nginx reverse proxy routes all requests internally over an isolated Docker network.

---

## 4. Elastic IP & DNS (Route 53)

1. Navigate to **EC2 Console -> Elastic IPs**.
2. Click **Allocate Elastic IP address** and click **Allocate**.
3. Select the IP, click **Actions -> Associate Elastic IP address**, and associate it with your VĀSTU EC2 instance.
4. In **Route 53** (or your DNS registrar), create an **A Record**:
   - `Record Name`: `vastu.yourdomain.com` (or `@` for root)
   - `Record Type`: `A`
   - `Value`: Your EC2 Elastic IP address
   - `TTL`: `300` seconds

---

## 5. Deployment via AWS Browser SSH (EC2 Instance Connect)

You don't need any local terminal or `.pem` file on your computer. You can do the entire setup directly in your browser:

### Step 5.1: Open Browser SSH in AWS Console
1. Go to the [AWS EC2 Console](https://console.aws.amazon.com/ec2/).
2. Select your running VĀSTU instance and click **Connect** in the top right.
3. Choose the **EC2 Instance Connect** tab.
4. Ensure the username is `ubuntu` and click the orange **Connect** button.
5. A browser-based terminal will immediately open inside your browser window.

---

### Step 5.2: Generate SSH Key & Authorize GitHub

In your EC2 browser terminal, run:

```bash
# 1. Generate an Ed25519 SSH keypair (press Enter for all prompts to use defaults)
ssh-keygen -t ed25519 -C "aws-ec2-vastu" -f ~/.ssh/id_ed25519 -N ""

# 2. Print your Public Key to the screen
cat ~/.ssh/id_ed25519.pub
```

Now copy the output line (starts with `ssh-ed25519 ... aws-ec2-vastu`) and add it to GitHub:
1. Open GitHub in a new browser tab: 👉 [https://github.com/settings/ssh/new](https://github.com/settings/ssh/new)
2. **Title**: `AWS EC2 VASTU Production`
3. **Key**: Paste the copied key.
4. Click **Add SSH key**.

---

### Step 5.3: Verify Connection & Clone via SSH

Back in your EC2 browser terminal, test the GitHub SSH connection:

```bash
# Verify GitHub connection (type 'yes' when prompted about host authenticity)
ssh -T git@github.com
```
*You will see: `Hi <username>! You've successfully authenticated...`*

Now clone the repository using SSH:
```bash
git clone git@github.com:Mayank190405/vastu-space.git vastu-namma-space
cd vastu-namma-space

# Check out the active architecture branch
git checkout cursor/service-to-service-architecture
```

---

### Step 5.4: Run the Automated Deployment

#### Option A: Quick Test / Demo Deployment (HTTP on EC2 IP)
```bash
./scripts/deploy-aws.sh
```

#### Option B: Production Deployment with Let's Encrypt SSL
```bash
DOMAIN_NAME=vastu.yourdomain.com CERTBOT_EMAIL=admin@yourdomain.com ./scripts/deploy-aws.sh --ssl
```
*This installs Docker, configures swap, executes PostGIS migrations, builds the multi-stage images, and starts all microservices with health checks.*

---

## 6. Accessing Platform Services

Once deployment finishes, all services are accessible via your domain or public IP:

| Service | URL | Notes |
| :--- | :--- | :--- |
| **Web App & 3D Viewer** | `https://vastu.yourdomain.com/` | Zero-install WebGL viewer |
| **Control Plane API** | `https://vastu.yourdomain.com/api/v1/` | Go backend REST API |
| **Spatial Engine (FastAPI)** | `https://vastu.yourdomain.com/py/` | Python photogrammetry gateway |
| **Interactive API Docs** | `https://vastu.yourdomain.com/docs` | Swagger / OpenAPI UI |
| **MinIO 3D Artifacts** | `https://vastu.yourdomain.com/vastu-artifacts/` | Public asset downloads |
| **MinIO Admin Console** | `https://vastu.yourdomain.com/minio-console/` | S3 bucket visual dashboard |

---

## 7. Operations & Maintenance

### Checking Live Service Health
```bash
docker compose -f docker-compose.prod.yml ps
```

### Viewing Real-Time Logs
```bash
# All services:
docker compose -f docker-compose.prod.yml logs -f

# Specific microservice:
docker compose -f docker-compose.prod.yml logs -f vastu-backend
docker compose -f docker-compose.prod.yml logs -f vastu-worker
docker compose -f docker-compose.prod.yml logs -f vastu-gateway
```

### Updating to New Code Versions
```bash
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.production build --parallel
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Automated Database Backups (Cron)
Add a daily cron job to backup the PostGIS spatial database to local compressed storage or AWS S3:
```bash
crontab -e
```
Add the following line (runs every midnight):
```cron
0 0 * * * docker exec vastu_postgres pg_dump -U vastu_user vastu_db | gzip > /home/ubuntu/backups/vastu_db_$(date +\%F).sql.gz
```
