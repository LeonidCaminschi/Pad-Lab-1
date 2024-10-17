package server

import (
	"encoding/json"
	"net/http"
	"sync"
)

type Service struct {
	Name string `json:"name"`
	Host string `json:"host"`
	Port int    `json:"port"`
}

var (
	services []Service
	mu       sync.Mutex
)

func RegisterHandler(w http.ResponseWriter, r *http.Request) {
	var service Service
	if err := json.NewDecoder(r.Body).Decode(&service); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid request payload"})
		return
	}

	if service.Name == "" || service.Host == "" || service.Port == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "Incomplete service information"})
		return
	}

	mu.Lock()
	defer mu.Unlock()

	for _, s := range services {
		if s.Name == service.Name && s.Host == service.Host && s.Port == service.Port {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "Duplicate service"})
			return
		}
	}

	services = append(services, service)

	response := map[string]string{"message": "Successfully registered service"}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func StatusHandler(w http.ResponseWriter, r *http.Request) {
	response := map[string]string{"status": "Service discovery is up and running"}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}
