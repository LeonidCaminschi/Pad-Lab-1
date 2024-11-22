import hashlib
import bisect
from redis import Redis

class ConsistentHashRing:
    def __init__(self, replicas=100):
        """
        Initialize the consistent hash ring.

        :param replicas: Number of virtual nodes (replicas) per server to improve distribution.
        """
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

    def _hash(self, key):
        """Hash a key using SHA-256 and return a large integer."""
        return int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16)

    def add_server(self, server):
        """
        Add a server to the hash ring.

        :param server: Server identifier (e.g., Redis connection string or object).
        """
        for i in range(self.replicas):
            replica_key = f"{server}-{i}"
            hash_value = self._hash(replica_key)
            self.ring[hash_value] = server
            bisect.insort(self.sorted_keys, hash_value)

    def remove_server(self, server):
        """
        Remove a server from the hash ring.

        :param server: Server identifier.
        """
        for i in range(self.replicas):
            replica_key = f"{server}-{i}"
            hash_value = self._hash(replica_key)
            self.ring.pop(hash_value, None)
            self.sorted_keys.remove(hash_value)

    def get_server(self, key):
        """
        Get the server responsible for a given key.

        :param key: The key to look up.
        :return: The server responsible for the key.
        """
        if not self.ring:
            return None
        
        hash_value = self._hash(key)
        index = bisect.bisect(self.sorted_keys, hash_value)
        
        # Wrap around to the first key if needed
        if index == len(self.sorted_keys):
            index = 0

        server_hash = self.sorted_keys[index]
        return self.ring[server_hash]