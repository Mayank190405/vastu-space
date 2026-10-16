-- ============================================================
-- VĀSTU INDOOR SPATIAL COMPUTING PLATFORM
-- Migration: 000015_enable_postgis_and_add_spatial_geometry.up.sql
-- Description: Enable PostGIS + PostGIS 3D extensions and add native
--              geometry columns to all spatial tables. Existing NUMERIC
--              scalar columns are preserved for backwards compat;
--              geometry columns are added alongside and populated from them.
-- Extensions required: postgis, postgis_sfcgal (for 3D operations)
-- Docker image: postgis/postgis:16-3.4 (already in docker-compose.yml)
-- ============================================================

-- ============================================================
-- 1. Enable Extensions
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;
DO $$ 
BEGIN 
    CREATE EXTENSION IF NOT EXISTS postgis_sfcgal; 
EXCEPTION WHEN OTHERS THEN 
    RAISE NOTICE 'postgis_sfcgal extension not present in this distribution, proceeding with native postgis'; 
END $$;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;   -- For fuzzy POI search support

-- ============================================================
-- 2. spatial_sections — bounding_box column → GEOMETRY(POLYGONZ)
--    Currently stored as JSONB; add a proper geometry column.
-- ============================================================

ALTER TABLE spatial_sections
    ADD COLUMN IF NOT EXISTS geom_bbox   GEOMETRY(POLYGONZ, 0)    NULL,
    ADD COLUMN IF NOT EXISTS geom_center GEOMETRY(POINTZ,   0)    NULL;

-- SRID 0 = local cartesian coordinate system (indoor metric space, not WGS84)

CREATE INDEX IF NOT EXISTS idx_spatial_sections_geom_bbox
    ON spatial_sections USING GIST(geom_bbox);

CREATE INDEX IF NOT EXISTS idx_spatial_sections_geom_center
    ON spatial_sections USING GIST(geom_center);

-- ============================================================
-- 3. spatial_pois — replace pos_x/y/z scalar with GEOMETRY(POINTZ)
--    Scalars kept for backwards compat; geometry derived from them.
-- ============================================================

ALTER TABLE spatial_pois
    ADD COLUMN IF NOT EXISTS geom        GEOMETRY(POINTZ, 0)  NULL,
    ADD COLUMN IF NOT EXISTS geom_normal GEOMETRY(POINTZ, 0)  NULL; -- surface normal vector as point offset

CREATE INDEX IF NOT EXISTS idx_pois_geom
    ON spatial_pois USING GIST(geom);

-- Back-populate geometry column from existing NUMERIC scalars
UPDATE spatial_pois
    SET geom = ST_SetSRID(ST_MakePoint(pos_x, pos_y, pos_z), 0)
    WHERE geom IS NULL
      AND pos_x IS NOT NULL;

UPDATE spatial_pois
    SET geom_normal = ST_SetSRID(ST_MakePoint(normal_x, normal_y, normal_z), 0)
    WHERE geom_normal IS NULL
      AND normal_x IS NOT NULL;

-- ============================================================
-- 4. nav_nodes — add GEOMETRY(POINTZ) column
--    Navigation graph nodes in 3D metric indoor space.
-- ============================================================

ALTER TABLE nav_nodes
    ADD COLUMN IF NOT EXISTS geom GEOMETRY(POINTZ, 0) NULL;

CREATE INDEX IF NOT EXISTS idx_nav_nodes_geom
    ON nav_nodes USING GIST(geom);

-- Back-populate
UPDATE nav_nodes
    SET geom = ST_SetSRID(ST_MakePoint(pos_x, pos_y, pos_z), 0)
    WHERE geom IS NULL;

-- ============================================================
-- 5. nav_edges — add pre-computed 3D linestring geometry
--    Enables spatial queries like "which edges cross this bounding box?"
-- ============================================================

ALTER TABLE nav_edges
    ADD COLUMN IF NOT EXISTS geom GEOMETRY(LINESTRINGZ, 0) NULL;

CREATE INDEX IF NOT EXISTS idx_nav_edges_geom
    ON nav_edges USING GIST(geom);

