package service

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type LocationSearchResult struct {
	PlaceID      string   `json:"place_id"`
	DisplayName  string   `json:"display_name"`
	AddressLine1 string   `json:"address_line_1"`
	Area         string   `json:"area"`
	City         string   `json:"city"`
	State        string   `json:"state"`
	Pincode      string   `json:"pincode"`
	Country      string   `json:"country"`
	Latitude     float64  `json:"latitude"`
	Longitude    float64  `json:"longitude"`
}

type LocationService struct {
	httpClient *http.Client
}

func NewLocationService() *LocationService {
	return &LocationService{
		httpClient: &http.Client{
			Timeout: 6 * time.Second,
		},
	}
}

type nominatimResult struct {
	PlaceID     int64             `json:"place_id"`
	OsmID       int64             `json:"osm_id"`
	DisplayName string            `json:"display_name"`
	Lat         string            `json:"lat"`
	Lon         string            `json:"lon"`
	Address     map[string]string `json:"address"`
}

func (s *LocationService) Search(ctx context.Context, query string) ([]LocationSearchResult, error) {
	query = strings.TrimSpace(query)
	if query == "" {
		return []LocationSearchResult{}, nil
	}

	searchURL := fmt.Sprintf(
		"https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=7&q=%s",
		url.QueryEscape(query),
	)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, searchURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "VastuSpatial/1.0 (contact@vastuspatial.cloud)")

	resp, err := s.httpClient.Do(req)
	if err != nil || resp.StatusCode != http.StatusOK {
		// Fallback to local heuristic parsing so users can still search offline / behind firewalls
		return s.fallbackSearch(query), nil
	}
	defer resp.Body.Close()

	var rawResults []nominatimResult
	if err := json.NewDecoder(resp.Body).Decode(&rawResults); err != nil {
		return s.fallbackSearch(query), nil
	}

	if len(rawResults) == 0 {
		return s.fallbackSearch(query), nil
	}

	var results []LocationSearchResult
	for _, r := range rawResults {
		lat, _ := strconv.ParseFloat(r.Lat, 64)
		lon, _ := strconv.ParseFloat(r.Lon, 64)

		line1 := extractLine1(r.Address)
		area := extractArea(r.Address)
		city := extractCity(r.Address)
		state := extractState(r.Address)
		pincode := r.Address["postcode"]
		country := r.Address["country"]
		if country == "" {
			country = "India"
		}

		results = append(results, LocationSearchResult{
			PlaceID:      fmt.Sprintf("osm_%d", r.PlaceID),
			DisplayName:  r.DisplayName,
			AddressLine1: line1,
			Area:         area,
			City:         city,
			State:        state,
			Pincode:      pincode,
			Country:      country,
			Latitude:     lat,
			Longitude:    lon,
		})
	}

	return results, nil
}

func (s *LocationService) ReverseGeocode(ctx context.Context, lat, lon float64) (*LocationSearchResult, error) {
	reverseURL := fmt.Sprintf(
		"https://nominatim.openstreetmap.org/reverse?format=json&addressdetails=1&lat=%.6f&lon=%.6f",
		lat, lon,
	)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, reverseURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "VastuSpatial/1.0 (contact@vastuspatial.cloud)")

	resp, err := s.httpClient.Do(req)
	if err != nil || resp.StatusCode != http.StatusOK {
		return &LocationSearchResult{
			PlaceID:      fmt.Sprintf("gps_%.4f_%.4f", lat, lon),
			DisplayName:  fmt.Sprintf("Coordinates: %.5f, %.5f", lat, lon),
			AddressLine1: fmt.Sprintf("Site at %.5f, %.5f", lat, lon),
			City:         "Current Location",
			State:        "",
			Country:      "India",
			Latitude:     lat,
			Longitude:    lon,
		}, nil
	}
	defer resp.Body.Close()

	var r nominatimResult
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		return nil, err
	}

	line1 := extractLine1(r.Address)
	area := extractArea(r.Address)
	city := extractCity(r.Address)
	state := extractState(r.Address)
	pincode := r.Address["postcode"]
	country := r.Address["country"]
	if country == "" {
		country = "India"
	}

	return &LocationSearchResult{
		PlaceID:      fmt.Sprintf("osm_%d", r.PlaceID),
		DisplayName:  r.DisplayName,
		AddressLine1: line1,
		Area:         area,
		City:         city,
		State:        state,
		Pincode:      pincode,
		Country:      country,
		Latitude:     lat,
		Longitude:    lon,
	}, nil
}

func (s *LocationService) fallbackSearch(q string) []LocationSearchResult {
	parts := strings.Split(q, ",")
	line1 := strings.TrimSpace(parts[0])
	city := "Bangalore"
	state := "Karnataka"
	if len(parts) > 1 {
		city = strings.TrimSpace(parts[1])
	}
	if len(parts) > 2 {
		state = strings.TrimSpace(parts[2])
	}

	return []LocationSearchResult{
		{
			PlaceID:      fmt.Sprintf("local_%d", time.Now().UnixNano()),
			DisplayName:  fmt.Sprintf("%s, %s, %s, India", line1, city, state),
			AddressLine1: line1,
			Area:         line1,
			City:         city,
			State:        state,
			Pincode:      "560001",
			Country:      "India",
			Latitude:     12.9716,
			Longitude:    77.5946,
		},
	}
}

func extractLine1(addr map[string]string) string {
	parts := []string{}
	if h, ok := addr["house_number"]; ok && h != "" {
		parts = append(parts, h)
	}
	if r, ok := addr["road"]; ok && r != "" {
		parts = append(parts, r)
	} else if b, ok := addr["building"]; ok && b != "" {
		parts = append(parts, b)
	}
	if len(parts) > 0 {
		return strings.Join(parts, ", ")
	}
	return addr["amenity"]
}

func extractArea(addr map[string]string) string {
	for _, k := range []string{"suburb", "neighbourhood", "residential", "quarter", "commercial"} {
		if v, ok := addr[k]; ok && v != "" {
			return v
		}
	}
	return ""
}

func extractCity(addr map[string]string) string {
	for _, k := range []string{"city", "town", "municipality", "village", "county", "district"} {
		if v, ok := addr[k]; ok && v != "" {
			return v
		}
	}
	return "City"
}

func extractState(addr map[string]string) string {
	for _, k := range []string{"state", "state_district", "region", "province"} {
		if v, ok := addr[k]; ok && v != "" {
			return v
		}
	}
	return ""
}
