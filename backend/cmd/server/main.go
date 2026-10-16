package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"vastu/backend/internal/config"
	"vastu/backend/internal/handler"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/pkg/jwt"
	"vastu/backend/internal/pkg/mailer"
	"vastu/backend/internal/pkg/queue"
	"vastu/backend/internal/repository/postgres"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
)

func main() {
	cfg := config.LoadConfig()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// 1. Initialize PostgreSQL Connection Pool
	pool, err := postgres.NewDBPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Fatal: Failed to connect to PostgreSQL: %v", err)
	}
	defer pool.Close()
	log.Println("✓ PostgreSQL database connection established")

	// 2. Initialize Repositories
	userRepo := postgres.NewUserRepo(pool)
	orgRepo := postgres.NewOrgRepo(pool)
	memberRepo := postgres.NewMemberRepo(pool)
	otpRepo := postgres.NewOTPRepo(pool)
	tokenRepo := postgres.NewTokenRepo(pool)
	identRepo := postgres.NewIdentifierRepo(pool)
	docRepo := postgres.NewDocumentRepo(pool)
	addrRepo := postgres.NewAddressRepo(pool)
	inviteRepo := postgres.NewInviteRepo(pool)
	joinReqRepo := postgres.NewJoinRequestRepo(pool)
	projectRepo := postgres.NewProjectRepo(pool)
	captureRepo := postgres.NewCaptureRepo(pool)
	uploadRepo := postgres.NewUploadRepo(pool)
	jobRepo := postgres.NewJobRepo(pool)
	modelRepo := postgres.NewModelRepo(pool)
	poiRepo := postgres.NewPOIRepo(pool)
	navRepo := postgres.NewNavigationRepo(pool)
	viewerRepo := postgres.NewViewerRepo(pool)

	// 3. Initialize Packages & Clients
	jwtManager := jwt.NewTokenManager(cfg.JWTSecret, cfg.JWTAccessExpiryMin, cfg.JWTRefreshExpiryDays)
	smtpMailer := mailer.NewSMTPMailer(cfg.SMTPHost, cfg.SMTPPort, cfg.SMTPUser, cfg.SMTPPassword, cfg.SMTPFromName, cfg.SMTPFromEmail)
	googleSvc := service.NewGoogleService(cfg.GoogleClientID)
	appleSvc := service.NewAppleService(cfg.AppleClientID)
	asynqClient := queue.NewAsynqClient(cfg.RedisURL, cfg.RedisPassword)
	defer asynqClient.Close()

	// 4. Initialize Services
	otpService := service.NewOTPService(otpRepo, smtpMailer)
	authService := service.NewAuthService(userRepo, orgRepo, memberRepo, tokenRepo, identRepo, docRepo, addrRepo, inviteRepo, joinReqRepo, otpService, googleSvc, appleSvc, jwtManager, "http://localhost:3000")
	orgService := service.NewOrgService(orgRepo, userRepo, memberRepo, identRepo, docRepo, addrRepo, inviteRepo, joinReqRepo, smtpMailer, jwtManager, "http://localhost:3000")
	projectService := service.NewProjectService(projectRepo, orgRepo, smtpMailer)
	captureService := service.NewCaptureService(captureRepo, projectRepo)
	uploadService := service.NewUploadService(uploadRepo, captureRepo, cfg.UploadDir)
	jobService := service.NewJobService(jobRepo, projectRepo, captureRepo, asynqClient)
	jobService.SetUploadDir(cfg.UploadDir)
	modelService := service.NewModelService(modelRepo, projectRepo)
	poiService := service.NewPOIService(poiRepo, projectRepo)
	searchService := service.NewSearchService(poiRepo, projectRepo)
	navService := service.NewNavigationService(navRepo, poiRepo)
	viewerService := service.NewViewerService(viewerRepo, projectRepo)
	locationService := service.NewLocationService()
	rescanService := service.NewRescanService(pool)

	// 5. Initialize Middlewares & Handlers
	authMiddleware := middleware.NewAuthMiddleware(jwtManager)
	authHandler := handler.NewAuthHandler(authService)
	orgHandler := handler.NewOrgHandler(orgService, cfg.UploadDir)
	projectHandler := handler.NewProjectHandler(projectService, cfg.UploadDir)
	locationHandler := handler.NewLocationHandler(locationService)
	captureHandler := handler.NewCaptureHandler(captureService)
	rescanHandler := handler.NewRescanHandler(rescanService)
	uploadHandler := handler.NewUploadHandler(uploadService)
	jobHandler := handler.NewJobHandler(jobService)
	modelHandler := handler.NewModelHandler(modelService)
	poiHandler := handler.NewPOIHandler(poiService)
	searchHandler := handler.NewSearchHandler(searchService)
	navHandler := handler.NewNavigationHandler(navService)
	viewerHandler := handler.NewViewerHandler(viewerService)

	// 6. Router Setup
	r := chi.NewRouter()
	r.Use(chimw.RequestID)
	r.Use(chimw.RealIP)
	r.Use(chimw.Logger)
	r.Use(chimw.Recoverer)
	r.Use(chimw.Timeout(60 * time.Second))

	r.Use(cors.Handler(cors.Options{
		AllowOriginFunc: func(r *http.Request, origin string) bool {
			return true
		},
		AllowedMethods:   []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Requested-With"},
		ExposedHeaders:   []string{"Link", "Authorization"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	// Health Check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		handler.JSON(w, http.StatusOK, map[string]string{
			"status":  "healthy",
			"service": "vastu-backend-control-plane",
			"version": "1.0.0",
		})
	})

	// Static Document Uploads
	_ = os.MkdirAll(cfg.UploadDir, 0755)
	fileServer := http.FileServer(http.Dir(cfg.UploadDir))
	r.Handle("/uploads/*", http.StripPrefix("/uploads/", fileServer))

	// API v1 Routes
	r.Route("/api/v1", func(r chi.Router) {
		// 1. Authentication Routes
		r.Route("/auth", func(r chi.Router) {
			r.Post("/signup/organization", authHandler.CompleteOrgSignup)
			r.Post("/signup/emp", authHandler.SubmitEmployeeJoin)
			r.Post("/join/org", authHandler.SubmitEmployeeJoin)
			r.Post("/otp/send", authHandler.SendOTP)
			r.Post("/otp/verify", authHandler.VerifyOTP)
			r.Post("/request-otp", authHandler.SendOTP)
			r.Post("/verify-otp", authHandler.VerifyOTP)
			r.Post("/login", authHandler.Login)
			r.Post("/google", authHandler.GoogleAuth)
			r.Post("/token/refresh", authHandler.Refresh)
			r.Post("/refresh", authHandler.Refresh)
			r.Post("/logout", authHandler.Logout)

			// Protected Auth Endpoint
			r.Group(func(r chi.Router) {
				r.Use(authMiddleware.Authenticate)
				r.Get("/me", authHandler.GetMe)
			})
		})

		// Places & Geocoding Location Routes
		r.Route("/locations", func(r chi.Router) {
			r.Get("/search", locationHandler.SearchLocations)
			r.Get("/reverse", locationHandler.ReverseGeocode)
		})

		// 2. Public Invite Validation
		r.Get("/organizations/invites/{orgCode}/{inviteToken}", orgHandler.ValidatePublicInvite)

		// 3. Organization & Member Management Routes (Protected)
		r.Route("/organizations", func(r chi.Router) {
			r.Group(func(r chi.Router) {
				r.Use(authMiddleware.Authenticate)
				r.Get("/me", orgHandler.GetMyOrg)
				r.Patch("/me", orgHandler.UpdateOrgDetails)
				r.Patch("/me/details", orgHandler.UpdateOrgDetails)
				r.Patch("/me/contact", orgHandler.UpdateOrgContact)
				r.Patch("/me/address", orgHandler.UpdateOrgAddress)
				r.Post("/me/gst", orgHandler.AddOrVerifyGST)
				r.Post("/me/gst/verify", orgHandler.AddOrVerifyGST)
				r.Post("/me/documents", orgHandler.UploadDocument)
				r.Get("/me/documents", orgHandler.ListDocuments)
				r.Delete("/me/documents/{id}", orgHandler.DeleteDocument)
				r.Get("/me/members", orgHandler.ListMembers)
				r.Post("/me/invites", orgHandler.CreateInvite)
				r.Get("/me/join-requests", orgHandler.ListJoinRequests)
				r.Patch("/me/join-requests/{id}", orgHandler.ReviewJoinRequest)
			})
		})

		// 3. Project Management Routes (Protected)
		r.Route("/projects", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Get("/types", projectHandler.GetProjectTypes)
			r.Post("/", projectHandler.Create)
			r.Post("/create-full", projectHandler.CreateFull)
			r.Post("/draft", projectHandler.SaveDraft)
			r.Post("/cover-image", projectHandler.UploadCoverImage)
			r.Get("/", projectHandler.List)
			r.Get("/trash", projectHandler.ListTrash)
			r.Get("/{projectId}", projectHandler.Get)
			r.Get("/{projectId}/full", projectHandler.GetFull)
			r.Put("/{projectId}", projectHandler.Update)
			r.Patch("/{projectId}", projectHandler.Update)
			r.Delete("/{projectId}", projectHandler.SoftDelete)
			r.Post("/{projectId}/restore", projectHandler.Restore)
			r.Delete("/{projectId}/permanent", projectHandler.PermanentDelete)
			r.Delete("/{projectId}/archive", projectHandler.Archive)

			// Floors
			r.Post("/{projectId}/floors", projectHandler.AddFloor)
			r.Get("/{projectId}/floors", projectHandler.ListFloors)
			r.Put("/{projectId}/floors/{floorId}", projectHandler.UpdateFloor)
			r.Patch("/{projectId}/floors/{floorId}", projectHandler.UpdateFloor)
			r.Delete("/{projectId}/floors/{floorId}", projectHandler.DeleteFloor)

			// Floor Plans (Upload & Vector Canvas)
			r.Post("/{projectId}/floors/{floorId}/floor-plan/upload", projectHandler.UploadFloorPlan)
			r.Post("/{projectId}/floors/{floorId}/floor-plan/draw", projectHandler.DrawFloorPlan)
			r.Get("/{projectId}/floors/{floorId}/floor-plan", projectHandler.GetFloorPlan)
			r.Patch("/{projectId}/floors/{floorId}/floor-plan", projectHandler.DrawFloorPlan)
			r.Delete("/{projectId}/floors/{floorId}/floor-plan", projectHandler.DeleteFloorPlan)

			// Team Members
			r.Get("/{projectId}/members", projectHandler.ListMembers)
			r.Post("/{projectId}/members", projectHandler.AddMember)
			r.Patch("/{projectId}/members/{userId}", projectHandler.AddMember)
			r.Delete("/{projectId}/members/{userId}", projectHandler.RemoveMember)

			// Timeline & Milestone Comments
			r.Get("/{projectId}/timeline", projectHandler.GetTimeline)
			r.Put("/{projectId}/timeline/{eventId}/status", projectHandler.UpdateTimelineEventStatus)
			r.Post("/{projectId}/timeline/{eventId}/comments", projectHandler.AddTimelineComment)

			// Real-Time Project Chat & Urgency Control
			r.Get("/{projectId}/chat", projectHandler.GetChat)
			r.Post("/{projectId}/chat", projectHandler.SendMessage)
			r.Post("/{projectId}/chat/{messageId}/resolve", projectHandler.ResolveMessage)

			// Client Emails & Notifications
			r.Get("/{projectId}/client-emails", projectHandler.GetClientEmails)
			r.Post("/{projectId}/client-emails/send", projectHandler.SendClientEmail)
			r.Post("/{projectId}/client-emails/{logId}/resend", projectHandler.ResendClientEmail)

			// Activity & Audit History
			r.Get("/{projectId}/activities", projectHandler.GetActivities)

			// Digital Twin Render & Viewing Link
			r.Get("/{projectId}/render", projectHandler.GetRender)
			r.Get("/{projectId}/view-link", projectHandler.GetViewingLink)
			r.Get("/{projectId}/pois", poiHandler.ListByProject)
		})

		// 4. Captures Core Service Routes (Protected)
		r.Route("/captures", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/", captureHandler.Create)
			r.Get("/{id}", captureHandler.Get)
			r.Get("/project/{projectId}", captureHandler.ListByProject)
			r.Put("/{id}/status", captureHandler.UpdateStatus)
		})

		// 4b. Targeted Rescan Requests Routes (Protected)
		r.Route("/rescan-requests", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/", rescanHandler.Create)
			r.Get("/project/{projectId}", rescanHandler.ListPending)
			r.Patch("/{id}/status", rescanHandler.UpdateStatus)
			r.Put("/{id}/status", rescanHandler.UpdateStatus)
		})

		// 5. Uploads Core Service Routes (Protected)
		r.Route("/uploads", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/init", uploadHandler.Init)
			r.Post("/{sessionId}/chunk/{chunkIndex}", uploadHandler.UploadChunk)
			r.Put("/{sessionId}/chunk/{chunkIndex}", uploadHandler.UploadChunk)
			r.Get("/{sessionId}/progress", uploadHandler.GetProgress)
			r.Post("/{sessionId}/complete", uploadHandler.Complete)
		})

		// 6. Processing Jobs Core Service Routes (Protected)
		r.Route("/jobs", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/", jobHandler.Create)
			r.Get("/{id}", jobHandler.Get)
			r.Get("/project/{projectId}", jobHandler.ListByProject)
			r.Put("/{id}/progress", jobHandler.UpdateProgress)
			r.Post("/{id}/logs", jobHandler.AddLog)
			r.Get("/{id}/logs", jobHandler.GetLogs)
		})

		// 7. Spatial Models Core Service Routes (Protected)
		r.Route("/models", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/", modelHandler.Create)
			r.Get("/{id}", modelHandler.Get)
			r.Get("/project/{projectId}/active", modelHandler.GetActive)
			r.Get("/project/{projectId}", modelHandler.ListByProject)
			r.Post("/{id}/artifacts", modelHandler.AddArtifact)
		})

		// 8. Spatial POIs Core Service Routes (Protected)
		r.Route("/pois", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/", poiHandler.Create)
			r.Get("/{id}", poiHandler.Get)
			r.Get("/project/{projectId}", poiHandler.ListByProject)
			r.Put("/{id}", poiHandler.Update)
			r.Delete("/{id}", poiHandler.Delete)
		})

		// 9. Semantic Spatial Search Route (Protected)
		r.Route("/search", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/spatial", searchHandler.SearchSpatial)
		})

		// 10. Indoor Navigation Engine Routes (Protected)
		r.Route("/navigation", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/nodes", navHandler.CreateNode)
			r.Get("/nodes/project/{projectId}", navHandler.ListNodes)
			r.Post("/edges", navHandler.CreateEdge)
			r.Get("/edges/project/{projectId}", navHandler.ListEdges)
			r.Post("/route", navHandler.CalculateRoute)
		})

		// 11. Spatial 3D Viewer & Annotations Routes (Protected)
		r.Route("/viewer", func(r chi.Router) {
			r.Use(authMiddleware.Authenticate)
			r.Post("/bookmarks", viewerHandler.CreateBookmark)
			r.Get("/bookmarks/project/{projectId}", viewerHandler.ListBookmarks)
			r.Delete("/bookmarks/{id}", viewerHandler.DeleteBookmark)
			r.Post("/annotations", viewerHandler.CreateAnnotation)
			r.Get("/annotations/project/{projectId}", viewerHandler.ListAnnotations)
			r.Delete("/annotations/{id}", viewerHandler.DeleteAnnotation)
		})
	})

	serverAddr := fmt.Sprintf(":%s", cfg.Port)
	srv := &http.Server{
		Addr:         serverAddr,
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		log.Printf("🚀 VĀSTU Go Control Plane Server listening on port %s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server listen failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server gracefully...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("Server forced shutdown: %v", err)
	}

	log.Println("Server exited cleanly.")
}
