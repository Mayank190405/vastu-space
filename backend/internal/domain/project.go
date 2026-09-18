package domain

import (
	"time"

	"github.com/google/uuid"
)

type ProjectTypology string

const (
	TypologyCommercial    ProjectTypology = "Commercial"
	TypologyResidential   ProjectTypology = "Residential"
	TypologyIndustrial    ProjectTypology = "Industrial"
	TypologyInstitutional ProjectTypology = "Institutional"
	TypologyHealthcare    ProjectTypology = "Healthcare"
	TypologyEducation     ProjectTypology = "Education"
	TypologyHospitality   ProjectTypology = "Hospitality"
	TypologyRetail        ProjectTypology = "Retail"
	TypologyGovernment    ProjectTypology = "Government"
	TypologyOffice        ProjectTypology = "Office"
	TypologyOther         ProjectTypology = "Other"
)

type ProjectStatus string

const (
	ProjectStatusDraft           ProjectStatus = "DRAFT"
	ProjectStatusSetup           ProjectStatus = "SETUP"
	ProjectStatusReadyForCapture ProjectStatus = "READY FOR CAPTURE"
	ProjectStatusCaptureActive   ProjectStatus = "CAPTURE IN PROGRESS"
	ProjectStatusProcessing      ProjectStatus = "PROCESSING"
	ProjectStatusQualityCheck    ProjectStatus = "QUALITY VALIDATION"
	ProjectStatusReviewRequired  ProjectStatus = "REVIEW REQUIRED"
	ProjectStatusRescanRequired  ProjectStatus = "RESCAN REQUIRED"
	ProjectStatusReadyApproval   ProjectStatus = "READY FOR APPROVAL"
	ProjectStatusApproved        ProjectStatus = "APPROVED"
	ProjectStatusPublished       ProjectStatus = "PUBLISHED"
	ProjectStatusActive          ProjectStatus = "ACTIVE"
	ProjectStatusArchived        ProjectStatus = "ARCHIVED"
)

type ProjectConfig struct {
	EnableViewer              bool `json:"enable_viewer"`
	EnableSearch              bool `json:"enable_search"`
	EnableNavigation          bool `json:"enable_navigation"`
	EnablePOIPlatform         bool `json:"enable_poi_management"`
	EnableModelVersioning     bool `json:"enable_model_versioning"`
	QualityValidationRequired bool `json:"quality_validation_required"`
	RequireAdminApproval      bool `json:"require_admin_approval"`
	NotifyProcessing          bool `json:"notify_processing"`
	NotifyQualityFailure      bool `json:"notify_quality_failure"`
	NotifyRescan              bool `json:"notify_rescan"`
	NotifyPublication         bool `json:"notify_publication"`
}

