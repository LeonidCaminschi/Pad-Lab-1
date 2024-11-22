from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
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

timeout_limit = 5

def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

def close_db_connection(cursor, connection):
    cursor.close()
    connection.close()

def validate_user(token):
    url = f'http://pad-lab-1-gateway-1:5003/validate-user/%s' % token
    for attempt in range(3):
        try:
            request = requests.get(url, timeout=timeout_limit)
            if request.status_code == 200:
                return request.json().get('username')
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(timeout_limit * 3.5)
    return None

def validate_subscription(token, owner):
    url = f'http://pad-lab-1-gateway-1:5003/validate-subscription/%s/%s' % (token, owner)
    for attempt in range(3):
        try:
            request = requests.get(url, timeout=timeout_limit)
            if request.status_code == 200:
                return True
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(timeout_limit * 3.5)
    return None

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def check_timeout(response):
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
    response = requests.get(f'http://redis-consistent-hashing:5006/retrieve_key?key=images_{owner}')
    cached_images = response.json().get('value') if response.status_code == 200 else None
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
        requests.post('http://redis-consistent-hashing:5006/store_key', json={"key": f'images_{owner}', "value": str(images)})

        return jsonify({"Response": images}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User does not have permission to view images"}), 400

@app.route('/user/<owner>/<image>', methods=['POST'])
def get_image(owner, image):
    data = request.json
    token = data.get('user')

    # Check Redis cache first
    response = requests.get(f'http://redis-consistent-hashing:5006/retrieve_key?key=images_{owner}')
    cached_image = response.json().get('value') if response.status_code == 200 else None
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
        requests.post('http://redis-consistent-hashing:5006/store_key', json={"key": f'images_{owner}', "value": str(image)})

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

        requests.delete(f'http://redis-consistent-hashing:5006/delete_key?key=images_{username[0]}')

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

@app.route('/rooms', methods=['GET'])
def get_rooms():
    return jsonify(list(rooms)), 200

# WebSocket event handlers
user_rooms = {}
rooms = set()

@socketio.on('join')
def on_join(data):
    username = data['username']
    for user in user_rooms.values():
        if user['username'] == username:
            send(f'Username {username} is already taken.', to=request.sid)
            return
    room = data['room']
    sid = request.sid
    user_rooms[sid] = {'username': username, 'room': room}
    rooms.add(room)
    join_room(room)
    send(f'{username} has entered the room.', to=room)

@socketio.on('leave')
def on_leave():
    sid = request.sid
    if sid in user_rooms:
        username = user_rooms[sid]['username']
        room = user_rooms[sid]['room']
        leave_room(room)
        send(f'{username} has left the room.', to=room)
        del user_rooms[sid]

@socketio.on('message')
def on_message(data):
    sid = request.sid
    if sid in user_rooms:
        room = user_rooms[sid]['room']
        username = user_rooms[sid]['username']
        send(f'{username}: {data["message"]}', to=room)
    else:
        send('You are not in a room.', to=sid)

def register_service():
    service_info = {
        "name": "serviceB",
        "host": socket.gethostname(),
        "port": 5000
    }

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
                time.sleep(retry_delay * 3.5)
            else:
                print("All attempts to register the service failed. Exiting.")
                sys.exit(1)

@app.route('/prepare_erase_user', methods=['POST'])
def prepare_erase_user():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({"Response": "Username not provided"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM images WHERE username = %s", (username,))
    images = cursor.fetchall()

    close_db_connection(cursor, connection)

    if images:
        return jsonify({"Response": "Data available for erasure", "Images": images}), 200
    else:
        return jsonify({"Response": "No data found for the given username"}), 200

@app.route('/commit_erase_user', methods=['POST'])
def commit_erase_user():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({"Response": "Username not provided"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM images WHERE username = %s", (username,))
        connection.commit()

        # Invalidate the cache
        requests.delete(f'http://redis-consistent-hashing:5006/delete_key?key=images_{username}')

        close_db_connection(cursor, connection)
        return jsonify({"Response": "Data erased successfully"}), 200
    except Exception as e:
        close_db_connection(cursor, connection)
        return jsonify({"Response": "Failed to erase data", "Error": str(e)}), 500

if __name__ == '__main__':
    register_service()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)