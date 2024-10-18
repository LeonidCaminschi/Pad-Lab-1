package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	maxConcurrentTasks = 10
	requestTimeout     = 5 * time.Second
)

var (
	semaphore    = make(chan struct{}, maxConcurrentTasks)
	loadBalancer = NewLoadBalancer()
)

func main() {
	// Discover services at startup
	time.Sleep(4 * time.Second)
	loadBalancer.DiscoverServices()

	router := gin.Default()
	router.POST("/register", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/login", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/registercard", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/subscribe", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.POST("/cancel-subscription", limitConcurrency(forwardRequest("serviceA", "POST")))
	router.GET("/validate-user/:token", limitConcurrency(forwardRequest("serviceA", "GET")))
	router.GET("/validate-subscription/:token/:owner", limitConcurrency(forwardRequest("serviceA", "GET")))

	router.POST("/upload", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/user/:owner", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/user/:owner/:id", limitConcurrency(forwardRequest("serviceB", "POST")))
	router.POST("/delete/:id", limitConcurrency(forwardRequest("serviceB", "POST")))

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

		service := loadBalancer.GetNextService(serviceName)
		if service.Name == "" {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "No available services"})
			return
		}

		url := "http://" + service.Host + ":" + strconv.Itoa(service.Port) + c.Request.URL.Path

		// Print data and host
		fmt.Printf("Request Data: %s\n", string(body))
		fmt.Printf("Request Host: %s\n", url)

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
			return
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read response"})
			return
		}

		// Print response data
		fmt.Printf("Response Data: %s\n", string(respBody))

		c.Data(resp.StatusCode, "application/json", respBody)
	}
}

func getStatus(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "Gateway is up and running"})
}
