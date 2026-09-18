package domain

import (
	"time"

	"github.com/google/uuid"
)

type OrgStatus string

const (
	OrgStatusPendingReview OrgStatus = "pending_review"
	OrgStatusActive        OrgStatus = "active"
	OrgStatusSuspended     OrgStatus = "suspended"
	OrgStatusRejected      OrgStatus = "rejected"
)

type Organization struct {
	ID                   uuid.UUID `json:"id"`
	OrgCode              string    `json:"org_code"` // Exactly 12-char URL-safe alphanumeric code
	Name                 string    `json:"name"`
	LegalName            *string   `json:"legal_name,omitempty"`
	OrgType              string    `json:"org_type"`
	Industry             string    `json:"industry"`
	Country              string    `json:"country"`
	State                string    `json:"state"`
	City                 string    `json:"city"`
	Website              string    `json:"website"`
	OrgSize              string    `json:"org_size"`
	Address              string    `json:"address"`
	PhoneNumber          string    `json:"phone_number"`
	OfficialEmail        *string   `json:"official_email,omitempty"`
	OfficialPhone        *string   `json:"official_phone,omitempty"`
	AlternatePhone       *string   `json:"alternate_phone,omitempty"`
	YearEstablished      *int      `json:"year_established,omitempty"`
	NumberOfEmployees    *string   `json:"number_of_employees,omitempty"`
	BusinessType         *string   `json:"business_type,omitempty"`
	GSTNumber            string    `json:"gst_number"`
	PANNumber            string    `json:"pan_number"`
	RegistrationNumber   string    `json:"registration_number"`
	LogoURL              string    `json:"logo_url"`
	Domain               string    `json:"domain"`
	Description          string    `json:"description"`
	TaxIDType            string    `json:"tax_id_type"`
	TaxIDNumber          string    `json:"tax_id_number"`
	DocumentURL          string    `json:"document_url"`
	DocumentOriginalName *string   `json:"document_original_name,omitempty"`
	Status               OrgStatus `json:"status"`
	CreatedAt            time.Time `json:"created_at"`
	UpdatedAt            time.Time `json:"updated_at"`
}

type OrganizationIdentifier struct {
	ID                 uuid.UUID  `json:"id"`
	OrganizationID     uuid.UUID  `json:"organization_id"`
	Type               string     `json:"type"` // GSTIN, PAN, UDYAM, SHOP_ACT
	Value              string     `json:"value"`
	NormalizedValue    string     `json:"normalized_value"`
	VerificationStatus string     `json:"verification_status"` // UNVERIFIED, VERIFIED, FAILED
	VerifiedAt         *time.Time `json:"verified_at,omitempty"`
	CreatedAt          time.Time  `json:"created_at"`
}

type OrganizationDocument struct {
	ID                 uuid.UUID  `json:"id"`
	OrganizationID     uuid.UUID  `json:"organization_id"`
	DocumentType       string     `json:"document_type"`
	FileID             string     `json:"file_id"`
	FileName           string     `json:"file_name"`
	MimeType           string     `json:"mime_type"`
	FileSize           int64      `json:"file_size"`
	DocumentNumber     *string    `json:"document_number,omitempty"`
	VerificationStatus string     `json:"verification_status"`
	UploadedAt         time.Time  `json:"uploaded_at"`
	VerifiedAt         *time.Time `json:"verified_at,omitempty"`
}