type Project struct {
	ID                         uuid.UUID       `json:"id"`
	OrgID                      uuid.UUID       `json:"org_id"`
	Name                       string          `json:"name"`
	ProjectCode                *string         `json:"project_code,omitempty"`
	Slug                       string          `json:"slug"`
	Description                *string         `json:"description,omitempty"`
	Purpose                    *string         `json:"purpose,omitempty"`
	Priority                   string          `json:"priority"`
	ClientType                 *string         `json:"client_type,omitempty"`
	ClientOrgName              *string         `json:"client_org_name,omitempty"`
	ClientContactPerson        *string         `json:"client_contact_person,omitempty"`
	ClientDesignation          *string         `json:"client_designation,omitempty"`
	ClientEmail                *string         `json:"client_email,omitempty"`
	ClientPhone                *string         `json:"client_phone,omitempty"`
	ClientWebsite              *string         `json:"client_website,omitempty"`
	ClientNotes                *string         `json:"client_notes,omitempty"`
	LocationCountry            string          `json:"location_country"`
	LocationState              *string         `json:"location_state,omitempty"`
	LocationCity               *string         `json:"location_city,omitempty"`
	SitePropertyName           *string         `json:"site_property_name,omitempty"`
	LocationAddress            *string         `json:"location_address,omitempty"`
	PostalCode                 *string         `json:"postal_code,omitempty"`
	Latitude                   *float64        `json:"latitude,omitempty"`
	Longitude                  *float64        `json:"longitude,omitempty"`
	PrimaryContactName         *string         `json:"primary_contact_name,omitempty"`
	PrimaryContactEmail        *string         `json:"primary_contact_email,omitempty"`
	PrimaryContactPhone        *string         `json:"primary_contact_phone,omitempty"`
	PrimaryContactDesignation  *string         `json:"primary_contact_designation,omitempty"`
	EmergencyContactName       *string         `json:"emergency_contact_name,omitempty"`
	EmergencyContactPhone      *string         `json:"emergency_contact_phone,omitempty"`
	EmergencyContactAvail      *string         `json:"emergency_contact_availability,omitempty"`
	EmergencyContactNotes      *string         `json:"emergency_contact_notes,omitempty"`
	StartDate                  *string         `json:"start_date,omitempty"`
	ExpectedCompletionDate     *string         `json:"expected_completion_date,omitempty"`
	CaptureStartDate           *string         `json:"capture_start_date,omitempty"`
	ExpectedCaptureCompletion  *string         `json:"expected_capture_completion,omitempty"`
	ProjectAdminID             *uuid.UUID      `json:"project_admin_id,omitempty"`
	AccessPolicy               string          `json:"access_policy"`
	AssignedMembers            []string        `json:"assigned_members,omitempty"`
	AssignedOperators          []string        `json:"assigned_operators,omitempty"`
	CaptureMethod              string          `json:"capture_method"`
	CaptureInstructions        *string         `json:"capture_instructions,omitempty"`
	SiteAccessRequirements     *string         `json:"site_access_requirements,omitempty"`
	RestrictedAreas            *string         `json:"restricted_areas,omitempty"`
	SpecialCaptureNotes        *string         `json:"special_capture_notes,omitempty"`
	ProjectConfig              *ProjectConfig  `json:"project_config,omitempty"`
	Typology                   ProjectTypology `json:"typology"`
	TotalAreaSqft              float64         `json:"total_area_sqft"`
	TotalAreaSqm               float64         `json:"total_area_sqm"`
	CeilingHeightMeters        float64         `json:"ceiling_height_meters"`
	TotalFloorsCount           int             `json:"total_floors_count"`
	TotalHallsCount            int             `json:"total_halls_count"`
	TotalRoomsCount            int             `json:"total_rooms_count"`
	TotalCorridorsCount        int             `json:"total_corridors_count"`
	PrecisionGateCm            float64         `json:"precision_gate_cm"`
	Status                     ProjectStatus   `json:"status"`
	CreatedBy                  *uuid.UUID      `json:"created_by,omitempty"`
	CreatedAt                  time.Time       `json:"created_at"`
	UpdatedAt                  time.Time       `json:"updated_at"`
	DeletedAt                  *time.Time      `json:"deleted_at,omitempty"`
	DaysRemaining              *int            `json:"days_remaining,omitempty"`

	// Escalation fields
	CoverImageID  *string         `json:"cover_image_id,omitempty"`
	CoverImageURL *string         `json:"cover_image_url,omitempty"`
	ContactName   string          `json:"contact_name,omitempty"`
	ContactEmail  string          `json:"contact_email,omitempty"`
	ContactPhone  string          `json:"contact_phone,omitempty"`
	ProjectType   string          `json:"project_type,omitempty"`
	CustomType    *string         `json:"custom_type,omitempty"`

	Address *ProjectAddress `json:"address,omitempty"`
	Floors  []*ProjectFloor `json:"floors,omitempty"`
	Team    []*ProjectMember `json:"team,omitempty"`

	Structures []*ProjectStructure `json:"structures,omitempty"`
	Updates    []*ProjectUpdate    `json:"updates,omitempty"`
}

type ProjectStructure struct {
	ID                  uuid.UUID `json:"id"`
	ProjectID           uuid.UUID `json:"project_id"`
	Name                string    `json:"name"`
	BuildingCode        *string   `json:"building_code,omitempty"`
	StructureType       string    `json:"structure_type"`
	FloorsCount         int       `json:"floors_count"`
	HallsCount          int       `json:"halls_count"`
	RoomsCount          int       `json:"rooms_count"`
	CorridorsCount      int       `json:"corridors_count"`
	AreaSqm             float64   `json:"area_sqm"`
	CeilingHeightMeters float64   `json:"ceiling_height_meters"`
	BuildingAddress     *string   `json:"building_address,omitempty"`
	BuildingDescription *string   `json:"building_description,omitempty"`
	AccessNotes         *string   `json:"access_notes,omitempty"`
	SiteRestrictions    *string   `json:"site_restrictions,omitempty"`
	CaptureInstructions *string   `json:"capture_instructions,omitempty"`
	WorkingHours        *string   `json:"working_hours,omitempty"`
	Status              string    `json:"status"`
	CreatedAt           time.Time `json:"created_at"`
	UpdatedAt           time.Time `json:"updated_at"`

	Levels []*SpatialLevel `json:"levels,omitempty"`
}

