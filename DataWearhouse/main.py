import time
import schedule
import mysql.connector
import requests

def extract_data():
    db_query = {
        "query": "SELECT * FROM tokens"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    tokens = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM billing"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    billing = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM subscription"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    subscription = response.json().get("Response")[0]
    
    db_query = {
        "query": "SELECT * FROM users"
    }
    response = requests.get('http://pad-lab-1-database-replication-1:5000/select', json=db_query)
    users = response.json().get("Response")[0]

    conn = mysql.connector.connect(
        user='root',
        password='',
        host='db2',
        database='ServiceB',
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images")
    images = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return tokens, billing, subscription, users, images

def transform_data(tokens, billing, subscription, users, images):
    print(tokens, billing, subscription, users, images, flush=True)
    transformed_tokens = [(token[0], token[1].upper(), token[2]) for token in tokens]
    transformed_billing = [(bill[0], bill[1].upper(), bill[2], bill[3], bill[4]) for bill in billing]
    transformed_subscription = [(sub[0], sub[1].upper(), sub[2].upper(), sub[3]) for sub in subscription]
    transformed_users = [(user[0].upper(), user[1]) for user in users]
    transformed_images = [(image[0].upper(), image[1]) for image in images]
    
    return transformed_tokens, transformed_billing, transformed_subscription, transformed_users, transformed_images

def load_data(transformed_tokens, transformed_billing, transformed_subscription, transformed_users, transformed_images):
    conn = mysql.connector.connect(
        database="Wearhouse",
        user="root",
        password="",
        host="db-wearhouse"
    )
    cursor = conn.cursor()

    # Insert or update users
    for user in transformed_users:
        cursor.execute("""
            INSERT INTO users (username, password) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE password=VALUES(password)
        """, user)

    # Insert or update tokens
    for token in transformed_tokens:
        cursor.execute("""
            INSERT INTO tokens (id, username, token) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE username=VALUES(username), token=VALUES(token)
        """, token)

    # Insert or update billing
    for bill in transformed_billing:
        cursor.execute("""
            INSERT INTO billing (id, username, card_info, cvv, money) VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE username=VALUES(username), card_info=VALUES(card_info), cvv=VALUES(cvv), money=VALUES(money)
        """, bill)

    # Insert or update subscription
    for sub in transformed_subscription:
        cursor.execute("""
            INSERT INTO subscription (id, sender, owner, subscription_date) VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE sender=VALUES(sender), owner=VALUES(owner), subscription_date=VALUES(subscription_date)
        """, sub)

    # Insert or update images
    for image in transformed_images:
        cursor.execute("""
            INSERT INTO images (image_name, image_data) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE image_data=VALUES(image_data)
        """, image)

    conn.commit()
    cursor.close()
    conn.close()

def etl_job():
    tokens, billing, subscription, users, images = extract_data()
    transformed_tokens, transformed_billing, transformed_subscription, transformed_users, transformed_images = transform_data(tokens, billing, subscription, users, images)
    load_data(transformed_tokens, transformed_billing, transformed_subscription, transformed_users, transformed_images)

# Schedule the ETL job to run every 30 seconds
schedule.every(30).seconds.do(etl_job)

while True:
    schedule.run_pending()
    time.sleep(1)