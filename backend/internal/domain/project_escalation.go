package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// ProjectAddress represents the verified structured address for a project
type ProjectAddress struct {
	ID           uuid.UUID `json:"id"`
	ProjectID    uuid.UUID `json:"project_id"`
	AddressLine1 string    `json:"address_line_1"`
	AddressLine2 *string   `json:"address_line_2,omitempty"`
	Area         *string   `json:"area,omitempty"`
	City         string    `json:"city"`
	State        string    `json:"state"`
	Pincode      string    `json:"pincode"`
	Country      string    `json:"country"`
	Latitude     *float64  `json:"latitude,omitempty"`
	Longitude    *float64  `json:"longitude,omitempty"`
	PlaceID      *string   `json:"place_id,omitempty"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type CreateAddressInput struct {
	AddressLine1 string   `json:"address_line_1"`
	AddressLine2 *string  `json:"address_line_2,omitempty"`
	Area         *string  `json:"area,omitempty"`
	City         string   `json:"city"`
	State        string   `json:"state"`
	Pincode      string   `json:"pincode"`
	Country      string   `json:"country"`
	Latitude     *float64 `json:"latitude,omitempty"`
	Longitude    *float64 `json:"longitude,omitempty"`
	PlaceID      *string  `json:"place_id,omitempty"`
}

// ProjectFloor represents an independently managed level/floor within a project structure
type ProjectFloor struct {
	ID          uuid.UUID  `json:"id"`
	ProjectID   uuid.UUID  `json:"project_id"`
	Name        string     `json:"name"`
	FloorNumber int        `json:"floor_number"`
	FloorType   string     `json:"floor_type"`
	AreaValue   float64    `json:"area_value"`
	AreaUnit    string     `json:"area_unit"` // SQFT
	HeightValue float64    `json:"height_value"`
	HeightUnit  string     `json:"height_unit"` // FT
	Sequence    int        `json:"sequence"`
	Description *string    `json:"description,omitempty"`
	FloorPlan   *FloorPlan `json:"floor_plan,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
}

type CreateFloorInput struct {
	Name        string   `json:"name"`
	FloorNumber int      `json:"floor_number"`
	FloorType   string   `json:"floor_type"`
	AreaValue   float64  `json:"area_value"`
	AreaUnit    string   `json:"area_unit"`
	HeightValue float64  `json:"height_value"`
	HeightUnit  string   `json:"height_unit"`
	Sequence    int      `json:"sequence"`
	Description *string  `json:"description,omitempty"`
}

type UpdateFloorInput struct {
	Name        *string  `json:"name,omitempty"`
	FloorNumber *int     `json:"floor_number,omitempty"`
	FloorType   *string  `json:"floor_type,omitempty"`
	AreaValue   *float64 `json:"area_value,omitempty"`
	AreaUnit    *string  `json:"area_unit,omitempty"`
	HeightValue *float64 `json:"height_value,omitempty"`
	HeightUnit  *string  `json:"height_unit,omitempty"`
	Sequence    *int     `json:"sequence,omitempty"`
	Description *string  `json:"description,omitempty"`
}

// FloorPlan represents an uploaded architectural sheet or interactive vector drawing
type FloorPlan struct {
	ID               uuid.UUID       `json:"id"`
	FloorID          uuid.UUID       `json:"floor_id"`
	PlanType         string          `json:"plan_type"` // UPLOADED or DRAWN
	FileID           *string         `json:"file_id,omitempty"`
	FileURL          *string         `json:"file_url,omitempty"`
	OriginalFileName *string         `json:"original_file_name,omitempty"`
	FileSizeBytes    int64           `json:"file_size_bytes"`
	MimeType         *string         `json:"mime_type,omitempty"`
	CanvasWidth      float64         `json:"canvas_width"`
	CanvasHeight     float64         `json:"canvas_height"`
	ScaleRatio       float64         `json:"scale_ratio"`
	DrawingData      json.RawMessage `json:"drawing_data,omitempty"`
	PreviewFileID    *string         `json:"preview_file_id,omitempty"`
	PreviewURL       *string         `json:"preview_url,omitempty"`
	CreatedAt        time.Time       `json:"created_at"`
	UpdatedAt        time.Time       `json:"updated_at"`
}

type DrawFloorPlanInput struct {
	CanvasWidth  float64         `json:"canvas_width"`
	CanvasHeight float64         `json:"canvas_height"`
	ScaleRatio   float64         `json:"scale_ratio"`
	DrawingData  json.RawMessage `json:"drawing_data"`
	PreviewBase64 *string        `json:"preview_base64,omitempty"`
}

