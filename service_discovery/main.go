package main

import (
	"log"
	"net"
	"net/http"
	"service-discovery/server"
	"strconv"
	"time"

	pb "service-discovery/service_discovery"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

var (
	pingsPerSecond = 1
)

func main() {
	http.HandleFunc("/register", server.RegisterHandler)
	http.HandleFunc("/status", server.StatusHandler)
	go func() {
		log.Println("Starting HTTP server on port 5005")
		if err := http.ListenAndServe(":5005", nil); err != nil {
			log.Fatalf("Failed to start HTTP server: %v", err)
		}
	}()

	// Start gRPC server for /discover endpoint
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen on port 50051: %v", err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterServiceDiscoveryServer(grpcServer, &server.Server{})

	reflection.Register(grpcServer)

	log.Println("Starting gRPC server on port 50051")
	go func() {
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatalf("Failed to start gRPC server: %v", err)
		}
	}()

	go startPeriodicPing()

	select {}
}

func startPeriodicPing() {
	ticker := time.NewTicker(time.Second / time.Duration(pingsPerSecond))
	defer ticker.Stop()

	for range ticker.C {
		services := server.GetRegisteredServices()
		for _, service := range services {
			go pingService(service)
		}
	}
}

func pingService(service server.Service) {
	url := "http://" + service.Host + ":" + strconv.Itoa(service.Port) + "/status"
	resp, err := http.Get(url)
	if err != nil {
		log.Printf("Failed to ping service %s: %v", service.Name, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Service %s returned non-OK status: %d", service.Name, resp.StatusCode)
		return
	}

	log.Printf("Service %s is up and running", service.Name)
}
