package domain

import (
	"time"

	"github.com/google/uuid"
)

type MemberRole string

const (
	RoleOwner           MemberRole = "owner"
	RoleOrgAdmin        MemberRole = "org_admin"
	RoleProjectManager  MemberRole = "project_manager"
	RoleCaptureOperator MemberRole = "capture_operator"
	RoleViewer          MemberRole = "viewer"
	RoleMember          MemberRole = "member"
)

type MemberStatus string

const (
	MemberStatusPendingApproval MemberStatus = "pending_approval"
	MemberStatusActive          MemberStatus = "active"
	MemberStatusRejected        MemberStatus = "rejected"
	MemberStatusSuspended       MemberStatus = "suspended"
)

type OrganizationMember struct {
	ID         uuid.UUID    `json:"id"`
	OrgID      uuid.UUID    `json:"org_id"`
	UserID     uuid.UUID    `json:"user_id"`
	Role       MemberRole   `json:"role"`
	Status     MemberStatus `json:"status"`
	ApprovedBy *uuid.UUID   `json:"approved_by,omitempty"`
	ApprovedAt *time.Time   `json:"approved_at,omitempty"`
	CreatedAt  time.Time    `json:"created_at"`
	UpdatedAt  time.Time    `json:"updated_at"`

	// Joined details for API responses
	UserName  string `json:"user_name,omitempty"`
	UserEmail string `json:"user_email,omitempty"`
	OrgName   string `json:"org_name,omitempty"`
	OrgCode   string `json:"org_code,omitempty"`
}

type JoinOrgInput struct {
	OrgCode string `json:"org_code"`
}

type ApproveMemberInput struct {
	AssignedRole MemberRole `json:"assigned_role"`
}
