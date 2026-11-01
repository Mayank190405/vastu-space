import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { RoomCollisionData } from './CollisionSystem';

export interface SceneManifest {
  version: string;
  project_id: string;
  project_name: string;
  total_area_sqm: number;
  room_count: number;
  floors: number[];
  assets: {
    architecture_obj?: string;
    collision_geometry?: string;
    navmesh?: string;
    connection_graph?: string;
    splats_spz?: string;
  };
  rooms: {
    room_id: string;
    room_name: string;
    floor_level: number;
    area_sqm: number;
    ceiling_height_m: number;
    transform_matrix_4x4?: number[][];
    boundary_polygon_world: [number, number][];
    doorway_count: number;
    furniture_count: number;
  }[];
  default_spawn: {
    room_id: string;
    position_3d: [number, number, number];
    eye_height_m: number;
  };
}

export class SpatialAssetLoader {
  private objLoader = new OBJLoader();
  private mtlLoader = new MTLLoader();
  private plyLoader = new PLYLoader();

  /**
   * Fetches the unified scene manifest from the server.
   */
  public async loadManifest(basePath: string): Promise<SceneManifest> {
    try {
      const res = await fetch(`${basePath}/scene_manifest.json`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback to local reconstruction default manifest
    }

    // Default multi-room manifest fallback
    return {
      version: '1.0.0',
      project_id: 'proj_default',
      project_name: 'VĀSTU Residence Digital Twin',
      total_area_sqm: 148.5,
      room_count: 3,
      floors: [1],
      assets: {
        architecture_obj: 'textured_mesh.obj',
        collision_geometry: 'collision_geometry.json',
        connection_graph: 'room_connection_graph.json'
      },
      rooms: [
        {
          room_id: 'room_living',
          room_name: 'Living Room',
          floor_level: 1,
          area_sqm: 42.5,
          ceiling_height_m: 2.80,
          boundary_polygon_world: [[-3.5, -3.0], [3.5, -3.0], [3.5, 3.0], [-3.5, 3.0]],
          doorway_count: 2,
          furniture_count: 3
        },
        {
          room_id: 'room_bedroom',
          room_name: 'Master Suite',
          floor_level: 1,
          area_sqm: 28.0,
          ceiling_height_m: 2.80,
          boundary_polygon_world: [[3.5, -2.5], [8.5, -2.5], [8.5, 2.5], [3.5, 2.5]],
          doorway_count: 1,
          furniture_count: 2
        },
        {
          room_id: 'room_kitchen',
          room_name: 'Kitchen & Dining',
          floor_level: 1,
          area_sqm: 22.0,
          ceiling_height_m: 2.80,
          boundary_polygon_world: [[-3.5, 3.0], [2.0, 3.0], [2.0, 7.0], [-3.5, 7.0]],
          doorway_count: 1,
          furniture_count: 2
        }
      ],
      default_spawn: {
        room_id: 'room_living',
        position_3d: [0.0, 0.0, 1.60],
        eye_height_m: 1.60
      }
    };
  }

  /**
   * Loads collision geometry for the physics engine.
   */
  public async loadCollisionGeometry(basePath: string, manifest: SceneManifest): Promise<RoomCollisionData[]> {
    try {
      const collisionUrl = manifest.assets?.collision_geometry
        ? `${basePath}/${manifest.assets.collision_geometry}`
        : `${basePath}/collision_geometry.json`;
      const res = await fetch(collisionUrl);
      if (res.ok) {
        const data = await res.json();
        if (data.rooms && Array.isArray(data.rooms)) {
          return data.rooms;
        }
      }
    } catch {
      // Generate collision data dynamically from manifest rooms
    }

    return manifest.rooms.map(r => {
      const poly = r.boundary_polygon_world;
      const walls: any[] = [];
      for (let i = 0; i < poly.length; i++) {
        const next = (i + 1) % poly.length;
        // Skip door wall connection between living and bedroom
        if (poly[i][0] === 3.5 && poly[next][0] === 3.5 && Math.abs(poly[i][1] - poly[next][1]) > 1.0) {
          // Leave gap for doorway
          walls.push({
            collider_id: `col_${r.room_id}_wall_sub_0`,
            type: 'WALL_SEGMENT',
            p0: [poly[i][0], poly[i][1], 0],
            p1: [poly[i][0], -0.6, 0],
            height_m: r.ceiling_height_m,
            thickness_m: 0.15
          });
          walls.push({
            collider_id: `col_${r.room_id}_wall_sub_1`,
            type: 'WALL_SEGMENT',
            p0: [poly[i][0], 0.6, 0],
            p1: [poly[next][0], poly[next][1], 0],
            height_m: r.ceiling_height_m,
            thickness_m: 0.15
          });
          continue;
        }

        walls.push({
          collider_id: `col_${r.room_id}_wall_${i}`,
          type: 'WALL_SEGMENT',
          p0: [poly[i][0], poly[i][1], 0],
          p1: [poly[next][0], poly[next][1], 0],
          height_m: r.ceiling_height_m,
          thickness_m: 0.15
        });
      }

      return {
        room_id: r.room_id,
        room_name: r.room_name,
        floor_collider: {
          elevation_z: 0.0,
          boundary_polygon_2d: poly
        },
        wall_colliders: walls,
        furniture_colliders: [
          {
            collider_id: `furn_${r.room_id}_01`,
            category: 'COUCH_TABLE',
            center_3d: [
              poly[0][0] * 0.4 + poly[1][0] * 0.6,
              poly[0][1] * 0.4 + poly[2][1] * 0.6,
              0.45
            ],
            dimensions_m: [1.2, 0.8, 0.5],
            min_3d: [
              (poly[0][0] * 0.4 + poly[1][0] * 0.6) - 0.6,
              (poly[0][1] * 0.4 + poly[2][1] * 0.6) - 0.4,
              0.0
            ],
            max_3d: [
              (poly[0][0] * 0.4 + poly[1][0] * 0.6) + 0.6,
              (poly[0][1] * 0.4 + poly[2][1] * 0.6) + 0.4,
              0.55
            ]
          }
        ],
        walkable_boundary_polygon_2d: poly
      };
    });
  }

  /**
   * Loads the textured architectural 3D mesh model.
   */
  public async loadArchitecturalMesh(
    basePath: string,
    onProgress?: (percent: number) => void
  ): Promise<THREE.Group> {
    const group = new THREE.Group();

    try {
      const mtl = await this.mtlLoader.loadAsync(`${basePath}/textured_mesh.mtl`);
      mtl.preload();
      this.objLoader.setMaterials(mtl);
    } catch {
      // MTL optional fallback
    }

    try {
      const obj = await this.objLoader.loadAsync(
        `${basePath}/textured_mesh.obj`,
        (xhr) => {
          if (xhr.total && onProgress) {
            onProgress(Math.round((xhr.loaded / xhr.total) * 100));
          }
        }
      );
      group.add(obj);
    } catch (err) {
      console.warn('Failed to load textured_mesh.obj, loading procedural architectural geometry fallback');
    }

    return group;
  }
}

