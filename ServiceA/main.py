from flask import Flask, request, jsonify
import mysql.connector
import re
import secrets
import time
import socket
import requests
import sys

from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

backups = {}

# Endpoints
def is_valid_username_password(username, password):
    return re.match("^[a-zA-Z0-9]+$", username) and re.match("^[a-zA-Z0-9]+$", password)

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

@app.route('/metrics')
def metrics():
    return metrics.registry.generate_latest(), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"Response": "Username and password cannot be empty"}), 401
    
    if not is_valid_username_password(username, password):
        return jsonify({"Response": "Invalid character-use \".|/ please use only alphanumerical values"}), 401

    db_query = {
        "query": "SELECT * FROM users WHERE username = '" + str(username) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    if len(response.json().get("Response")[0]) > 0:
        return jsonify({"Response": "username already exists"}), 401
    
    db_query = {
        "query": "INSERT INTO users (username, password) VALUES ('" + str(username) + "', '" + str(password) + "')"
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to insert user"}), 500

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
    
    db_query = {
        "query": "SELECT * FROM users WHERE username = '" + str(username) + "' AND password = '" + str(password) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    
    if user:
        token = secrets.token_hex(8)
        db_query = {
            "query": "SELECT * FROM tokens WHERE username = '" + str(username) + "'"
        }
        print(db_query, flush=True)
        response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
        if len(response.json().get("Response")[0]) > 0:
            db_query = {
            "query": "UPDATE tokens SET token = '" + str(token) + "' WHERE username = '" + str(username) + "'"
            }
            print(db_query, flush=True)
            response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
        else:
            db_query = {
            "query": "INSERT INTO tokens (username, token) VALUES ('" + str(username) + "', '" + str(token) + "')"
            }
            print(db_query, flush=True)
            response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
        
        if response.status_code == 200:
            return jsonify({"Response": "Logged in successfully", "token": token}), 200
        else:
            return jsonify({"Response": "Failed to update/insert token"}), 500
    else:
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
    
    # if the card info and cvv are valid insert them into the billing table
    db_query = {
        "query": "SELECT username FROM tokens WHERE token = '" + str(token) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    if not user:
        return jsonify({"Response": "Invalid token"}), 401
    else:
        db_query = {
            "query": "SELECT * FROM billing WHERE card_info = '" + str(card_info) + "' OR username = '" + str(user[0][0]) + "'"
        }
        print(db_query, flush=True)
        response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
        print(response.json().get("Response")[0], flush=True)
        if len(response.json().get("Response")[0]) > 0:
            return jsonify({"Response": "User already has a card binded"}), 401
        
        db_query = {
            "query": "INSERT INTO billing (username, card_info, cvv, money) VALUES ('" + str(user[0][0]) + "', '" + str(card_info) + "', '" + str(cvv) + "', " + str(money) + ")"
        }
        print(db_query, flush=True)
        response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
        if response.status_code == 200:
            return jsonify({"Response": "Card registered successfully"}), 200
        else:
            return jsonify({"Response": "Failed to register card"}), 500

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    token = data.get('user')
    owner = data.get('owner')
    
    db_query = {
        "query": "SELECT username FROM tokens WHERE token = '" + str(token) + "'"
    }
    print(db_query, flush=True)
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    if not user:
        return jsonify({"Response": "Invalid token"}), 401
    
    db_query = {
        "query": "SELECT * FROM billing WHERE username = '" + str(user[0][0]) + "'"
    }
    print(db_query, flush=True)
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    card = response.json().get("Response")[0]
    if not card:
        return jsonify({"Response": "Invalid card could not be found for the current user"}), 401

    db_query = {
        "query": "SELECT * FROM subscription WHERE sender = '" + str(user[0][0]) + "' AND owner = '" + str(owner) + "'"
    }
    print(db_query, flush=True)
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    subscription = response.json().get("Response")[0]
    if subscription:
        return jsonify({"Response": "User already subscribed to this user"}), 401

    if int(card[0][3]) < 5:
        return jsonify({"Response": "Insufficient funds"}), 401
    
    db_query = {
        "query": "UPDATE billing SET money = money - 5 WHERE username = '" + str(user[0][0]) + "'"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Transaction Error reverting"}), 400

    db_query = {
        "query": "UPDATE billing SET money = money + 5 WHERE username = '" + str(owner) + "'"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Transaction Error reverting"}), 400

    db_query = {
        "query": "INSERT INTO subscription (sender, owner) VALUES ('" + str(user[0][0]) + "', '" + str(owner) + "')"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code == 200:
        return jsonify({"Response": "Successful subscription"}), 200
    else:
        return jsonify({"Response": "Transaction Error reverting"}), 400

@app.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    data = request.json
    token = data.get('user')
    owner = data.get('owner')
    
    db_query = {
        "query": "SELECT username FROM tokens WHERE token = '" + str(token) + "'"
    }
    print(db_query, flush=True)
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    if not user:
        return jsonify({"Response": "Invalid token"}), 401
    
    db_query = {
        "query": "SELECT * FROM subscription WHERE sender = '" + str(user[0][0]) + "' AND owner = '" + str(owner) + "'"
    }
    print(db_query, flush=True)
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    subscription = response.json().get("Response")[0]
    if not subscription:
        return jsonify({"Response": "Invalid subscription"}), 401
    
    db_query = {
        "query": "DELETE FROM subscription WHERE sender = '" + str(user[0][0]) + "' AND owner = '" + str(owner) + "'"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to cancel subscription"}), 500

    db_query = {
        "query": "UPDATE billing SET money = money + 5 WHERE username = '" + str(user[0][0]) + "'"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to update sender's balance"}), 500

    db_query = {
        "query": "UPDATE billing SET money = money - 5 WHERE username = '" + str(owner) + "'"
    }
    print(db_query, flush=True)
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to update owner's balance"}), 500

    return jsonify({"Response": "Successful subscription canceled"}), 200

@app.route('/validate-user/<token>', methods=['GET'])
def validate_user(token):
    db_query = {
        "query": "SELECT username FROM tokens WHERE token = '" + str(token) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    if not user:
        return jsonify({"Response": "Invalid token"}), 401
    
    return jsonify({"Response": "User successfully validated", "username": user[0][0]}), 200

@app.route('/validate-subscription/<token>/<owner>', methods=['GET'])
def validate_subscription(token, owner):
    db_query = {
        "query": "SELECT username FROM tokens WHERE token = '" + str(token) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    user = response.json().get("Response")[0]
    if not user:
        return jsonify({"Response": "Invalid token"}), 401
    
    db_query = {
        "query": "SELECT * FROM subscription WHERE sender = '" + str(user[0][0]) + "' AND owner = '" + str(owner) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    subscription = response.json().get("Response")[0]
    if not subscription:
        return jsonify({"Response": "User is not subscribed to this user"}), 401
    
    return jsonify({"Response": "User is subscribed to this user"}), 200

@app.route('/status', methods=['GET'])
def status():
    try:
        response = requests.get('http://pad-lab-1-database-replication-1:5000/status')
        if response.status_code != 200:
            return jsonify({"Response": "Service A is down", "Error": response.json()}), 500
    except Exception as e:
        return jsonify({"Response": "Service A is down", "Error": str(e)}), 500
    
    return jsonify({"Response": "Service A is up and running", "Host": socket.gethostname()}), 200

def register_service():
    service_info = {
        "name": "serviceA",
        "host": socket.gethostname(),
        "port": 5000
    }

    # pseudo circuit breaker xD
    timeout_limit = 5  # Timeout limit in seconds
    max_retries = 3  # Number of retries
    retry_delay = timeout_limit * 3.5  # Delay between retries in seconds

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

@app.route('/commit_erase_user', methods=['POST'])
def commit_erase_user():
    global backups
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"Response": "Username cannot be empty"}), 400
    
    db_query = {
        "query": "SELECT * FROM tokens WHERE username = '" + str(username) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    tokens_backup = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM billing WHERE username = '" + str(username) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    billing_backup = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM subscription WHERE sender = '" + str(username) + "' OR owner = '" + str(username) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    subscription_backup = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM users WHERE username = '" + str(username) + "'"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    users_backup = response.json().get("Response")[0]
    
    backups[username] = {
        "tokens": tokens_backup,
        "billing": billing_backup,
        "subscription": subscription_backup,
        "users": users_backup
    }
    
    db_query = {
        "query": "DELETE FROM tokens WHERE username = '" + str(username) + "'"
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    
    db_query = {
        "query": "DELETE FROM billing WHERE username = '" + str(username) + "'"
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    
    db_query = {
        "query": "DELETE FROM subscription WHERE sender = '" + str(username) + "' OR owner = '" + str(username) + "'"
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    
    db_query = {
        "query": "DELETE FROM users WHERE username = '" + str(username) + "'"
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    
    if response.status_code == 200:
        return jsonify({"Response": "Data erased successfully", "backups": backups}), 200
    else:
        return jsonify({"Response": "Failed to erase data"}), 500

@app.route('/rollback_erase_user', methods=['POST'])
def rollback_erase_user():
    global backups
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"Response": "Username cannot be empty"}), 400
    
    if username not in backups:
        return jsonify({"Response": f"No backup found for the given username: {username}, {backups}"}), 400
    
    db_query = {
        "query": "INSERT INTO tokens (username, token) VALUES " + ", ".join(
            [f"('{token[0]}', '{token[1]}')" for token in backups[username]["tokens"]]
        )
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to restore tokens"}), 500

    db_query = {
        "query": "INSERT INTO billing (username, card_info, cvv, money) VALUES " + ", ".join(
            [f"('{billing[0]}', '{billing[1]}', '{billing[2]}', {billing[3]})" for billing in backups[username]["billing"]]
        )
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to restore billing"}), 500

    db_query = {
        "query": "INSERT INTO subscription (sender, owner) VALUES " + ", ".join(
            [f"('{subscription[0]}', '{subscription[1]}')" for subscription in backups[username]["subscription"]]
        )
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to restore subscription"}), 500

    db_query = {
        "query": "INSERT INTO users (username, password) VALUES " + ", ".join(
            [f"('{user[0]}', '{user[1]}')" for user in backups[username]["users"]]
        )
    }
    response = requests.post('http://pad-lab-1-database-replication-1:5000/modify-query', json=db_query)
    if response.status_code != 200:
        return jsonify({"Response": "Failed to restore users"}), 500

    return jsonify({"Response": "Data restored successfully"}), 200

if __name__ == '__main__':
    register_service()
    app.run(debug=False, host='0.0.0.0', port=5000)