package main

import (
	"log"
	"net"
	"net/http"
	"service-discovery/server"

	pb "service-discovery/service_discovery"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

func main() {
	// Start HTTP server for /register endpoint
	http.HandleFunc("/register", server.RegisterHandler)
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

	// Register reflection service on gRPC server.
	reflection.Register(grpcServer)

	log.Println("Starting gRPC server on port 50051")
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to start gRPC server: %v", err)
	}
}
