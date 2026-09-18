package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/jwt"
	"vastu/backend/internal/pkg/mailer"
	"vastu/backend/internal/pkg/utils"
	"vastu/backend/internal/pkg/validator"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type OrgService struct {
	orgRepo     repository.OrgRepository
	userRepo    repository.UserRepository
	memberRepo  repository.MemberRepository
	identRepo   repository.IdentifierRepository
	docRepo     repository.DocumentRepository
	addrRepo    repository.AddressRepository
	inviteRepo  repository.InviteRepository
	joinReqRepo repository.JoinRequestRepository
	mailer      *mailer.SMTPMailer
	jwtManager  *jwt.TokenManager
	appBaseURL  string
}

func NewOrgService(
	orgRepo repository.OrgRepository,
	userRepo repository.UserRepository,
	memberRepo repository.MemberRepository,
	identRepo repository.IdentifierRepository,
	docRepo repository.DocumentRepository,
	addrRepo repository.AddressRepository,
	inviteRepo repository.InviteRepository,
	joinReqRepo repository.JoinRequestRepository,
	mailer *mailer.SMTPMailer,
	jwtManager *jwt.TokenManager,
	appBaseURL string,
) *OrgService {
	if appBaseURL == "" {
		appBaseURL = "http://localhost:3000"
	}
	return &OrgService{
		orgRepo:     orgRepo,
		userRepo:    userRepo,
		memberRepo:  memberRepo,
		identRepo:   identRepo,
		docRepo:     docRepo,
		addrRepo:    addrRepo,
		inviteRepo:  inviteRepo,
		joinReqRepo: joinReqRepo,
		mailer:      mailer,
		jwtManager:  jwtManager,
		appBaseURL:  appBaseURL,
	}
}

func (s *OrgService) GetOrgByID(ctx context.Context, orgID uuid.UUID) (*domain.Organization, error) {
	return s.orgRepo.GetByID(ctx, orgID)
}

func (s *OrgService) GetOrgByCode(ctx context.Context, orgCode string) (*domain.Organization, error) {
	return s.orgRepo.GetByCode(ctx, orgCode)
}

func (s *OrgService) UpdateOrgDetails(ctx context.Context, orgID uuid.UUID, updates map[string]interface{}) (*domain.Organization, error) {
	org, err := s.orgRepo.GetByID(ctx, orgID)
	if err != nil {
		return nil, err
	}

	if name, ok := updates["name"].(string); ok && name != "" {
		org.Name = name
	}
	if legalName, ok := updates["legal_name"].(string); ok {
		org.LegalName = &legalName
	}
	if orgType, ok := updates["org_type"].(string); ok {
		org.OrgType = orgType
	}
	if industry, ok := updates["industry"].(string); ok {
		org.Industry = industry
	}
	if website, ok := updates["website"].(string); ok {
		org.Website = website
	}
	if desc, ok := updates["description"].(string); ok {
		org.Description = desc
	}
	if logoURL, ok := updates["logo_url"].(string); ok {
		org.LogoURL = logoURL
	}

	if err := s.orgRepo.Update(ctx, org); err != nil {
		return nil, err
	}
	return org, nil
}

func (s *OrgService) UpdateOrgContact(ctx context.Context, orgID uuid.UUID, officialEmail, officialPhone, altPhone string) (*domain.Organization, error) {
	org, err := s.orgRepo.GetByID(ctx, orgID)
	if err != nil {
		return nil, err
	}

	if officialEmail != "" {
		org.OfficialEmail = &officialEmail
	}
	if officialPhone != "" {
		org.OfficialPhone = &officialPhone
	}
	if altPhone != "" {
		org.AlternatePhone = &altPhone
	}

	if err := s.orgRepo.Update(ctx, org); err != nil {
		return nil, err
	}
	return org, nil
}

func (s *OrgService) UpdateOrgAddress(ctx context.Context, orgID uuid.UUID, addr *domain.OrganizationAddress) (*domain.OrganizationAddress, error) {
	addr.OrganizationID = orgID
	existing, _ := s.addrRepo.GetPrimaryByOrg(ctx, orgID)
	if existing == nil {
		if err := s.addrRepo.Create(ctx, addr); err != nil {
			return nil, err
		}
		return addr, nil
	}

	if err := s.addrRepo.UpdatePrimary(ctx, addr); err != nil {
		return nil, err
	}
	return addr, nil
}

func (s *OrgService) GetOrgAddress(ctx context.Context, orgID uuid.UUID) (*domain.OrganizationAddress, error) {
	return s.addrRepo.GetPrimaryByOrg(ctx, orgID)
}

func (s *OrgService) AddGSTIdentifier(ctx context.Context, orgID uuid.UUID, gstin string) (*domain.OrganizationIdentifier, error) {
	clean := strings.ToUpper(strings.TrimSpace(gstin))
	if !validator.ValidateGSTIN(clean) {
		return nil, errors.New("invalid GSTIN format. Expected 15 alphanumeric characters (e.g. 29AAAAA0000A1Z5)")
	}

	existing, err := s.identRepo.GetByNormalized(ctx, "GSTIN", clean)
	if err == nil && existing != nil {
		if existing.OrganizationID == orgID {
			return existing, nil
		}
		return nil, errors.New("this GSTIN is already registered to another organization")
	}

	ident := &domain.OrganizationIdentifier{
		ID:                 uuid.New(),
		OrganizationID:     orgID,
		Type:               "GSTIN",
		Value:              clean,
		NormalizedValue:    clean,
		VerificationStatus: "VERIFIED", // Verified format
		VerifiedAt:         nil,
	}

	if err := s.identRepo.Create(ctx, ident); err != nil {
		return nil, err
	}
	return ident, nil
}