type SpatialLevel struct {
	ID                  uuid.UUID `json:"id"`
	StructureID         uuid.UUID `json:"structure_id"`
	LevelNumber         int       `json:"level_number"`
	LevelName           string    `json:"level_name"`
	ElevationMeters     float64   `json:"elevation_meters"`
	FloorDescription    *string   `json:"floor_description,omitempty"`
	CaptureStatus       string    `json:"capture_status"`
	ProcessingStatus    string    `json:"processing_status"`
	QualityStatus       string    `json:"quality_status"`
	CurrentModelVersion *string   `json:"current_model_version,omitempty"`
	HallsCount          int       `json:"halls_count"`
	RoomsCount          int       `json:"rooms_count"`
	CorridorsCount      int       `json:"corridors_count"`
	AreaSqm             float64   `json:"area_sqm"`
	CreatedAt           time.Time `json:"created_at"`
	UpdatedAt           time.Time `json:"updated_at"`

	Sections []*SpatialSection `json:"sections,omitempty"`
}

type SpatialSection struct {
	ID          uuid.UUID              `json:"id"`
	LevelID     uuid.UUID              `json:"level_id"`
	Name        string                 `json:"name"`
	SectionType string                 `json:"section_type"`
	AreaSqm     float64                `json:"area_sqm"`
	BoundingBox map[string]interface{} `json:"bounding_box,omitempty"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
}

type ProjectUpdate struct {
	ID          uuid.UUID  `json:"id"`
	ProjectID   uuid.UUID  `json:"project_id"`
	AuthorID    *uuid.UUID `json:"author_id,omitempty"`
	UpdateType  string     `json:"update_type"`
	Title       string     `json:"title"`
	Description string     `json:"description"`
	Priority    string     `json:"priority"`
	BuildingID  *uuid.UUID `json:"building_id,omitempty"`
	FloorID     *uuid.UUID `json:"floor_id,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
}

type FloorInput struct {
	LevelName        string  `json:"level_name"`
	LevelNumber      int     `json:"level_number"`
	FloorDescription *string `json:"floor_description,omitempty"`
}

type BuildingInput struct {
	Name                string       `json:"name"`
	BuildingCode        *string      `json:"building_code,omitempty"`
	BuildingType        string       `json:"building_type"`
	FloorsCount         int          `json:"floors_count"`
	BuildingAddress     *string      `json:"building_address,omitempty"`
	BuildingDescription *string      `json:"building_description,omitempty"`
	AccessNotes         *string      `json:"access_notes,omitempty"`
	SiteRestrictions    *string      `json:"site_restrictions,omitempty"`
	CaptureInstructions *string      `json:"capture_instructions,omitempty"`
	WorkingHours        *string      `json:"working_hours,omitempty"`
	Floors              []FloorInput `json:"floors,omitempty"`
}

type CreateProjectInput struct {
	Name                      string          `json:"name"`
	ProjectCode               *string         `json:"project_code,omitempty"`
	Typology                  ProjectTypology `json:"typology"`
	Description               *string         `json:"description,omitempty"`
	Purpose                   *string         `json:"purpose,omitempty"`
	Priority                  *string         `json:"priority,omitempty"`
	ClientType                *string         `json:"client_type,omitempty"`
	ClientOrgName             *string         `json:"client_org_name,omitempty"`
	ClientContactPerson       *string         `json:"client_contact_person,omitempty"`
	ClientDesignation         *string         `json:"client_designation,omitempty"`
	ClientEmail               *string         `json:"client_email,omitempty"`
	ClientPhone               *string         `json:"client_phone,omitempty"`
	ClientWebsite             *string         `json:"client_website,omitempty"`
	ClientNotes               *string         `json:"client_notes,omitempty"`
	LocationCountry           string          `json:"location_country"`
	LocationState             *string         `json:"location_state,omitempty"`
	LocationCity              *string         `json:"location_city,omitempty"`
	SitePropertyName          *string         `json:"site_property_name,omitempty"`
	LocationAddress           *string         `json:"location_address,omitempty"`
	PostalCode                *string         `json:"postal_code,omitempty"`
	Latitude                  *float64        `json:"latitude,omitempty"`
	Longitude                 *float64        `json:"longitude,omitempty"`
	PrimaryContactName        *string         `json:"primary_contact_name,omitempty"`
	PrimaryContactEmail       *string         `json:"primary_contact_email,omitempty"`
	PrimaryContactPhone       *string         `json:"primary_contact_phone,omitempty"`
	PrimaryContactDesignation *string         `json:"primary_contact_designation,omitempty"`
	EmergencyContactName      *string         `json:"emergency_contact_name,omitempty"`
	EmergencyContactPhone     *string         `json:"emergency_contact_phone,omitempty"`
	EmergencyContactAvail     *string         `json:"emergency_contact_availability,omitempty"`
	EmergencyContactNotes     *string         `json:"emergency_contact_notes,omitempty"`
	StartDate                 *string         `json:"start_date,omitempty"`
	ExpectedCompletionDate    *string         `json:"expected_completion_date,omitempty"`
	CaptureStartDate          *string         `json:"capture_start_date,omitempty"`
	ExpectedCaptureCompletion *string         `json:"expected_capture_completion,omitempty"`
	ProjectAdminID            *uuid.UUID      `json:"project_admin_id,omitempty"`
	AccessPolicy              *string         `json:"access_policy,omitempty"`
	AssignedMembers           []string        `json:"assigned_members,omitempty"`
	AssignedOperators         []string        `json:"assigned_operators,omitempty"`
	CaptureMethod             *string         `json:"capture_method,omitempty"`
	CaptureInstructions       *string         `json:"capture_instructions,omitempty"`
	SiteAccessRequirements    *string         `json:"site_access_requirements,omitempty"`
	RestrictedAreas           *string         `json:"restricted_areas,omitempty"`
	SpecialCaptureNotes       *string         `json:"special_capture_notes,omitempty"`
	ProjectConfig             *ProjectConfig  `json:"project_config,omitempty"`
	Status                    *ProjectStatus  `json:"status,omitempty"`

	Buildings []BuildingInput `json:"buildings,omitempty"`
}

