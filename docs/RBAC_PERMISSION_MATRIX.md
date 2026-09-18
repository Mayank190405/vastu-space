# RBAC PERMISSION MATRIX
*Generated for Phase 2.4 Audit*

## Roles Definition
- **Admin**: Full control over the Organization and all underlying resources.
- **Manager**: Can manage Projects, Captures, and resources, but cannot manage Organization billing or delete the Organization.
- **Member**: Can upload Captures, view Projects, and interact with the 3D Viewer. Cannot delete Projects or manage Organization members.
- **Viewer**: Read-only access to Projects, Viewer, and POIs.

## Permission Matrix

| Resource | Action | Admin | Manager | Member | Viewer |
|---|---|---|---|---|---|
| **Organization** | Update Org Profile | ✅ | ❌ | ❌ | ❌ |
| | Invite Members | ✅ | ✅ | ❌ | ❌ |
| | Remove Members | ✅ | ❌ | ❌ | ❌ |
| | Delete Org | ✅ | ❌ | ❌ | ❌ |
| **Project** | Create Project | ✅ | ✅ | ❌ | ❌ |
| | View Project | ✅ | ✅ | ✅ | ✅ |
| | Update Project | ✅ | ✅ | ❌ | ❌ |
| | Soft Delete | ✅ | ✅ | ❌ | ❌ |
| | Hard Delete | ✅ | ❌ | ❌ | ❌ |
| | Add Timeline Event| ✅ | ✅ | ✅ | ❌ |
| **Capture / Upload**| Register Capture | ✅ | ✅ | ✅ | ❌ |
| | Upload Chunks | ✅ | ✅ | ✅ | ❌ |
| **Processing Job** | Trigger Job | ✅ | ✅ | ✅ | ❌ |
| | View Job Status | ✅ | ✅ | ✅ | ✅ |
| **Model / POI** | Create/Update | ✅ | ✅ | ✅ | ❌ |
| | Delete | ✅ | ✅ | ❌ | ❌ |
| | View | ✅ | ✅ | ✅ | ✅ |
| **Viewer / Nav** | Add Annotation | ✅ | ✅ | ✅ | ❌ |
| | Calculate Route | ✅ | ✅ | ✅ | ✅ |

*Note: All actions are implicitly scoped to the Tenant (Organization) of the User. Cross-tenant access is strictly denied at the database query level.*
