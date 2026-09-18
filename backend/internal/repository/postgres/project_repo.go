package postgres

import (
	"context"
	"encoding/json"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type ProjectRepo struct {
	pool *pgxpool.Pool
}

func NewProjectRepo(pool *pgxpool.Pool) repository.ProjectRepository {
	return &ProjectRepo{pool: pool}
}

func (r *ProjectRepo) Create(ctx context.Context, p *domain.Project) error {
	assignedMembersJSON, _ := json.Marshal(p.AssignedMembers)
	assignedOperatorsJSON, _ := json.Marshal(p.AssignedOperators)
	configJSON, _ := json.Marshal(p.ProjectConfig)

	query := `
		INSERT INTO projects (
			id, org_id, name, project_code, slug, description, purpose, priority,
			client_type, client_org_name, client_contact_person, client_designation,
			client_email, client_phone, client_website, client_notes,
			location_country, location_state, location_city, site_property_name, location_address, postal_code,
			latitude, longitude,
			primary_contact_name, primary_contact_email, primary_contact_phone, primary_contact_designation,
			emergency_contact_name, emergency_contact_phone, emergency_contact_availability, emergency_contact_notes,
			start_date, expected_completion_date, capture_start_date, expected_capture_completion,
			project_admin_id, access_policy, assigned_members, assigned_operators,
			capture_method, capture_instructions, site_access_requirements, restricted_areas, special_capture_notes,
			project_config,
			typology, total_area_sqft, total_area_sqm, ceiling_height_meters,
			total_floors_count, total_halls_count, total_rooms_count, total_corridors_count,
			precision_gate_cm, status, created_by, created_at, updated_at,
			cover_image_id, cover_image_url, contact_name, contact_email, contact_phone, project_type, custom_type
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8,
			$9, $10, $11, $12,
			$13, $14, $15, $16,
			$17, $18, $19, $20, $21, $22,
			$23, $24,
			$25, $26, $27, $28,
			$29, $30, $31, $32,
			$33, $34, $35, $36,
			$37, $38, $39, $40,
			$41, $42, $43, $44, $45,
			$46,
			$47, $48, $49, $50,
			$51, $52, $53, $54,
			$55, $56, $57, $58, $59,
			$60, $61, $62, $63, $64, $65, $66
		)
	`
	if p.ProjectType == "" {
		p.ProjectType = "Building"
	}
	_, err := r.pool.Exec(ctx, query,
		p.ID, p.OrgID, p.Name, p.ProjectCode, p.Slug, p.Description, p.Purpose, p.Priority,
		p.ClientType, p.ClientOrgName, p.ClientContactPerson, p.ClientDesignation,
		p.ClientEmail, p.ClientPhone, p.ClientWebsite, p.ClientNotes,
		p.LocationCountry, p.LocationState, p.LocationCity, p.SitePropertyName, p.LocationAddress, p.PostalCode,
		p.Latitude, p.Longitude,
		p.PrimaryContactName, p.PrimaryContactEmail, p.PrimaryContactPhone, p.PrimaryContactDesignation,
		p.EmergencyContactName, p.EmergencyContactPhone, p.EmergencyContactAvail, p.EmergencyContactNotes,
		p.StartDate, p.ExpectedCompletionDate, p.CaptureStartDate, p.ExpectedCaptureCompletion,
		p.ProjectAdminID, p.AccessPolicy, assignedMembersJSON, assignedOperatorsJSON,
		p.CaptureMethod, p.CaptureInstructions, p.SiteAccessRequirements, p.RestrictedAreas, p.SpecialCaptureNotes,
		configJSON,
		p.Typology, p.TotalAreaSqft, p.TotalAreaSqm, p.CeilingHeightMeters,
		p.TotalFloorsCount, p.TotalHallsCount, p.TotalRoomsCount, p.TotalCorridorsCount,
		p.PrecisionGateCm, p.Status, p.CreatedBy, p.CreatedAt, p.UpdatedAt,
		p.CoverImageID, p.CoverImageURL, p.ContactName, p.ContactEmail, p.ContactPhone, p.ProjectType, p.CustomType,
	)
	return err
}

func (r *ProjectRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.Project, error) {
	query := `
		SELECT 
			id, org_id, name, project_code, slug, description, purpose, priority,
			client_type, client_org_name, client_contact_person, client_designation,
			client_email, client_phone, client_website, client_notes,
			location_country, location_state, location_city, site_property_name, location_address, postal_code,
			latitude, longitude,
			primary_contact_name, primary_contact_email, primary_contact_phone, primary_contact_designation,
			emergency_contact_name, emergency_contact_phone, emergency_contact_availability, emergency_contact_notes,
			start_date, expected_completion_date, capture_start_date, expected_capture_completion,
			project_admin_id, access_policy, assigned_members, assigned_operators,
			capture_method, capture_instructions, site_access_requirements, restricted_areas, special_capture_notes,
			project_config,
			typology, total_area_sqft, total_area_sqm, ceiling_height_meters,
			total_floors_count, total_halls_count, total_rooms_count, total_corridors_count,
			precision_gate_cm, status, created_by, created_at, updated_at, deleted_at,
			cover_image_id, cover_image_url, contact_name, contact_email, contact_phone, COALESCE(project_type, 'Building'), custom_type
		FROM projects
		WHERE id = $1
	`
	row := r.pool.QueryRow(ctx, query, id)

	var p domain.Project
	var membersRaw, operatorsRaw, configRaw []byte
	err := row.Scan(
		&p.ID, &p.OrgID, &p.Name, &p.ProjectCode, &p.Slug, &p.Description, &p.Purpose, &p.Priority,
		&p.ClientType, &p.ClientOrgName, &p.ClientContactPerson, &p.ClientDesignation,
		&p.ClientEmail, &p.ClientPhone, &p.ClientWebsite, &p.ClientNotes,
		&p.LocationCountry, &p.LocationState, &p.LocationCity, &p.SitePropertyName, &p.LocationAddress, &p.PostalCode,
		&p.Latitude, &p.Longitude,
		&p.PrimaryContactName, &p.PrimaryContactEmail, &p.PrimaryContactPhone, &p.PrimaryContactDesignation,
		&p.EmergencyContactName, &p.EmergencyContactPhone, &p.EmergencyContactAvail, &p.EmergencyContactNotes,
		&p.StartDate, &p.ExpectedCompletionDate, &p.CaptureStartDate, &p.ExpectedCaptureCompletion,
		&p.ProjectAdminID, &p.AccessPolicy, &membersRaw, &operatorsRaw,
		&p.CaptureMethod, &p.CaptureInstructions, &p.SiteAccessRequirements, &p.RestrictedAreas, &p.SpecialCaptureNotes,
		&configRaw,
		&p.Typology, &p.TotalAreaSqft, &p.TotalAreaSqm, &p.CeilingHeightMeters,
		&p.TotalFloorsCount, &p.TotalHallsCount, &p.TotalRoomsCount, &p.TotalCorridorsCount,
		&p.PrecisionGateCm, &p.Status, &p.CreatedBy, &p.CreatedAt, &p.UpdatedAt, &p.DeletedAt,
		&p.CoverImageID, &p.CoverImageURL, &p.ContactName, &p.ContactEmail, &p.ContactPhone, &p.ProjectType, &p.CustomType,
	)
	if err != nil {
		return nil, err
	}

	_ = json.Unmarshal(membersRaw, &p.AssignedMembers)
	_ = json.Unmarshal(operatorsRaw, &p.AssignedOperators)
	_ = json.Unmarshal(configRaw, &p.ProjectConfig)

	structures, _ := r.ListStructuresByProject(ctx, p.ID)
	p.Structures = structures

	updates, _ := r.ListProjectUpdates(ctx, p.ID)
	p.Updates = updates

	p.Address, _ = r.GetAddressByProjectID(ctx, p.ID)
	p.Floors, _ = r.ListFloorsByProjectID(ctx, p.ID)
	p.Team, _ = r.ListProjectMembers(ctx, p.ID)

	return &p, nil
}

func (r *ProjectRepo) ListByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error) {
	query := `
		SELECT 
			id, org_id, name, project_code, slug, description, purpose, priority,
			client_type, client_org_name, client_contact_person, client_designation,
			client_email, client_phone, client_website, client_notes,
			location_country, location_state, location_city, site_property_name, location_address, postal_code,
			latitude, longitude,
			primary_contact_name, primary_contact_email, primary_contact_phone, primary_contact_designation,
			emergency_contact_name, emergency_contact_phone, emergency_contact_availability, emergency_contact_notes,
			start_date, expected_completion_date, capture_start_date, expected_capture_completion,
			project_admin_id, access_policy, assigned_members, assigned_operators,
			capture_method, capture_instructions, site_access_requirements, restricted_areas, special_capture_notes,
			project_config,
			typology, total_area_sqft, total_area_sqm, ceiling_height_meters,
			total_floors_count, total_halls_count, total_rooms_count, total_corridors_count,
			precision_gate_cm, status, created_by, created_at, updated_at, deleted_at,
			cover_image_id, cover_image_url, contact_name, contact_email, contact_phone, COALESCE(project_type, 'Building'), custom_type
		FROM projects
		WHERE org_id = $1 AND deleted_at IS NULL
		ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var projects []*domain.Project
	for rows.Next() {
		var p domain.Project
		var membersRaw, operatorsRaw, configRaw []byte
		err := rows.Scan(
			&p.ID, &p.OrgID, &p.Name, &p.ProjectCode, &p.Slug, &p.Description, &p.Purpose, &p.Priority,
			&p.ClientType, &p.ClientOrgName, &p.ClientContactPerson, &p.ClientDesignation,
			&p.ClientEmail, &p.ClientPhone, &p.ClientWebsite, &p.ClientNotes,
			&p.LocationCountry, &p.LocationState, &p.LocationCity, &p.SitePropertyName, &p.LocationAddress, &p.PostalCode,
			&p.Latitude, &p.Longitude,
			&p.PrimaryContactName, &p.PrimaryContactEmail, &p.PrimaryContactPhone, &p.PrimaryContactDesignation,
			&p.EmergencyContactName, &p.EmergencyContactPhone, &p.EmergencyContactAvail, &p.EmergencyContactNotes,
			&p.StartDate, &p.ExpectedCompletionDate, &p.CaptureStartDate, &p.ExpectedCaptureCompletion,
			&p.ProjectAdminID, &p.AccessPolicy, &membersRaw, &operatorsRaw,
			&p.CaptureMethod, &p.CaptureInstructions, &p.SiteAccessRequirements, &p.RestrictedAreas, &p.SpecialCaptureNotes,
			&configRaw,
			&p.Typology, &p.TotalAreaSqft, &p.TotalAreaSqm, &p.CeilingHeightMeters,
			&p.TotalFloorsCount, &p.TotalHallsCount, &p.TotalRoomsCount, &p.TotalCorridorsCount,
			&p.PrecisionGateCm, &p.Status, &p.CreatedBy, &p.CreatedAt, &p.UpdatedAt, &p.DeletedAt,
			&p.CoverImageID, &p.CoverImageURL, &p.ContactName, &p.ContactEmail, &p.ContactPhone, &p.ProjectType, &p.CustomType,
		)
		if err != nil {
			continue
		}
		_ = json.Unmarshal(membersRaw, &p.AssignedMembers)
		_ = json.Unmarshal(operatorsRaw, &p.AssignedOperators)
		_ = json.Unmarshal(configRaw, &p.ProjectConfig)
		structures, _ := r.ListStructuresByProject(ctx, p.ID)
		p.Structures = structures

		p.Address, _ = r.GetAddressByProjectID(ctx, p.ID)
		p.Floors, _ = r.ListFloorsByProjectID(ctx, p.ID)
		if len(p.Floors) > 0 && p.TotalFloorsCount == 0 {
			p.TotalFloorsCount = len(p.Floors)
		}

		projects = append(projects, &p)
	}

	return projects, nil
}

func (r *ProjectRepo) ListTrashByOrg(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error) {
	query := `
		SELECT 
			id, org_id, name, project_code, slug, description, purpose, priority,
			client_type, client_org_name, client_contact_person, client_designation,
			client_email, client_phone, client_website, client_notes,
			location_country, location_state, location_city, site_property_name, location_address, postal_code,
			latitude, longitude,
			primary_contact_name, primary_contact_email, primary_contact_phone, primary_contact_designation,
			emergency_contact_name, emergency_contact_phone, emergency_contact_availability, emergency_contact_notes,
			start_date, expected_completion_date, capture_start_date, expected_capture_completion,
			project_admin_id, access_policy, assigned_members, assigned_operators,
			capture_method, capture_instructions, site_access_requirements, restricted_areas, special_capture_notes,
			project_config,
			typology, total_area_sqft, total_area_sqm, ceiling_height_meters,
			total_floors_count, total_halls_count, total_rooms_count, total_corridors_count,
			precision_gate_cm, status, created_by, created_at, updated_at, deleted_at,
			EXTRACT(DAY FROM (deleted_at + INTERVAL '30 days' - NOW()))::INT AS days_remaining
		FROM projects
		WHERE org_id = $1 AND deleted_at IS NOT NULL AND deleted_at > NOW() - INTERVAL '30 days'
		ORDER BY deleted_at DESC
	`
	rows, err := r.pool.Query(ctx, query, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var projects []*domain.Project
	for rows.Next() {
		var p domain.Project
		var membersRaw, operatorsRaw, configRaw []byte
		var daysRemaining int
		err := rows.Scan(
			&p.ID, &p.OrgID, &p.Name, &p.ProjectCode, &p.Slug, &p.Description, &p.Purpose, &p.Priority,
			&p.ClientType, &p.ClientOrgName, &p.ClientContactPerson, &p.ClientDesignation,
			&p.ClientEmail, &p.ClientPhone, &p.ClientWebsite, &p.ClientNotes,
			&p.LocationCountry, &p.LocationState, &p.LocationCity, &p.SitePropertyName, &p.LocationAddress, &p.PostalCode,
			&p.Latitude, &p.Longitude,
			&p.PrimaryContactName, &p.PrimaryContactEmail, &p.PrimaryContactPhone, &p.PrimaryContactDesignation,
			&p.EmergencyContactName, &p.EmergencyContactPhone, &p.EmergencyContactAvail, &p.EmergencyContactNotes,
			&p.StartDate, &p.ExpectedCompletionDate, &p.CaptureStartDate, &p.ExpectedCaptureCompletion,
			&p.ProjectAdminID, &p.AccessPolicy, &membersRaw, &operatorsRaw,
			&p.CaptureMethod, &p.CaptureInstructions, &p.SiteAccessRequirements, &p.RestrictedAreas, &p.SpecialCaptureNotes,
			&configRaw,
			&p.Typology, &p.TotalAreaSqft, &p.TotalAreaSqm, &p.CeilingHeightMeters,
			&p.TotalFloorsCount, &p.TotalHallsCount, &p.TotalRoomsCount, &p.TotalCorridorsCount,
			&p.PrecisionGateCm, &p.Status, &p.CreatedBy, &p.CreatedAt, &p.UpdatedAt, &p.DeletedAt,
			&daysRemaining,
		)
		if err == nil {
			_ = json.Unmarshal(membersRaw, &p.AssignedMembers)
			_ = json.Unmarshal(operatorsRaw, &p.AssignedOperators)
			_ = json.Unmarshal(configRaw, &p.ProjectConfig)
			p.DaysRemaining = &daysRemaining
			projects = append(projects, &p)
		}
	}

	return projects, nil
}

func (r *ProjectRepo) Update(ctx context.Context, p *domain.Project) error {
	assignedMembersJSON, _ := json.Marshal(p.AssignedMembers)
	assignedOperatorsJSON, _ := json.Marshal(p.AssignedOperators)
	configJSON, _ := json.Marshal(p.ProjectConfig)

	query := `
		UPDATE projects SET
			name = $2, project_code = $3, slug = $4, description = $5, purpose = $6, priority = $7,
			client_type = $8, client_org_name = $9, client_contact_person = $10, client_designation = $11,
			client_email = $12, client_phone = $13, client_website = $14, client_notes = $15,
			location_country = $16, location_state = $17, location_city = $18, site_property_name = $19, location_address = $20, postal_code = $21,
			latitude = $22, longitude = $23,
			primary_contact_name = $24, primary_contact_email = $25, primary_contact_phone = $26, primary_contact_designation = $27,
			emergency_contact_name = $28, emergency_contact_phone = $29, emergency_contact_availability = $30, emergency_contact_notes = $31,
			start_date = $32, expected_completion_date = $33, capture_start_date = $34, expected_capture_completion = $35,
			project_admin_id = $36, access_policy = $37, assigned_members = $38, assigned_operators = $39,
			capture_method = $40, capture_instructions = $41, site_access_requirements = $42, restricted_areas = $43, special_capture_notes = $44,
			project_config = $45,
			typology = $46, total_area_sqft = $47, total_area_sqm = $48, ceiling_height_meters = $49,
			total_floors_count = $50, total_halls_count = $51, total_rooms_count = $52, total_corridors_count = $53,
			precision_gate_cm = $54, status = $55,
			cover_image_id = $56, cover_image_url = $57, contact_name = $58, contact_email = $59, contact_phone = $60, project_type = $61, custom_type = $62,
			updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query,
		p.ID, p.Name, p.ProjectCode, p.Slug, p.Description, p.Purpose, p.Priority,
		p.ClientType, p.ClientOrgName, p.ClientContactPerson, p.ClientDesignation,
		p.ClientEmail, p.ClientPhone, p.ClientWebsite, p.ClientNotes,
		p.LocationCountry, p.LocationState, p.LocationCity, p.SitePropertyName, p.LocationAddress, p.PostalCode,
		p.Latitude, p.Longitude,
		p.PrimaryContactName, p.PrimaryContactEmail, p.PrimaryContactPhone, p.PrimaryContactDesignation,
		p.EmergencyContactName, p.EmergencyContactPhone, p.EmergencyContactAvail, p.EmergencyContactNotes,
		p.StartDate, p.ExpectedCompletionDate, p.CaptureStartDate, p.ExpectedCaptureCompletion,
		p.ProjectAdminID, p.AccessPolicy, assignedMembersJSON, assignedOperatorsJSON,
		p.CaptureMethod, p.CaptureInstructions, p.SiteAccessRequirements, p.RestrictedAreas, p.SpecialCaptureNotes,
		configJSON,
		p.Typology, p.TotalAreaSqft, p.TotalAreaSqm, p.CeilingHeightMeters,
		p.TotalFloorsCount, p.TotalHallsCount, p.TotalRoomsCount, p.TotalCorridorsCount,
		p.PrecisionGateCm, p.Status,
		p.CoverImageID, p.CoverImageURL, p.ContactName, p.ContactEmail, p.ContactPhone, p.ProjectType, p.CustomType,
	)
	return err
}

