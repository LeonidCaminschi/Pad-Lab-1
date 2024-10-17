package server

import (
	"context"
	pb "service-discovery/service_discovery"
)

type Server struct {
	pb.UnimplementedServiceDiscoveryServer
}

func (s *Server) Discover(ctx context.Context, req *pb.DiscoverRequest) (*pb.DiscoverResponse, error) {
	mu.Lock()
	defer mu.Unlock()

	var grpcServices []*pb.Service
	for _, service := range services {
		grpcServices = append(grpcServices, &pb.Service{
			Name: service.Name,
			Host: service.Host,
			Port: int32(service.Port),
		})
	}

	return &pb.DiscoverResponse{Services: grpcServices}, nil
}