// ProjectMember represents an organization user assigned a project-specific role
type ProjectMember struct {
	ID          uuid.UUID       `json:"id"`
	ProjectID   uuid.UUID       `json:"project_id"`
	UserID      uuid.UUID       `json:"user_id"`
	ProjectRole string          `json:"project_role"`
	Permissions json.RawMessage `json:"permissions"`
	Status      string          `json:"status"`
	AssignedBy  *uuid.UUID      `json:"assigned_by,omitempty"`
	AssignedAt  time.Time       `json:"assigned_at"`
	User        *User           `json:"user,omitempty"`
}

type AssignProjectMemberInput struct {
	UserID      uuid.UUID `json:"user_id"`
	ProjectRole string    `json:"project_role"`
}

// ProjectCreationFullInput represents the unified payload for multi-step creation or draft save
type ProjectCreationFullInput struct {
	Name         string                    `json:"name"`
	CoverImageID *string                   `json:"cover_image_id,omitempty"`
	CoverImageURL *string                  `json:"cover_image_url,omitempty"`
	ContactName  string                    `json:"contact_name"`
	ContactEmail string                    `json:"contact_email"`
	ContactPhone string                    `json:"contact_phone"`
	ProjectType  string                    `json:"project_type"`
	CustomType   *string                   `json:"custom_type,omitempty"`
	Description  *string                   `json:"description,omitempty"`
	Status       *string                   `json:"status,omitempty"` // DRAFT or ACTIVE
	Address      CreateAddressInput        `json:"address"`
	Floors       []CreateFloorInput        `json:"floors,omitempty"`
	Members      []AssignProjectMemberInput `json:"members,omitempty"`
}

// ProjectFull represents the complete project aggregation for dashboard and management
type ProjectFull = Project

// ProjectTypeDefinition holds metadata for supported architectural topologies
type ProjectTypeDefinition struct {
	Key             string   `json:"key"`
	Name            string   `json:"name"`
	Category        string   `json:"category"`
	Description     string   `json:"description"`
	MultiFloor      bool     `json:"multi_floor"`
	DefaultFloorTypes []string `json:"default_floor_types"`
}

