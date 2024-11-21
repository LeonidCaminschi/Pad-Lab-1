package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	maxConcurrentTasks      = 10
	requestTimeout          = 5 * time.Second
	circuitBreakerThreshold = 3
	circuitBreakerWindow    = requestTimeout*3 + (requestTimeout / 2)
)

var (
	semaphore      = make(chan struct{}, maxConcurrentTasks)
	loadBalancer   = NewLoadBalancer()
	circuitBreaker = NewCircuitBreaker()
)

func main() {
	// Discover services at startup
	time.Sleep(4 * time.Second) // time to wait for other services to start
	loadBalancer.DiscoverServices()

	router := gin.Default()
	router.POST("/register", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/login", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/registercard", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/subscribe", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/cancel-subscription", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.GET("/validate-user/:token", limitConcurrency(forwardRequest("serviceA", "GET")))
	router.GET("/validate-subscription/:token/:owner", limitConcurrency(forwardRequest("serviceA", "GET")))
	router.GET("/statusA", limitConcurrency(forwardRequest("serviceA", "GET")))

	router.POST("/upload", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/user/:owner", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/user/:owner/:id", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/delete/:id", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.GET("/statusB", limitConcurrency(forwardRequest("serviceB", "GET")))

	router.GET("/rooms", limitConcurrency(getRooms))

	router.GET("/status", limitConcurrency(getStatus))

	router.Run("0.0.0.0:5003")
}

func limitConcurrency(handler gin.HandlerFunc) gin.HandlerFunc {
	return func(c *gin.Context) {
		semaphore <- struct{}{}
		defer func() { <-semaphore }()
		handler(c)
	}
}

func forwardRequest(serviceName, method string) gin.HandlerFunc {
	return func(c *gin.Context) {
		body, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
			return
		}

		services := loadBalancer.GetAllServices(serviceName)
		if len(services) == 0 {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "No available services"})
			return
		}

		for _, service := range services {
			if circuitBreaker.IsTripped(service) {
				log.Printf("All services for %s are down", service.Name)
				continue
			}

			url := "http://" + service.Host + ":" + strconv.Itoa(service.Port) + c.Request.URL.Path
			log.Println("Forwarding request to URL:", url)

			for i := 0; i < circuitBreakerThreshold; i++ {
				req, err := http.NewRequest(method, url, io.NopCloser(bytes.NewBuffer(body)))
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create request"})
					return
				}
				req.Header.Set("Content-Type", "application/json")

				client := &http.Client{
					Timeout: requestTimeout,
				}

				ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
				defer cancel()

				req = req.WithContext(ctx)

				resp, err := client.Do(req)
				if err != nil {
					if ctx.Err() == context.DeadlineExceeded {
						c.JSON(http.StatusRequestTimeout, gin.H{"error": "Request timed out"})
					} else {
						c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to send request"})
					}
					circuitBreaker.RecordFailure(service)
					continue
				}
				defer resp.Body.Close()

				if resp.StatusCode >= 500 {
					circuitBreaker.RecordFailure(service)
					time.Sleep(circuitBreakerWindow)
					continue
				}

				respBody, err := io.ReadAll(resp.Body)
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read response"})
					return
				}

				circuitBreaker.Reset(service)
				c.Data(resp.StatusCode, "application/json", respBody)
				return
			}
		}

		log.Printf("All services for %s are down", serviceName)
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "All services are temporarily unavailable"})
	}
}

func getRooms(c *gin.Context) {
	services := loadBalancer.GetAllServices("serviceB")
	var wg sync.WaitGroup
	var mu sync.Mutex
	rooms := make(map[string][]string)

	for _, service := range services {
		wg.Add(1)
		go func(service Service) {
			defer wg.Done()

			url := "http://" + service.Host + ":" + strconv.Itoa(service.Port) + "/rooms"
			client := &http.Client{
				Timeout: requestTimeout,
			}

			req, err := http.NewRequest("GET", url, nil)
			if err != nil {
				log.Printf("Failed to create request for service %s: %v", service.Name, err)
				return
			}

			ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
			defer cancel()

			req = req.WithContext(ctx)

			resp, err := client.Do(req)
			if err != nil {
				log.Printf("Failed to send request to service %s: %v", service.Name, err)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode != http.StatusOK {
				log.Printf("Service %s returned non-OK status: %d", service.Name, resp.StatusCode)
				return
			}

			respBody, err := io.ReadAll(resp.Body)
			if err != nil {
				log.Printf("Failed to read response from service %s: %v", service.Name, err)
				return
			}

			var serviceRooms []string
			if err := json.Unmarshal(respBody, &serviceRooms); err != nil {
				log.Printf("Failed to unmarshal response from service %s: %v", service.Name, err)
				return
			}

			mu.Lock()
			rooms[service.Host] = serviceRooms
			mu.Unlock()
		}(service)
	}

	wg.Wait()

	c.JSON(http.StatusOK, rooms)
}

func getStatus(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "Gateway is up and running"})
}
