package events

import (
	"context"
	"sync"
	"time"

	"github.com/google/uuid"
)

// Standardized Domain Event Topics according to VĀSTU Specification
const (
	TopicCaptureCreated          = "capture.created"
	TopicUploadStarted           = "upload.started"
	TopicUploadCompleted         = "upload.completed"
	TopicValidationCompleted     = "validation.completed"
	TopicFramesExtracted         = "frames.extracted"
	TopicReconstructionStarted   = "reconstruction.started"
	TopicReconstructionCompleted = "reconstruction.completed"
	TopicQualityStarted          = "quality.started"
	TopicQualityFailed           = "quality.failed"
	TopicRescanRequired          = "rescan.required"
	TopicModelCreated            = "model.created"
	TopicModelPublished          = "model.published"
	TopicJobFailed               = "job.failed"
)

type DomainEvent struct {
	ID            uuid.UUID              `json:"id"`
	Topic         string                 `json:"topic"`
	CorrelationID uuid.UUID              `json:"correlation_id"`
	Payload       map[string]interface{} `json:"payload"`
	Timestamp     time.Time              `json:"timestamp"`
}

type EventHandler func(ctx context.Context, event DomainEvent) error

type EventBus struct {
	mu          sync.RWMutex
	subscribers map[string][]EventHandler
	history     []DomainEvent
	maxHistory  int
}

var (
	defaultBus  *EventBus
	defaultOnce sync.Once
)

func GetEventBus() *EventBus {
	defaultOnce.Do(func() {
		defaultBus = NewEventBus(1000)
	})
	return defaultBus
}

func NewEventBus(maxHistory int) *EventBus {
	return &EventBus{
		subscribers: make(map[string][]EventHandler),
		history:     make([]DomainEvent, 0),
		maxHistory:  maxHistory,
	}
}

func (b *EventBus) Subscribe(topic string, handler EventHandler) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.subscribers[topic] = append(b.subscribers[topic], handler)
}

func (b *EventBus) Publish(ctx context.Context, topic string, correlationID uuid.UUID, payload map[string]interface{}) {
	event := DomainEvent{
		ID:            uuid.New(),
		Topic:         topic,
		CorrelationID: correlationID,
		Payload:       payload,
		Timestamp:     time.Now().UTC(),
	}

	b.mu.Lock()
	if len(b.history) >= b.maxHistory {
		b.history = b.history[1:]
	}
	b.history = append(b.history, event)
	handlers := append([]EventHandler{}, b.subscribers[topic]...)
	wildcardHandlers := append([]EventHandler{}, b.subscribers["*"]...)
	b.mu.Unlock()

	// Dispatch asynchronously
	go func() {
		allHandlers := append(handlers, wildcardHandlers...)
		for _, h := range allHandlers {
			_ = h(ctx, event)
		}
	}()
}

func (b *EventBus) GetRecentEvents() []DomainEvent {
	b.mu.RLock()
	defer b.mu.RUnlock()
	copied := make([]DomainEvent, len(b.history))
	copy(copied, b.history)
	return copied
}
