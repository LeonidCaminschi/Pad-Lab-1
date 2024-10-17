package main

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

const maxConcurrentTasks = 10
const requestTimeout = 10 * time.Second

var semaphore = make(chan struct{}, maxConcurrentTasks)

func main() {
	router := gin.Default()
	router.POST("/register", limitConcurrency(postRegister))
	router.POST("/login", limitConcurrency(postLogin))
	router.POST("/registercard", limitConcurrency(postRegisterCard))
	router.POST("/subscribe", limitConcurrency(postSubscribe))
	router.POST("/cancel-subscription", limitConcurrency(postCancelSubscription))
	router.GET("/validate-user/:token", limitConcurrency(getValidateUser))
	router.GET("/validate-subscription/:token/:owner", limitConcurrency(getValidateSubscription))
	router.GET("/statusA", limitConcurrency(getStatusA))

	router.POST("/upload", limitConcurrency(postUpload))
	router.POST("/user/:owner", limitConcurrency(postUser))
	router.POST("/user/:owner/:id", limitConcurrency(postUserImage))
	router.POST("/delete/:id", limitConcurrency(postDelete))
	router.GET("statusB", limitConcurrency(getStatusB))

	router.Run("localhost:5003")
}

func limitConcurrency(handler gin.HandlerFunc) gin.HandlerFunc {
	return func(c *gin.Context) {
		semaphore <- struct{}{}
		defer func() { <-semaphore }()
		handler(c)
	}
}

func forwardRequest(c *gin.Context, url string, method string) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

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

	c.Data(resp.StatusCode, "application/json", respBody)
}

func postRegister(c *gin.Context) {
	url := "http://127.0.0.1:5001/register"
	forwardRequest(c, url, "POST")
}

func postLogin(c *gin.Context) {
	url := "http://127.0.0.1:5001/login"
	forwardRequest(c, url, "POST")
}

func postRegisterCard(c *gin.Context) {
	url := "http://127.0.0.1:5001/registercard"
	forwardRequest(c, url, "POST")
}

func postSubscribe(c *gin.Context) {
	url := "http://127.0.0.1:5001/subscribe"
	forwardRequest(c, url, "POST")
}

func postCancelSubscription(c *gin.Context) {
	url := "http://127.0.0.1:5001/cancel-subscription"
	forwardRequest(c, url, "POST")
}

func getValidateUser(c *gin.Context) {
	url := "http://127.0.0.1:5001/validate-user/" + c.Param("token")
	forwardRequest(c, url, "GET")
}

func getValidateSubscription(c *gin.Context) {
	url := "http://127.0.0.1:5001/validate-subscription/" + c.Param("token") + "/" + c.Param("owner")
	forwardRequest(c, url, "GET")
}

func getStatusA(c *gin.Context) {
	url := "http://127.0.0.1:5001/status"
	forwardRequest(c, url, "GET")
}

/////////////////////////////////////////////////////

func postUpload(c *gin.Context) {
	url := "http://127.0.0.1:5002/upload"
	forwardRequest(c, url, "POST")
}

func postUser(c *gin.Context) {
	url := "http://127.0.0.1:5002/user/" + c.Param("owner")
	forwardRequest(c, url, "POST")
}

func postUserImage(c *gin.Context) {
	url := "http://127.0.0.1:5002/user/" + c.Param("owner") + "/" + c.Param("id")
	forwardRequest(c, url, "POST")
}

func postDelete(c *gin.Context) {
	url := "http://127.0.0.1:5002/delete/" + c.Param("id")
	forwardRequest(c, url, "POST")
}

func getStatusB(c *gin.Context) {
	url := "http://127.0.0.1:5002/status"
	forwardRequest(c, url, "GET")
}
