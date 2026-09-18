import {
  AuthTokens,
  User,
  Organization,
  OrganizationDocument,
  OrganizationMember,
  OrganizationJoinRequest,
  Project,
  ProjectFloor,
  FloorPlan,
  ProjectMember,
  ProjectCreationFullInput,
  ProjectTypeDefinition,
  LocationSearchResult,
  CreateFloorInput,
  UpdateFloorInput,
  AssignProjectMemberInput,
} from '../types';

const API_BASE = '/api/v1';

class ApiService {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem('vastu_access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const authHeaders = this.getAuthHeader();
    Object.assign(headers, authHeaders);

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/otp')) {
        // Attempt refresh
        const refreshed = await this.refreshToken();
        if (refreshed) {
          return this.request<T>(endpoint, options);
        }
      }
      const errorMsg = data.message || data.error || `Request failed with status ${response.status}`;
      throw new Error(errorMsg);
    }

    return (data.data !== undefined ? data.data : data) as T;
  }

  async refreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('vastu_refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/token/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        this.clearTokens();
        return false;
      }
      const result = await response.json();
      const tokens: AuthTokens = result.data || result;
      localStorage.setItem('vastu_access_token', tokens.access_token);
      localStorage.setItem('vastu_refresh_token', tokens.refresh_token);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  clearTokens() {
    localStorage.removeItem('vastu_access_token');
    localStorage.removeItem('vastu_refresh_token');
  }

  // --- AUTH ENDPOINTS ---

  async sendOTP(email: string, purpose: 'LOGIN' | 'ORG_SIGNUP' | 'EMPLOYEE_SIGNUP' = 'LOGIN') {
    return this.request<{ email: string; purpose: string }>('/auth/otp/send', {
      method: 'POST',
      body: JSON.stringify({ email, purpose }),
    });
  }

  async verifyOTP(email: string, otpCode: string, purpose: string = 'LOGIN') {
    return this.request<{
      user?: User;
      tokens?: AuthTokens;
      memberships?: OrganizationMember[];
    }>('/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ email, otp_code: otpCode, purpose }),
    });
  }

  async login(email: string, password?: string) {
    return this.request<{
      user: User;
      tokens: AuthTokens;
      memberships: OrganizationMember[];
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async googleAuth(idToken: string) {
    return this.request<{
      user: User;
      tokens: AuthTokens;
      memberships: OrganizationMember[];
    }>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken }),
    });
  }

  async completeOrganizationSignup(input: {
    applicant_name: string;
    email: string;
    phone: string;
    password?: string;
    google_token?: string;
    organization_name: string;
    legal_name?: string;
    organization_type?: string;
    industry?: string;
    official_email?: string;
    official_phone?: string;
    website?: string;
    year_established?: number;
    number_of_employees?: string;
    business_type?: string;
    description?: string;
    logo_url?: string;
    identifier_type?: string;
    identifier_value?: string;
    document_url?: string;
    document_name?: string;
    document_type?: string;
    address_line1?: string;
    address_line2?: string;
    locality?: string;
    city?: string;
    district?: string;
    state?: string;
    country?: string;
    pincode?: string;
  }) {
    return this.request<{
      user: User;
      organization: {
        id: string;
        org_code: string;
        name: string;
        legal_name?: string;
        role: string;
      };
      tokens: AuthTokens;
      invite: {
        invite_url: string;
        invite_token: string;
        whatsapp_message: string;
      };
    }>('/auth/signup/organization', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async submitEmployeeJoin(input: {
    org_code: string;
    invite_token?: string;
    full_name: string;
    email: string;
    phone?: string;
    password?: string;
    google_token?: string;
  }) {
    return this.request<{
      user: User;
      organization: {
        id: string;
        org_code: string;
        name: string;
      };
      join_request: {
        id: string;
        status: string;
      };
      tokens: AuthTokens;
    }>('/auth/signup/emp', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async getMe() {
    return this.request<{
      user: User;
      active_org?: Organization;
      active_role?: string;
      memberships: OrganizationMember[];
      claims: any;
    }>('/auth/me');
  }

  async logout() {
    const refreshToken = localStorage.getItem('vastu_refresh_token');
    try {
      await this.request('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } finally {
      this.clearTokens();
    }
  }

  // --- PUBLIC INVITE VALIDATION ---
  async validateInvite(orgCode: string, inviteToken: string) {
    return this.request<{
      valid: boolean;
      organization_id: string;
      organization_name: string;
      org_code: string;
    }>(`/organizations/invites/${orgCode}/${inviteToken}`);
  }

  // --- ORGANIZATION MANAGEMENT (PROTECTED) ---

  async getMyOrg() {
    return this.request<{
      organization: Organization;
      address?: any;
      documents?: OrganizationDocument[];
      members_count: number;
      role: string;
    }>('/organizations/me');
  }

  async updateOrgDetails(updates: Partial<Organization>) {
    return this.request<Organization>('/organizations/me', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async updateOrgContact(contact: { official_email?: string; official_phone?: string; alternate_phone?: string }) {
    return this.request<Organization>('/organizations/me/contact', {
      method: 'PATCH',
      body: JSON.stringify(contact),
    });
  }

  async updateOrgAddress(address: any) {
    return this.request<any>('/organizations/me/address', {
      method: 'PATCH',
      body: JSON.stringify(address),
    });
  }

  async verifyGST(gstin: string) {
    return this.request<any>('/organizations/me/gst', {
      method: 'POST',
      body: JSON.stringify({ gstin }),
    });
  }

  async uploadDocument(file: File, documentType: string) {
    const formData = new FormData();
    formData.append('document', file);
    formData.append('document_type', documentType);

    return this.request<OrganizationDocument>('/organizations/me/documents', {
      method: 'POST',
      body: formData,
    });
  }

  async listDocuments() {
    return this.request<OrganizationDocument[]>('/organizations/me/documents');
  }

  async deleteDocument(id: string) {
    return this.request<void>(`/organizations/me/documents/${id}`, {
      method: 'DELETE',
    });
  }

  async listMembers() {
    return this.request<OrganizationMember[]>('/organizations/me/members');
  }

  async createInvite() {
    return this.request<{
      invite_id: string;
      invite_url: string;
      invite_token: string;
      expires_at: string;
      whatsapp_message: string;
    }>('/organizations/me/invites', {
      method: 'POST',
    });
  }

  async listJoinRequests() {
    return this.request<OrganizationJoinRequest[]>('/organizations/me/join-requests');
  }

  async reviewJoinRequest(requestId: string, status: 'APPROVED' | 'REJECTED', assignedRole: string) {
    return this.request<void>(`/organizations/me/join-requests/${requestId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, assigned_role: assignedRole }),
    });
  }

  // --- LOCATION ENDPOINTS ---

  async searchLocations(query: string, limit: number = 5): Promise<{ query: string; results: LocationSearchResult[] }> {
    return this.request<{ query: string; results: LocationSearchResult[] }>(
      `/locations/search?q=${encodeURIComponent(query)}&limit=${limit}`
    );
  }

  async reverseGeocode(lat: number, lng: number): Promise<LocationSearchResult> {
    return this.request<LocationSearchResult>(`/locations/reverse?lat=${lat}&lng=${lng}`);
  }

  // --- PROJECT CREATION & MANAGEMENT ENDPOINTS ---

  async getProjectTypes(): Promise<ProjectTypeDefinition[]> {
    return this.request<ProjectTypeDefinition[]>('/projects/types');
  }

  async listProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}`);
  }

  async getProjectFull(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}/full`);
  }

  async createProject(input: ProjectCreationFullInput): Promise<Project> {
    return this.request<Project>('/projects/create-full', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async saveProjectDraft(input: ProjectCreationFullInput): Promise<Project> {
    return this.request<Project>('/projects/draft', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async uploadProjectCover(file: File): Promise<{ cover_image_id: string; cover_image_url: string }> {
    const formData = new FormData();
    formData.append('cover_image', file);
    return this.request<{ cover_image_id: string; cover_image_url: string }>('/projects/cover-image', {
      method: 'POST',
      body: formData,
    });
  }

  async updateProject(id: string, data: Partial<Project>): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async softDeleteProject(id: string): Promise<void> {
    return this.request<void>(`/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // --- FLOORS & SECTIONS ---

  async listFloors(projectId: string): Promise<ProjectFloor[]> {
    return this.request<ProjectFloor[]>(`/projects/${projectId}/floors`);
  }

  async addFloor(projectId: string, input: CreateFloorInput): Promise<ProjectFloor> {
    return this.request<ProjectFloor>(`/projects/${projectId}/floors`, {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async updateFloor(projectId: string, floorId: string, input: UpdateFloorInput): Promise<ProjectFloor> {
    return this.request<ProjectFloor>(`/projects/${projectId}/floors/${floorId}`, {
      method: 'PUT',
      body: JSON.stringify(input),
    });
  }

  async deleteFloor(projectId: string, floorId: string): Promise<void> {
    return this.request<void>(`/projects/${projectId}/floors/${floorId}`, {
      method: 'DELETE',
    });
  }

  // --- FLOOR PLANS (UPLOAD & VECTOR CANVAS) ---

  async uploadFloorPlan(projectId: string, floorId: string, file: File): Promise<FloorPlan> {
    const formData = new FormData();
    formData.append('floor_plan', file);
    return this.request<FloorPlan>(`/projects/${projectId}/floors/${floorId}/floor-plan/upload`, {
      method: 'POST',
      body: formData,
    });
  }

  async drawFloorPlan(
    projectId: string,
    floorId: string,
    data: {
      canvas_width: number;
      canvas_height: number;
      scale_ratio: number;
      drawing_data: any;
      preview_base64?: string;
    }
  ): Promise<FloorPlan> {
    return this.request<FloorPlan>(`/projects/${projectId}/floors/${floorId}/floor-plan/draw`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getFloorPlan(projectId: string, floorId: string): Promise<FloorPlan> {
    return this.request<FloorPlan>(`/projects/${projectId}/floors/${floorId}/floor-plan`);
  }

  // --- PROJECT MEMBERS ---

  async listProjectMembers(projectId: string): Promise<ProjectMember[]> {
    return this.request<ProjectMember[]>(`/projects/${projectId}/members`);
  }

  async addProjectMember(projectId: string, input: AssignProjectMemberInput): Promise<ProjectMember> {
    return this.request<ProjectMember>(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  async removeProjectMember(projectId: string, userId: string): Promise<void> {
    return this.request<void>(`/projects/${projectId}/members/${userId}`, {
      method: 'DELETE',
    });
  }

  // --- PROJECT 3D DIGITAL TWIN RENDERS & VIEWING LINKS ---

  async getProjectRender(projectId: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/render`);
  }

  async getProjectViewingLink(projectId: string): Promise<{ viewing_url: string; share_token?: string }> {
    return this.request<{ viewing_url: string; share_token?: string }>(`/projects/${projectId}/view-link`);
  }
}

export const api = new ApiService();
