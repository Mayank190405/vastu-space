package repository

import (
	"context"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/geo"

	"github.com/google/uuid"
)

type UserRepository interface {
	Create(ctx context.Context, user *domain.User) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.User, error)
	GetByEmail(ctx context.Context, email string) (*domain.User, error)
	GetByGoogleID(ctx context.Context, googleID string) (*domain.User, error)
	GetByAppleID(ctx context.Context, appleID string) (*domain.User, error)
	GetUserByAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.User, error)
	LinkAuthProvider(ctx context.Context, userID uuid.UUID, provider, providerUserID string) error
	GetAuthProvider(ctx context.Context, provider, providerUserID string) (*domain.UserAuthProvider, error)
	UpdateEmailVerified(ctx context.Context, id uuid.UUID, verified bool) error
	UpdateLastLogin(ctx context.Context, id uuid.UUID) error

	// Auth Identities
	LinkAuthIdentity(ctx context.Context, identity *domain.AuthIdentity) error
	GetAuthIdentity(ctx context.Context, provider, providerSubject string) (*domain.AuthIdentity, error)
	GetUserByAuthIdentity(ctx context.Context, provider, providerSubject string) (*domain.User, error)
}

type OrgRepository interface {
	Create(ctx context.Context, org *domain.Organization) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Organization, error)
	GetByCode(ctx context.Context, orgCode string) (*domain.Organization, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status domain.OrgStatus) error
	UpdateOrgCode(ctx context.Context, id uuid.UUID, newCode string) error
	Update(ctx context.Context, org *domain.Organization) error

	// Atomic Organization Onboarding Transaction
	CreateOrganizationAtomic(
		ctx context.Context,
		user *domain.User,
		authIdentity *domain.AuthIdentity,
		org *domain.Organization,
		identifier *domain.OrganizationIdentifier,
		document *domain.OrganizationDocument,
		address *domain.OrganizationAddress,
		member *domain.OrganizationMember,
		invite *domain.OrganizationInvite,
	) error
}

type IdentifierRepository interface {
	Create(ctx context.Context, ident *domain.OrganizationIdentifier) error
	GetByNormalized(ctx context.Context, identType, normalized string) (*domain.OrganizationIdentifier, error)
	ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationIdentifier, error)
	Verify(ctx context.Context, id uuid.UUID, status string) error
}

type DocumentRepository interface {
	Create(ctx context.Context, doc *domain.OrganizationDocument) error
	ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationDocument, error)
	GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationDocument, error)
	Delete(ctx context.Context, id uuid.UUID) error
}

type AddressRepository interface {
	Create(ctx context.Context, addr *domain.OrganizationAddress) error
	GetPrimaryByOrg(ctx context.Context, orgID uuid.UUID) (*domain.OrganizationAddress, error)
	UpdatePrimary(ctx context.Context, addr *domain.OrganizationAddress) error
}

type InviteRepository interface {
	Create(ctx context.Context, invite *domain.OrganizationInvite) error
	GetByTokenHash(ctx context.Context, tokenHash string) (*domain.OrganizationInvite, error)
	GetActiveByOrg(ctx context.Context, orgID uuid.UUID) (*domain.OrganizationInvite, error)
	IncrementUse(ctx context.Context, id uuid.UUID) error
	Revoke(ctx context.Context, id uuid.UUID) error
}

type JoinRequestRepository interface {
	Create(ctx context.Context, req *domain.OrganizationJoinRequest) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationJoinRequest, error)
	GetByOrgAndUser(ctx context.Context, orgID, userID uuid.UUID) (*domain.OrganizationJoinRequest, error)
	ListPendingByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationJoinRequest, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status string, assignedRole *string, reviewerID uuid.UUID) error
}

