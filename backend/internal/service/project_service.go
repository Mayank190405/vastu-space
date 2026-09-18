package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/mailer"
	"vastu/backend/internal/pkg/utils"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type ProjectService struct {
	projectRepo repository.ProjectRepository
	orgRepo     repository.OrgRepository
	mailer      *mailer.SMTPMailer
}

func NewProjectService(
	projectRepo repository.ProjectRepository,
	orgRepo repository.OrgRepository,
	mailer *mailer.SMTPMailer,
) *ProjectService {
	return &ProjectService{
		projectRepo: projectRepo,
		orgRepo:     orgRepo,
		mailer:      mailer,
	}
}

func (s *ProjectService) CreateProject(ctx context.Context, orgID, userID uuid.UUID, input domain.CreateProjectInput) (*domain.Project, error) {
	name := strings.TrimSpace(input.Name)
	if name == "" {
		return nil, errors.New("project name is required")
	}

	slug := utils.Slugify(name) + "-" + strings.ToLower(utils.RandomAlphaNum(4))
	now := time.Now().UTC()

	status := domain.ProjectStatusDraft
	if input.Status != nil && *input.Status != "" {
		status = *input.Status
	}

	priority := "High"
	if input.Priority != nil && *input.Priority != "" {
		priority = *input.Priority
	}

	accessPolicy := "assigned_only"
	if input.AccessPolicy != nil && *input.AccessPolicy != "" {
		accessPolicy = *input.AccessPolicy
	}

	captureMethod := "Smartphone Video Capture"
	if input.CaptureMethod != nil && *input.CaptureMethod != "" {
		captureMethod = *input.CaptureMethod
	}

	projectCode := input.ProjectCode
	if projectCode == nil || strings.TrimSpace(*projectCode) == "" {
		generatedCode := "PRJ-" + strings.ToUpper(utils.RandomAlphaNum(6))
		projectCode = &generatedCode
	}

	totalFloors := 0
	for _, b := range input.Buildings {
		if len(b.Floors) > 0 {
			totalFloors += len(b.Floors)
		} else if b.FloorsCount > 0 {
			totalFloors += b.FloorsCount
		} else {
			totalFloors += 1
		}
	}
	if totalFloors <= 0 {
		totalFloors = 1
	}

	config := input.ProjectConfig
	if config == nil {
		config = &domain.ProjectConfig{
			EnableViewer:              true,
			EnableSearch:              true,
			EnableNavigation:          true,
			EnablePOIPlatform:         true,
			EnableModelVersioning:     true,
			QualityValidationRequired: true,
			RequireAdminApproval:      true,
			NotifyProcessing:          true,
			NotifyQualityFailure:      true,
			NotifyRescan:              true,
			NotifyPublication:         true,
		}
	}

	project := &domain.Project{
		ID:                        uuid.New(),
		OrgID:                     orgID,
		Name:                      name,
		ProjectCode:               projectCode,
		Slug:                      slug,
		Description:               input.Description,
		Purpose:                   input.Purpose,
		Priority:                  priority,
		ClientType:                input.ClientType,
		ClientOrgName:             input.ClientOrgName,
		ClientContactPerson:       input.ClientContactPerson,
		ClientDesignation:         input.ClientDesignation,
		ClientEmail:               input.ClientEmail,
		ClientPhone:               input.ClientPhone,
		ClientWebsite:             input.ClientWebsite,
		ClientNotes:               input.ClientNotes,
		LocationCountry:           input.LocationCountry,
		LocationState:             input.LocationState,
		LocationCity:              input.LocationCity,
		SitePropertyName:          input.SitePropertyName,
		LocationAddress:           input.LocationAddress,
		PostalCode:                input.PostalCode,
		Latitude:                  input.Latitude,
		Longitude:                 input.Longitude,
		PrimaryContactName:        input.PrimaryContactName,
		PrimaryContactEmail:       input.PrimaryContactEmail,
		PrimaryContactPhone:       input.PrimaryContactPhone,
		PrimaryContactDesignation: input.PrimaryContactDesignation,
		EmergencyContactName:      input.EmergencyContactName,
		EmergencyContactPhone:     input.EmergencyContactPhone,
		EmergencyContactAvail:     input.EmergencyContactAvail,
		EmergencyContactNotes:     input.EmergencyContactNotes,
		StartDate:                 input.StartDate,
		ExpectedCompletionDate:    input.ExpectedCompletionDate,
		CaptureStartDate:          input.CaptureStartDate,
		ExpectedCaptureCompletion: input.ExpectedCaptureCompletion,
		ProjectAdminID:            input.ProjectAdminID,
		AccessPolicy:              accessPolicy,
		AssignedMembers:           input.AssignedMembers,
		AssignedOperators:         input.AssignedOperators,
		CaptureMethod:             captureMethod,
		CaptureInstructions:       input.CaptureInstructions,
		SiteAccessRequirements:    input.SiteAccessRequirements,
		RestrictedAreas:           input.RestrictedAreas,
		SpecialCaptureNotes:       input.SpecialCaptureNotes,
		ProjectConfig:             config,
		Typology:                  input.Typology,
		TotalFloorsCount:          totalFloors,
		PrecisionGateCm:           2.5,
		Status:                    status,
		CreatedBy:                 &userID,
		CreatedAt:                 now,
		UpdatedAt:                 now,
	}

	if err := s.projectRepo.Create(ctx, project); err != nil {
		return nil, err
	}

	// Create Buildings & Floors
	if len(input.Buildings) > 0 {
		for bIdx, b := range input.Buildings {
			flCount := b.FloorsCount
			if flCount <= 0 {
				flCount = len(b.Floors)
				if flCount <= 0 {
					flCount = 1
				}
			}
			structType := b.BuildingType
			if structType == "" {
				structType = string(project.Typology)
			}
			structure := &domain.ProjectStructure{
				ID:                  uuid.New(),
				ProjectID:           project.ID,
				Name:                b.Name,
				BuildingCode:        b.BuildingCode,
				StructureType:       structType,
				FloorsCount:         flCount,
				BuildingAddress:     b.BuildingAddress,
				BuildingDescription: b.BuildingDescription,
				AccessNotes:         b.AccessNotes,
				SiteRestrictions:    b.SiteRestrictions,
				CaptureInstructions: b.CaptureInstructions,
				WorkingHours:        b.WorkingHours,
				Status:              "active",
				CreatedAt:           now,
				UpdatedAt:           now,
			}
			_ = s.projectRepo.CreateStructure(ctx, structure)

			// Create Floors
			if len(b.Floors) > 0 {
				for _, fl := range b.Floors {
					level := &domain.SpatialLevel{
						ID:                  uuid.New(),
						StructureID:         structure.ID,
						LevelNumber:         fl.LevelNumber,
						LevelName:           fl.LevelName,
						FloorDescription:    fl.FloorDescription,
						CaptureStatus:       "not_started",
						ProcessingStatus:    "not_started",
						QualityStatus:       "not_started",
						CurrentModelVersion: nil,
						CreatedAt:           now,
						UpdatedAt:           now,
					}
					_ = s.projectRepo.CreateLevel(ctx, level)
				}
			} else {
				for f := 0; f < flCount; f++ {
					levelName := fmt.Sprintf("Floor %d", f)
					if f == 0 {
						levelName = "Ground Floor"
					}
					level := &domain.SpatialLevel{
						ID:               uuid.New(),
						StructureID:      structure.ID,
						LevelNumber:      f,
						LevelName:        levelName,
						CaptureStatus:    "not_started",
						ProcessingStatus: "not_started",
						QualityStatus:    "not_started",
						CreatedAt:        now,
						UpdatedAt:        now,
					}
					_ = s.projectRepo.CreateLevel(ctx, level)
				}
			}
			_ = bIdx
		}
	} else {
		// Create default building & floor
		defaultStructure := &domain.ProjectStructure{
			ID:            uuid.New(),
			ProjectID:     project.ID,
			Name:          "Main Building",
			StructureType: string(project.Typology),
			FloorsCount:   1,
			Status:        "active",
			CreatedAt:     now,
			UpdatedAt:     now,
		}
		_ = s.projectRepo.CreateStructure(ctx, defaultStructure)

		_ = s.projectRepo.CreateLevel(ctx, &domain.SpatialLevel{
			ID:               uuid.New(),
			StructureID:      defaultStructure.ID,
			LevelNumber:      0,
			LevelName:        "Ground Floor",
			CaptureStatus:    "not_started",
			ProcessingStatus: "not_started",
			QualityStatus:    "not_started",
			CreatedAt:        now,
			UpdatedAt:        now,
		})
	}

	// Create Initial Project Update (Operational Progress Feed)
	bCount := len(input.Buildings)
	if bCount == 0 {
		bCount = 1
	}
	initialUpdate := &domain.ProjectUpdate{
		ID:          uuid.New(),
		ProjectID:   project.ID,
		AuthorID:    &userID,
		UpdateType:  "General Update",
		Title:       "Project Created",
		Description: fmt.Sprintf("%s was created with %d building(s) and %d floor(s) configured. Status: %s.", project.Name, bCount, totalFloors, project.Status),
		Priority:    "Normal",
		CreatedAt:   now,
	}
	_ = s.projectRepo.CreateProjectUpdate(ctx, initialUpdate)

	// Initialize Project Timeline Milestones
	milestones := []struct {
		eventType   string
		title       string
		description string
		status      string
		dateOffset  time.Duration
	}{
		{
			eventType:   "project_created",
			title:       "Project Registration & Workspace Setup",
			description: fmt.Sprintf("Project container '%s' registered under %s typology.", project.Name, project.Typology),
			status:      "completed",
			dateOffset:  0,
		},
		{
			eventType:   "client_onboarding",
			title:       "Client Verification & Spatial Briefing",
			description: "Thank You & Spatial Verification email dispatched to client. Pending client approval.",
			status:      "in_progress",
			dateOffset:  1 * time.Hour,
		},
		{
			eventType:   "capture_planning",
			title:       "Capture Team Assignment & Access Clearance",
			description: fmt.Sprintf("Assigned capture operators. Method: %s.", project.CaptureMethod),
			status:      "pending",
			dateOffset:  24 * time.Hour,
		},
		{
			eventType:   "mobile_capture",
			title:       "On-Site Physical Capture Session",
			description: "Operators recording continuous 60Hz IMU + optical video streams.",
			status:      "pending",
			dateOffset:  48 * time.Hour,
		},
		{
			eventType:   "reconstruction",
			title:       "Photogrammetric & Neural Reconstruction",
			description: "Multi-view processing and dense point cloud alignment.",
			status:      "pending",
			dateOffset:  72 * time.Hour,
		},
		{
			eventType:   "quality_sla",
			title:       "Quality Gate & Spatial Precision Check",
			description: "Verification of confidence maps and <= 2.5cm spatial tolerance.",
			status:      "pending",
			dateOffset:  96 * time.Hour,
		},
		{
			eventType:   "twin_publication",
			title:       "Interactive 3D Digital Twin Publication",
			description: "Publish digital twin model with POIs, search, and indoor navigation.",
			status:      "pending",
			dateOffset:  120 * time.Hour,
		},
	}

	for _, m := range milestones {
		eventID := uuid.New()
		_ = s.projectRepo.CreateTimelineEvent(ctx, &domain.TimelineEvent{
			ID:            eventID,
			ProjectID:     project.ID,
			EventType:     m.eventType,
			Title:         m.title,
			Description:   m.description,
			Status:        m.status,
			MilestoneDate: now.Add(m.dateOffset),
			CreatedAt:     now,
		})

		// Add an initial note to the first milestone
		if m.eventType == "project_created" {
			_ = s.projectRepo.AddTimelineComment(ctx, &domain.TimelineComment{
				ID:         uuid.New(),
				EventID:    eventID,
				AuthorID:   &userID,
				AuthorName: "System Automation",
				AuthorRole: "System Admin",
				Content:    fmt.Sprintf("Initial spatial container setup completed with %d building(s).", bCount),
				CreatedAt:  now,
			})
		}
	}

	// Dispatch Client Thank You Email if client email provided
	if input.ClientEmail != nil && strings.TrimSpace(*input.ClientEmail) != "" {
		cEmail := strings.TrimSpace(*input.ClientEmail)
		cName := "Valued Client"
		if input.ClientContactPerson != nil && strings.TrimSpace(*input.ClientContactPerson) != "" {
			cName = strings.TrimSpace(*input.ClientContactPerson)
		}
		subject := fmt.Sprintf("Welcome to VĀSTU — Spatial Digital Twin Registration for %s (%s)", project.Name, *project.ProjectCode)
		_ = s.projectRepo.LogClientEmail(ctx, &domain.ClientEmailLog{
			ID:             uuid.New(),
			ProjectID:      project.ID,
			RecipientEmail: cEmail,
			RecipientName:  &cName,
			Subject:        subject,
			EmailType:      "thank_you_and_verification",
			Status:         "sent",
			DispatchedAt:   now,
		})

		city := "India"
		if project.LocationCity != nil {
			city = *project.LocationCity
		}

		siteInfo := fmt.Sprintf(`
			<div class="info-line"><strong>📍 Site Location:</strong> %s, %s</div>
			<div class="info-line"><strong>🏢 Space Scope:</strong> %d Building(s), %d Floor(s)</div>
			<div class="info-line"><strong>📐 Measurement Accuracy:</strong> True-to-life 3D digital twin accurate within 1 inch (2.5 cm)</div>
		`, city, project.LocationCountry, bCount, totalFloors)

		s.sendClientHTMLEmail(
			cEmail,
			cName,
			subject,
			fmt.Sprintf("Welcome to VĀSTU — %s", project.Name),
			fmt.Sprintf("Thank you for choosing VĀSTU. We have initiated the physical space digitization workspace for <strong>%s</strong> (Project Code: <code>%s</code>).", project.Name, *project.ProjectCode),
			siteInfo,
		)
	}

	return project, nil
}