-- Populate edge geometry from node positions (requires join)
UPDATE nav_edges e
    SET geom = ST_SetSRID(
        ST_MakeLine(
            (SELECT geom FROM nav_nodes WHERE id = e.from_node_id),
            (SELECT geom FROM nav_nodes WHERE id = e.to_node_id)
        ), 0
    )
    WHERE e.geom IS NULL
      AND EXISTS (SELECT 1 FROM nav_nodes WHERE id = e.from_node_id AND geom IS NOT NULL)
      AND EXISTS (SELECT 1 FROM nav_nodes WHERE id = e.to_node_id   AND geom IS NOT NULL);

-- ============================================================
-- 6. spatial_models — add bounding box as GEOMETRY(POLYHEDRALSURFACEZ)
--    and model origin as GEOMETRY(POINTZ)
-- ============================================================

ALTER TABLE spatial_models
    ADD COLUMN IF NOT EXISTS geom_bbox   GEOMETRY(POLYHEDRALSURFACEZ, 0) NULL,
    ADD COLUMN IF NOT EXISTS geom_origin GEOMETRY(POINTZ, 0)             NULL;

CREATE INDEX IF NOT EXISTS idx_spatial_models_geom_bbox
    ON spatial_models USING GIST(geom_bbox);

CREATE INDEX IF NOT EXISTS idx_spatial_models_geom_origin
    ON spatial_models USING GIST(geom_origin);

-- ============================================================
-- 7. captures — add trajectory GEOMETRY(LINESTRINGZ)
--    Enables trajectory length computation and spatial overlap queries.
-- ============================================================

ALTER TABLE captures
    ADD COLUMN IF NOT EXISTS geom_trajectory GEOMETRY(LINESTRINGZ, 0) NULL,
    ADD COLUMN IF NOT EXISTS geom_bbox       GEOMETRY(POLYGONZ, 0)    NULL;

CREATE INDEX IF NOT EXISTS idx_captures_geom_trajectory
    ON captures USING GIST(geom_trajectory);

CREATE INDEX IF NOT EXISTS idx_captures_geom_bbox
    ON captures USING GIST(geom_bbox);

-- ============================================================
-- 8. Spatial helper functions
-- ============================================================

-- Function: find POIs within a 3D radius of a query point (indoor spatial search)
CREATE OR REPLACE FUNCTION vastu_pois_within_radius(
    p_project_id UUID,
    p_x          DOUBLE PRECISION,
    p_y          DOUBLE PRECISION,
    p_z          DOUBLE PRECISION,
    p_radius_m   DOUBLE PRECISION
)
RETURNS TABLE(
    id            UUID,
    title         VARCHAR,
    category      VARCHAR,
    pos_x         NUMERIC,
    pos_y         NUMERIC,
    pos_z         NUMERIC,
    distance_m    DOUBLE PRECISION
)
LANGUAGE sql STABLE AS $$
    SELECT
        sp.id,
        sp.title,
        sp.category::VARCHAR,
        sp.pos_x,
        sp.pos_y,
        sp.pos_z,
        ST_3DDistance(
            sp.geom,
            ST_SetSRID(ST_MakePoint(p_x, p_y, p_z), 0)
        ) AS distance_m
    FROM spatial_pois sp
    WHERE sp.project_id = p_project_id
      AND sp.geom IS NOT NULL
      AND ST_3DDWithin(
            sp.geom,
            ST_SetSRID(ST_MakePoint(p_x, p_y, p_z), 0),
            p_radius_m
          )
    ORDER BY distance_m ASC;
$$;

