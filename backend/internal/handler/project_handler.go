package handler

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

type ProjectHandler struct {
	projectService *service.ProjectService
	uploadDir      string
}

func NewProjectHandler(projectService *service.ProjectService, uploadDir string) *ProjectHandler {
	_ = os.MkdirAll(uploadDir, 0755)
	return &ProjectHandler{
		projectService: projectService,
		uploadDir:      uploadDir,
	}
}

// GET /api/v1/projects/types
func (h *ProjectHandler) GetProjectTypes(w http.ResponseWriter, r *http.Request) {
	types := h.projectService.GetSupportedProjectTypes()
	JSONSuccess(w, http.StatusOK, "Supported project types retrieved", types)
}

// POST /api/v1/projects (Protected)
func (h *ProjectHandler) Create(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if claims.OrgID == nil {
		JSONError(w, http.StatusBadRequest, "active organization context required")
		return
	}

	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "failed to read request body")
		return
	}

	// Try detecting if it's the full creation input
	var fullInput domain.ProjectCreationFullInput
	if err := json.Unmarshal(bodyBytes, &fullInput); err == nil && (fullInput.Address.AddressLine1 != "" || len(fullInput.Floors) > 0 || fullInput.ContactEmail != "") {
		project, err := h.projectService.CreateProjectFull(r.Context(), *claims.OrgID, claims.UserID, fullInput)
		if err != nil {
			JSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		JSONSuccess(w, http.StatusCreated, "Project created successfully", project)
		return
	}

	// Fallback to legacy CreateProjectInput
	var legacyInput domain.CreateProjectInput
	if err := json.Unmarshal(bodyBytes, &legacyInput); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	project, err := h.projectService.CreateProject(r.Context(), *claims.OrgID, claims.UserID, legacyInput)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Project created successfully", project)
}

