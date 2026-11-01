package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

type SessionManagementHandler struct {
	sessionService *service.SessionManagerService
}

func NewSessionManagementHandler(sessionService *service.SessionManagerService) *SessionManagementHandler {
	return &SessionManagementHandler{sessionService: sessionService}
}

// ----------------------------------------------------
// Capture Sessions
// ----------------------------------------------------

func (h *SessionManagementHandler) CreateSession(w http.ResponseWriter, r *http.Request) {
	var input domain.CreateCaptureSessionInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	session, err := h.sessionService.CreateCaptureSession(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Capture session created successfully", session)
}

func (h *SessionManagementHandler) GetSession(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")
	if sessionID == "" {
		JSONError(w, http.StatusBadRequest, "sessionId is required")
		return
	}

	session, err := h.sessionService.GetSession(r.Context(), sessionID)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Session details retrieved", session)
}

func (h *SessionManagementHandler) ListSessions(w http.ResponseWriter, r *http.Request) {
	projectIDStr := r.URL.Query().Get("project_id")
	if projectIDStr != "" {
		projectID, err := uuid.Parse(projectIDStr)
		if err != nil {
			JSONError(w, http.StatusBadRequest, "Invalid project_id UUID")
			return
		}
		sessions, err := h.sessionService.ListSessionsByProject(r.Context(), projectID)
		if err != nil {
			JSONError(w, http.StatusInternalServerError, err.Error())
			return
		}
		JSONSuccess(w, http.StatusOK, "Sessions retrieved", sessions)
		return
	}

	sessions, err := h.sessionService.ListAllSessions(r.Context())
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}
	JSONSuccess(w, http.StatusOK, "Sessions retrieved", sessions)
}

func (h *SessionManagementHandler) RevokeSession(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")
	if sessionID == "" {
		JSONError(w, http.StatusBadRequest, "sessionId is required")
		return
	}

	if err := h.sessionService.RevokeSession(r.Context(), sessionID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Session revoked successfully", map[string]string{"session_id": sessionID, "status": "REVOKED"})
}

func (h *SessionManagementHandler) RedeemChallenge(w http.ResponseWriter, r *http.Request) {
	var input domain.RedeemChallengeInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid redemption JSON payload")
		return
	}

	resp, err := h.sessionService.RedeemChallenge(r.Context(), input)
	if err != nil {
		JSONError(w, http.StatusUnauthorized, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Session authorized for device capture", resp)
}

// ----------------------------------------------------
// Devices & Heartbeats
// ----------------------------------------------------

func (h *SessionManagementHandler) RecordHeartbeat(w http.ResponseWriter, r *http.Request) {
	var input domain.DeviceHeartbeatInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid heartbeat JSON payload")
		return
	}

	if input.DeviceUUID == "" {
		JSONError(w, http.StatusBadRequest, "device_uuid is required")
		return
	}

	if err := h.sessionService.ProcessHeartbeat(r.Context(), &input); err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Heartbeat acknowledged", map[string]bool{"acknowledged": true})
}

func (h *SessionManagementHandler) ListDevices(w http.ResponseWriter, r *http.Request) {
	devices, err := h.sessionService.ListConnectedDevices(r.Context())
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Connected devices retrieved", devices)
}

// ----------------------------------------------------
// Pipeline Stages & SSE Stream
// ----------------------------------------------------

func (h *SessionManagementHandler) GetPipelineStages(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")
	if sessionID == "" {
		JSONError(w, http.StatusBadRequest, "sessionId is required")
		return
	}

	stages, err := h.sessionService.GetPipelineStages(r.Context(), sessionID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Pipeline stages retrieved", stages)
}

func (h *SessionManagementHandler) UpdatePipelineStage(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")
	stageName := chi.URLParam(r, "stageName")
	if sessionID == "" || stageName == "" {
		JSONError(w, http.StatusBadRequest, "sessionId and stageName are required")
		return
	}

	var input domain.UpdatePipelineStageInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	stage, err := h.sessionService.UpdateStage(r.Context(), sessionID, stageName, input)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Pipeline stage updated", stage)
}

func (h *SessionManagementHandler) StreamPipelineEvents(w http.ResponseWriter, r *http.Request) {
	sessionID := chi.URLParam(r, "sessionId")
	if sessionID == "" {
		http.Error(w, "sessionId is required", http.StatusBadRequest)
		return
	}

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	// Subscribe to live stage updates
	eventsChan, unsubscribe := h.sessionService.SubscribeStages(sessionID)
	defer unsubscribe()

	// Initial ping
	fmt.Fprintf(w, "event: connected\ndata: {\"session_id\": \"%s\", \"time\": \"%s\"}\n\n", sessionID, time.Now().Format(time.RFC3339))
	flusher.Flush()

	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	notify := r.Context().Done()
	for {
		select {
		case <-notify:
			return
		case <-ticker.C:
			// Keepalive comment
			fmt.Fprintf(w, ": keepalive\n\n")
			flusher.Flush()
		case stageRecord, ok := <-eventsChan:
			if !ok {
				return
			}
			stageBytes, _ := json.Marshal(stageRecord)
			fmt.Fprintf(w, "event: stage_update\ndata: %s\n\n", string(stageBytes))
			flusher.Flush()
		}
	}
}

// ----------------------------------------------------
// Room Mapping
// ----------------------------------------------------

func (h *SessionManagementHandler) ListRooms(w http.ResponseWriter, r *http.Request) {
	projectIDStr := chi.URLParam(r, "projectId")
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid project ID UUID")
		return
	}

	rooms, err := h.sessionService.ListRoomsByProject(r.Context(), projectID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Rooms retrieved", rooms)
}

func (h *SessionManagementHandler) CreateRoom(w http.ResponseWriter, r *http.Request) {
	floorIDStr := chi.URLParam(r, "floorId")
	floorID, err := uuid.Parse(floorIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid floor ID UUID")
		return
	}

	var input domain.CreateRoomInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid room JSON payload")
		return
	}

	room, err := h.sessionService.CreateRoom(r.Context(), floorID, input)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Room created successfully", room)
}

