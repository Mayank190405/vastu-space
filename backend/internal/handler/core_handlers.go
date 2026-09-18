package handler

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

// ==========================================
// 1. Captures Handler
// ==========================================

type CaptureHandler struct {
	captureService *service.CaptureService
}

func NewCaptureHandler(captureService *service.CaptureService) *CaptureHandler {
	return &CaptureHandler{captureService: captureService}
}

func (h *CaptureHandler) Create(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.CreateCaptureInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	capture, err := h.captureService.CreateCapture(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Capture session initiated", capture)
}

func (h *CaptureHandler) Get(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid capture id")
		return
	}

	capture, err := h.captureService.GetCapture(r.Context(), id)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Capture retrieved", capture)
}

func (h *CaptureHandler) ListByProject(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	list, err := h.captureService.ListCapturesByProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Captures list retrieved", list)
}

func (h *CaptureHandler) UpdateStatus(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid capture id")
		return
	}

	var input domain.UpdateCaptureStatusInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	updated, err := h.captureService.UpdateCaptureStatus(r.Context(), id, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Capture status updated", updated)
}

// ==========================================
// 2. Uploads Handler
// ==========================================

type UploadHandler struct {
	uploadService *service.UploadService
}

func NewUploadHandler(uploadService *service.UploadService) *UploadHandler {
	return &UploadHandler{uploadService: uploadService}
}

func (h *UploadHandler) Init(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.InitUploadInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	session, err := h.uploadService.InitSession(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Upload session initiated", session)
}

func (h *UploadHandler) UploadChunk(w http.ResponseWriter, r *http.Request) {
	sessionIDStr := chi.URLParam(r, "sessionId")
	sessionID, err := uuid.Parse(sessionIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid session id")
		return
	}

	chunkIndexStr := chi.URLParam(r, "chunkIndex")
	chunkIndex, err := strconv.Atoi(chunkIndexStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid chunk index")
		return
	}

	chunkChecksum := r.Header.Get("X-Chunk-SHA256")

	// Support raw body stream or multipart file
	var reader = r.Body
	if strings.HasPrefix(r.Header.Get("Content-Type"), "multipart/form-data") {
		if err := r.ParseMultipartForm(15 << 20); err == nil {
			file, _, err := r.FormFile("chunk")
			if err == nil {
				defer file.Close()
				reader = file
			}
		}
	}

	chunk, err := h.uploadService.SaveChunk(r.Context(), sessionID, chunkIndex, chunkChecksum, reader)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Chunk uploaded successfully", chunk)
}

func (h *UploadHandler) GetProgress(w http.ResponseWriter, r *http.Request) {
	sessionIDStr := chi.URLParam(r, "sessionId")
	sessionID, err := uuid.Parse(sessionIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid session id")
		return
	}

	progress, err := h.uploadService.GetProgress(r.Context(), sessionID)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Upload progress retrieved", progress)
}

func (h *UploadHandler) Complete(w http.ResponseWriter, r *http.Request) {
	sessionIDStr := chi.URLParam(r, "sessionId")
	sessionID, err := uuid.Parse(sessionIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid session id")
		return
	}

	var input domain.CompleteUploadInput
	if r.Body != nil {
		_ = json.NewDecoder(r.Body).Decode(&input)
	}
	var checksum string
	if input.FinalChecksumSHA256 != nil && *input.FinalChecksumSHA256 != "" {
		checksum = *input.FinalChecksumSHA256
	}

	fileURL, err := h.uploadService.CompleteUpload(r.Context(), sessionID, checksum)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Upload finalized and verified successfully", map[string]string{
		"file_url": fileURL,
	})
}

// ==========================================
// 3. Jobs Handler
// ==========================================

type JobHandler struct {
	jobService *service.JobService
}

func NewJobHandler(jobService *service.JobService) *JobHandler {
	return &JobHandler{jobService: jobService}
}

