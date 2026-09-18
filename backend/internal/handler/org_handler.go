package handler

import (
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

type OrgHandler struct {
	orgService *service.OrgService
	uploadDir  string
}

func NewOrgHandler(orgService *service.OrgService, uploadDir string) *OrgHandler {
	_ = os.MkdirAll(uploadDir, 0755)
	return &OrgHandler{
		orgService: orgService,
		uploadDir:  uploadDir,
	}
}

// GET /api/v1/organizations/me
func (h *OrgHandler) GetMyOrg(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "no active organization in session")
		return
	}

	org, err := h.orgService.GetOrgByID(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusNotFound, "organization not found")
		return
	}

	addr, _ := h.orgService.GetOrgAddress(r.Context(), *claims.OrgID)
	docs, _ := h.orgService.ListDocuments(r.Context(), *claims.OrgID)
	members, _ := h.orgService.ListMembers(r.Context(), *claims.OrgID)

	JSONSuccess(w, http.StatusOK, "Organization profile retrieved", map[string]interface{}{
		"organization": org,
		"address":      addr,
		"documents":    docs,
		"members_count": len(members),
		"role":          claims.MemberRole,
	})
}

// PATCH /api/v1/organizations/me or /api/v1/organizations/me/details
func (h *OrgHandler) UpdateOrgDetails(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var updates map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&updates); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	org, err := h.orgService.UpdateOrgDetails(r.Context(), *claims.OrgID, updates)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Organization details updated successfully", org)
}

// PATCH /api/v1/organizations/me/contact
func (h *OrgHandler) UpdateOrgContact(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input struct {
		OfficialEmail  string `json:"official_email"`
		OfficialPhone  string `json:"official_phone"`
		AlternatePhone string `json:"alternate_phone"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	org, err := h.orgService.UpdateOrgContact(r.Context(), *claims.OrgID, input.OfficialEmail, input.OfficialPhone, input.AlternatePhone)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Organization contact information updated", org)
}

// PATCH /api/v1/organizations/me/address
func (h *OrgHandler) UpdateOrgAddress(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var addr domain.OrganizationAddress
	if err := json.NewDecoder(r.Body).Decode(&addr); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	res, err := h.orgService.UpdateOrgAddress(r.Context(), *claims.OrgID, &addr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Organization address updated successfully", res)
}

// POST /api/v1/organizations/me/gst and /api/v1/organizations/me/gst/verify
func (h *OrgHandler) AddOrVerifyGST(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var input struct {
		GSTIN string `json:"gstin"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	ident, err := h.orgService.AddGSTIdentifier(r.Context(), *claims.OrgID, input.GSTIN)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "GSTIN verified and linked successfully", ident)
}

// POST /api/v1/organizations/me/documents
func (h *OrgHandler) UploadDocument(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	if err := r.ParseMultipartForm(15 << 20); err != nil {
		JSONError(w, http.StatusBadRequest, "file size exceeds limit")
		return
	}

	docType := r.FormValue("document_type")
	if docType == "" {
		docType = "Registration Document"
	}

	file, header, err := r.FormFile("document")
	if err != nil {
		JSONError(w, http.StatusBadRequest, "document file is required")
		return
	}
	defer file.Close()

	ext := strings.ToLower(filepath.Ext(header.Filename))
	fileID := fmt.Sprintf("doc_%d_%s%s", time.Now().UnixNano(), uuid.New().String()[:8], ext)
	dstPath := filepath.Join(h.uploadDir, fileID)

	dst, err := os.Create(dstPath)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to save document")
		return
	}
	defer dst.Close()

	size, err := io.Copy(dst, file)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "failed to write file")
		return
	}

	doc, err := h.orgService.AddDocument(r.Context(), *claims.OrgID, docType, fileID, header.Filename, header.Header.Get("Content-Type"), size)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Document uploaded successfully", doc)
}

// GET /api/v1/organizations/me/documents
func (h *OrgHandler) ListDocuments(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	docs, err := h.orgService.ListDocuments(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Documents retrieved", docs)
}

// DELETE /api/v1/organizations/me/documents/{id}
func (h *OrgHandler) DeleteDocument(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	docIDStr := chi.URLParam(r, "id")
	docID, err := uuid.Parse(docIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid document ID")
		return
	}

	if err := h.orgService.DeleteDocument(r.Context(), *claims.OrgID, docID); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Document deleted successfully", nil)
}

// GET /api/v1/organizations/me/members
func (h *OrgHandler) ListMembers(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	members, err := h.orgService.ListMembers(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Organization members retrieved", members)
}

// POST /api/v1/organizations/me/invites
func (h *OrgHandler) CreateInvite(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	invite, err := h.orgService.CreateInvite(r.Context(), *claims.OrgID, claims.UserID)
	if err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusCreated, "Invite link generated successfully", invite)
}

// GET /api/v1/organizations/me/join-requests
func (h *OrgHandler) ListJoinRequests(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	requests, err := h.orgService.ListJoinRequests(r.Context(), *claims.OrgID)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Pending join requests retrieved", requests)
}

// PATCH /api/v1/organizations/me/join-requests/{id}
func (h *OrgHandler) ReviewJoinRequest(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok || claims.OrgID == nil {
		JSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	reqIDStr := chi.URLParam(r, "id")
	reqID, err := uuid.Parse(reqIDStr)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "invalid join request ID")
		return
	}

	var input struct {
		Status       string `json:"status"` // APPROVED or REJECTED
		AssignedRole string `json:"assigned_role"` // Employee, Manager, Project Manager, Admin
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		JSONError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if err := h.orgService.ReviewJoinRequest(r.Context(), *claims.OrgID, reqID, claims.UserID, input.Status, input.AssignedRole); err != nil {
		JSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, fmt.Sprintf("Join request %s successfully", strings.ToLower(input.Status)), nil)
}

// GET /api/v1/organizations/invites/{orgCode}/{inviteToken} (Public)
func (h *OrgHandler) ValidatePublicInvite(w http.ResponseWriter, r *http.Request) {
	orgCode := chi.URLParam(r, "orgCode")
	inviteToken := chi.URLParam(r, "inviteToken")

	result, err := h.orgService.ValidateInvite(r.Context(), orgCode, inviteToken)
	if err != nil {
		JSONError(w, http.StatusNotFound, err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Invite is valid", result)
}
