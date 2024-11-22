from flask import Flask, jsonify, request
import socket
import requests
import time
import sys
from redis import Redis
from hashring import ConsistentHashRing

app = Flask(__name__)

# Initialize Redis connections
servers = {
    "redis://redis1:6379": Redis(host="redis1", port=6379),
    "redis://redis2:6379": Redis(host="redis2", port=6379),
    "redis://redis3:6379": Redis(host="redis3", port=6379),
}

# Create consistent hash ring
ring = ConsistentHashRing()

# Add servers to the ring
for server in servers.keys():
    ring.add_server(server)

@app.route('/store_key', methods=['POST'])
def store_key():
    data = request.json
    key = data['key']
    value = data['value']
    server = ring.get_server(key)
    redis_client = servers[server]
    redis_client.set(key, value)
    return jsonify({"Response": f"Stored {key} in {server}"}), 200

@app.route('/retrieve_key', methods=['GET'])
def retrieve_key():
    key = request.args.get('key')
    server = ring.get_server(key)
    redis_client = servers[server]
    value = redis_client.get(key)
    if value:
        return jsonify({"Response": f"Retrieved {key} from {server}: {value.decode('utf-8')}"}), 200
    else:
        return jsonify({"Response": f"{key} not found in {server}"}), 404
        
@app.route('/delete_key', methods=['DELETE'])
def delete_key():
    key = request.args.get('key')
    server = ring.get_server(key)
    redis_client = servers[server]
    result = redis_client.delete(key)
    if result:
        return jsonify({"Response": f"Deleted {key} from {server}"}), 200
    else:
        return jsonify({"Response": f"{key} not found in {server}"}), 404

@app.route('/add_server', methods=['POST'])
def add_server():
    data = request.json
    new_server = data['server']
    servers[new_server] = Redis.from_url(new_server)
    ring.add_server(new_server)
    return jsonify({"Response": f"Added server {new_server}"}), 200

@app.route('/remove_server', methods=['POST'])
def remove_server():
    data = request.json
    removed_server = data['server']
    ring.remove_server(removed_server)
    del servers[removed_server]
    return jsonify({"Response": f"Removed server {removed_server}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)