func (r *ProjectRepo) SoftDelete(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE projects SET deleted_at = NOW(), updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *ProjectRepo) Restore(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE projects SET deleted_at = NULL, updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *ProjectRepo) PermanentDelete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM projects WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *ProjectRepo) Archive(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE projects SET status = 'ARCHIVED', updated_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *ProjectRepo) CreateStructure(ctx context.Context, s *domain.ProjectStructure) error {
	query := `
		INSERT INTO project_structures (
			id, project_id, name, building_code, structure_type, floors_count, halls_count, rooms_count,
			corridors_count, area_sqm, ceiling_height_meters, building_address, building_description,
			access_notes, site_restrictions, capture_instructions, working_hours,
			status, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
	`
	_, err := r.pool.Exec(ctx, query,
		s.ID, s.ProjectID, s.Name, s.BuildingCode, s.StructureType, s.FloorsCount, s.HallsCount, s.RoomsCount,
		s.CorridorsCount, s.AreaSqm, s.CeilingHeightMeters, s.BuildingAddress, s.BuildingDescription,
		s.AccessNotes, s.SiteRestrictions, s.CaptureInstructions, s.WorkingHours,
		s.Status, s.CreatedAt, s.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) ListStructuresByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectStructure, error) {
	query := `
		SELECT 
			id, project_id, name, building_code, structure_type, floors_count, halls_count, rooms_count,
			corridors_count, area_sqm, ceiling_height_meters, building_address, building_description,
			access_notes, site_restrictions, capture_instructions, working_hours,
			status, created_at, updated_at
		FROM project_structures
		WHERE project_id = $1
		ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var structures []*domain.ProjectStructure
	for rows.Next() {
		var s domain.ProjectStructure
		err := rows.Scan(
			&s.ID, &s.ProjectID, &s.Name, &s.BuildingCode, &s.StructureType, &s.FloorsCount, &s.HallsCount, &s.RoomsCount,
			&s.CorridorsCount, &s.AreaSqm, &s.CeilingHeightMeters, &s.BuildingAddress, &s.BuildingDescription,
			&s.AccessNotes, &s.SiteRestrictions, &s.CaptureInstructions, &s.WorkingHours,
			&s.Status, &s.CreatedAt, &s.UpdatedAt,
		)
		if err == nil {
			levels, _ := r.ListLevelsByStructure(ctx, s.ID)
			s.Levels = levels
			structures = append(structures, &s)
		}
	}
	return structures, nil
}

func (r *ProjectRepo) CreateLevel(ctx context.Context, l *domain.SpatialLevel) error {
	query := `
		INSERT INTO spatial_levels (
			id, structure_id, level_number, level_name, elevation_meters, floor_description,
			capture_status, processing_status, quality_status, current_model_version,
			halls_count, rooms_count, corridors_count, area_sqm, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
	`
	_, err := r.pool.Exec(ctx, query,
		l.ID, l.StructureID, l.LevelNumber, l.LevelName, l.ElevationMeters, l.FloorDescription,
		l.CaptureStatus, l.ProcessingStatus, l.QualityStatus, l.CurrentModelVersion,
		l.HallsCount, l.RoomsCount, l.CorridorsCount, l.AreaSqm, l.CreatedAt, l.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) ListLevelsByStructure(ctx context.Context, structureID uuid.UUID) ([]*domain.SpatialLevel, error) {
	query := `
		SELECT 
			id, structure_id, level_number, level_name, elevation_meters, floor_description,
			capture_status, processing_status, quality_status, current_model_version,
			halls_count, rooms_count, corridors_count, area_sqm, created_at, updated_at
		FROM spatial_levels
		WHERE structure_id = $1
		ORDER BY level_number ASC
	`
	rows, err := r.pool.Query(ctx, query, structureID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var levels []*domain.SpatialLevel
	for rows.Next() {
		var l domain.SpatialLevel
		err := rows.Scan(
			&l.ID, &l.StructureID, &l.LevelNumber, &l.LevelName, &l.ElevationMeters, &l.FloorDescription,
			&l.CaptureStatus, &l.ProcessingStatus, &l.QualityStatus, &l.CurrentModelVersion,
			&l.HallsCount, &l.RoomsCount, &l.CorridorsCount, &l.AreaSqm, &l.CreatedAt, &l.UpdatedAt,
		)
		if err == nil {
			sections, _ := r.ListSectionsByLevel(ctx, l.ID)
			l.Sections = sections
			levels = append(levels, &l)
		}
	}
	return levels, nil
}

func (r *ProjectRepo) CreateSection(ctx context.Context, s *domain.SpatialSection) error {
	query := `
		INSERT INTO spatial_sections (
			id, level_id, name, section_type, area_sqm, bounding_box, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err := r.pool.Exec(ctx, query,
		s.ID, s.LevelID, s.Name, s.SectionType, s.AreaSqm, s.BoundingBox, s.CreatedAt, s.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) ListSectionsByLevel(ctx context.Context, levelID uuid.UUID) ([]*domain.SpatialSection, error) {
	query := `
		SELECT id, level_id, name, section_type, area_sqm, bounding_box, created_at, updated_at
		FROM spatial_sections
		WHERE level_id = $1
		ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, levelID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sections []*domain.SpatialSection
	for rows.Next() {
		var s domain.SpatialSection
		err := rows.Scan(
			&s.ID, &s.LevelID, &s.Name, &s.SectionType, &s.AreaSqm, &s.BoundingBox, &s.CreatedAt, &s.UpdatedAt,
		)
		if err == nil {
			sections = append(sections, &s)
		}
	}
	return sections, nil
}

func (r *ProjectRepo) CreateProjectUpdate(ctx context.Context, u *domain.ProjectUpdate) error {
	query := `
		INSERT INTO project_updates (
			id, project_id, author_id, update_type, title, description, priority, building_id, floor_id, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	_, err := r.pool.Exec(ctx, query,
		u.ID, u.ProjectID, u.AuthorID, u.UpdateType, u.Title, u.Description, u.Priority, u.BuildingID, u.FloorID, u.CreatedAt,
	)
	return err
}

func (r *ProjectRepo) ListProjectUpdates(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectUpdate, error) {
	query := `
		SELECT id, project_id, author_id, update_type, title, description, priority, building_id, floor_id, created_at
		FROM project_updates
		WHERE project_id = $1
		ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var updates []*domain.ProjectUpdate
	for rows.Next() {
		var u domain.ProjectUpdate
		err := rows.Scan(
			&u.ID, &u.ProjectID, &u.AuthorID, &u.UpdateType, &u.Title, &u.Description, &u.Priority, &u.BuildingID, &u.FloorID, &u.CreatedAt,
		)
		if err == nil {
			updates = append(updates, &u)
		}
	}
	return updates, nil
}

func (r *ProjectRepo) CreateTimelineEvent(ctx context.Context, e *domain.TimelineEvent) error {
	query := `
		INSERT INTO project_timeline_events (id, project_id, event_type, title, description, status, milestone_date, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err := r.pool.Exec(ctx, query, e.ID, e.ProjectID, e.EventType, e.Title, e.Description, e.Status, e.MilestoneDate, e.CreatedAt)
	return err
}

func (r *ProjectRepo) ListTimelineEvents(ctx context.Context, projectID uuid.UUID) ([]*domain.TimelineEvent, error) {
	query := `
		SELECT id, project_id, event_type, title, description, status, milestone_date, created_at
		FROM project_timeline_events
		WHERE project_id = $1
		ORDER BY milestone_date ASC, created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []*domain.TimelineEvent
	for rows.Next() {
		var e domain.TimelineEvent
		if err := rows.Scan(&e.ID, &e.ProjectID, &e.EventType, &e.Title, &e.Description, &e.Status, &e.MilestoneDate, &e.CreatedAt); err == nil {
			comments, _ := r.ListTimelineComments(ctx, e.ID)
			e.Comments = comments
			events = append(events, &e)
		}
	}
	return events, nil
}

func (r *ProjectRepo) UpdateTimelineEventStatus(ctx context.Context, eventID uuid.UUID, status string) error {
	query := `
		UPDATE project_timeline_events
		SET status = $2
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, eventID, status)
	return err
}

func (r *ProjectRepo) AddTimelineComment(ctx context.Context, c *domain.TimelineComment) error {
	query := `
		INSERT INTO timeline_event_comments (id, event_id, author_id, author_name, author_role, content, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
	`
	_, err := r.pool.Exec(ctx, query, c.ID, c.EventID, c.AuthorID, c.AuthorName, c.AuthorRole, c.Content, c.CreatedAt)
	return err
}

func (r *ProjectRepo) ListTimelineComments(ctx context.Context, eventID uuid.UUID) ([]*domain.TimelineComment, error) {
	query := `
		SELECT id, event_id, author_id, author_name, author_role, content, created_at
		FROM timeline_event_comments
		WHERE event_id = $1
		ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, eventID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var comments []*domain.TimelineComment
	for rows.Next() {
		var c domain.TimelineComment
		if err := rows.Scan(&c.ID, &c.EventID, &c.AuthorID, &c.AuthorName, &c.AuthorRole, &c.Content, &c.CreatedAt); err == nil {
			comments = append(comments, &c)
		}
	}
	return comments, nil
}

func (r *ProjectRepo) CreateChatMessage(ctx context.Context, m *domain.ProjectChatMessage) error {
	query := `
		INSERT INTO project_chat_messages (id, project_id, sender_id, sender_name, sender_role, content, urgency_level, is_pinned, is_resolved, resolved_by, resolved_at, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`
	_, err := r.pool.Exec(ctx, query, m.ID, m.ProjectID, m.SenderID, m.SenderName, m.SenderRole, m.Content, m.UrgencyLevel, m.IsPinned, m.IsResolved, m.ResolvedBy, m.ResolvedAt, m.CreatedAt)
	return err
}

func (r *ProjectRepo) ListChatMessages(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectChatMessage, error) {
	query := `
		SELECT id, project_id, sender_id, sender_name, sender_role, content, urgency_level, is_pinned, is_resolved, resolved_by, resolved_at, created_at
		FROM project_chat_messages
		WHERE project_id = $1
		ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*domain.ProjectChatMessage
	for rows.Next() {
		var m domain.ProjectChatMessage
		if err := rows.Scan(&m.ID, &m.ProjectID, &m.SenderID, &m.SenderName, &m.SenderRole, &m.Content, &m.UrgencyLevel, &m.IsPinned, &m.IsResolved, &m.ResolvedBy, &m.ResolvedAt, &m.CreatedAt); err == nil {
			messages = append(messages, &m)
		}
	}
	return messages, nil
}

func (r *ProjectRepo) ResolveChatMessage(ctx context.Context, messageID uuid.UUID, resolvedBy string) error {
	query := `
		UPDATE project_chat_messages
		SET is_resolved = true, resolved_by = $2, resolved_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, messageID, resolvedBy)
	return err
}

func (r *ProjectRepo) LogClientEmail(ctx context.Context, l *domain.ClientEmailLog) error {
	query := `
		INSERT INTO client_email_logs (id, project_id, recipient_email, recipient_name, subject, email_type, status, dispatched_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err := r.pool.Exec(ctx, query, l.ID, l.ProjectID, l.RecipientEmail, l.RecipientName, l.Subject, l.EmailType, l.Status, l.DispatchedAt)
	return err
}

func (r *ProjectRepo) ListClientEmails(ctx context.Context, projectID uuid.UUID) ([]*domain.ClientEmailLog, error) {
	query := `
		SELECT id, project_id, recipient_email, recipient_name, subject, email_type, status, dispatched_at
		FROM client_email_logs
		WHERE project_id = $1
		ORDER BY dispatched_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []*domain.ClientEmailLog
	for rows.Next() {
		var l domain.ClientEmailLog
		if err := rows.Scan(&l.ID, &l.ProjectID, &l.RecipientEmail, &l.RecipientName, &l.Subject, &l.EmailType, &l.Status, &l.DispatchedAt); err == nil {
			logs = append(logs, &l)
		}
	}
	return logs, nil
}

func (r *ProjectRepo) LogProjectActivity(ctx context.Context, l *domain.ProjectActivityLog) error {
	query := `
		INSERT INTO project_activity_logs (id, project_id, actor_id, actor_name, actor_role, action_type, action_title, details, old_value, new_value, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
	`
	_, err := r.pool.Exec(ctx, query, l.ID, l.ProjectID, l.ActorID, l.ActorName, l.ActorRole, l.ActionType, l.ActionTitle, l.Details, l.OldValue, l.NewValue, l.CreatedAt)
	return err
}

func (r *ProjectRepo) ListProjectActivities(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectActivityLog, error) {
	query := `
		SELECT id, project_id, actor_id, actor_name, actor_role, action_type, action_title, details, old_value, new_value, created_at
		FROM project_activity_logs
		WHERE project_id = $1
		ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []*domain.ProjectActivityLog
	for rows.Next() {
		var l domain.ProjectActivityLog
		if err := rows.Scan(&l.ID, &l.ProjectID, &l.ActorID, &l.ActorName, &l.ActorRole, &l.ActionType, &l.ActionTitle, &l.Details, &l.OldValue, &l.NewValue, &l.CreatedAt); err == nil {
			logs = append(logs, &l)
		}
	}
	return logs, nil
}

// ----------------- Project Address -----------------

func (r *ProjectRepo) SaveAddress(ctx context.Context, addr *domain.ProjectAddress) error {
	query := `
		INSERT INTO project_addresses (
			id, project_id, address_line_1, address_line_2, area, city, state, pincode, country, latitude, longitude, place_id, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
		)
		ON CONFLICT (project_id) DO UPDATE SET
			address_line_1 = EXCLUDED.address_line_1,
			address_line_2 = EXCLUDED.address_line_2,
			area = EXCLUDED.area,
			city = EXCLUDED.city,
			state = EXCLUDED.state,
			pincode = EXCLUDED.pincode,
			country = EXCLUDED.country,
			latitude = EXCLUDED.latitude,
			longitude = EXCLUDED.longitude,
			place_id = EXCLUDED.place_id,
			updated_at = NOW()
	`
	_, err := r.pool.Exec(ctx, query,
		addr.ID, addr.ProjectID, addr.AddressLine1, addr.AddressLine2, addr.Area,
		addr.City, addr.State, addr.Pincode, addr.Country,
		addr.Latitude, addr.Longitude, addr.PlaceID, addr.CreatedAt, addr.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) GetAddressByProjectID(ctx context.Context, projectID uuid.UUID) (*domain.ProjectAddress, error) {
	query := `
		SELECT id, project_id, address_line_1, address_line_2, area, city, state, pincode, country, latitude, longitude, place_id, created_at, updated_at
		FROM project_addresses
		WHERE project_id = $1
	`
	var a domain.ProjectAddress
	err := r.pool.QueryRow(ctx, query, projectID).Scan(
		&a.ID, &a.ProjectID, &a.AddressLine1, &a.AddressLine2, &a.Area,
		&a.City, &a.State, &a.Pincode, &a.Country,
		&a.Latitude, &a.Longitude, &a.PlaceID, &a.CreatedAt, &a.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &a, nil
}

// ----------------- Project Floors -----------------

func (r *ProjectRepo) CreateFloor(ctx context.Context, floor *domain.ProjectFloor) error {
	query := `
		INSERT INTO project_floors (
			id, project_id, name, floor_number, floor_type, area_value, area_unit, height_value, height_unit, sequence, description, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
		)
	`
	_, err := r.pool.Exec(ctx, query,
		floor.ID, floor.ProjectID, floor.Name, floor.FloorNumber, floor.FloorType,
		floor.AreaValue, floor.AreaUnit, floor.HeightValue, floor.HeightUnit,
		floor.Sequence, floor.Description, floor.CreatedAt, floor.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) GetFloorByID(ctx context.Context, floorID uuid.UUID) (*domain.ProjectFloor, error) {
	query := `
		SELECT id, project_id, name, floor_number, floor_type, area_value, area_unit, height_value, height_unit, sequence, description, created_at, updated_at
		FROM project_floors
		WHERE id = $1
	`
	var f domain.ProjectFloor
	err := r.pool.QueryRow(ctx, query, floorID).Scan(
		&f.ID, &f.ProjectID, &f.Name, &f.FloorNumber, &f.FloorType,
		&f.AreaValue, &f.AreaUnit, &f.HeightValue, &f.HeightUnit,
		&f.Sequence, &f.Description, &f.CreatedAt, &f.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}

	plan, _ := r.GetFloorPlanByFloorID(ctx, f.ID)
	f.FloorPlan = plan
	return &f, nil
}

func (r *ProjectRepo) ListFloorsByProjectID(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectFloor, error) {
	query := `
		SELECT id, project_id, name, floor_number, floor_type, area_value, area_unit, height_value, height_unit, sequence, description, created_at, updated_at
		FROM project_floors
		WHERE project_id = $1
		ORDER BY sequence ASC, floor_number ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var floors []*domain.ProjectFloor
	for rows.Next() {
		var f domain.ProjectFloor
		if err := rows.Scan(
			&f.ID, &f.ProjectID, &f.Name, &f.FloorNumber, &f.FloorType,
			&f.AreaValue, &f.AreaUnit, &f.HeightValue, &f.HeightUnit,
			&f.Sequence, &f.Description, &f.CreatedAt, &f.UpdatedAt,
		); err == nil {
			plan, _ := r.GetFloorPlanByFloorID(ctx, f.ID)
			f.FloorPlan = plan
			floors = append(floors, &f)
		}
	}
	return floors, nil
}

func (r *ProjectRepo) UpdateFloor(ctx context.Context, floor *domain.ProjectFloor) error {
	query := `
		UPDATE project_floors SET
			name = $2, floor_number = $3, floor_type = $4,
			area_value = $5, area_unit = $6, height_value = $7, height_unit = $8,
			sequence = $9, description = $10, updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query,
		floor.ID, floor.Name, floor.FloorNumber, floor.FloorType,
		floor.AreaValue, floor.AreaUnit, floor.HeightValue, floor.HeightUnit,
		floor.Sequence, floor.Description,
	)
	return err
}

func (r *ProjectRepo) DeleteFloor(ctx context.Context, floorID uuid.UUID) error {
	query := `DELETE FROM project_floors WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, floorID)
	return err
}

// ----------------- Floor Plans (Upload & Draw) -----------------

func (r *ProjectRepo) SaveFloorPlan(ctx context.Context, plan *domain.FloorPlan) error {
	query := `
		INSERT INTO floor_plans (
			id, floor_id, plan_type, file_id, file_url, original_file_name, file_size_bytes,
			mime_type, canvas_width, canvas_height, scale_ratio, drawing_data, preview_file_id, preview_url,
			created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
		)
		ON CONFLICT (floor_id) DO UPDATE SET
			plan_type = EXCLUDED.plan_type,
			file_id = EXCLUDED.file_id,
			file_url = EXCLUDED.file_url,
			original_file_name = EXCLUDED.original_file_name,
			file_size_bytes = EXCLUDED.file_size_bytes,
			mime_type = EXCLUDED.mime_type,
			canvas_width = EXCLUDED.canvas_width,
			canvas_height = EXCLUDED.canvas_height,
			scale_ratio = EXCLUDED.scale_ratio,
			drawing_data = EXCLUDED.drawing_data,
			preview_file_id = EXCLUDED.preview_file_id,
			preview_url = EXCLUDED.preview_url,
			updated_at = NOW()
	`
	drawingJSON := plan.DrawingData
	if len(drawingJSON) == 0 {
		drawingJSON = []byte(`{"objects": []}`)
	}
	_, err := r.pool.Exec(ctx, query,
		plan.ID, plan.FloorID, plan.PlanType, plan.FileID, plan.FileURL, plan.OriginalFileName, plan.FileSizeBytes,
		plan.MimeType, plan.CanvasWidth, plan.CanvasHeight, plan.ScaleRatio, drawingJSON, plan.PreviewFileID, plan.PreviewURL,
		plan.CreatedAt, plan.UpdatedAt,
	)
	return err
}

func (r *ProjectRepo) GetFloorPlanByFloorID(ctx context.Context, floorID uuid.UUID) (*domain.FloorPlan, error) {
	query := `
		SELECT id, floor_id, plan_type, file_id, file_url, original_file_name, file_size_bytes,
		       mime_type, canvas_width, canvas_height, scale_ratio, drawing_data, preview_file_id, preview_url,
		       created_at, updated_at
		FROM floor_plans
		WHERE floor_id = $1
	`
	var p domain.FloorPlan
	var drawingRaw []byte
	err := r.pool.QueryRow(ctx, query, floorID).Scan(
		&p.ID, &p.FloorID, &p.PlanType, &p.FileID, &p.FileURL, &p.OriginalFileName, &p.FileSizeBytes,
		&p.MimeType, &p.CanvasWidth, &p.CanvasHeight, &p.ScaleRatio, &drawingRaw, &p.PreviewFileID, &p.PreviewURL,
		&p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	p.DrawingData = drawingRaw
	return &p, nil
}

func (r *ProjectRepo) DeleteFloorPlan(ctx context.Context, floorID uuid.UUID) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM floor_plans WHERE floor_id = $1`, floorID)
	return err
}

// ----------------- Project Members -----------------

func (r *ProjectRepo) AddProjectMember(ctx context.Context, member *domain.ProjectMember) error {
	query := `
		INSERT INTO project_members (
			id, project_id, user_id, project_role, permissions, status, assigned_by, assigned_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8
		)
		ON CONFLICT (project_id, user_id) DO UPDATE SET
			project_role = EXCLUDED.project_role,
			permissions = EXCLUDED.permissions,
			status = EXCLUDED.status,
			assigned_by = EXCLUDED.assigned_by,
			assigned_at = NOW()
	`
	permJSON := member.Permissions
	if len(permJSON) == 0 {
		permJSON = []byte(`[]`)
	}
	_, err := r.pool.Exec(ctx, query,
		member.ID, member.ProjectID, member.UserID, member.ProjectRole, permJSON, member.Status,
		member.AssignedBy, member.AssignedAt,
	)
	return err
}

func (r *ProjectRepo) ListProjectMembers(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectMember, error) {
	query := `
		SELECT 
			pm.id, pm.project_id, pm.user_id, pm.project_role, pm.permissions, pm.status, pm.assigned_by, pm.assigned_at,
			u.id, u.email, u.full_name, u.phone, u.avatar_url, u.status
		FROM project_members pm
		JOIN users u ON pm.user_id = u.id
		WHERE pm.project_id = $1
		ORDER BY pm.assigned_at ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var members []*domain.ProjectMember
	for rows.Next() {
		var m domain.ProjectMember
		var permRaw []byte
		var u domain.User
		if err := rows.Scan(
			&m.ID, &m.ProjectID, &m.UserID, &m.ProjectRole, &permRaw, &m.Status, &m.AssignedBy, &m.AssignedAt,
			&u.ID, &u.Email, &u.FullName, &u.Phone, &u.AvatarURL, &u.Status,
		); err == nil {
			m.Permissions = permRaw
			m.User = &u
			members = append(members, &m)
		}
	}
	return members, nil
}

func (r *ProjectRepo) RemoveProjectMember(ctx context.Context, projectID, userID uuid.UUID) error {
	query := `DELETE FROM project_members WHERE project_id = $1 AND user_id = $2`
	_, err := r.pool.Exec(ctx, query, projectID, userID)
	return err
}



