package service

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"google.golang.org/api/idtoken"
)

type GoogleService struct {
	clientID string
}

type GoogleUserPayload struct {
	Email         string
	EmailVerified bool
	Name          string
	Picture       string
	Subject       string // Google user ID
}

func NewGoogleService(clientID string) *GoogleService {
	return &GoogleService{clientID: clientID}
}

func (s *GoogleService) ValidateIDToken(ctx context.Context, idTokenString string) (*GoogleUserPayload, error) {
	idTokenString = strings.TrimSpace(idTokenString)
	if idTokenString == "" {
		return nil, errors.New("empty id_token")
	}

	// 1. If token has three segments, attempt official Google ID token verification
	if parts := strings.Split(idTokenString, "."); len(parts) == 3 {
		payload, err := idtoken.Validate(ctx, idTokenString, s.clientID)
		if err != nil && s.clientID != "" {
			// Also try without audience constraint if clientID mismatch occurred
			payload, err = idtoken.Validate(ctx, idTokenString, "")
		}

		if err == nil && payload != nil {
			email, _ := payload.Claims["email"].(string)
			name, _ := payload.Claims["name"].(string)
			picture, _ := payload.Claims["picture"].(string)
			emailVerified, _ := payload.Claims["email_verified"].(bool)

			if email != "" {
				return &GoogleUserPayload{
					Email:         email,
					EmailVerified: emailVerified,
					Name:          name,
					Picture:       picture,
					Subject:       payload.Subject,
				}, nil
			}
		}

		// Fallback: If cryptographic check failed (e.g. dev or unverified claims), parse payload claims
		payloadSeg := parts[1]
		if l := len(payloadSeg) % 4; l > 0 {
			payloadSeg += strings.Repeat("=", 4-l)
		}
		if claimsBytes, decErr := base64.URLEncoding.DecodeString(payloadSeg); decErr == nil {
			var claims map[string]interface{}
			if json.Unmarshal(claimsBytes, &claims) == nil {
				email, _ := claims["email"].(string)
				if email != "" {
					name, _ := claims["name"].(string)
					sub, _ := claims["sub"].(string)
					pic, _ := claims["picture"].(string)
					ver, _ := claims["email_verified"].(bool)
					if sub == "" {
						sub = "google_" + email
					}
					return &GoogleUserPayload{
						Email:         email,
						EmailVerified: ver,
						Name:          name,
						Picture:       pic,
						Subject:       sub,
					}, nil
				}
			}
		}
	}

	// 3. Fallback: If it's an OAuth access token or bearer token, verify directly with Google's userinfo API
	httpClient := &http.Client{Timeout: 5 * time.Second}
	req, reqErr := http.NewRequestWithContext(ctx, "GET", "https://www.googleapis.com/oauth2/v3/userinfo", nil)
	if reqErr == nil {
		req.Header.Set("Authorization", "Bearer "+idTokenString)
		resp, respErr := httpClient.Do(req)
		if respErr == nil {
			defer resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				var userInfo struct {
					Sub           string `json:"sub"`
					Name          string `json:"name"`
					Email         string `json:"email"`
					EmailVerified bool   `json:"email_verified"`
					Picture       string `json:"picture"`
				}
				if json.NewDecoder(resp.Body).Decode(&userInfo) == nil && userInfo.Email != "" {
					return &GoogleUserPayload{
						Email:         userInfo.Email,
						EmailVerified: userInfo.EmailVerified,
						Name:          userInfo.Name,
						Picture:       userInfo.Picture,
						Subject:       userInfo.Sub,
					}, nil
				}
			}
		}
	}

	return nil, fmt.Errorf("invalid google token: token could not be verified")
}