-- Function: find the nearest nav_node to a 3D query position
CREATE OR REPLACE FUNCTION vastu_nearest_nav_node(
    p_project_id UUID,
    p_x          DOUBLE PRECISION,
    p_y          DOUBLE PRECISION,
    p_z          DOUBLE PRECISION,
    p_wheelchair BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(
    id          UUID,
    node_type   VARCHAR,
    pos_x       NUMERIC,
    pos_y       NUMERIC,
    pos_z       NUMERIC,
    distance_m  DOUBLE PRECISION
)
LANGUAGE sql STABLE AS $$
    SELECT
        n.id,
        n.node_type::VARCHAR,
        n.pos_x,
        n.pos_y,
        n.pos_z,
        ST_3DDistance(
            n.geom,
            ST_SetSRID(ST_MakePoint(p_x, p_y, p_z), 0)
        ) AS distance_m
    FROM nav_nodes n
    WHERE n.project_id = p_project_id
      AND n.geom IS NOT NULL
      AND (NOT p_wheelchair OR n.is_wheelchair_accessible = TRUE)
    ORDER BY n.geom <-> ST_SetSRID(ST_MakePoint(p_x, p_y, p_z), 0)
    LIMIT 1;
$$;

-- Function: find all captures whose trajectory overlaps a 3D bounding box
CREATE OR REPLACE FUNCTION vastu_captures_in_bbox(
    p_project_id UUID,
    p_min_x      DOUBLE PRECISION,
    p_min_y      DOUBLE PRECISION,
    p_min_z      DOUBLE PRECISION,
    p_max_x      DOUBLE PRECISION,
    p_max_y      DOUBLE PRECISION,
    p_max_z      DOUBLE PRECISION
)
RETURNS TABLE(id UUID, status VARCHAR, created_at TIMESTAMPTZ)
LANGUAGE sql STABLE AS $$
    SELECT c.id, c.status::VARCHAR, c.created_at
    FROM captures c
    WHERE c.project_id = p_project_id
      AND c.geom_bbox IS NOT NULL
      AND ST_3DIntersects(
            c.geom_bbox,
            ST_SetSRID(
                ST_MakeEnvelope(p_min_x, p_min_y, p_max_x, p_max_y),
                0
            )
          );
$$;

-- ============================================================
-- 9. Trigger: auto-sync NUMERIC pos_x/y/z → geom on poi INSERT/UPDATE
-- ============================================================

CREATE OR REPLACE FUNCTION vastu_sync_poi_geom()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.geom := ST_SetSRID(
        ST_MakePoint(NEW.pos_x, NEW.pos_y, NEW.pos_z),
        0
    );
    IF NEW.normal_x IS NOT NULL THEN
        NEW.geom_normal := ST_SetSRID(
            ST_MakePoint(NEW.normal_x, NEW.normal_y, NEW.normal_z),
            0
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_poi_sync_geom ON spatial_pois;
CREATE TRIGGER trg_poi_sync_geom
    BEFORE INSERT OR UPDATE OF pos_x, pos_y, pos_z, normal_x, normal_y, normal_z
    ON spatial_pois
    FOR EACH ROW EXECUTE FUNCTION vastu_sync_poi_geom();

-- ============================================================
-- 10. Trigger: auto-sync nav_node pos → geom on INSERT/UPDATE
-- ============================================================

CREATE OR REPLACE FUNCTION vastu_sync_nav_node_geom()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.geom := ST_SetSRID(
        ST_MakePoint(NEW.pos_x, NEW.pos_y, NEW.pos_z),
        0
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_nav_node_sync_geom ON nav_nodes;
CREATE TRIGGER trg_nav_node_sync_geom
    BEFORE INSERT OR UPDATE OF pos_x, pos_y, pos_z
    ON nav_nodes
    FOR EACH ROW EXECUTE FUNCTION vastu_sync_nav_node_geom();

-- ============================================================
-- 11. Trigger: auto-recompute nav_edge linestring when node moves
-- ============================================================

CREATE OR REPLACE FUNCTION vastu_sync_nav_edge_geom()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Update all edges that involve this node
    UPDATE nav_edges e
        SET geom = ST_SetSRID(
            ST_MakeLine(
                (SELECT geom FROM nav_nodes WHERE id = e.from_node_id),
                (SELECT geom FROM nav_nodes WHERE id = e.to_node_id)
            ), 0
        )
    WHERE (e.from_node_id = NEW.id OR e.to_node_id = NEW.id)
      AND (SELECT geom FROM nav_nodes WHERE id = e.from_node_id) IS NOT NULL
      AND (SELECT geom FROM nav_nodes WHERE id = e.to_node_id)   IS NOT NULL;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_nav_node_update_edges ON nav_nodes;
CREATE TRIGGER trg_nav_node_update_edges
    AFTER INSERT OR UPDATE OF geom
    ON nav_nodes
    FOR EACH ROW EXECUTE FUNCTION vastu_sync_nav_edge_geom();