var SupportedProjectTypes = []ProjectTypeDefinition{
	{Key: "Building", Name: "Building", Category: "General", Description: "Multi-level commercial, residential, or mixed-use building", MultiFloor: true, DefaultFloorTypes: []string{"Basement", "Ground Floor", "Podium", "Lobby", "Typical Floor", "Terrace"}},
	{Key: "Residential Building", Name: "Residential Building", Category: "Residential", Description: "Apartment complex, residential tower, or condominium", MultiFloor: true, DefaultFloorTypes: []string{"Basement Parking", "Ground Floor", "Podium", "Residential Floor", "Terrace", "Service Floor"}},
	{Key: "Commercial Building", Name: "Commercial Building", Category: "Commercial", Description: "Multi-tenant office or commercial complex", MultiFloor: true, DefaultFloorTypes: []string{"Basement Parking", "Ground Lobby", "Office Floor", "Service Floor", "Terrace"}},
	{Key: "Office", Name: "Office", Category: "Commercial", Description: "Corporate office building, tech park, or single enterprise facility", MultiFloor: true, DefaultFloorTypes: []string{"Ground Floor", "Lobby", "Office Floor", "Cafeteria", "Meeting Suites"}},
	{Key: "Mall", Name: "Mall", Category: "Retail", Description: "Retail shopping mall with multi-level stores and food courts", MultiFloor: true, DefaultFloorTypes: []string{"Basement Parking", "Ground Floor Retail", "Retail Floor", "Food Court", "Multiplex Floor"}},
	{Key: "Shopping Complex", Name: "Shopping Complex", Category: "Retail", Description: "Multi-store shopping center or plaza", MultiFloor: true, DefaultFloorTypes: []string{"Basement", "Ground Floor", "First Floor", "Retail Deck"}},
	{Key: "Hall", Name: "Hall", Category: "Assembly", Description: "Auditorium, town hall, or multi-purpose gathering venue", MultiFloor: false, DefaultFloorTypes: []string{"Main Hall", "Mezzanine Seating", "Backstage", "Foyer"}},
	{Key: "Banquet Hall", Name: "Banquet Hall", Category: "Hospitality", Description: "Celebration and banquet venue with dining and stage areas", MultiFloor: false, DefaultFloorTypes: []string{"Grand Ballroom", "Dining Hall", "Pre-function Area", "Lounge"}},
	{Key: "Convention Centre", Name: "Convention Centre", Category: "Assembly", Description: "Large-scale exhibition and convention hall", MultiFloor: true, DefaultFloorTypes: []string{"Plenary Hall", "Exhibition Floor", "Concourse", "Meeting Rooms"}},
	{Key: "Hotel", Name: "Hotel", Category: "Hospitality", Description: "Hospitality property with guest rooms, restaurants, and amenities", MultiFloor: true, DefaultFloorTypes: []string{"Basement Service", "Lobby & Reception", "Amenities Floor", "Guest Rooms", "Rooftop"}},
	{Key: "Hospital", Name: "Hospital", Category: "Healthcare", Description: "Medical hospital or multi-specialty clinical facility", MultiFloor: true, DefaultFloorTypes: []string{"Emergency / Triage", "OPD Floor", "Operation Theatres", "Inpatient Wards", "ICU Floor", "Diagnostics"}},
	{Key: "School", Name: "School", Category: "Education", Description: "Primary or secondary educational campus structure", MultiFloor: true, DefaultFloorTypes: []string{"Ground Floor", "Classrooms", "Laboratories", "Library", "Auditorium"}},
	{Key: "College", Name: "College", Category: "Education", Description: "University academic block or higher education faculty", MultiFloor: true, DefaultFloorTypes: []string{"Ground Floor", "Lecture Theatres", "Labs", "Faculty Offices", "Seminar Hall"}},
	{Key: "Warehouse", Name: "Warehouse", Category: "Industrial", Description: "Logistics, storage, and inventory distribution warehouse", MultiFloor: false, DefaultFloorTypes: []string{"Storage Bay / Ground", "Mezzanine Office", "Loading Dock"}},
	{Key: "Factory", Name: "Factory", Category: "Industrial", Description: "Industrial manufacturing and assembly plant", MultiFloor: false, DefaultFloorTypes: []string{"Shop Floor", "Assembly Line", "Testing Bay", "Plant Administration"}},
	{Key: "Industrial Facility", Name: "Industrial Facility", Category: "Industrial", Description: "Heavy industrial processing or utility facility", MultiFloor: false, DefaultFloorTypes: []string{"Main Plant", "Control Room", "Maintenance Deck"}},
	{Key: "Campus", Name: "Campus", Category: "Institutional", Description: "Multi-building institutional, technology, or corporate campus", MultiFloor: true, DefaultFloorTypes: []string{"Main Block", "Academic Wing", "Admin Center", "Recreation Center"}},
	{Key: "Showroom", Name: "Showroom", Category: "Retail", Description: "Automotive, equipment, or furniture display showroom", MultiFloor: false, DefaultFloorTypes: []string{"Display Floor", "Customer Lounge", "Service Bay"}},
	{Key: "Retail Store", Name: "Retail Store", Category: "Retail", Description: "Supermarket, department store, or stand-alone boutique", MultiFloor: false, DefaultFloorTypes: []string{"Sales Floor", "Stock Room", "Checkout Area"}},
	{Key: "Restaurant", Name: "Restaurant", Category: "Hospitality", Description: "Dining restaurant, kitchen, and bar lounge", MultiFloor: false, DefaultFloorTypes: []string{"Dining Area", "Kitchen", "Bar Lounge", "Outdoor Patio"}},
	{Key: "Multiplex", Name: "Multiplex", Category: "Entertainment", Description: "Cinema multiplex with movie halls and concessions", MultiFloor: true, DefaultFloorTypes: []string{"Concourse & Tickets", "Audi 1-4 Level", "Projection Booths"}},
	{Key: "Parking Structure", Name: "Parking Structure", Category: "Infrastructure", Description: "Multi-story vehicle parking garage", MultiFloor: true, DefaultFloorTypes: []string{"Basement P1", "Ground Level", "Level P1", "Level P2", "Rooftop Deck"}},
	{Key: "Government Building", Name: "Government Building", Category: "Institutional", Description: "Municipal, civic, or administrative government office", MultiFloor: true, DefaultFloorTypes: []string{"Public Concierge", "Administrative Floor", "Council Chambers", "Records Floor"}},
	{Key: "Other", Name: "Other", Category: "Custom", Description: "Custom architectural structure with bespoke configuration", MultiFloor: true, DefaultFloorTypes: []string{"Ground Floor", "Level 1"}},
}
