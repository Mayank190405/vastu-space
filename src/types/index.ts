export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  avatar_url?: string;
  auth_provider: string;
  is_email_verified: boolean;
  status: string;
  global_role: string;
  created_at: string;
}

export interface Organization {
  id: string;
  org_code: string;
  name: string;
  legal_name?: string;
  org_type?: string;
  industry?: string;
  country?: string;
  state?: string;
  city?: string;
  website?: string;
  official_email?: string;
  official_phone?: string;
  year_established?: number;
  number_of_employees?: string;
  business_type?: string;
  description?: string;
  logo_url?: string;
  status: string;
  created_at: string;
}

export interface OrganizationAddress {
  id: string;
  organization_id: string;
  type: string;
  address_line1: string;
  address_line2?: string;
  locality?: string;
  city: string;
  district?: string;
  state: string;
  country: string;
  pincode: string;
  is_primary: boolean;
}

export interface OrganizationDocument {
  id: string;
  organization_id: string;
  document_type: string;
  file_id: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  verification_status: string;
  uploaded_at: string;
}

export interface OrganizationMember {
  id: string;
  org_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'project_manager' | 'manager' | 'employee' | 'member' | string;
  status: 'active' | 'suspended' | 'invited' | 'pending_approval' | string;
  created_at: string;
  user_name?: string;
  user_email?: string;
  org_name?: string;
  org_code?: string;
  user?: User;
  organization?: Organization;
}

export interface OrganizationJoinRequest {
  id: string;
  organization_id: string;
  user_id: string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone?: string;
  requested_role: string;
  assigned_role?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_at?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ==================== PROJECT ESCALATION TYPES ====================

export interface LocationSearchResult {
  place_id: string;
  display_name: string;
  address_line_1: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  latitude: number;
  longitude: number;
}

export interface ProjectAddress {
  id?: string;
  project_id?: string;
  address_line_1: string;
  address_line_2?: string;
  area?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  latitude?: number;
  longitude?: number;
  place_id?: string;
}

export interface DrawingObject {
  id: string;
  type: 'wall' | 'room' | 'door' | 'window' | 'line' | 'rect' | 'polygon';
  points?: { x: number; y: number }[];
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  strokeColor?: string;
  fillColor?: string;
  lineWidth?: number;
  label?: string;
}

export interface FloorPlanDrawingData {
  objects: DrawingObject[];
  scale_unit?: string;
}

export interface FloorPlan {
  id: string;
  floor_id: string;
  plan_type: 'UPLOADED' | 'DRAWN';
  file_id?: string;
  file_url?: string;
  original_file_name?: string;
  file_size_bytes?: number;
  mime_type?: string;
  canvas_width: number;
  canvas_height: number;
  scale_ratio: number;
  drawing_data?: FloorPlanDrawingData;
  preview_file_id?: string;
  preview_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectFloor {
  id: string;
  project_id: string;
  name: string;
  floor_number: number;
  floor_type: string;
  area_value: number;
  area_unit: 'SQFT' | 'SQM';
  height_value: number;
  height_unit: 'FT' | 'M';
  sequence: number;
  description?: string;
  floor_plan?: FloorPlan;
  created_at?: string;
  updated_at?: string;
}

export interface CreateFloorInput {
  name: string;
  floor_number: number;
  floor_type: string;
  area_value: number;
  area_unit: string;
  height_value: number;
  height_unit: string;
  sequence: number;
  description?: string;
}

export interface UpdateFloorInput {
  name?: string;
  floor_number?: number;
  floor_type?: string;
  area_value?: number;
  area_unit?: string;
  height_value?: number;
  height_unit?: string;
  sequence?: number;
  description?: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  project_role: 'Project Admin' | 'Project Manager' | 'Site Manager' | 'Surveyor' | 'Architect' | 'Engineer' | 'Supervisor' | 'Field Executive' | 'Viewer' | string;
  permissions?: string[];
  status: string;
  assigned_by?: string;
  assigned_at: string;
  user?: User;
}

export interface AssignProjectMemberInput {
  user_id: string;
  project_role: string;
}

export interface ProjectTypeDefinition {
  key: string;
  name: string;
  category: string;
  description: string;
  multi_floor: boolean;
  default_floor_types: string[];
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  project_code?: string;
  slug: string;
  description?: string;
  priority: string;
  status: 'DRAFT' | 'ACTIVE' | 'ARCHIVED' | 'COMPLETED' | string;
  total_area_sqft: number;
  total_area_sqm: number;
  total_floors_count: number;
  precision_gate_cm: number;
  created_at: string;
  updated_at: string;

  // Escalation fields
  cover_image_id?: string;
  cover_image_url?: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  project_type: string;
  custom_type?: string;

  address?: ProjectAddress;
  floors?: ProjectFloor[];
  team?: ProjectMember[];
}

export interface ProjectCreationFullInput {
  name: string;
  cover_image_id?: string;
  cover_image_url?: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  project_type: string;
  custom_type?: string;
  description?: string;
  status?: string; // DRAFT or ACTIVE
  address: {
    address_line_1: string;
    address_line_2?: string;
    area?: string;
    city: string;
    state: string;
    pincode: string;
    country: string;
    latitude?: number;
    longitude?: number;
    place_id?: string;
  };
  floors: CreateFloorInput[];
  members: AssignProjectMemberInput[];
}