func (h *JobHandler) Create(w http.ResponseWriter, r *http.Request) {
	var input domain.CreateJobInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	job, err := h.jobService.CreateJob(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Processing job created", job)
}

func (h *JobHandler) Get(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid job id")
		return
	}

	job, err := h.jobService.GetJob(r.Context(), id)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Job details retrieved", job)
}

func (h *JobHandler) ListByProject(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	jobs, err := h.jobService.ListJobsByProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Jobs retrieved", jobs)
}

func (h *JobHandler) UpdateProgress(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid job id")
		return
	}

	var input domain.UpdateJobProgressInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	updated, err := h.jobService.UpdateProgress(r.Context(), id, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Job progress updated", updated)
}

func (h *JobHandler) AddLog(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid job id")
		return
	}

	var input struct {
		Stage   string                 `json:"stage"`
		Level   string                 `json:"level"`
		Message string                 `json:"message"`
		Meta    map[string]interface{} `json:"meta"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	if err := h.jobService.AddLog(r.Context(), id, input.Stage, input.Level, input.Message, input.Meta); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Log appended successfully", nil)
}

func (h *JobHandler) GetLogs(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid job id")
		return
	}

	logs, err := h.jobService.GetLogs(r.Context(), id)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Job logs retrieved", logs)
}

// ==========================================
// 4. Models Handler
// ==========================================

type ModelHandler struct {
	modelService *service.ModelService
}

func NewModelHandler(modelService *service.ModelService) *ModelHandler {
	return &ModelHandler{modelService: modelService}
}

func (h *ModelHandler) Create(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.CreateModelInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	model, err := h.modelService.CreateModel(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Spatial model registered", model)
}

func (h *ModelHandler) Get(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid model id")
		return
	}

	model, err := h.modelService.GetModel(r.Context(), id)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Model retrieved", model)
}

func (h *ModelHandler) GetActive(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	model, err := h.modelService.GetActiveModel(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Active model retrieved", model)
}

func (h *ModelHandler) ListByProject(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	models, err := h.modelService.ListModelsByProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Models retrieved", models)
}

func (h *ModelHandler) AddArtifact(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid model id")
		return
	}

	var input domain.CreateArtifactInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	artifact, err := h.modelService.AddArtifact(r.Context(), id, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Artifact added to model", artifact)
}

// ==========================================
// 5. POIs Handler
// ==========================================

type POIHandler struct {
	poiService *service.POIService
}

func NewPOIHandler(poiService *service.POIService) *POIHandler {
	return &POIHandler{poiService: poiService}
}

func (h *POIHandler) Create(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.CreatePOIInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	poi, err := h.poiService.CreatePOI(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "POI created successfully", poi)
}

func (h *POIHandler) Get(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid poi id")
		return
	}

	poi, err := h.poiService.GetPOI(r.Context(), id)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "POI retrieved", poi)
}

func (h *POIHandler) ListByProject(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	pois, err := h.poiService.ListPOIsByProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "POIs retrieved", pois)
}

func (h *POIHandler) Update(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid poi id")
		return
	}

	var input domain.UpdatePOIInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	updated, err := h.poiService.UpdatePOI(r.Context(), id, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "POI updated", updated)
}

func (h *POIHandler) Delete(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid poi id")
		return
	}

	if err := h.poiService.DeletePOI(r.Context(), id); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "POI deleted successfully", nil)
}

// ==========================================
// 6. Search Handler
// ==========================================

type SearchHandler struct {
	searchService *service.SearchService
}

func NewSearchHandler(searchService *service.SearchService) *SearchHandler {
	return &SearchHandler{searchService: searchService}
}

func (h *SearchHandler) SearchSpatial(w http.ResponseWriter, r *http.Request) {
	var query domain.SpatialSearchQuery
	if err := json.NewDecoder(r.Body).Decode(&query); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid search query payload")
		return
	}

	results, err := h.searchService.SearchSpatial(r.Context(), query)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Spatial search results", results)
}

// ==========================================
// 7. Navigation Handler
// ==========================================

type NavigationHandler struct {
	navService *service.NavigationService
}

func NewNavigationHandler(navService *service.NavigationService) *NavigationHandler {
	return &NavigationHandler{navService: navService}
}

func (h *NavigationHandler) CreateNode(w http.ResponseWriter, r *http.Request) {
	var node domain.NavNode
	if err := json.NewDecoder(r.Body).Decode(&node); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	if err := h.navService.CreateNode(r.Context(), &node); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Navigation node created", node)
}

func (h *NavigationHandler) ListNodes(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	nodes, err := h.navService.ListNodes(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Navigation nodes retrieved", nodes)
}

func (h *NavigationHandler) CreateEdge(w http.ResponseWriter, r *http.Request) {
	var edge domain.NavEdge
	if err := json.NewDecoder(r.Body).Decode(&edge); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	if err := h.navService.CreateEdge(r.Context(), &edge); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Navigation edge created", edge)
}

func (h *NavigationHandler) ListEdges(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	edges, err := h.navService.ListEdges(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Navigation edges retrieved", edges)
}

func (h *NavigationHandler) CalculateRoute(w http.ResponseWriter, r *http.Request) {
	var req domain.NavRouteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid route request payload")
		return
	}

	route, err := h.navService.CalculateRoute(r.Context(), req)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Navigation route calculated", route)
}

// ==========================================
// 8. Viewer Handler
// ==========================================

type ViewerHandler struct {
	viewerService *service.ViewerService
}

func NewViewerHandler(viewerService *service.ViewerService) *ViewerHandler {
	return &ViewerHandler{viewerService: viewerService}
}

func (h *ViewerHandler) CreateBookmark(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.CreateBookmarkInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	bookmark, err := h.viewerService.CreateBookmark(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Camera bookmark saved", bookmark)
}

func (h *ViewerHandler) ListBookmarks(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	bookmarks, err := h.viewerService.ListBookmarks(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Camera bookmarks retrieved", bookmarks)
}

func (h *ViewerHandler) DeleteBookmark(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid bookmark id")
		return
	}

	if err := h.viewerService.DeleteBookmark(r.Context(), id); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Camera bookmark deleted", nil)
}

func (h *ViewerHandler) CreateAnnotation(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input domain.CreateAnnotationInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	annotation, err := h.viewerService.CreateAnnotation(r.Context(), claims.UserID, input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Viewer annotation created", annotation)
}

func (h *ViewerHandler) ListAnnotations(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	annotations, err := h.viewerService.ListAnnotations(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Viewer annotations retrieved", annotations)
}

func (h *ViewerHandler) DeleteAnnotation(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid annotation id")
		return
	}

	if err := h.viewerService.DeleteAnnotation(r.Context(), id); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Viewer annotation deleted", nil)
}

// ==========================================
// 14. Rescan Requests Handler
// ==========================================

type RescanHandler struct {
	rescanService *service.RescanService
}

func NewRescanHandler(rescanService *service.RescanService) *RescanHandler {
	return &RescanHandler{rescanService: rescanService}
}

func (h *RescanHandler) Create(w http.ResponseWriter, r *http.Request) {
	var input service.CreateRescanRequestInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	rescanReq, err := h.rescanService.CreateRequest(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Rescan request created", rescanReq)
}

func (h *RescanHandler) ListPending(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid project id")
		return
	}

	list, err := h.rescanService.ListPendingRequests(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Pending rescan requests retrieved", list)
}

type UpdateRescanStatusInput struct {
	Status    string     `json:"status"`
	CaptureID *uuid.UUID `json:"capture_id,omitempty"`
}

func (h *RescanHandler) UpdateStatus(w http.ResponseWriter, r *http.Request) {
	idStr := chi.URLParam(r, "id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid rescan request id")
		return
	}

	var input UpdateRescanStatusInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request payload")
		return
	}

	if err := h.rescanService.UpdateStatus(r.Context(), id, input.Status, input.CaptureID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Rescan request status updated", nil)
}

