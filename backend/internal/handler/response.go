package handler

import (
	"encoding/json"
	"net/http"
)

type ErrorResponse struct {
	Error string `json:"error"`
}

type SuccessResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Message string      `json:"message,omitempty"`
}

func JSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func JSONError(w http.ResponseWriter, status int, message string) {
	JSON(w, status, ErrorResponse{Error: message})
}

func JSONSuccess(w http.ResponseWriter, status int, message string, data interface{}) {
	JSON(w, status, SuccessResponse{
		Success: true,
		Message: message,
		Data:    data,
	})
}
