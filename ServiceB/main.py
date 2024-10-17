from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
import requests
import time
import redis
import socket
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# MySQL configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'db2',
    'database': 'ServiceB',
    'port': 3306
}

redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

def close_db_connection(cursor, connection):
    cursor.close()
    connection.close()

def validate_user(token):
    request = requests.get(f'http://127.0.0.1:5001/validate-user/%s' % token)
    if request.status_code == 200:
        return request.json().get('username')
    return None

def validate_subscription(token, owner):
    request = requests.get(f'http://127.0.0.1:5001/validate-subscription/%s/%s' % (token, owner))
    if request.status_code == 200:
        return True
    return None

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def check_timeout(response):
    # Set timeout limit (in seconds)
    timeout_limit = 5  # For example, 5 seconds
    duration = time.time() - request.start_time

    # If the request took longer than the timeout limit, return a 408 response
    if duration > timeout_limit:
        # Create a response object with the 408 status
        response = jsonify({"Response": "Request Timeout"})
        response.status_code = 408
        return response

    return response

@app.route('/upload', methods=['POST'])
def upload():
    data = request.json
    token = data.get('user')
    image = data.get('image')

    username = validate_user(token)
    if not username:
        return jsonify({"Response": "user not found"}), 400

    if not image:
        return jsonify({"Response": "image not valid"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM images WHERE image = %s", (image,))
    if cursor.fetchone():
        return jsonify({"Response": "Image already exists"}), 400

    cursor.execute("INSERT INTO images (username, image) VALUES (%s, %s)", (username, image))
    connection.commit()

    return jsonify({"Response": "Image successfully published"}), 200

@app.route('/user/<owner>', methods=['POST'])
def get_images(owner):
    data = request.json
    token = data.get('user')

    # Check Redis cache first
    cached_images = redis_client.get(f'images_{owner}')
    if cached_images:
        return jsonify({"Response": eval(cached_images)}), 200

    connection = get_db_connection()
    cursor = connection.cursor()

    isvalid = validate_subscription(token, owner)
    if isvalid or owner == validate_user(token):
        cursor.execute("SELECT * FROM images WHERE username = %s", (owner,))
        images = cursor.fetchall()
        close_db_connection(cursor, connection)

        # Store the result in Redis
        redis_client.set(f'images_{owner}', str(images))

        return jsonify({"Response": images}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User does not have permission to view images"}), 400

@app.route('/user/<owner>/<image>', methods=['POST'])
def get_image(owner, image):
    data = request.json
    token = data.get('user')

    # Check Redis cache first
    cached_image = redis_client.get(f'image_{image}')
    if cached_image:
        return jsonify({"Response": eval(cached_image)}), 200

    connection = get_db_connection()
    cursor = connection.cursor()

    isvalid = validate_subscription(token, owner)
    if isvalid or owner == validate_user(token):
        cursor.execute("SELECT * FROM images WHERE image = %s", (image,))
        image = cursor.fetchone()
        if not image:
            close_db_connection(cursor, connection)
            return jsonify({"Response": "Image not found"}), 400

        close_db_connection(cursor, connection)

        # Store the result in Redis
        redis_client.set(f'image_{image}', str(image))

        return jsonify({"Response": image}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User does not have permission to view image"}), 400

@app.route('/delete/<image>', methods=['POST'])
def delete_image(image):
    data = request.json
    token = data.get('user')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT username FROM images WHERE image = %s", (image,))
    username = cursor.fetchone()
    if not username:
        close_db_connection(cursor, connection)
        return jsonify({"Response": "Image not found"}), 400

    owner = validate_user(token)
    if username and username[0] == owner:
        cursor.execute("DELETE FROM images WHERE image = %s", (image,))
        connection.commit()

        # Invalidate the cache
        redis_client.delete(f'image_{image}')
        redis_client.delete(f'images_{username[0]}')

        close_db_connection(cursor, connection)
        return jsonify({"Response": "Image successfully deleted"}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User does not have permission to delete image"}), 400

@app.route('/status', methods=['GET'])
def status():
    try:
        connection = get_db_connection()
        close_db_connection(connection=connection, cursor=connection.cursor())
    except Exception as e:
        return jsonify({"Response": "Service B is down"}), 500
    
    return jsonify({"Response": "Service B is up and running"}), 200

all_lobbies = []
users = {}

@socketio.on('connect')
def handle_connect():
    print(f'Client connected with sid: {request.sid}')
    sid = request.sid
    users[sid] = {'username': None, 'lobby': None}  # Initialize with no username and no lobby
    emit('message', "Welcome to the server!")

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in users:
        username = users[sid]['username']
        lobby = users[sid]['lobby']
        if lobby:
            emit('message', f"{username} has disconnected")
        print(f'Client {username} disconnected')
        del users[sid]

@socketio.on('join_lobby')
def handle_join_lobby(data):
    sid = request.sid
    lobby = data.get('lobby')
    username = data.get('username')
    
    # Store username and lobby in the users dictionary
    users[sid]['username'] = username
    users[sid]['lobby'] = lobby

    all_lobbies.append(lobby)
    emit('message', f"{username} has joined the lobby {lobby}")

@socketio.on('leave_lobby')
def handle_leave_lobby():
    sid = request.sid
    username = users[sid]['username']
    lobby = users[sid]['lobby']

    if lobby in all_lobbies:
        all_lobbies.remove(lobby)
        emit('message', f"{username} has left the lobby {lobby}")
        users[sid]['lobby'] = None

@socketio.on('send_message')
def handle_send_message(data):
    sid = request.sid
    message = data.get('message')
    username = users[sid]['username']
    lobby = users[sid]['lobby']

    if lobby:
        emit('message', f"{username}: {message}")

def register_service():
    service_info = {
        "name": "serviceB",
        "host": socket.gethostname(),
        "port": 5000
    }

    timeout_limit = 5  # Timeout limit in seconds
    max_retries = 3  # Number of retries
    retry_delay = 2  # Delay between retries in seconds

    for attempt in range(max_retries):
        try:
            response = requests.post('http://pad-lab-1-service-discovery-1:5005/register', json=service_info, timeout=timeout_limit)
            if response.status_code == 200:
                print("Service registered successfully")
                break
            else:
                print(f"Failed to register service, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print("All attempts to register the service failed. Exiting.")
                sys.exit(1)

if __name__ == '__main__':
    # register_service()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)