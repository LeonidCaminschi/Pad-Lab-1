from flask import Flask, request, jsonify
import mysql.connector
import re
import secrets

app = Flask(__name__)

# MySQL configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'ServiceA',
    'port': 3307
}

# Establish MySQL connection
def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

def close_db_connection(cursor, connection):
    cursor.close()
    connection.close()

# Endpoints
def is_valid_username_password(username, password):
    return re.match("^[a-zA-Z0-9]+$", username) and re.match("^[a-zA-Z0-9]+$", password)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"Response": "Username and password cannot be empty"}), 401
    
    if not is_valid_username_password(username, password):
        return jsonify({"Response": "Invalid character-use \".|/ please use only alphanumerical values"}), 401

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "username already exists"}), 401
    
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    connection.commit()
    close_db_connection(connection=connection, cursor=cursor)
    
    return jsonify({"Response": "Account created"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"Response": "Username and password cannot be empty"}), 401
    
    if not is_valid_username_password(username, password):
        return jsonify({"Response": "Invalid character-use \".|/ please use only alphanumerical values"}), 401
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    
    if user:
        token = secrets.token_hex(8)
        cursor.execute("SELECT * FROM tokens WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.execute("UPDATE tokens SET token = %s WHERE username = %s", (token, username))
        else:
            cursor.execute("INSERT INTO tokens (username, token) VALUES (%s, %s)", (username, token))
        connection.commit()
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Loged in succesful", "token": token}), 200
    else:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid username/password please try again"}), 401

@app.route('/registercard', methods=['POST'])
def registercard():
    data = request.json
    token = data.get('user')
    card_info = data.get('card-info')
    cvv = data.get('cvv')
    money = data.get('money')

    if not card_info or not cvv:
        return jsonify({"Response": "Card information and cvv cannot be empty"}), 401
    
    if not re.match("^[0-9]+$", card_info) or not re.match("^[0-9]+$", cvv) or len(card_info) != 16 or len(cvv) != 3:
        return jsonify({"Response": "Invalid card information"}), 401
    
    # if the card info and cvv are valid inser them into the billing table
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM tokens WHERE token = %s", (token,))
    user = cursor.fetchone()
    if not user:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid token"}), 401
    else:
        cursor.execute("SELECT * FROM billing WHERE card_info = %s OR username = %s", (card_info, user[0]))
        if cursor.fetchone():
            close_db_connection(connection=connection, cursor=cursor)
            return jsonify({"Response": "User already has a card binded"}), 401
        
        cursor.execute("INSERT INTO billing (username, card_info, cvv, money) VALUES (%s, %s, %s, %s)", (user[0], card_info, cvv, money))
        connection.commit()
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Card registered succesfuly"}), 200

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    token = data.get('user')
    owner = data.get('owner')
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM tokens WHERE token = %s", (token,))
    user = cursor.fetchone()
    if not user:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid token"}), 401
    
    cursor.execute("SELECT * FROM billing WHERE username = %s", (user[0],))
    card = cursor.fetchone()
    if not card:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid card coujld not be found for the current user"}), 401

    cursor.execute("SELECT * FROM subscription WHERE sender = %s AND owner = %s", (user[0], owner))
    subscription = cursor.fetchall()
    if subscription:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "User already subscribed to this user"}), 401

    if card[4] < 5:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Insufficient funds"}), 401
    
    cursor.execute("UPDATE billing SET money = money - 5 WHERE username = %s", (user[0],))
    cursor.execute("UPDATE billing SET money = money + 5 WHERE username = %s", (owner,))

    cursor.execute("INSERT INTO subscription (sender, owner) VALUES (%s, %s)", (user[0], owner))

    try:
        connection.commit()
        subscription_successful = True
    except Exception as e:
        connection.rollback()
        subscription_successful = False

    if subscription_successful:
        return jsonify({"Response": "Succesful subscription"}), 200
    else:
        return jsonify({"Response": "Transaction Error reverting"}), 400

@app.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    data = request.json
    token = data.get('user')
    owner = data.get('owner')
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT username FROM tokens WHERE token = %s", (token,))
    user = cursor.fetchone()
    if not user:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid token"}), 401
    
    cursor.execute("SELECT * FROM subscription WHERE sender = %s AND owner = %s", (user[0], owner))
    subscription = cursor.fetchall()
    if not subscription:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid subscription"}), 401
    
    cursor.execute("DELETE FROM subscription WHERE sender = %s AND owner = %s", (user[0], owner))

    cursor.execute("UPDATE billing SET money = money + 5 WHERE username = %s", (user[0],))
    cursor.execute("UPDATE billing SET money = money - 5 WHERE username = %s", (owner,))

    try:
        connection.commit()
        cancellation_successful = True
    except Exception as e:
        connection.rollback()
        cancellation_successful = False

    if cancellation_successful:
        return jsonify({"Response": "Succesful subscription canceled"}), 200
    else:
        return jsonify({"Response": "Invalid user information"}), 400

@app.route('/validate-user/<token>', methods=['GET'])
def validate_user(token):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM tokens WHERE token = %s", (token,))
    user = cursor.fetchone()
    if not user:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid token"}), 401
    
    close_db_connection(connection=connection, cursor=cursor)
    return jsonify({"Response": "User succesfuly validated", "username":user[0]}), 200

@app.route('/validate-subscription/<token>/<owner>', methods=['GET'])
def validate_subscription(token, owner):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM tokens WHERE token = %s", (token,))
    user = cursor.fetchone()
    if not user:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "Invalid token"}), 401
    
    cursor.execute("SELECT * FROM subscription WHERE sender = %s AND owner = %s", (user[0], owner))
    subscription = cursor.fetchall()
    if not subscription:
        close_db_connection(connection=connection, cursor=cursor)
        return jsonify({"Response": "User is not subscribed to this user"}), 401
    
    close_db_connection(connection=connection, cursor=cursor)
    return jsonify({"Response": "User is subscribed to this user"}), 200

@app.route('/status', methods=['GET'])
def status():
    try:
        connection = get_db_connection()
        close_db_connection(connection=connection, cursor=connection.cursor())
    except Exception as e:
        return jsonify({"Response": "Service A is down"}), 500
    
    return jsonify({"Response": "Service A is up and running"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)