from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
import requests
import time
import redis

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

# @socketio.on('connect')
# def handle_connect():
#     emit('message', {'data': 'Connected to the server'})

# @socketio.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected')

# @socketio.on('subscribe_to_images')
# def handle_subscribe_to_images(data):
#     token = data.get('token')
#     owner = data.get('owner')

#     username = validate_user(token)
#     if not username:
#         emit('error', {"Response": "Invalid token"})
#         return

#     isvalid = validate_subscription(token, owner)
#     if not isvalid and owner != username:
#         emit('error', {"Response": "User does not have permission to view images"})
#         return

#     connection = get_db_connection()
#     cursor = connection.cursor()

#     cursor.execute("SELECT * FROM images WHERE username = %s", (owner,))
#     images = cursor.fetchall()
#     close_db_connection(cursor, connection)

#     emit('images', {"Response": images})

# @socketio.on('new_image')
# def handle_new_image(data):
#     token = data.get('token')
#     image = data.get('image')

#     username = validate_user(token)
#     if not username:
#         emit('error', {"Response": "Invalid token"})
#         return

#     connection = get_db_connection()
#     cursor = connection.cursor()

#     cursor.execute("SELECT * FROM images WHERE image = %s", (image,))
#     if cursor.fetchone():
#         emit('error', {"Response": "Image already exists"})
#         close_db_connection(cursor, connection)
#         return

#     cursor.execute("INSERT INTO images (username, image) VALUES (%s, %s)", (username, image))
#     connection.commit()
#     close_db_connection(cursor, connection)

#     emit('new_image', {"Response": "Image successfully published", "image": image})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)