type MemberRepository interface {
	Create(ctx context.Context, member *domain.OrganizationMember) error
	GetByOrgAndUser(ctx context.Context, orgID, userID uuid.UUID) (*domain.OrganizationMember, error)
	GetByID(ctx context.Context, id uuid.UUID) (*domain.OrganizationMember, error)
	GetUserMemberships(ctx context.Context, userID uuid.UUID) ([]*domain.OrganizationMember, error)
	GetPendingMembersByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error)
	ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.OrganizationMember, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status domain.MemberStatus, role domain.MemberRole, approvedBy uuid.UUID, approvedAt time.Time) error
}

type OTPRepository interface {
	Create(ctx context.Context, otp *domain.EmailOTP) error
	GetValidOTP(ctx context.Context, email, otpCode string, purpose domain.OtpPurpose) (*domain.EmailOTP, error)
	MarkAsUsed(ctx context.Context, id uuid.UUID) error
	CountRecentAttempts(ctx context.Context, email string, purpose domain.OtpPurpose, window time.Duration) (int, error)
}

type TokenRepository interface {
	CreateRefreshToken(ctx context.Context, token *domain.RefreshToken) error
	GetRefreshToken(ctx context.Context, tokenHash string) (*domain.RefreshToken, error)
	RevokeRefreshToken(ctx context.Context, tokenHash string) error
	RevokeUserTokens(ctx context.Context, userID uuid.UUID) error
}

type ProjectRepository interface {
	Create(ctx context.Context, project *domain.Project) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Project, error)
	ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error)
	ListTrashByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error)
	Update(ctx context.Context, project *domain.Project) error
	SoftDelete(ctx context.Context, id uuid.UUID) error
	Restore(ctx context.Context, id uuid.UUID) error
	PermanentDelete(ctx context.Context, id uuid.UUID) error
	Archive(ctx context.Context, id uuid.UUID) error

	CreateStructure(ctx context.Context, structure *domain.ProjectStructure) error
	ListStructuresByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectStructure, error)
	CreateLevel(ctx context.Context, level *domain.SpatialLevel) error
	ListLevelsByStructure(ctx context.Context, structureID uuid.UUID) ([]*domain.SpatialLevel, error)
	CreateSection(ctx context.Context, section *domain.SpatialSection) error
	ListSectionsByLevel(ctx context.Context, levelID uuid.UUID) ([]*domain.SpatialSection, error)

	CreateProjectUpdate(ctx context.Context, update *domain.ProjectUpdate) error
	ListProjectUpdates(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectUpdate, error)

	CreateTimelineEvent(ctx context.Context, event *domain.TimelineEvent) error
	ListTimelineEvents(ctx context.Context, projectID uuid.UUID) ([]*domain.TimelineEvent, error)
	UpdateTimelineEventStatus(ctx context.Context, eventID uuid.UUID, status string) error
	AddTimelineComment(ctx context.Context, comment *domain.TimelineComment) error
	ListTimelineComments(ctx context.Context, eventID uuid.UUID) ([]*domain.TimelineComment, error)

	CreateChatMessage(ctx context.Context, msg *domain.ProjectChatMessage) error
	ListChatMessages(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectChatMessage, error)
	ResolveChatMessage(ctx context.Context, messageID uuid.UUID, resolvedBy string) error

	LogClientEmail(ctx context.Context, log *domain.ClientEmailLog) error
	ListClientEmails(ctx context.Context, projectID uuid.UUID) ([]*domain.ClientEmailLog, error)

	LogProjectActivity(ctx context.Context, log *domain.ProjectActivityLog) error
	ListProjectActivities(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectActivityLog, error)

	// Project Escalation: Address, Floors, Floor Plans, Members
	SaveAddress(ctx context.Context, addr *domain.ProjectAddress) error
	GetAddressByProjectID(ctx context.Context, projectID uuid.UUID) (*domain.ProjectAddress, error)

	CreateFloor(ctx context.Context, floor *domain.ProjectFloor) error
	GetFloorByID(ctx context.Context, floorID uuid.UUID) (*domain.ProjectFloor, error)
	ListFloorsByProjectID(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectFloor, error)
	UpdateFloor(ctx context.Context, floor *domain.ProjectFloor) error
	DeleteFloor(ctx context.Context, floorID uuid.UUID) error

	SaveFloorPlan(ctx context.Context, plan *domain.FloorPlan) error
	GetFloorPlanByFloorID(ctx context.Context, floorID uuid.UUID) (*domain.FloorPlan, error)
	DeleteFloorPlan(ctx context.Context, floorID uuid.UUID) error

	AddProjectMember(ctx context.Context, member *domain.ProjectMember) error
	ListProjectMembers(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectMember, error)
	RemoveProjectMember(ctx context.Context, projectID, userID uuid.UUID) error
}

