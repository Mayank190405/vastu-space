/**
 * VĀSTU Spatial Computing Platform: Shared Canonical Contracts
 * Authoritative single source of truth schemas across iOS, Android, and Web clients.
 * Zero mock, zero fallback.
 */

export type UUID = string;

export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type QualityVerdict = 'PASS' | 'WARNING' | 'FAIL';

export type ProvenanceCode = 0 | 1 | 2 | 3;
export type ProvenanceTag = 'OBSERVED' | 'ESTIMATED' | 'INFERRED' | 'UNRESOLVED';

export interface SpatialVector3 {
  x: number;
  y: number;
  z: number;
}

export interface UserProfile {
  id: UUID;
  email: string;
  full_name: string;
  phone?: string;
  role?: string;
  avatar_url?: string;
}

export interface Organization {
  id: UUID;
  name: string;
  org_code: string;
  slug?: string;
  verified_domain?: string;
  subscription_tier?: string;
  created_at?: string;
}

export interface ProjectFloor {
  id: UUID;
  project_id: UUID;
  name: string;
  floor_number: number;
  floor_type?: string;
  area_value?: number;
  area_unit?: string;
  height_value?: number;
  height_unit?: string;
  sequence?: number;
  created_at?: string;
}

export interface SpatialPOI {
  id: UUID;
  project_id: UUID;
  floor_id?: UUID;
  name: string;
  category?: string;
  position: [number, number, number]; // [x, y, z] in world meters
  color: string;
  description?: string;
  created_at?: string;
}

export interface CreatePOIInput {
  project_id: UUID;
  floor_id?: UUID;
  name: string;
  category?: string;
  position: [number, number, number];
  color?: string;
  description?: string;
}

export interface Project {
  id: UUID;
  name: string;
  project_code: string;
  project_type: string;
  status: string;
  description?: string;
  total_area_sqft?: number;
  total_area_sqm?: number;
  total_floors_count?: number;
  precision_gate_cm?: number;
  floors?: ProjectFloor[];
  team?: any[];
  cover_image_url?: string;
  created_at: string;
  updated_at?: string;
}

export interface UploadSession {
  session_id: UUID;
  project_id: UUID;
  floor_id?: UUID;
  status: 'INITIALIZED' | 'UPLOADING' | 'COMPLETED' | 'FAILED';
  total_chunks: number;
  chunk_size_bytes: number;
  total_size_bytes: number;
  chunks_received: number[];
  created_at: string;
}

export interface ReconstructionJob {
  id: UUID;
  project_id: UUID;
  capture_session_id?: UUID;
  status: JobStatus;
  current_stage: string;
  progress: number;
  error_message?: string;
  worker_node_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface NavigationRouteStep {
  step_index: number;
  instruction: string;
  turn_type: 'straight' | 'turn-left' | 'turn-right' | 'arrive';
  distance_meters: number;
  from_position: SpatialVector3;
  to_position: SpatialVector3;
}

export interface NavigationRoute {
  project_id: UUID;
  total_distance_meters: number;
  estimated_walk_seconds: number;
  is_wheelchair_accessible: boolean;
  waypoints: SpatialVector3[];
  steps?: NavigationRouteStep[];
}

export interface DigitalTwinSummary {
  project_id: string;
  project_name: string;
  quality_status: QualityVerdict;
  quality_score: number;
  stages_executed: number;
  statistics?: {
    mesh_vertices?: number;
    mesh_triangles?: number;
    room_dimensions?: string;
    texture_resolution?: string;
  };
  assets: {
    obj_mesh?: string;
    mtl_material?: string;
    texture_atlas?: string;
    ply_mesh?: string;
    point_cloud?: string;
    viewing_link?: string;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}
