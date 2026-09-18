-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000015_enable_postgis_and_add_spatial_geometry.down.sql
-- ============================================================

-- Drop triggers
DROP TRIGGER IF EXISTS trg_nav_node_update_edges ON nav_nodes;
DROP TRIGGER IF EXISTS trg_nav_node_sync_geom    ON nav_nodes;
DROP TRIGGER IF EXISTS trg_poi_sync_geom          ON spatial_pois;

-- Drop trigger functions
DROP FUNCTION IF EXISTS vastu_sync_nav_edge_geom();
DROP FUNCTION IF EXISTS vastu_sync_nav_node_geom();
DROP FUNCTION IF EXISTS vastu_sync_poi_geom();

-- Drop helper functions
DROP FUNCTION IF EXISTS vastu_captures_in_bbox(UUID, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);
DROP FUNCTION IF EXISTS vastu_nearest_nav_node(UUID, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, BOOLEAN);
DROP FUNCTION IF EXISTS vastu_pois_within_radius(UUID, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);

-- Drop geometry indexes
DROP INDEX IF EXISTS idx_captures_geom_bbox;
DROP INDEX IF EXISTS idx_captures_geom_trajectory;
DROP INDEX IF EXISTS idx_spatial_models_geom_origin;
DROP INDEX IF EXISTS idx_spatial_models_geom_bbox;
DROP INDEX IF EXISTS idx_nav_edges_geom;
DROP INDEX IF EXISTS idx_nav_nodes_geom;
DROP INDEX IF EXISTS idx_pois_geom;
DROP INDEX IF EXISTS idx_spatial_sections_geom_center;
DROP INDEX IF EXISTS idx_spatial_sections_geom_bbox;

-- Drop geometry columns
ALTER TABLE captures        DROP COLUMN IF EXISTS geom_bbox;
ALTER TABLE captures        DROP COLUMN IF EXISTS geom_trajectory;
ALTER TABLE spatial_models  DROP COLUMN IF EXISTS geom_origin;
ALTER TABLE spatial_models  DROP COLUMN IF EXISTS geom_bbox;
ALTER TABLE nav_edges       DROP COLUMN IF EXISTS geom;
ALTER TABLE nav_nodes       DROP COLUMN IF EXISTS geom;
ALTER TABLE spatial_pois    DROP COLUMN IF EXISTS geom_normal;
ALTER TABLE spatial_pois    DROP COLUMN IF EXISTS geom;
ALTER TABLE spatial_sections DROP COLUMN IF EXISTS geom_center;
ALTER TABLE spatial_sections DROP COLUMN IF EXISTS geom_bbox;

-- Drop extensions (only if no other schemas depend on them)
DROP EXTENSION IF EXISTS fuzzystrmatch;
DROP EXTENSION IF EXISTS postgis_sfcgal;
DROP EXTENSION IF EXISTS postgis;