func (s *ProjectService) ListProjects(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error) {
	return s.projectRepo.ListByOrg(ctx, orgID)
}

func (s *ProjectService) ListTrashProjects(ctx context.Context, orgID uuid.UUID) ([]*domain.Project, error) {
	return s.projectRepo.ListTrashByOrg(ctx, orgID)
}

func (s *ProjectService) GetProject(ctx context.Context, projectID uuid.UUID) (*domain.Project, error) {
	return s.projectRepo.GetByID(ctx, projectID)
}

func (s *ProjectService) UpdateProject(ctx context.Context, projectID uuid.UUID, input domain.UpdateProjectInput) (*domain.Project, error) {
	project, err := s.projectRepo.GetByID(ctx, projectID)
	if err != nil {
		return nil, err
	}

	if input.Name != nil && strings.TrimSpace(*input.Name) != "" {
		project.Name = strings.TrimSpace(*input.Name)
		project.Slug = utils.Slugify(project.Name)
	}
	if input.ProjectCode != nil {
		project.ProjectCode = input.ProjectCode
	}
	if input.Description != nil {
		project.Description = input.Description
	}
	if input.Purpose != nil {
		project.Purpose = input.Purpose
	}
	if input.Priority != nil {
		project.Priority = *input.Priority
	}
	if input.ClientType != nil {
		project.ClientType = input.ClientType
	}
	if input.ClientOrgName != nil {
		project.ClientOrgName = input.ClientOrgName
	}
	if input.ClientContactPerson != nil {
		project.ClientContactPerson = input.ClientContactPerson
	}
	if input.ClientDesignation != nil {
		project.ClientDesignation = input.ClientDesignation
	}
	if input.ClientEmail != nil {
		project.ClientEmail = input.ClientEmail
	}
	if input.ClientPhone != nil {
		project.ClientPhone = input.ClientPhone
	}
	if input.ClientWebsite != nil {
		project.ClientWebsite = input.ClientWebsite
	}
	if input.ClientNotes != nil {
		project.ClientNotes = input.ClientNotes
	}
	if input.LocationAddress != nil {
		project.LocationAddress = input.LocationAddress
	}
	if input.LocationCity != nil {
		project.LocationCity = input.LocationCity
	}
	if input.LocationState != nil {
		project.LocationState = input.LocationState
	}
	if input.LocationCountry != nil {
		project.LocationCountry = *input.LocationCountry
	}
	if input.SitePropertyName != nil {
		project.SitePropertyName = input.SitePropertyName
	}
	if input.PostalCode != nil {
		project.PostalCode = input.PostalCode
	}
	if input.Latitude != nil {
		project.Latitude = input.Latitude
	}
	if input.Longitude != nil {
		project.Longitude = input.Longitude
	}
	if input.PrimaryContactName != nil {
		project.PrimaryContactName = input.PrimaryContactName
	}
	if input.PrimaryContactEmail != nil {
		project.PrimaryContactEmail = input.PrimaryContactEmail
	}
	if input.PrimaryContactPhone != nil {
		project.PrimaryContactPhone = input.PrimaryContactPhone
	}
	if input.PrimaryContactDesignation != nil {
		project.PrimaryContactDesignation = input.PrimaryContactDesignation
	}
	if input.EmergencyContactName != nil {
		project.EmergencyContactName = input.EmergencyContactName
	}
	if input.EmergencyContactPhone != nil {
		project.EmergencyContactPhone = input.EmergencyContactPhone
	}
	if input.EmergencyContactAvail != nil {
		project.EmergencyContactAvail = input.EmergencyContactAvail
	}
	if input.EmergencyContactNotes != nil {
		project.EmergencyContactNotes = input.EmergencyContactNotes
	}
	if input.StartDate != nil {
		project.StartDate = input.StartDate
	}
	if input.ExpectedCompletionDate != nil {
		project.ExpectedCompletionDate = input.ExpectedCompletionDate
	}
	if input.CaptureStartDate != nil {
		project.CaptureStartDate = input.CaptureStartDate
	}
	if input.ExpectedCaptureCompletion != nil {
		project.ExpectedCaptureCompletion = input.ExpectedCaptureCompletion
	}
	if input.ProjectAdminID != nil {
		project.ProjectAdminID = input.ProjectAdminID
	}
	if input.AccessPolicy != nil {
		project.AccessPolicy = *input.AccessPolicy
	}
	if input.AssignedMembers != nil {
		project.AssignedMembers = input.AssignedMembers
	}
	if input.AssignedOperators != nil {
		project.AssignedOperators = input.AssignedOperators
	}
	if input.CaptureMethod != nil {
		project.CaptureMethod = *input.CaptureMethod
	}
	if input.CaptureInstructions != nil {
		project.CaptureInstructions = input.CaptureInstructions
	}
	if input.SiteAccessRequirements != nil {
		project.SiteAccessRequirements = input.SiteAccessRequirements
	}
	if input.RestrictedAreas != nil {
		project.RestrictedAreas = input.RestrictedAreas
	}
	if input.SpecialCaptureNotes != nil {
		project.SpecialCaptureNotes = input.SpecialCaptureNotes
	}
	if input.ProjectConfig != nil {
		project.ProjectConfig = input.ProjectConfig
	}
	if input.Typology != nil {
		project.Typology = *input.Typology
	}
	oldStatus := project.Status
	if input.Status != nil {
		project.Status = *input.Status
	}

	if err := s.projectRepo.Update(ctx, project); err != nil {
		return nil, err
	}

	actorName := "Admin"
	if input.ActorName != nil && strings.TrimSpace(*input.ActorName) != "" {
		actorName = strings.TrimSpace(*input.ActorName)
	}
	actorRole := "Operations Lead"
	if input.ActorRole != nil && strings.TrimSpace(*input.ActorRole) != "" {
		actorRole = strings.TrimSpace(*input.ActorRole)
	}

	// Log activity if status changed
	if input.Status != nil && *input.Status != oldStatus {
		oldVal := string(oldStatus)
		newVal := string(*input.Status)
		detail := fmt.Sprintf("Project operational status transitioned from %s to %s", oldVal, newVal)
		s.LogActivity(ctx, project.ID, nil, actorName, actorRole, "status_change", fmt.Sprintf("Status updated to %s", newVal), &detail, &oldVal, &newVal)
	} else {
		detail := "Project specifications and workspace metadata updated"
		s.LogActivity(ctx, project.ID, nil, actorName, actorRole, "project_updated", "Project Details Updated", &detail, nil, nil)
	}

	// Auto-dispatch event email to client if status changed and client email exists
	if input.Status != nil && *input.Status != oldStatus && project.ClientEmail != nil && strings.TrimSpace(*project.ClientEmail) != "" {
		cEmail := strings.TrimSpace(*project.ClientEmail)
		cName := "Valued Client"
		if project.ClientContactPerson != nil && strings.TrimSpace(*project.ClientContactPerson) != "" {
			cName = strings.TrimSpace(*project.ClientContactPerson)
		}
		subj := fmt.Sprintf("Project Status Update: %s is now %s", project.Name, *input.Status)
		_ = s.projectRepo.LogClientEmail(ctx, &domain.ClientEmailLog{
			ID:             uuid.New(),
			ProjectID:      project.ID,
			RecipientEmail: cEmail,
			RecipientName:  &cName,
			Subject:        subj,
			EmailType:      fmt.Sprintf("status_changed_to_%s", strings.ToLower(string(*input.Status))),
			Status:         "sent",
			DispatchedAt:   time.Now().UTC(),
		})

		siteInfo := fmt.Sprintf(`
			<div class="info-line"><strong>Project Name:</strong> %s (<code>%s</code>)</div>
			<div class="info-line"><strong>New Status:</strong> <span style="color:#dfb873; font-weight:bold;">%s</span></div>
			<div class="info-line"><strong>Location:</strong> %s, %s</div>
		`, project.Name, *project.ProjectCode, *input.Status, *project.LocationCity, project.LocationCountry)

		s.sendClientHTMLEmail(
			cEmail,
			cName,
			subj,
			fmt.Sprintf("Status Update: %s", *input.Status),
			fmt.Sprintf("The operational status of your digital twin workspace <strong>%s</strong> has progressed to <strong>%s</strong>.", project.Name, *input.Status),
			siteInfo,
		)

		emailDetail := fmt.Sprintf("Status transition email sent to %s (%s)", cName, cEmail)
		s.LogActivity(ctx, project.ID, nil, "Hostinger SMTP", "Automated Dispatch", "email_dispatched", fmt.Sprintf("Client Notification: %s", subj), &emailDetail, nil, nil)
	}

	return project, nil
}

