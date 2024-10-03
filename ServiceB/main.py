from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# MySQL configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'ServiceB',
    'port': 3308
}

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

    connection = get_db_connection()
    cursor = connection.cursor()

    isvalid = validate_subscription(token, owner)
    if isvalid or owner == validate_user(token):
        cursor.execute("SELECT * FROM images WHERE username = %s", (owner,))
        images = cursor.fetchall()
        close_db_connection(cursor, connection)
        return jsonify({"Response": images}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User does not have permission to view images"}), 400

@app.route('/user/<owner>/<image>', methods=['POST'])
def get_image(owner, image):
    data = request.json
    token = data.get('user')

    connection = get_db_connection()
    cursor = connection.cursor()

    isvalid = validate_subscription(token, owner)
    if isvalid or owner == validate_user(token):
        # check if image exists first
        cursor.execute("SELECT * FROM images WHERE image = %s", (image,))
        image = cursor.fetchone()
        if not image:
            close_db_connection(cursor, connection)
            return jsonify({"Response": "Image not found"}), 400
        
        close_db_connection(cursor, connection)
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
        close_db_connection(cursor, connection)
        return jsonify({"Response": "Image successfully deleted"}), 200

    close_db_connection(cursor, connection)
    return jsonify({"Response": "User is not the owner of the image"}), 400

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
    socketio.run(app, host='localhost', port=5002)