// GET /api/v1/projects (Protected)
func (h *ProjectHandler) List(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if claims.OrgID == nil {
		JSONError(w, http.StatusBadRequest, "active organization context required")
		return
	}

	projects, err := h.projectService.ListProjects(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Projects retrieved", projects)
}

// GET /api/v1/projects/trash (Protected)
func (h *ProjectHandler) ListTrash(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if claims.OrgID == nil {
		JSONError(w, http.StatusBadRequest, "active organization context required")
		return
	}

	projects, err := h.projectService.ListTrashProjects(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Trash projects retrieved (30-day recovery active)", projects)
}

// GET /api/v1/projects/{projectId} (Protected)
func (h *ProjectHandler) Get(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	project, err := h.projectService.GetProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	JSONSuccess(w, http.StatusOK, "Project details retrieved", project)
}

// PUT /api/v1/projects/{projectId} (Protected)
func (h *ProjectHandler) Update(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	var input domain.UpdateProjectInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	project, err := h.projectService.UpdateProject(r.Context(), projectID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project updated successfully", project)
}

// DELETE /api/v1/projects/{projectId} (Soft Delete - 30 days recovery)
func (h *ProjectHandler) SoftDelete(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	if err := h.projectService.SoftDeleteProject(r.Context(), projectID); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project moved to trash (recoverable up to 30 days)", nil)
}

// POST /api/v1/projects/{projectId}/restore (Restore from Trash)
func (h *ProjectHandler) Restore(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	if err := h.projectService.RestoreProject(r.Context(), projectID); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project restored successfully", nil)
}

// DELETE /api/v1/projects/{projectId}/permanent (Permanent Delete)
func (h *ProjectHandler) PermanentDelete(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	if err := h.projectService.PermanentDeleteProject(r.Context(), projectID); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project permanently deleted", nil)
}

// DELETE /api/v1/projects/{projectId}/archive (Protected)
func (h *ProjectHandler) Archive(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	if err := h.projectService.ArchiveProject(r.Context(), projectID); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project archived", nil)
}

// GET /api/v1/projects/{projectId}/timeline
func (h *ProjectHandler) GetTimeline(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	events, err := h.projectService.GetTimeline(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Timeline events retrieved", events)
}

// POST /api/v1/projects/{projectId}/timeline/{eventId}/comments
func (h *ProjectHandler) AddTimelineComment(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	eventIDStr := chi.URLParam(r, "eventId")
	eventID, err := uuid.Parse(eventIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid event id")
		return
	}

	var input domain.CreateCommentInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	comment, err := h.projectService.AddTimelineComment(r.Context(), projectID, eventID, claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Comment added to timeline event", comment)
}

// PUT /api/v1/projects/{projectId}/timeline/{eventId}/status
func (h *ProjectHandler) UpdateTimelineEventStatus(w http.ResponseWriter, r *http.Request) {
	claims, _ := middleware.GetClaimsFromContext(r.Context())

	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	eventIDStr := chi.URLParam(r, "eventId")
	eventID, err := uuid.Parse(eventIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid event id")
		return
	}

	var input struct {
		Status    string `json:"status"`
		ActorName string `json:"actor_name"`
		ActorRole string `json:"actor_role"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil || input.Status == "" {
		JSONError(w, http.StatusBadRequest, "status is required")
		return
	}

	actorName := "Admin"
	if input.ActorName != "" {
		actorName = input.ActorName
	}
	actorRole := "Operations Lead"
	if input.ActorRole != "" {
		actorRole = input.ActorRole
	}

	var actorID *uuid.UUID
	if claims != nil {
		actorID = &claims.UserID
	}

	if err := h.projectService.UpdateTimelineEventStatus(r.Context(), projectID, eventID, input.Status, actorName, actorRole, actorID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Timeline milestone status updated", map[string]string{"status": input.Status})
}



// GET /api/v1/projects/{projectId}/chat
func (h *ProjectHandler) GetChat(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	messages, err := h.projectService.GetChatMessages(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Chat messages retrieved", messages)
}

// POST /api/v1/projects/{projectId}/chat
func (h *ProjectHandler) SendMessage(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	var input domain.SendChatMessageInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	msg, err := h.projectService.SendChatMessage(r.Context(), projectID, claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Message sent successfully", msg)
}

// POST /api/v1/projects/{projectId}/chat/{messageId}/resolve
func (h *ProjectHandler) ResolveMessage(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	messageIDStr := chi.URLParam(r, "messageId")
	messageID, err := uuid.Parse(messageIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid message id")
		return
	}

	resolvedBy := claims.Email
	if resolvedBy == "" {
		resolvedBy = "Project Admin"
	}

	if err := h.projectService.ResolveChatMessage(r.Context(), messageID, resolvedBy); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Urgent message marked as resolved", nil)
}

// GET /api/v1/projects/{projectId}/client-emails
func (h *ProjectHandler) GetClientEmails(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	logs, err := h.projectService.GetClientEmails(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Client emails retrieved", logs)
}

// POST /api/v1/projects/{projectId}/client-emails/send
func (h *ProjectHandler) SendClientEmail(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	var input struct {
		EventType string `json:"event_type"`
		Subject   string `json:"subject"`
	}
	_ = json.NewDecoder(r.Body).Decode(&input)

	log, err := h.projectService.SendClientEventEmail(r.Context(), projectID, input.EventType, input.Subject)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Email update dispatched to client", log)
}

// POST /api/v1/projects/{projectId}/client-emails/{logId}/resend
func (h *ProjectHandler) ResendClientEmail(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	logIDStr := chi.URLParam(r, "logId")
	logID, _ := uuid.Parse(logIDStr)

	log, err := h.projectService.ResendClientEmail(r.Context(), projectID, logID)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Email re-sent to client successfully", log)
}

// GET /api/v1/projects/{projectId}/activities
func (h *ProjectHandler) GetActivities(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	activities, err := h.projectService.GetProjectActivities(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project activities retrieved", activities)
}

// POST /api/v1/projects/create-full (Protected)
func (h *ProjectHandler) CreateFull(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if claims.OrgID == nil {
		JSONError(w, http.StatusBadRequest, "active organization context required")
		return
	}

	var input domain.ProjectCreationFullInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	project, err := h.projectService.CreateProjectFull(r.Context(), *claims.OrgID, claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Project created successfully", project)
}

// POST /api/v1/projects/draft (Protected)
func (h *ProjectHandler) SaveDraft(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if claims.OrgID == nil {
		JSONError(w, http.StatusBadRequest, "active organization context required")
		return
	}

	var input domain.ProjectCreationFullInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	project, err := h.projectService.SaveProjectDraft(r.Context(), *claims.OrgID, claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Project draft saved successfully", project)
}

// POST /api/v1/projects/cover-image (Protected)
func (h *ProjectHandler) UploadCoverImage(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseMultipartForm(15 << 20); err != nil {
		JSONError(w, http.StatusBadRequest, "file too large (max 15MB)")
		return
	}

	file, header, err := r.FormFile("cover_image")
	if err != nil {
		file, header, err = r.FormFile("file")
	}
	if err != nil {
		JSONError(w, http.StatusBadRequest, "cover_image file is required")
		return
	}
	defer file.Close()

	ext := strings.ToLower(filepath.Ext(header.Filename))
	if ext != ".png" && ext != ".jpg" && ext != ".jpeg" && ext != ".webp" {
		JSONError(w, http.StatusBadRequest, "cover image must be PNG, JPG, JPEG, or WEBP")
		return
	}

	fileID := fmt.Sprintf("proj_cover_%d_%s%s", time.Now().UnixNano(), uuid.New().String()[:8], ext)
	dstPath := filepath.Join(h.uploadDir, fileID)

	dst, err := os.Create(dstPath)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to save cover image")
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to write cover image")
		return
	}

	coverURL := "/uploads/" + fileID
	JSONSuccess(w, http.StatusCreated, "Cover image uploaded successfully", map[string]interface{}{
		"cover_image_id":  fileID,
		"cover_image_url": coverURL,
	})
}

// GET /api/v1/projects/{projectId}/full (Protected)
func (h *ProjectHandler) GetFull(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	project, err := h.projectService.GetProjectFull(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	JSONSuccess(w, http.StatusOK, "Full project retrieved", project)
}

// POST /api/v1/projects/{projectId}/floors (Protected)
func (h *ProjectHandler) AddFloor(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	var input domain.CreateFloorInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor input: "+err.Error())
		return
	}

	floor, err := h.projectService.AddFloor(r.Context(), projectID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Floor added successfully", floor)
}

// GET /api/v1/projects/{projectId}/floors (Protected)
func (h *ProjectHandler) ListFloors(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	p, err := h.projectService.GetProjectFull(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	JSONSuccess(w, http.StatusOK, "Floors retrieved", p.Floors)
}

// PUT /api/v1/projects/{projectId}/floors/{floorId} (Protected)
func (h *ProjectHandler) UpdateFloor(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	var input domain.UpdateFloorInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor update: "+err.Error())
		return
	}

	floor, err := h.projectService.UpdateFloor(r.Context(), floorID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Floor updated successfully", floor)
}

// DELETE /api/v1/projects/{projectId}/floors/{floorId} (Protected)
func (h *ProjectHandler) DeleteFloor(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	if err := h.projectService.DeleteFloor(r.Context(), floorID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Floor deleted successfully", nil)
}

// POST /api/v1/projects/{projectId}/floors/{floorId}/floor-plan/upload (Protected)
func (h *ProjectHandler) UploadFloorPlan(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	if err := r.ParseMultipartForm(50 << 20); err != nil {
		JSONError(w, http.StatusBadRequest, "file too large (max 50MB)")
		return
	}

	file, header, err := r.FormFile("floor_plan")
	if err != nil {
		file, header, err = r.FormFile("file")
	}
	if err != nil {
		JSONError(w, http.StatusBadRequest, "floor plan file is required")
		return
	}
	defer file.Close()

	ext := strings.ToLower(filepath.Ext(header.Filename))
	if ext != ".png" && ext != ".jpg" && ext != ".jpeg" && ext != ".pdf" {
		JSONError(w, http.StatusBadRequest, "floor plan must be PNG, JPG, JPEG, or PDF")
		return
	}

	fileID := fmt.Sprintf("plan_%d_%s%s", time.Now().UnixNano(), uuid.New().String()[:8], ext)
	dstPath := filepath.Join(h.uploadDir, fileID)

	dst, err := os.Create(dstPath)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to save floor plan file")
		return
	}
	defer dst.Close()

	size, err := io.Copy(dst, file)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to write floor plan file")
		return
	}

	fileURL := "/uploads/" + fileID
	mimeType := header.Header.Get("Content-Type")
	if mimeType == "" {
		mimeType = "application/octet-stream"
	}

	plan, err := h.projectService.UploadFloorPlan(r.Context(), floorID, fileID, fileURL, header.Filename, mimeType, size)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Floor plan uploaded successfully", plan)
}

// POST /api/v1/projects/{projectId}/floors/{floorId}/floor-plan/draw (Protected)
func (h *ProjectHandler) DrawFloorPlan(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	var input domain.DrawFloorPlanInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid drawing data: "+err.Error())
		return
	}

	var previewURL *string
	if input.PreviewBase64 != nil && *input.PreviewBase64 != "" {
		base64Str := *input.PreviewBase64
		if idx := strings.Index(base64Str, ","); idx != -1 {
			base64Str = base64Str[idx+1:]
		}
		imgBytes, decErr := base64.StdEncoding.DecodeString(base64Str)
		if decErr == nil && len(imgBytes) > 0 {
			prevFileID := fmt.Sprintf("plan_preview_%d_%s.png", time.Now().UnixNano(), uuid.New().String()[:8])
			prevPath := filepath.Join(h.uploadDir, prevFileID)
			if err := os.WriteFile(prevPath, imgBytes, 0644); err == nil {
				url := "/uploads/" + prevFileID
				previewURL = &url
			}
		}
	}

	plan, err := h.projectService.DrawFloorPlan(r.Context(), floorID, input, previewURL)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Floor plan drawing saved successfully", plan)
}

// GET /api/v1/projects/{projectId}/floors/{floorId}/floor-plan (Protected)
func (h *ProjectHandler) GetFloorPlan(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	plan, err := h.projectService.GetFloorPlan(r.Context(), floorID)
	if err != nil || plan == nil {
		JSONError(w, http.StatusNotFound, "floor plan not found for this floor")
		return
	}

	JSONSuccess(w, http.StatusOK, "Floor plan retrieved", plan)
}

// DELETE /api/v1/projects/{projectId}/floors/{floorId}/floor-plan (Protected)
func (h *ProjectHandler) DeleteFloorPlan(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid floor id")
		return
	}

	if err := h.projectService.DeleteFloorPlan(r.Context(), floorID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Floor plan deleted successfully", nil)
}

// GET /api/v1/projects/{projectId}/members (Protected)
func (h *ProjectHandler) ListMembers(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	p, err := h.projectService.GetProjectFull(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	JSONSuccess(w, http.StatusOK, "Project members retrieved", p.Team)
}

// POST /api/v1/projects/{projectId}/members (Protected)
func (h *ProjectHandler) AddMember(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	var input domain.AssignProjectMemberInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid member input: "+err.Error())
		return
	}

	member, err := h.projectService.AssignMember(r.Context(), projectID, input, claims.UserID)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Project member assigned successfully", member)
}

// DELETE /api/v1/projects/{projectId}/members/{userId} (Protected)
func (h *ProjectHandler) RemoveMember(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	userIDStr := chi.URLParam(r, "userId")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid user id")
		return
	}

	if err := h.projectService.RemoveMember(r.Context(), projectID, userID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Project member removed successfully", nil)
}

// GET /api/v1/projects/{projectId}/render
func (h *ProjectHandler) GetRender(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	_, err = h.projectService.GetProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	summaryPath := filepath.Join(h.uploadDir, "renders", projectID.String(), "digital_twin_summary.json")
	var summaryData map[string]interface{}
	data, err := os.ReadFile(summaryPath)
	if err != nil {
		JSONError(w, http.StatusNotFound, "reconstruction digital twin render not found for this project")
		return
	}
	if err := json.Unmarshal(data, &summaryData); err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to parse digital twin summary")
		return
	}

	JSONSuccess(w, http.StatusOK, "Digital twin render retrieved", summaryData)
}

// GET /api/v1/projects/{projectId}/view-link
func (h *ProjectHandler) GetViewingLink(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	project, err := h.projectService.GetProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "project not found")
		return
	}

	viewingURL := fmt.Sprintf("/view/%s", projectID.String())
	JSONSuccess(w, http.StatusOK, "Viewing link generated", map[string]interface{}{
		"project_id":   projectID.String(),
		"project_name": project.Name,
		"project_code": project.ProjectCode,
		"viewing_url":  viewingURL,
		"status":       "ACTIVE",
	})
}