type OrganizationAddress struct {
	ID             uuid.UUID `json:"id"`
	OrganizationID uuid.UUID `json:"organization_id"`
	Type           string    `json:"type"` // PRIMARY, REGISTERED, BRANCH
	AddressLine1   string    `json:"address_line_1"`
	AddressLine2   *string   `json:"address_line_2,omitempty"`
	Locality       *string   `json:"locality,omitempty"`
	City           string    `json:"city"`
	District       *string   `json:"district,omitempty"`
	State          string    `json:"state"`
	Country        string    `json:"country"`
	Pincode        string    `json:"pincode"`
	Latitude       *float64  `json:"latitude,omitempty"`
	Longitude      *float64  `json:"longitude,omitempty"`
	IsPrimary      bool      `json:"is_primary"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type OrganizationInvite struct {
	ID               uuid.UUID `json:"id"`
	OrganizationID   uuid.UUID `json:"organization_id"`
	TokenHash        string    `json:"-"`
	RawTokenPreview  string    `json:"raw_token_preview"`
	ExpiresAt        time.Time `json:"expires_at"`
	MaxUses          int       `json:"max_uses"`
	UseCount         int       `json:"use_count"`
	IsRevoked        bool      `json:"is_revoked"`
	CreatedBy        *uuid.UUID `json:"created_by,omitempty"`
	CreatedAt        time.Time `json:"created_at"`
}

type OrganizationJoinRequest struct {
	ID             uuid.UUID  `json:"id"`
	OrganizationID uuid.UUID  `json:"organization_id"`
	UserID         uuid.UUID  `json:"user_id"`
	InviteID       *uuid.UUID `json:"invite_id,omitempty"`
	ApplicantName  string     `json:"applicant_name"`
	ApplicantEmail string     `json:"applicant_email"`
	ApplicantPhone string     `json:"applicant_phone"`
	RequestedRole  string     `json:"requested_role"`
	AssignedRole   *string    `json:"assigned_role,omitempty"`
	Status         string     `json:"status"` // PENDING, APPROVED, REJECTED
	ReviewedBy     *uuid.UUID `json:"reviewed_by,omitempty"`
	ReviewedAt     *time.Time `json:"reviewed_at,omitempty"`
	CreatedAt      time.Time  `json:"created_at"`
	OrgName        string     `json:"org_name,omitempty"`
	OrgCode        string     `json:"org_code,omitempty"`
}

type OrgSignupInitialInput struct {
	OrganizationName string `json:"organization_name"`
	ApplicantName    string `json:"applicant_name"`
	Position         string `json:"position"`
	Phone            string `json:"phone"`
	Email            string `json:"email"`
}

type OrgSignupCompleteInput struct {
	// Applicant / User Info
	ApplicantName string `json:"applicant_name"`
	FullName      string `json:"full_name,omitempty"`
	Email         string `json:"email"`
	Phone         string `json:"phone"`
	Position      string `json:"position"`
	Password      string `json:"password,omitempty"`
	GoogleToken   string `json:"google_token,omitempty"`

	// Legal Organization Details
	OrganizationName  string  `json:"organization_name"`
	OrgName           string  `json:"org_name,omitempty"`
	LegalName         string  `json:"legal_name"`
	OrganizationType  string  `json:"organization_type"`
	Industry          string  `json:"industry"`
	OfficialEmail     string  `json:"official_email"`
	OfficialPhone     string  `json:"official_phone"`
	Website           string  `json:"website,omitempty"`
	YearEstablished   *int    `json:"year_established,omitempty"`
	NumberOfEmployees string  `json:"number_of_employees,omitempty"`
	BusinessType      string  `json:"business_type,omitempty"`
	Description       string  `json:"description,omitempty"`
	LogoURL           string  `json:"logo_url,omitempty"`

	// Identifier
	IdentifierType  string `json:"identifier_type"` // GSTIN, PAN, UDYAM, SHOP_ACT
	IdentifierValue string `json:"identifier_value"`

	// Supporting Document
	DocumentType string `json:"document_type,omitempty"`
	DocumentURL  string `json:"document_url,omitempty"`
	DocumentName string `json:"document_name,omitempty"`

	// Structured Address
	AddressLine1 string   `json:"address_line_1"`
	AddressLine2 string   `json:"address_line_2,omitempty"`
	Locality     string   `json:"locality,omitempty"`
	City         string   `json:"city"`
	District     string   `json:"district,omitempty"`
	State        string   `json:"state"`
	Country      string   `json:"country"`
	Pincode      string   `json:"pincode"`
	Latitude     *float64 `json:"latitude,omitempty"`
	Longitude    *float64 `json:"longitude,omitempty"`
}

type EmployeeSignupInput struct {
	OrgCode     string `json:"org_code"`
	InviteToken string `json:"invite_token"`
	FullName    string `json:"full_name"`
	Email       string `json:"email"`
	Phone       string `json:"phone"`
	Password    string `json:"password,omitempty"`
	GoogleToken string `json:"google_token,omitempty"`
}

type OrgSignupInput struct {
	OrgName              string `json:"org_name"`
	OrgType              string `json:"org_type"`
	Industry             string `json:"industry"`
	BusinessEmail        string `json:"business_email"`
	PhoneNumber          string `json:"phone_number"`
	Country              string `json:"country"`
	State                string `json:"state"`
	City                 string `json:"city"`
	Website              string `json:"website"`
	OrgSize              string `json:"org_size"`
	Address              string `json:"address"`
	AdminName            string `json:"admin_name"`
	AdminEmail           string `json:"admin_email"`
	AdminPassword        string `json:"admin_password"`
	GSTNumber            string `json:"gst_number"`
	PANNumber            string `json:"pan_number"`
	RegistrationNumber   string `json:"registration_number"`
	LogoURL              string `json:"logo_url"`
	Domain               string `json:"domain"`
	Description          string `json:"description"`
	TaxIDType            string `json:"tax_id_type"`
	TaxIDNumber          string `json:"tax_id_number"`
	DocumentURL          string `json:"document_url"`
	DocumentOriginalName string `json:"document_original_name"`
}
