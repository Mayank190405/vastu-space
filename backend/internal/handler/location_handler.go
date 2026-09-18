package handler

import (
	"net/http"
	"strconv"

	"vastu/backend/internal/service"
)

type LocationHandler struct {
	locationService *service.LocationService
}

func NewLocationHandler(locService *service.LocationService) *LocationHandler {
	return &LocationHandler{locationService: locService}
}

// SearchLocations handles place search query
// GET /api/v1/locations/search?q=...&limit=5
func (h *LocationHandler) SearchLocations(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	if q == "" {
		JSONSuccess(w, http.StatusOK, "Locations retrieved", map[string]interface{}{
			"results": []interface{}{},
		})
		return
	}

	limit := 5
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if parsedLimit, err := strconv.Atoi(limitStr); err == nil && parsedLimit > 0 && parsedLimit <= 20 {
			limit = parsedLimit
		}
	}

	results, err := h.locationService.Search(r.Context(), q)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "Failed to search locations: "+err.Error())
		return
	}

	if limit > 0 && len(results) > limit {
		results = results[:limit]
	}

	JSONSuccess(w, http.StatusOK, "Locations retrieved", map[string]interface{}{
		"query":   q,
		"results": results,
	})
}

// ReverseGeocode handles lat/lng reverse geocoding
// GET /api/v1/locations/reverse?lat=...&lng=...
func (h *LocationHandler) ReverseGeocode(w http.ResponseWriter, r *http.Request) {
	latStr := r.URL.Query().Get("lat")
	lngStr := r.URL.Query().Get("lng")

	if latStr == "" || lngStr == "" {
		JSONError(w, http.StatusBadRequest, "Both 'lat' and 'lng' query parameters are required")
		return
	}

	lat, err := strconv.ParseFloat(latStr, 64)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid 'lat' coordinate")
		return
	}

	lng, err := strconv.ParseFloat(lngStr, 64)
	if err != nil {
		JSONError(w, http.StatusBadRequest, "Invalid 'lng' coordinate")
		return
	}

	result, err := h.locationService.ReverseGeocode(r.Context(), lat, lng)
	if err != nil {
		JSONError(w, http.StatusInternalServerError, "Failed to reverse geocode: "+err.Error())
		return
	}

	JSONSuccess(w, http.StatusOK, "Address resolved", result)
}