type CaptureRepository interface {
	Create(ctx context.Context, capture *domain.Capture) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.Capture, error)
	ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.Capture, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status domain.CaptureStatus, qualityScore *float64, manifestURL, videoURL, imuURL, lidarURL *string) error
}

type UploadRepository interface {
	CreateSession(ctx context.Context, session *domain.UploadSession) error
	GetSessionByID(ctx context.Context, id uuid.UUID) (*domain.UploadSession, error)
	SaveChunk(ctx context.Context, chunk *domain.UploadChunk) error
	ListChunksBySession(ctx context.Context, sessionID uuid.UUID) ([]*domain.UploadChunk, error)
	UpdateSessionStatus(ctx context.Context, sessionID uuid.UUID, status domain.UploadStatus, uploadedChunks int) error
}

type JobRepository interface {
	Create(ctx context.Context, job *domain.ProcessingJob) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.ProcessingJob, error)
	ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProcessingJob, error)
	UpdateProgress(ctx context.Context, id uuid.UUID, stage domain.JobStage, progress int, workerNodeID, errorCode, errorMessage *string) error
	AddLog(ctx context.Context, log *domain.JobLog) error
	ListLogs(ctx context.Context, jobID uuid.UUID) ([]*domain.JobLog, error)
}

type ModelRepository interface {
	Create(ctx context.Context, model *domain.SpatialModel) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialModel, error)
	ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialModel, error)
	GetActiveByProject(ctx context.Context, projectID uuid.UUID) (*domain.SpatialModel, error)
	CreateArtifact(ctx context.Context, artifact *domain.ModelArtifact) error
	ListArtifactsByModel(ctx context.Context, modelID uuid.UUID) ([]*domain.ModelArtifact, error)
	PublishModel(ctx context.Context, modelID uuid.UUID) error
	SetActiveVersion(ctx context.Context, projectID, modelID uuid.UUID) error
	Update(ctx context.Context, model *domain.SpatialModel) error
}

type POIRepository interface {
	Create(ctx context.Context, poi *domain.SpatialPOI) error
	GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error)
	ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error)
	Update(ctx context.Context, poi *domain.SpatialPOI) error
	Delete(ctx context.Context, id uuid.UUID) error
	Search(ctx context.Context, query domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error)
}

type NavigationRepository interface {
	CreateNode(ctx context.Context, node *domain.NavNode) error
	GetNodeByID(ctx context.Context, id uuid.UUID) (*domain.NavNode, error)
	ListNodesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error)
	CreateEdge(ctx context.Context, edge *domain.NavEdge) error
	ListEdgesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error)
	DeleteNode(ctx context.Context, id uuid.UUID) error
	DeleteEdge(ctx context.Context, fromID, toID uuid.UUID) error
	NearestNode(ctx context.Context, projectID uuid.UUID, pos geo.Point3D, wheelchairOnly bool) (*domain.NavNode, error)
}

type ViewerRepository interface {
	CreateBookmark(ctx context.Context, bookmark *domain.ViewerBookmark) error
	ListBookmarksByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerBookmark, error)
	DeleteBookmark(ctx context.Context, id uuid.UUID) error
	CreateAnnotation(ctx context.Context, annotation *domain.ViewerAnnotation) error
	ListAnnotationsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerAnnotation, error)
	DeleteAnnotation(ctx context.Context, id uuid.UUID) error
}
