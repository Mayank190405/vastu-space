package domain

import (
	"time"

	"github.com/google/uuid"
)

type TimelineEvent struct {
	ID            uuid.UUID          `json:"id"`
	ProjectID     uuid.UUID          `json:"project_id"`
	EventType     string             `json:"event_type"`
	Title         string             `json:"title"`
	Description   string             `json:"description"`
	Status        string             `json:"status"` // completed, in_progress, pending, blocked
	MilestoneDate time.Time          `json:"milestone_date"`
	CreatedAt     time.Time          `json:"created_at"`
	Comments      []*TimelineComment `json:"comments,omitempty"`
}

type TimelineComment struct {
	ID         uuid.UUID  `json:"id"`
	EventID    uuid.UUID  `json:"event_id"`
	AuthorID   *uuid.UUID `json:"author_id,omitempty"`
	AuthorName string     `json:"author_name"`
	AuthorRole string     `json:"author_role"`
	Content    string     `json:"content"`
	CreatedAt  time.Time  `json:"created_at"`
}

type ChatUrgencyLevel string

const (
	UrgencyNormal   ChatUrgencyLevel = "normal"
	UrgencyHigh     ChatUrgencyLevel = "high"
	UrgencyUrgent   ChatUrgencyLevel = "urgent"
	UrgencyCritical ChatUrgencyLevel = "critical"
)

type ProjectChatMessage struct {
	ID           uuid.UUID        `json:"id"`
	ProjectID    uuid.UUID        `json:"project_id"`
	SenderID     *uuid.UUID       `json:"sender_id,omitempty"`
	SenderName   string           `json:"sender_name"`
	SenderRole   string           `json:"sender_role"`
	Content      string           `json:"content"`
	UrgencyLevel ChatUrgencyLevel `json:"urgency_level"`
	IsPinned     bool             `json:"is_pinned"`
	IsResolved   bool             `json:"is_resolved"`
	ResolvedBy   *string          `json:"resolved_by,omitempty"`
	ResolvedAt   *time.Time       `json:"resolved_at,omitempty"`
	CreatedAt    time.Time        `json:"created_at"`
}

type ClientEmailLog struct {
	ID             uuid.UUID `json:"id"`
	ProjectID      uuid.UUID `json:"project_id"`
	RecipientEmail string    `json:"recipient_email"`
	RecipientName  *string   `json:"recipient_name,omitempty"`
	Subject        string    `json:"subject"`
	EmailType      string    `json:"email_type"`
	Status         string    `json:"status"`
	DispatchedAt   time.Time `json:"dispatched_at"`
}

type CreateCommentInput struct {
	AuthorName string `json:"author_name"`
	AuthorRole string `json:"author_role"`
	Content    string `json:"content"`
}

type SendChatMessageInput struct {
	SenderName   string           `json:"sender_name"`
	SenderRole   string           `json:"sender_role"`
	Content      string           `json:"content"`
	UrgencyLevel ChatUrgencyLevel `json:"urgency_level"`
	IsPinned     bool             `json:"is_pinned"`
}

type ProjectActivityLog struct {
	ID          uuid.UUID  `json:"id"`
	ProjectID   uuid.UUID  `json:"project_id"`
	ActorID     *uuid.UUID `json:"actor_id,omitempty"`
	ActorName   string     `json:"actor_name"`
	ActorRole   string     `json:"actor_role"`
	ActionType  string     `json:"action_type"` // status_change, milestone_updated, comment_added, email_dispatched, member_assigned, project_created, project_updated
	ActionTitle string     `json:"action_title"`
	Details     *string    `json:"details,omitempty"`
	OldValue    *string    `json:"old_value,omitempty"`
	NewValue    *string    `json:"new_value,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
}

