package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type Config struct {
	DatabaseURL          string
	Port                 string
	AppURL               string
	UploadDir            string
	JWTSecret            string
	JWTAccessExpiryMin   int
	JWTRefreshExpiryDays int
	SMTPHost             string
	SMTPPort             int
	SMTPUser             string
	SMTPPassword         string
	SMTPFromName         string
	SMTPFromEmail        string
	GoogleClientID       string
	GoogleClientSecret   string
	AppleClientID        string
}

func LoadConfig() *Config {
	_ = godotenv.Load()

	dbURL := getEnv("DATABASE_URL", "postgresql://vastu_user:vastu_secure_password_2026@localhost:5432/vastu_db?sslmode=disable")
	port := getEnv("PORT", "8080")
	appURL := getEnv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
	uploadDir := getEnv("UPLOAD_DIR", "./uploads")

	jwtSecret := getEnv("JWT_SECRET", "vastu_production_secure_jwt_signing_key_994829384729103847291028347")
	jwtAccessMin := getEnvAsInt("JWT_ACCESS_EXPIRY_MINUTES", 15)
	jwtRefreshDays := getEnvAsInt("JWT_REFRESH_EXPIRY_DAYS", 7)

	smtpHost := getEnv("SMTP_HOST", "smtp.hostinger.com")
	smtpPort := getEnvAsInt("SMTP_PORT", 465)
	smtpUser := getEnv("SMTP_USER", "noreply@krads.co.in")
	smtpPass := getEnv("SMTP_PASSWORD", "Krads@123#")
	smtpFromName := getEnv("SMTP_FROM_NAME", "VĀSTU Spatial Platform")
	smtpFromEmail := getEnv("SMTP_FROM_EMAIL", "noreply@krads.co.in")

	googleClientID := getEnv("GOOGLE_CLIENT_ID", "")
	googleClientSecret := getEnv("GOOGLE_CLIENT_SECRET", "")
	appleClientID := getEnv("APPLE_CLIENT_ID", "")

	return &Config{
		DatabaseURL:          dbURL,
		Port:                 port,
		AppURL:               appURL,
		UploadDir:            uploadDir,
		JWTSecret:            jwtSecret,
		JWTAccessExpiryMin:   jwtAccessMin,
		JWTRefreshExpiryDays: jwtRefreshDays,
		SMTPHost:             smtpHost,
		SMTPPort:             smtpPort,
		SMTPUser:             smtpUser,
		SMTPPassword:         smtpPass,
		SMTPFromName:         smtpFromName,
		SMTPFromEmail:        smtpFromEmail,
		GoogleClientID:       googleClientID,
		GoogleClientSecret:   googleClientSecret,
		AppleClientID:        appleClientID,
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func getEnvAsInt(key string, defaultVal int) int {
	valStr := os.Getenv(key)
	if valStr == "" {
		return defaultVal
	}
	val, err := strconv.Atoi(valStr)
	if err != nil {
		return defaultVal
	}
	return val
}
