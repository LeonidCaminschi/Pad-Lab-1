# Use the official Golang image as the base image
FROM golang:1.23

# Set the Current Working Directory inside the container
WORKDIR /app

# Copy go.mod and go.sum files
COPY go.mod go.sum ./

# Download all dependencies. Dependencies will be cached if the go.mod and go.sum files are not changed
RUN go mod download

# Copy the source from the current directory to the Working Directory inside the container
COPY . .

# Build the Go app
RUN go build -o service-discovery .

# Expose ports for HTTP and gRPC
EXPOSE 5005
EXPOSE 50051

# Command to run the executable
CMD ["./service-discovery"]