func (s *ProjectService) SoftDeleteProject(ctx context.Context, projectID uuid.UUID) error {
	return s.projectRepo.SoftDelete(ctx, projectID)
}

func (s *ProjectService) RestoreProject(ctx context.Context, projectID uuid.UUID) error {
	return s.projectRepo.Restore(ctx, projectID)
}

func (s *ProjectService) PermanentDeleteProject(ctx context.Context, projectID uuid.UUID) error {
	return s.projectRepo.PermanentDelete(ctx, projectID)
}

func (s *ProjectService) ArchiveProject(ctx context.Context, projectID uuid.UUID) error {
	return s.projectRepo.Archive(ctx, projectID)
}

func (s *ProjectService) LogActivity(ctx context.Context, projectID uuid.UUID, actorID *uuid.UUID, actorName, actorRole, actionType, actionTitle string, details, oldValue, newValue *string) {
	if actorName == "" {
		actorName = "Admin"
	}
	if actorRole == "" {
		actorRole = "Operations Lead"
	}
	log := &domain.ProjectActivityLog{
		ID:          uuid.New(),
		ProjectID:   projectID,
		ActorID:     actorID,
		ActorName:   actorName,
		ActorRole:   actorRole,
		ActionType:  actionType,
		ActionTitle: actionTitle,
		Details:     details,
		OldValue:    oldValue,
		NewValue:    newValue,
		CreatedAt:   time.Now().UTC(),
	}
	_ = s.projectRepo.LogProjectActivity(ctx, log)
}

