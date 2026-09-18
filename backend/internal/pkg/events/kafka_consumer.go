package events

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/segmentio/kafka-go"
)

// KafkaConsumerConfig configures a Kafka consumer group for a set of topics.
type KafkaConsumerConfig struct {
	Brokers       []string
	GroupID       string // Consumer group — enables at-least-once delivery
	TopicPrefix   string
	MinBytes      int           // default 1KB
	MaxBytes      int           // default 1MB
	CommitInterval time.Duration // how often to auto-commit offsets
}

// KafkaConsumer reads DomainEvents from Kafka and dispatches them to registered
// EventHandlers using the same interface as the in-process EventBus.
// This allows orchestrator_service.go to subscribe once and receive events
// whether they come from in-process pub/sub or Kafka — transparently.
type KafkaConsumer struct {
	cfg      KafkaConsumerConfig
	readers  map[string]*kafka.Reader   // topic → reader
	handlers map[string][]EventHandler  // topic → handlers (same as EventBus)
	done     chan struct{}
}

// NewKafkaConsumer creates a consumer. Topics are subscribed via Subscribe().
func NewKafkaConsumer(cfg KafkaConsumerConfig) *KafkaConsumer {
	if cfg.MinBytes == 0 {
		cfg.MinBytes = 1024
	}
	if cfg.MaxBytes == 0 {
		cfg.MaxBytes = 1024 * 1024
	}
	if cfg.CommitInterval == 0 {
		cfg.CommitInterval = time.Second
	}
	return &KafkaConsumer{
		cfg:      cfg,
		readers:  make(map[string]*kafka.Reader),
		handlers: make(map[string][]EventHandler),
		done:     make(chan struct{}),
	}
}

func (c *KafkaConsumer) topicName(domainTopic string) string {
	if c.cfg.TopicPrefix == "" {
		return domainTopic
	}
	return c.cfg.TopicPrefix + domainTopic
}

// Subscribe registers an EventHandler for a Kafka topic.
// Must be called before Start().
func (c *KafkaConsumer) Subscribe(topic string, handler EventHandler) {
	c.handlers[topic] = append(c.handlers[topic], handler)
}

// Start launches one goroutine per subscribed topic, reading messages in a
// loop and dispatching to registered handlers.
// Handlers returning an error cause the message offset to NOT be committed —
// Kafka will redeliver on the next poll (at-least-once semantics).
func (c *KafkaConsumer) Start(ctx context.Context) {
	for topic, handlers := range c.handlers {
		kafkaTopic := c.topicName(topic)
		r := kafka.NewReader(kafka.ReaderConfig{
			Brokers:        c.cfg.Brokers,
			GroupID:        c.cfg.GroupID,
			Topic:          kafkaTopic,
			MinBytes:       c.cfg.MinBytes,
			MaxBytes:       c.cfg.MaxBytes,
			CommitInterval: c.cfg.CommitInterval,
		})
		c.readers[topic] = r

		go func(domainTopic string, reader *kafka.Reader, hs []EventHandler) {
			defer func() {
				if err := reader.Close(); err != nil {
					log.Printf("[KafkaConsumer] error closing reader for %s: %v", domainTopic, err)
				}
			}()

			for {
				select {
				case <-c.done:
					return
				default:
				}

				msg, err := reader.FetchMessage(ctx)
				if err != nil {
					if ctx.Err() != nil {
						return // Context cancelled — clean shutdown
					}
					log.Printf("[KafkaConsumer] fetch error on topic %s: %v", domainTopic, err)
					time.Sleep(500 * time.Millisecond) // brief backoff on transient errors
					continue
				}

				var event DomainEvent
				if unmarshalErr := json.Unmarshal(msg.Value, &event); unmarshalErr != nil {
					log.Printf("[KafkaConsumer] unmarshal error on topic %s: %v — skipping", domainTopic, unmarshalErr)
					// Commit even on unmarshal failure — bad messages should not block the queue
					_ = reader.CommitMessages(ctx, msg)
					continue
				}

				// Dispatch to all handlers for this topic
				handlerErr := false
				for _, h := range hs {
					if herr := h(ctx, event); herr != nil {
						log.Printf("[KafkaConsumer] handler error for topic %s event %s: %v",
							domainTopic, event.ID, herr)
						handlerErr = true
					}
				}

				// Only commit offset if all handlers succeeded
				if !handlerErr {
					if commitErr := reader.CommitMessages(ctx, msg); commitErr != nil {
						log.Printf("[KafkaConsumer] commit error on topic %s: %v", domainTopic, commitErr)
					}
				}
				// If handlerErr: offset not committed → Kafka redelivers on next poll
			}
		}(topic, r, handlers)
	}
}

// Stop signals all consumer goroutines to shut down.
func (c *KafkaConsumer) Stop() {
	close(c.done)
}

// BridgeToEventBus registers all topics from an EventBus into this KafkaConsumer,
// so the same in-process subscribers also receive Kafka messages.
// Call this after creating the KafkaConsumer and before Start().
func (c *KafkaConsumer) BridgeToEventBus(bus *EventBus) {
	for topic := range bus.subscribers {
		for _, h := range bus.subscribers[topic] {
			c.Subscribe(topic, h)
		}
	}
}

// LaunchBridged is a convenience function that creates and starts a KafkaConsumer
// wired to receive messages for all standard VĀSTU domain event topics.
func LaunchBridged(ctx context.Context, cfg KafkaConsumerConfig, bus *EventBus) (*KafkaConsumer, error) {
	c := NewKafkaConsumer(cfg)

	allTopics := []string{
		TopicCaptureCreated,
		TopicUploadStarted,
		TopicUploadCompleted,
		TopicValidationCompleted,
		TopicFramesExtracted,
		TopicReconstructionStarted,
		TopicReconstructionCompleted,
		TopicQualityStarted,
		TopicQualityFailed,
		TopicRescanRequired,
		TopicModelCreated,
		TopicModelPublished,
		TopicJobFailed,
	}

	for _, topic := range allTopics {
		topicHandlers := bus.subscribers[topic]
		if len(topicHandlers) > 0 {
			for _, h := range topicHandlers {
				c.Subscribe(topic, h)
			}
		}
	}

	if len(c.cfg.Brokers) == 0 {
		return nil, fmt.Errorf("kafka_consumer: no brokers configured")
	}

	c.Start(ctx)
	return c, nil
}