type UpdateProjectInput struct {
	Name                      *string          `json:"name,omitempty"`
	ProjectCode               *string          `json:"project_code,omitempty"`
	Typology                  *ProjectTypology `json:"typology,omitempty"`
	Description               *string          `json:"description,omitempty"`
	Purpose                   *string          `json:"purpose,omitempty"`
	Priority                  *string          `json:"priority,omitempty"`
	ClientType                *string          `json:"client_type,omitempty"`
	ClientOrgName             *string          `json:"client_org_name,omitempty"`
	ClientContactPerson       *string          `json:"client_contact_person,omitempty"`
	ClientDesignation         *string          `json:"client_designation,omitempty"`
	ClientEmail               *string          `json:"client_email,omitempty"`
	ClientPhone               *string          `json:"client_phone,omitempty"`
	ClientWebsite             *string          `json:"client_website,omitempty"`
	ClientNotes               *string          `json:"client_notes,omitempty"`
	LocationCountry           *string          `json:"location_country,omitempty"`
	LocationState             *string          `json:"location_state,omitempty"`
	LocationCity              *string          `json:"location_city,omitempty"`
	SitePropertyName          *string          `json:"site_property_name,omitempty"`
	LocationAddress           *string          `json:"location_address,omitempty"`
	PostalCode                *string          `json:"postal_code,omitempty"`
	Latitude                  *float64         `json:"latitude,omitempty"`
	Longitude                 *float64         `json:"longitude,omitempty"`
	PrimaryContactName        *string          `json:"primary_contact_name,omitempty"`
	PrimaryContactEmail       *string          `json:"primary_contact_email,omitempty"`
	PrimaryContactPhone       *string          `json:"primary_contact_phone,omitempty"`
	PrimaryContactDesignation *string          `json:"primary_contact_designation,omitempty"`
	EmergencyContactName      *string          `json:"emergency_contact_name,omitempty"`
	EmergencyContactPhone     *string          `json:"emergency_contact_phone,omitempty"`
	EmergencyContactAvail     *string          `json:"emergency_contact_availability,omitempty"`
	EmergencyContactNotes     *string          `json:"emergency_contact_notes,omitempty"`
	StartDate                 *string          `json:"start_date,omitempty"`
	ExpectedCompletionDate    *string          `json:"expected_completion_date,omitempty"`
	CaptureStartDate          *string          `json:"capture_start_date,omitempty"`
	ExpectedCaptureCompletion *string          `json:"expected_capture_completion,omitempty"`
	ProjectAdminID            *uuid.UUID       `json:"project_admin_id,omitempty"`
	AccessPolicy              *string          `json:"access_policy,omitempty"`
	AssignedMembers           []string         `json:"assigned_members,omitempty"`
	AssignedOperators         []string         `json:"assigned_operators,omitempty"`
	CaptureMethod             *string          `json:"capture_method,omitempty"`
	CaptureInstructions       *string          `json:"capture_instructions,omitempty"`
	SiteAccessRequirements    *string          `json:"site_access_requirements,omitempty"`
	RestrictedAreas           *string          `json:"restricted_areas,omitempty"`
	SpecialCaptureNotes       *string          `json:"special_capture_notes,omitempty"`
	ProjectConfig             *ProjectConfig   `json:"project_config,omitempty"`
	Status                    *ProjectStatus   `json:"status,omitempty"`
	ActorName                 *string          `json:"actor_name,omitempty"`
	ActorRole                 *string          `json:"actor_role,omitempty"`

	Buildings []BuildingInput `json:"buildings,omitempty"`
}

