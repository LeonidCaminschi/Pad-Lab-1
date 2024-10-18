package main

import (
	"context"
	"log"
	"sync"
	"time"

	pb "Gateway/service_discovery/service_discovery"

	"google.golang.org/grpc"
)

type Service struct {
	Name string
	Host string
	Port int
}

type LoadBalancer struct {
	services map[string][]Service
	index    map[string]int
	mu       sync.Mutex
}

func NewLoadBalancer() *LoadBalancer {
	return &LoadBalancer{
		services: make(map[string][]Service),
		index:    make(map[string]int),
	}
}

func (lb *LoadBalancer) DiscoverServices() {
	conn, err := grpc.Dial("service-discovery:50051", grpc.WithInsecure(), grpc.WithBlock())
	if err != nil {
		log.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewServiceDiscoveryClient(conn)

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	req := &pb.DiscoverRequest{}
	res, err := client.Discover(ctx, req)
	if err != nil {
		log.Fatalf("could not discover services: %v", err)
	}

	lb.mu.Lock()
	defer lb.mu.Unlock()

	lb.services = make(map[string][]Service)
	for _, s := range res.Services {
		service := Service{
			Name: s.Name,
			Host: s.Host,
			Port: int(s.Port),
		}
		lb.services[s.Name] = append(lb.services[s.Name], service)
	}
}

func (lb *LoadBalancer) GetNextService(serviceName string) Service {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	services, exists := lb.services[serviceName]
	if !exists || len(services) == 0 {
		return Service{}
	}

	index := lb.index[serviceName]
	service := services[index]
	lb.index[serviceName] = (index + 1) % len(services)
	return service
}
