package server

import "sync"

type StorageService struct {
	Name string `json:"name"`
	Host string `json:"host"`
	Port int    `json:"port"`
}

var (
	storageServices []StorageService
	storageMu       sync.Mutex
)

func AddStorageService(service StorageService) {
	storageMu.Lock()
	defer storageMu.Unlock()
	storageServices = append(storageServices, service)
}

func GetStorageServices() []StorageService {
	storageMu.Lock()
	defer storageMu.Unlock()
	return storageServices
}
