// Code generated by protoc-gen-go-grpc. DO NOT EDIT.
// versions:
// - protoc-gen-go-grpc v1.5.1
// - protoc             v3.12.4
// source: service_discovery.proto

package service_discovery

import (
	context "context"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.64.0 or later.
const _ = grpc.SupportPackageIsVersion9

const (
	ServiceDiscovery_Discover_FullMethodName = "/service_discovery.ServiceDiscovery/Discover"
)

// ServiceDiscoveryClient is the client API for ServiceDiscovery service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type ServiceDiscoveryClient interface {
	Discover(ctx context.Context, in *DiscoverRequest, opts ...grpc.CallOption) (*DiscoverResponse, error)
}

type serviceDiscoveryClient struct {
	cc grpc.ClientConnInterface
}

func NewServiceDiscoveryClient(cc grpc.ClientConnInterface) ServiceDiscoveryClient {
	return &serviceDiscoveryClient{cc}
}

func (c *serviceDiscoveryClient) Discover(ctx context.Context, in *DiscoverRequest, opts ...grpc.CallOption) (*DiscoverResponse, error) {
	cOpts := append([]grpc.CallOption{grpc.StaticMethod()}, opts...)
	out := new(DiscoverResponse)
	err := c.cc.Invoke(ctx, ServiceDiscovery_Discover_FullMethodName, in, out, cOpts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ServiceDiscoveryServer is the server API for ServiceDiscovery service.
// All implementations must embed UnimplementedServiceDiscoveryServer
// for forward compatibility.
type ServiceDiscoveryServer interface {
	Discover(context.Context, *DiscoverRequest) (*DiscoverResponse, error)
	mustEmbedUnimplementedServiceDiscoveryServer()
}

// UnimplementedServiceDiscoveryServer must be embedded to have
// forward compatible implementations.
//
// NOTE: this should be embedded by value instead of pointer to avoid a nil
// pointer dereference when methods are called.
type UnimplementedServiceDiscoveryServer struct{}

func (UnimplementedServiceDiscoveryServer) Discover(context.Context, *DiscoverRequest) (*DiscoverResponse, error) {
	return nil, status.Errorf(codes.Unimplemented, "method Discover not implemented")
}
func (UnimplementedServiceDiscoveryServer) mustEmbedUnimplementedServiceDiscoveryServer() {}
func (UnimplementedServiceDiscoveryServer) testEmbeddedByValue()                          {}

// UnsafeServiceDiscoveryServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to ServiceDiscoveryServer will
// result in compilation errors.
type UnsafeServiceDiscoveryServer interface {
	mustEmbedUnimplementedServiceDiscoveryServer()
}

func RegisterServiceDiscoveryServer(s grpc.ServiceRegistrar, srv ServiceDiscoveryServer) {
	// If the following call pancis, it indicates UnimplementedServiceDiscoveryServer was
	// embedded by pointer and is nil.  This will cause panics if an
	// unimplemented method is ever invoked, so we test this at initialization
	// time to prevent it from happening at runtime later due to I/O.
	if t, ok := srv.(interface{ testEmbeddedByValue() }); ok {
		t.testEmbeddedByValue()
	}
	s.RegisterService(&ServiceDiscovery_ServiceDesc, srv)
}

func _ServiceDiscovery_Discover_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(DiscoverRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ServiceDiscoveryServer).Discover(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: ServiceDiscovery_Discover_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(ServiceDiscoveryServer).Discover(ctx, req.(*DiscoverRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// ServiceDiscovery_ServiceDesc is the grpc.ServiceDesc for ServiceDiscovery service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var ServiceDiscovery_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "service_discovery.ServiceDiscovery",
	HandlerType: (*ServiceDiscoveryServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "Discover",
			Handler:    _ServiceDiscovery_Discover_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "service_discovery.proto",
}