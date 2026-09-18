# VĀSTU Database Architecture

This directory houses the database migrations and data access patterns for the VĀSTU / Namma Space platform.

## Database Engine
- **Engine**: PostgreSQL 16+ with **PostGIS 3.4+** extensions enabled.
- **Connection Environment Variables**:
  - `DATABASE_URL`: `postgresql://postgres:postgres@localhost:5432/vastu?sslmode=disable`
  - `POSTGRES_DB`: `vastu`
  - `POSTGRES_USER`: `postgres`
  - `POSTGRES_PASSWORD`: `postgres`

## Migrations Overview
Migrations are managed using standard SQL migrate tooling:
- `000001` - `000013`: Auth, organizations, project definitions, and timeline activities.
- `000014`: Core services schema (jobs, captures, models, POIs).
- `000015`: PostGIS extensions, 3D metric bounding boxes, spatial polygons, and navigation topological graphs.
- `000016`: Spatial cells partitioning, quality reports, and rescan requests (Contracts 6, 11, 12).

## Running Migrations
```bash
migrate -path database/migrations -database "$DATABASE_URL" up
```
