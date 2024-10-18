package main

import (
	"sync"
	"time"
)

type CircuitBreaker struct {
	failures map[string][]time.Time
	mu       sync.Mutex
}

func NewCircuitBreaker() *CircuitBreaker {
	return &CircuitBreaker{
		failures: make(map[string][]time.Time),
	}
}

func (cb *CircuitBreaker) RecordFailure(service Service) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	now := time.Now()
	cb.failures[service.Name] = append(cb.failures[service.Name], now)

	// Remove old failures outside the time window
	windowStart := now.Add(-circuitBreakerWindow)
	failures := cb.failures[service.Name]
	for len(failures) > 0 && failures[0].Before(windowStart) {
		failures = failures[1:]
	}
	cb.failures[service.Name] = failures
}

func (cb *CircuitBreaker) IsTripped(service Service) bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	failures := cb.failures[service.Name]
	return len(failures) >= circuitBreakerThreshold
}

func (cb *CircuitBreaker) Reset(service Service) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failures[service.Name] = nil
}