func (s *OrgService) AddDocument(ctx context.Context, orgID uuid.UUID, docType, fileID, fileName, mimeType string, fileSize int64) (*domain.OrganizationDocument, error) {
	doc := &domain.OrganizationDocument{
		ID:                 uuid.New(),
		OrganizationID:     orgID,
		DocumentType:       docType,
		FileID:             fileID,
		FileName:           fileName,
		MimeType:           mimeType,
		FileSize:           fileSize,
		VerificationStatus: "UPLOADED",
		UploadedAt:         time.Now().UTC(),
	}

	if err := s.docRepo.Create(ctx, doc); err != nil {
		return nil, err
	}
	return doc, nil
}

func (s *OrgService) ListDocuments(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationDocument, error) {
	return s.docRepo.ListByOrg(ctx, orgID)
}

func (s *OrgService) DeleteDocument(ctx context.Context, orgID, docID uuid.UUID) error {
	doc, err := s.docRepo.GetByID(ctx, docID)
	if err != nil || doc == nil {
		return errors.New("document not found")
	}
	if doc.OrganizationID != orgID {
		return errors.New("unauthorized to delete this document")
	}
	return s.docRepo.Delete(ctx, docID)
}

func (s *OrgService) ListMembers(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error) {
	return s.memberRepo.ListByOrg(ctx, orgID)
}

func (s *OrgService) CreateInvite(ctx context.Context, orgID, createdBy uuid.UUID) (map[string]interface{}, error) {
	org, err := s.orgRepo.GetByID(ctx, orgID)
	if err != nil || org == nil {
		return nil, errors.New("organization not found")
	}

	rawToken, tokenHash := utils.GenerateInviteToken()
	preview := rawToken
	if len(preview) > 12 {
		preview = preview[:12]
	}

	invite := &domain.OrganizationInvite{
		ID:              uuid.New(),
		OrganizationID:  orgID,
		TokenHash:       tokenHash,
		RawTokenPreview: preview,
		ExpiresAt:       time.Now().UTC().Add(30 * 24 * time.Hour), // 30 days
		MaxUses:         0,                                         // unlimited
		CreatedBy:       &createdBy,
	}

	if err := s.inviteRepo.Create(ctx, invite); err != nil {
		return nil, err
	}

	inviteURL := fmt.Sprintf("%s/join/%s/%s", s.appBaseURL, org.OrgCode, rawToken)
	whatsAppMsg := fmt.Sprintf("You are invited to join %s.\nJoin the organization using this link:\n%s", org.Name, inviteURL)

	return map[string]interface{}{
		"invite_id":        invite.ID,
		"invite_url":       inviteURL,
		"invite_token":     rawToken,
		"expires_at":       invite.ExpiresAt,
		"whatsapp_message": whatsAppMsg,
	}, nil
}

func (s *OrgService) ValidateInvite(ctx context.Context, orgCode, inviteToken string) (map[string]interface{}, error) {
	cleanOrgCode := strings.ToUpper(strings.TrimSpace(orgCode))
	org, err := s.orgRepo.GetByCode(ctx, cleanOrgCode)
	if err != nil || org == nil {
		return nil, errors.New("invalid organization code")
	}

	tokenHash := utils.HashInviteToken(inviteToken)
	invite, err := s.inviteRepo.GetByTokenHash(ctx, tokenHash)
	if err != nil || invite == nil {
		return nil, errors.New("invalid or expired invite link")
	}

	if invite.IsRevoked || invite.ExpiresAt.Before(time.Now().UTC()) {
		return nil, errors.New("this invite link has expired or been revoked")
	}
	if invite.OrganizationID != org.ID {
		return nil, errors.New("invite token does not belong to this organization")
	}

	return map[string]interface{}{
		"valid":            true,
		"organization_id":  org.ID,
		"organization_name": org.Name,
		"org_code":         org.OrgCode,
	}, nil
}

func (s *OrgService) ListJoinRequests(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationJoinRequest, error) {
	return s.joinReqRepo.ListPendingByOrg(ctx, orgID)
}

func (s *OrgService) ReviewJoinRequest(ctx context.Context, orgID, reqID, reviewerID uuid.UUID, status, assignedRole string) error {
	req, err := s.joinReqRepo.GetByID(ctx, reqID)
	if err != nil || req == nil {
		return errors.New("join request not found")
	}
	if req.OrganizationID != orgID {
		return errors.New("join request does not belong to this organization")
	}

	status = strings.ToUpper(strings.TrimSpace(status))
	if status != "APPROVED" && status != "REJECTED" {
		return errors.New("invalid status: must be APPROVED or REJECTED")
	}

	if err := s.joinReqRepo.UpdateStatus(ctx, reqID, status, &assignedRole, reviewerID); err != nil {
		return err
	}

	if status == "APPROVED" {
		role := domain.MemberRole(strings.ToLower(assignedRole))
		if role == "" {
			role = domain.RoleMember
		}

		member := &domain.OrganizationMember{
			ID:         uuid.New(),
			OrgID:      orgID,
			UserID:     req.UserID,
			Role:       role,
			Status:     domain.MemberStatusActive,
			ApprovedBy: &reviewerID,
		}
		_ = s.memberRepo.Create(ctx, member)
	}

	return nil
}