func (s *ProjectService) GetProjectActivities(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectActivityLog, error) {
	return s.projectRepo.ListProjectActivities(ctx, projectID)
}

func (s *ProjectService) GetTimeline(ctx context.Context, projectID uuid.UUID) ([]*domain.TimelineEvent, error) {
	events, err := s.projectRepo.ListTimelineEvents(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if len(events) == 0 {
		// Auto-initialize default spatial milestones for this project if not yet seeded
		now := time.Now().UTC()
		milestones := []struct {
			eventType   string
			title       string
			description string
			status      string
			dateOffset  time.Duration
		}{
			{
				eventType:   "project_created",
				title:       "Project Registration & Workspace Setup",
				description: "Project container registered with spatial specifications and access policies.",
				status:      "completed",
				dateOffset:  0,
			},
			{
				eventType:   "client_onboarding",
				title:       "Client Verification & Spatial Briefing",
				description: "Thank You & Spatial Verification email dispatched to client for milestone alignment.",
				status:      "in_progress",
				dateOffset:  1 * time.Hour,
			},
			{
				eventType:   "capture_planning",
				title:       "Capture Team Assignment & Access Clearance",
				description: "Assigned certified capture team and verified on-site physical entry permissions.",
				status:      "pending",
				dateOffset:  24 * time.Hour,
			},
			{
				eventType:   "mobile_capture",
				title:       "On-Site Physical Capture Session",
				description: "Operators recording continuous 60Hz IMU + high-resolution terrestrial photogrammetry scan streams.",
				status:      "pending",
				dateOffset:  48 * time.Hour,
			},
			{
				eventType:   "reconstruction",
				title:       "Photogrammetric & Spatial Mesh Reconstruction",
				description: "Multi-view 3D point cloud alignment, noise filtering, and architectural floor plan structuring.",
				status:      "pending",
				dateOffset:  72 * time.Hour,
			},
			{
				eventType:   "quality_sla",
				title:       "Measurement Accuracy Validation",
				description: "True-to-life 3D digital twin validated within 1 inch (2.5 cm) of reality with spatial tolerance check.",
				status:      "pending",
				dateOffset:  96 * time.Hour,
			},
			{
				eventType:   "twin_publication",
				title:       "Interactive 3D Digital Twin Publication",
				description: "Publish interactive digital twin live with indoor navigation, measurement tools, and spatial analytics.",
				status:      "pending",
				dateOffset:  120 * time.Hour,
			},
		}

		for _, m := range milestones {
			eventID := uuid.New()
			_ = s.projectRepo.CreateTimelineEvent(ctx, &domain.TimelineEvent{
				ID:            eventID,
				ProjectID:     projectID,
				EventType:     m.eventType,
				Title:         m.title,
				Description:   m.description,
				Status:        m.status,
				MilestoneDate: now.Add(m.dateOffset),
				CreatedAt:     now,
			})
			if m.eventType == "project_created" {
				_ = s.projectRepo.AddTimelineComment(ctx, &domain.TimelineComment{
					ID:         uuid.New(),
					EventID:    eventID,
					AuthorName: "Operations Lead",
					AuthorRole: "System Admin",
					Content:    "Workspace initialized with complete spatial lifecycle tracking.",
					CreatedAt:  now,
				})
			}
		}

		initDetail := "Initial workspace provisioning and spatial milestones generated."
		s.LogActivity(ctx, projectID, nil, "System Admin", "Operations Lead", "project_created", "Project Workspace Initialized", &initDetail, nil, nil)

		return s.projectRepo.ListTimelineEvents(ctx, projectID)
	}
	return events, nil
}

func (s *ProjectService) UpdateTimelineEventStatus(ctx context.Context, projectID, eventID uuid.UUID, status, actorName, actorRole string, actorID *uuid.UUID) error {
	if err := s.projectRepo.UpdateTimelineEventStatus(ctx, eventID, status); err != nil {
		return err
	}

	detail := fmt.Sprintf("Milestone status transitioned to %s", strings.ToUpper(status))
	s.LogActivity(ctx, projectID, actorID, actorName, actorRole, "milestone_updated", fmt.Sprintf("Milestone Status: %s", strings.ToUpper(status)), &detail, nil, &status)
	return nil
}

func (s *ProjectService) AddTimelineComment(ctx context.Context, projectID, eventID, authorID uuid.UUID, input domain.CreateCommentInput) (*domain.TimelineComment, error) {
	if strings.TrimSpace(input.Content) == "" {
		return nil, errors.New("comment content cannot be empty")
	}
	comment := &domain.TimelineComment{
		ID:         uuid.New(),
		EventID:    eventID,
		AuthorID:   &authorID,
		AuthorName: input.AuthorName,
		AuthorRole: input.AuthorRole,
		Content:    strings.TrimSpace(input.Content),
		CreatedAt:  time.Now().UTC(),
	}
	if err := s.projectRepo.AddTimelineComment(ctx, comment); err != nil {
		return nil, err
	}

	detail := fmt.Sprintf("\"%s\"", comment.Content)
	s.LogActivity(ctx, projectID, &authorID, comment.AuthorName, comment.AuthorRole, "comment_added", "Added Note on Milestone", &detail, nil, nil)
	return comment, nil
}

func (s *ProjectService) GetChatMessages(ctx context.Context, projectID uuid.UUID) ([]*domain.ProjectChatMessage, error) {
	return s.projectRepo.ListChatMessages(ctx, projectID)
}

func (s *ProjectService) SendChatMessage(ctx context.Context, projectID, senderID uuid.UUID, input domain.SendChatMessageInput) (*domain.ProjectChatMessage, error) {
	if strings.TrimSpace(input.Content) == "" {
		return nil, errors.New("message content cannot be empty")
	}
	urgency := input.UrgencyLevel
	if urgency == "" {
		urgency = domain.UrgencyNormal
	}
	isPinned := input.IsPinned || urgency == domain.UrgencyCritical || urgency == domain.UrgencyUrgent

	msg := &domain.ProjectChatMessage{
		ID:           uuid.New(),
		ProjectID:    projectID,
		SenderID:     &senderID,
		SenderName:   input.SenderName,
		SenderRole:   input.SenderRole,
		Content:      strings.TrimSpace(input.Content),
		UrgencyLevel: urgency,
		IsPinned:     isPinned,
		IsResolved:   false,
		CreatedAt:    time.Now().UTC(),
	}
	if err := s.projectRepo.CreateChatMessage(ctx, msg); err != nil {
		return nil, err
	}
	return msg, nil
}

func (s *ProjectService) ResolveChatMessage(ctx context.Context, messageID uuid.UUID, resolvedBy string) error {
	return s.projectRepo.ResolveChatMessage(ctx, messageID, resolvedBy)
}

func (s *ProjectService) GetClientEmails(ctx context.Context, projectID uuid.UUID) ([]*domain.ClientEmailLog, error) {
	return s.projectRepo.ListClientEmails(ctx, projectID)
}

func (s *ProjectService) SendClientEventEmail(ctx context.Context, projectID uuid.UUID, eventType, subject string) (*domain.ClientEmailLog, error) {
	project, err := s.projectRepo.GetByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project.ClientEmail == nil || strings.TrimSpace(*project.ClientEmail) == "" {
		return nil, errors.New("project does not have a client email configured")
	}

	cEmail := strings.TrimSpace(*project.ClientEmail)
	cName := "Valued Client"
	if project.ClientContactPerson != nil && strings.TrimSpace(*project.ClientContactPerson) != "" {
		cName = strings.TrimSpace(*project.ClientContactPerson)
	}

	if strings.TrimSpace(subject) == "" {
		subject = fmt.Sprintf("VĀSTU Spatial Update: %s - %s", project.Name, eventType)
	}

	log := &domain.ClientEmailLog{
		ID:             uuid.New(),
		ProjectID:      project.ID,
		RecipientEmail: cEmail,
		RecipientName:  &cName,
		Subject:        subject,
		EmailType:      eventType,
		Status:         "sent",
		DispatchedAt:   time.Now().UTC(),
	}
	if err := s.projectRepo.LogClientEmail(ctx, log); err != nil {
		return nil, err
	}

	city := "India"
	if project.LocationCity != nil {
		city = *project.LocationCity
	}
	code := "PRJ"
	if project.ProjectCode != nil {
		code = *project.ProjectCode
	}

	siteInfo := fmt.Sprintf(`
		<div class="info-line"><strong>Project:</strong> %s (<code>%s</code>)</div>
		<div class="info-line"><strong>Event Notification:</strong> %s</div>
		<div class="info-line"><strong>Location:</strong> %s, %s</div>
		<div class="info-line"><strong>Measurement Accuracy:</strong> True-to-life 3D digital twin accurate within 1 inch (2.5 cm)</div>
	`, project.Name, code, eventType, city, project.LocationCountry)

	s.sendClientHTMLEmail(
		cEmail,
		cName,
		subject,
		fmt.Sprintf("Spatial Project Update: %s", project.Name),
		fmt.Sprintf("We have dispatched an automated operational update regarding <strong>%s</strong>.", project.Name),
		siteInfo,
	)

	return log, nil
}

func (s *ProjectService) ResendClientEmail(ctx context.Context, projectID, logID uuid.UUID) (*domain.ClientEmailLog, error) {
	project, err := s.projectRepo.GetByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project.ClientEmail == nil || strings.TrimSpace(*project.ClientEmail) == "" {
		return nil, errors.New("project does not have a client email configured")
	}

	cEmail := strings.TrimSpace(*project.ClientEmail)
	cName := "Valued Client"
	if project.ClientContactPerson != nil && strings.TrimSpace(*project.ClientContactPerson) != "" {
		cName = strings.TrimSpace(*project.ClientContactPerson)
	}

	code := "PRJ"
	if project.ProjectCode != nil {
		code = *project.ProjectCode
	}
	subject := fmt.Sprintf("RE-SENT: Spatial Update for %s (%s)", project.Name, code)

	log := &domain.ClientEmailLog{
		ID:             uuid.New(),
		ProjectID:      project.ID,
		RecipientEmail: cEmail,
		RecipientName:  &cName,
		Subject:        subject,
		EmailType:      "resend_notification",
		Status:         "sent",
		DispatchedAt:   time.Now().UTC(),
	}
	if err := s.projectRepo.LogClientEmail(ctx, log); err != nil {
		return nil, err
	}

	city := "India"
	if project.LocationCity != nil {
		city = *project.LocationCity
	}

	siteInfo := fmt.Sprintf(`
		<div class="info-line"><strong>Project:</strong> %s (<code>%s</code>)</div>
		<div class="info-line"><strong>Location:</strong> %s, %s</div>
		<div class="info-line"><strong>Measurement Accuracy:</strong> Accurate within 1 inch (2.5 cm) of reality</div>
	`, project.Name, code, city, project.LocationCountry)

	s.sendClientHTMLEmail(
		cEmail,
		cName,
		subject,
		fmt.Sprintf("Spatial Notification: %s", project.Name),
		fmt.Sprintf("This is a re-sent operational notification for your physical space digitization project <strong>%s</strong>.", project.Name),
		siteInfo,
	)

	return log, nil
}

func (s *ProjectService) sendClientHTMLEmail(toEmail, toName, subject, headline, messageBody, siteInfo string) {
	if s.mailer == nil || toEmail == "" {
		return
	}
	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #1a120b; color: #fdfbf7; padding: 20px; }
    .container { max-width: 580px; margin: 0 auto; background: #25180f; border-radius: 14px; border: 1px solid rgba(184, 138, 56, 0.4); padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .badge { display: inline-block; background: rgba(184, 138, 56, 0.2); color: #dfb873; border: 1px solid #b88a38; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-family: monospace; font-weight: bold; margin-bottom: 12px; }
    .header { font-size: 22px; font-weight: 700; color: #dfb873; letter-spacing: 0.5px; margin-bottom: 16px; }
    .info-card { background: rgba(0, 0, 0, 0.35); border-radius: 10px; border: 1px solid rgba(184, 138, 56, 0.25); padding: 16px; margin: 20px 0; }
    .info-line { font-size: 13px; color: #e6dfd5; margin: 6px 0; }
    .info-line strong { color: #ffffff; }
    .footer { font-size: 11px; color: #a89a8c; margin-top: 28px; text-align: center; border-top: 1px solid rgba(184, 138, 56, 0.2); padding-top: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">VĀSTU / NAMMA SPACE &bull; SPATIAL TWIN NOTIFICATION</div>
    <div class="header">%s</div>
    <p style="font-size: 15px; color: #fdfbf7;">Dear <strong>%s</strong>,</p>
    <p style="font-size: 13px; color: #e6dfd5; line-height: 1.6;">%s</p>
    
    <div class="info-card">
      %s
    </div>
    
    <p style="font-size: 13px; color: #e6dfd5;">Our spatial engineering team is active on your project workspace. Please contact your project lead if you have any questions.</p>
    
    <div class="footer">
      VĀSTU Physical Space Digitization Platform &bull; Automated Delivery
    </div>
  </div>
</body>
</html>`, headline, toName, messageBody, siteInfo)

	go func() {
		err := s.mailer.SendMail(toEmail, subject, strings.TrimSpace(htmlBody))
		if err != nil {
			fmt.Printf("[SMTP ERROR] Failed to deliver client email to %s: %v\n", toEmail, err)
		} else {
			fmt.Printf("[SMTP SUCCESS] Client email delivered to %s (Subject: %s)\n", toEmail, subject)
		}
	}()
}

// ------------------ Escalated Project Creation & Configuration ------------------

func (s *ProjectService) GetSupportedProjectTypes() []domain.ProjectTypeDefinition {
	return domain.SupportedProjectTypes
}

func (s *ProjectService) CreateProjectFull(ctx context.Context, orgID, userID uuid.UUID, input domain.ProjectCreationFullInput) (*domain.Project, error) {
	name := strings.TrimSpace(input.Name)
	if name == "" {
		return nil, errors.New("project name is required")
	}

	projectType := strings.TrimSpace(input.ProjectType)
	if projectType == "" {
		projectType = "Building"
	}

	contactName := strings.TrimSpace(input.ContactName)
	if contactName == "" {
		return nil, errors.New("contact person name is required")
	}
	contactPhone := strings.TrimSpace(input.ContactPhone)
	if contactPhone == "" {
		return nil, errors.New("contact phone number is required")
	}
	contactEmail := strings.TrimSpace(input.ContactEmail)
	if contactEmail == "" {
		return nil, errors.New("contact email is required")
	}

	// Structured Address Validation
	addrInput := input.Address
	if strings.TrimSpace(addrInput.AddressLine1) == "" {
		return nil, errors.New("address line 1 is required")
	}
	if strings.TrimSpace(addrInput.City) == "" {
		return nil, errors.New("city is required")
	}
	if strings.TrimSpace(addrInput.State) == "" {
		return nil, errors.New("state is required")
	}
	if strings.TrimSpace(addrInput.Pincode) == "" {
		return nil, errors.New("postal code / pincode is required")
	}

	// Floors Validation
	if len(input.Floors) == 0 {
		return nil, errors.New("at least one floor or section is required")
	}

	// Generate Server-Side UUIDs
	projectID := uuid.New()
	slug := utils.Slugify(name) + "-" + strings.ToLower(utils.RandomAlphaNum(4))
	projectCode := "PRJ-" + strings.ToUpper(utils.RandomAlphaNum(6))
	now := time.Now().UTC()

	status := domain.ProjectStatusDraft
	if input.Status != nil && *input.Status != "" {
		status = domain.ProjectStatus(*input.Status)
	}

	// Calculate total area
	totalAreaSqft := 0.0
	for _, f := range input.Floors {
		if f.AreaUnit == "SQM" {
			totalAreaSqft += f.AreaValue * 10.7639
		} else {
			totalAreaSqft += f.AreaValue
		}
	}
	totalAreaSqm := totalAreaSqft * 0.092903

	project := &domain.Project{
		ID:                  projectID,
		OrgID:               orgID,
		Name:                name,
		ProjectCode:         &projectCode,
		Slug:                slug,
		Description:         input.Description,
		Purpose:             nil,
		Priority:            "High",
		LocationCountry:     addrInput.Country,
		LocationState:       &addrInput.State,
		LocationCity:        &addrInput.City,
		LocationAddress:     &addrInput.AddressLine1,
		PostalCode:          &addrInput.Pincode,
		Latitude:            addrInput.Latitude,
		Longitude:           addrInput.Longitude,
		PrimaryContactName:  &contactName,
		PrimaryContactEmail: &contactEmail,
		PrimaryContactPhone: &contactPhone,
		ProjectAdminID:      &userID,
		AccessPolicy:        "assigned_only",
		CaptureMethod:       "Smartphone Video Capture",
		Typology:            domain.TypologyCommercial,
		TotalAreaSqft:       totalAreaSqft,
		TotalAreaSqm:        totalAreaSqm,
		TotalFloorsCount:    len(input.Floors),
		PrecisionGateCm:     2.0,
		Status:              status,
		CreatedBy:           &userID,
		CreatedAt:           now,
		UpdatedAt:           now,
		CoverImageID:        input.CoverImageID,
		CoverImageURL:       input.CoverImageURL,
		ContactName:         contactName,
		ContactEmail:        contactEmail,
		ContactPhone:        contactPhone,
		ProjectType:         projectType,
		CustomType:          input.CustomType,
	}

	if project.LocationCountry == "" {
		project.LocationCountry = "India"
	}

	if err := s.projectRepo.Create(ctx, project); err != nil {
		return nil, fmt.Errorf("failed to create project record: %w", err)
	}

	// Save Project Address
	addressID := uuid.New()
	addr := &domain.ProjectAddress{
		ID:           addressID,
		ProjectID:    projectID,
		AddressLine1: addrInput.AddressLine1,
		AddressLine2: addrInput.AddressLine2,
		Area:         addrInput.Area,
		City:         addrInput.City,
		State:        addrInput.State,
		Pincode:      addrInput.Pincode,
		Country:      addrInput.Country,
		Latitude:     addrInput.Latitude,
		Longitude:    addrInput.Longitude,
		PlaceID:      addrInput.PlaceID,
		CreatedAt:    now,
		UpdatedAt:    now,
	}
	if addr.Country == "" {
		addr.Country = "India"
	}
	if err := s.projectRepo.SaveAddress(ctx, addr); err != nil {
		fmt.Printf("[ProjectService] warning: saving address failed: %v\n", err)
	}
	project.Address = addr

	// Save Project Floors
	var createdFloors []*domain.ProjectFloor
	for idx, f := range input.Floors {
		floorName := strings.TrimSpace(f.Name)
		if floorName == "" {
			floorName = fmt.Sprintf("Floor %d", idx)
		}
		floorType := strings.TrimSpace(f.FloorType)
		if floorType == "" {
			floorType = "Typical Floor"
		}
		areaUnit := strings.ToUpper(strings.TrimSpace(f.AreaUnit))
		if areaUnit == "" {
			areaUnit = "SQFT"
		}
		heightUnit := strings.ToUpper(strings.TrimSpace(f.HeightUnit))
		if heightUnit == "" {
			heightUnit = "FT"
		}
		heightVal := f.HeightValue
		if heightVal <= 0 {
			heightVal = 10.0
		}
		seq := f.Sequence
		if seq <= 0 {
			seq = idx + 1
		}

		fl := &domain.ProjectFloor{
			ID:          uuid.New(),
			ProjectID:   projectID,
			Name:        floorName,
			FloorNumber: f.FloorNumber,
			FloorType:   floorType,
			AreaValue:   f.AreaValue,
			AreaUnit:    areaUnit,
			HeightValue: heightVal,
			HeightUnit:  heightUnit,
			Sequence:    seq,
			Description: f.Description,
			CreatedAt:   now,
			UpdatedAt:   now,
		}
		if err := s.projectRepo.CreateFloor(ctx, fl); err != nil {
			fmt.Printf("[ProjectService] warning: creating floor failed: %v\n", err)
		} else {
			createdFloors = append(createdFloors, fl)
		}
	}
	project.Floors = createdFloors

	// Assign Creator as Project Admin / Owner
	creatorMember := &domain.ProjectMember{
		ID:          uuid.New(),
		ProjectID:   projectID,
		UserID:      userID,
		ProjectRole: "Project Admin",
		Status:      "ACTIVE",
		AssignedBy:  &userID,
		AssignedAt:  now,
	}
	_ = s.projectRepo.AddProjectMember(ctx, creatorMember)

	// Assign other members
	var teamMembers []*domain.ProjectMember
	teamMembers = append(teamMembers, creatorMember)
	for _, m := range input.Members {
		if m.UserID == userID || m.UserID == uuid.Nil {
			continue
		}
		role := strings.TrimSpace(m.ProjectRole)
		if role == "" {
			role = "Viewer"
		}
		pm := &domain.ProjectMember{
			ID:          uuid.New(),
			ProjectID:   projectID,
			UserID:      m.UserID,
			ProjectRole: role,
			Status:      "ACTIVE",
			AssignedBy:  &userID,
			AssignedAt:  now,
		}
		if err := s.projectRepo.AddProjectMember(ctx, pm); err == nil {
			teamMembers = append(teamMembers, pm)
		}
	}
	project.Team = teamMembers

	// Log creation activity
	detailsStr := fmt.Sprintf("Created project '%s' (%s) with %d floors", name, projectType, len(createdFloors))
	_ = s.projectRepo.LogProjectActivity(ctx, &domain.ProjectActivityLog{
		ID:          uuid.New(),
		ProjectID:   projectID,
		ActorID:     &userID,
		ActorName:   contactName,
		ActorRole:   "Project Admin",
		ActionType:  "PROJECT_CREATED",
		ActionTitle: "Project Initialized",
		Details:     &detailsStr,
		CreatedAt:   now,
	})

	return project, nil
}

func (s *ProjectService) SaveProjectDraft(ctx context.Context, orgID, userID uuid.UUID, input domain.ProjectCreationFullInput) (*domain.Project, error) {
	name := strings.TrimSpace(input.Name)
	if name == "" {
		name = "Untitled Project (" + time.Now().Format("Jan 02 15:04") + ")"
	}
	input.Name = name
	draftStatus := "DRAFT"
	input.Status = &draftStatus

	if strings.TrimSpace(input.ContactName) == "" {
		input.ContactName = "Primary Contact"
	}
	if strings.TrimSpace(input.ContactEmail) == "" {
		input.ContactEmail = "contact@project.internal"
	}
	if strings.TrimSpace(input.ContactPhone) == "" {
		input.ContactPhone = "+910000000000"
	}
	if strings.TrimSpace(input.Address.AddressLine1) == "" {
		input.Address.AddressLine1 = "Draft Address"
	}
	if strings.TrimSpace(input.Address.City) == "" {
		input.Address.City = "Unassigned"
	}
	if strings.TrimSpace(input.Address.State) == "" {
		input.Address.State = "Unassigned"
	}
	if strings.TrimSpace(input.Address.Pincode) == "" {
		input.Address.Pincode = "000000"
	}
	if len(input.Floors) == 0 {
		input.Floors = []domain.CreateFloorInput{
			{Name: "Ground Floor", FloorNumber: 0, FloorType: "Ground Floor", AreaValue: 0, AreaUnit: "SQFT", HeightValue: 10, HeightUnit: "FT", Sequence: 1},
		}
	}

	return s.CreateProjectFull(ctx, orgID, userID, input)
}

func (s *ProjectService) GetProjectFull(ctx context.Context, projectID uuid.UUID) (*domain.Project, error) {
	p, err := s.projectRepo.GetByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	return p, nil
}

func (s *ProjectService) AddFloor(ctx context.Context, projectID uuid.UUID, input domain.CreateFloorInput) (*domain.ProjectFloor, error) {
	name := strings.TrimSpace(input.Name)
	if name == "" {
		return nil, errors.New("floor name is required")
	}
	floorType := strings.TrimSpace(input.FloorType)
	if floorType == "" {
		floorType = "Typical Floor"
	}
	areaUnit := strings.ToUpper(strings.TrimSpace(input.AreaUnit))
	if areaUnit == "" {
		areaUnit = "SQFT"
	}
	heightUnit := strings.ToUpper(strings.TrimSpace(input.HeightUnit))
	if heightUnit == "" {
		heightUnit = "FT"
	}
	heightVal := input.HeightValue
	if heightVal <= 0 {
		heightVal = 10.0
	}

	now := time.Now().UTC()
	fl := &domain.ProjectFloor{
		ID:          uuid.New(),
		ProjectID:   projectID,
		Name:        name,
		FloorNumber: input.FloorNumber,
		FloorType:   floorType,
		AreaValue:   input.AreaValue,
		AreaUnit:    areaUnit,
		HeightValue: heightVal,
		HeightUnit:  heightUnit,
		Sequence:    input.Sequence,
		Description: input.Description,
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := s.projectRepo.CreateFloor(ctx, fl); err != nil {
		return nil, err
	}
	return fl, nil
}

func (s *ProjectService) UpdateFloor(ctx context.Context, floorID uuid.UUID, input domain.UpdateFloorInput) (*domain.ProjectFloor, error) {
	existing, err := s.projectRepo.GetFloorByID(ctx, floorID)
	if err != nil {
		return nil, errors.New("floor not found")
	}

	if input.Name != nil && strings.TrimSpace(*input.Name) != "" {
		existing.Name = strings.TrimSpace(*input.Name)
	}
	if input.FloorNumber != nil {
		existing.FloorNumber = *input.FloorNumber
	}
	if input.FloorType != nil && strings.TrimSpace(*input.FloorType) != "" {
		existing.FloorType = strings.TrimSpace(*input.FloorType)
	}
	if input.AreaValue != nil {
		existing.AreaValue = *input.AreaValue
	}
	if input.AreaUnit != nil && strings.TrimSpace(*input.AreaUnit) != "" {
		existing.AreaUnit = strings.ToUpper(strings.TrimSpace(*input.AreaUnit))
	}
	if input.HeightValue != nil {
		existing.HeightValue = *input.HeightValue
	}
	if input.HeightUnit != nil && strings.TrimSpace(*input.HeightUnit) != "" {
		existing.HeightUnit = strings.ToUpper(strings.TrimSpace(*input.HeightUnit))
	}
	if input.Sequence != nil {
		existing.Sequence = *input.Sequence
	}
	if input.Description != nil {
		existing.Description = input.Description
	}

	if err := s.projectRepo.UpdateFloor(ctx, existing); err != nil {
		return nil, err
	}
	return existing, nil
}

func (s *ProjectService) DeleteFloor(ctx context.Context, floorID uuid.UUID) error {
	return s.projectRepo.DeleteFloor(ctx, floorID)
}

func (s *ProjectService) UploadFloorPlan(ctx context.Context, floorID uuid.UUID, fileID, fileURL, origName, mimeType string, fileSize int64) (*domain.FloorPlan, error) {
	now := time.Now().UTC()
	plan := &domain.FloorPlan{
		ID:               uuid.New(),
		FloorID:          floorID,
		PlanType:         "UPLOADED",
		FileID:           &fileID,
		FileURL:          &fileURL,
		OriginalFileName: &origName,
		FileSizeBytes:    fileSize,
		MimeType:         &mimeType,
		CanvasWidth:      1200,
		CanvasHeight:     800,
		ScaleRatio:       1.0,
		DrawingData:      []byte(`{"objects": []}`),
		PreviewFileID:    &fileID,
		PreviewURL:       &fileURL,
		CreatedAt:        now,
		UpdatedAt:        now,
	}

	if err := s.projectRepo.SaveFloorPlan(ctx, plan); err != nil {
		return nil, err
	}
	return plan, nil
}

func (s *ProjectService) DrawFloorPlan(ctx context.Context, floorID uuid.UUID, input domain.DrawFloorPlanInput, previewURL *string) (*domain.FloorPlan, error) {
	now := time.Now().UTC()
	w := input.CanvasWidth
	if w <= 0 {
		w = 1200
	}
	h := input.CanvasHeight
	if h <= 0 {
		h = 800
	}
	scale := input.ScaleRatio
	if scale <= 0 {
		scale = 1.0
	}

	drawingJSON := input.DrawingData
	if len(drawingJSON) == 0 {
		drawingJSON = []byte(`{"objects": []}`)
	}

	plan := &domain.FloorPlan{
		ID:           uuid.New(),
		FloorID:      floorID,
		PlanType:     "DRAWN",
		CanvasWidth:  w,
		CanvasHeight: h,
		ScaleRatio:   scale,
		DrawingData:  drawingJSON,
		PreviewURL:   previewURL,
		CreatedAt:    now,
		UpdatedAt:    now,
	}

	if err := s.projectRepo.SaveFloorPlan(ctx, plan); err != nil {
		return nil, err
	}
	return plan, nil
}

func (s *ProjectService) AssignMember(ctx context.Context, projectID uuid.UUID, input domain.AssignProjectMemberInput, assignedBy uuid.UUID) (*domain.ProjectMember, error) {
	if input.UserID == uuid.Nil {
		return nil, errors.New("valid user_id is required")
	}
	role := strings.TrimSpace(input.ProjectRole)
	if role == "" {
		role = "Viewer"
	}

	now := time.Now().UTC()
	member := &domain.ProjectMember{
		ID:          uuid.New(),
		ProjectID:   projectID,
		UserID:      input.UserID,
		ProjectRole: role,
		Permissions: []byte(`[]`),
		Status:      "ACTIVE",
		AssignedBy:  &assignedBy,
		AssignedAt:  now,
	}

	if err := s.projectRepo.AddProjectMember(ctx, member); err != nil {
		return nil, err
	}
	return member, nil
}

func (s *ProjectService) GetFloorPlan(ctx context.Context, floorID uuid.UUID) (*domain.FloorPlan, error) {
	return s.projectRepo.GetFloorPlanByFloorID(ctx, floorID)
}

func (s *ProjectService) DeleteFloorPlan(ctx context.Context, floorID uuid.UUID) error {
	return s.projectRepo.DeleteFloorPlan(ctx, floorID)
}

func (s *ProjectService) RemoveMember(ctx context.Context, projectID, userID uuid.UUID) error {
	return s.projectRepo.RemoveProjectMember(ctx, projectID, userID)
}




