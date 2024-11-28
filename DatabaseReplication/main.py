from flask import Flask, jsonify, request
import mysql.connector
import threading
import time

app = Flask(__name__)

databases = [
    {"host": "db1-1", "user": "root", "password": "", "database": "ServiceA"},
    {"host": "db1-2", "user": "root", "password": "", "database": "ServiceA"},
    {"host": "db1-3", "user": "root", "password": "", "database": "ServiceA"}
]

inaccessible_databases = []
current_master = databases[0]

def check_database_status(db_config):
    try:
        connection = mysql.connector.connect(**db_config)
        connection.close()
        return True
    except mysql.connector.Error:
        return False

def fix_database(db, current_master):
    try:
        master_connection = mysql.connector.connect(**current_master)
        master_cursor = master_connection.cursor()

        recovered_connection = mysql.connector.connect(**db)
        recovered_cursor = recovered_connection.cursor()

        master_cursor.execute("SHOW TABLES")
        tables = master_cursor.fetchall()
        for (table,) in tables:
            master_cursor.execute(f"SELECT * FROM {table}")
            rows = master_cursor.fetchall()
            columns = [desc[0] for desc in master_cursor.description]

            recovered_cursor.execute(f"DELETE FROM {table}")

            for row in rows:
                placeholders = ', '.join(['%s'] * len(row))
                columns_str = ', '.join(columns)
                recovered_cursor.execute(
                    f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", row
                )

        recovered_connection.commit()

        master_cursor.close()
        master_connection.close()
        recovered_cursor.close()
        recovered_connection.close()

        databases.append(db)
        inaccessible_databases.remove(db)
        print(f"Database {db['host']} is back online, data synchronized, and added to the list.")
    except mysql.connector.Error as e:
        print(f"Error synchronizing database {db['host']}: {str(e)}")

def change_master():
    global current_master
    for db in databases:
        if db != current_master and check_database_status(db):
            current_master = db
            print(f"Master database changed to {current_master['host']}")
            return True
    return False

@app.route('/insert', methods=['POST'])
def post_insert():
    global current_master
    global inaccessible_databases
    data = request.json
    query = data.get('query')

    err = ""

    for db in databases[:]:
        if not check_database_status(db):
            inaccessible_databases.append(db)
            databases.remove(db)

    for db in inaccessible_databases[:]:
        if check_database_status(db):
            databases.append(db)
            inaccessible_databases.remove(db)
            try:
                master_connection = mysql.connector.connect(**current_master)
                master_cursor = master_connection.cursor()

                recovered_connection = mysql.connector.connect(**db)
                recovered_cursor = recovered_connection.cursor()

                master_cursor.execute("SHOW TABLES")
                tables = master_cursor.fetchall()
                for (table,) in reversed(tables):
                    master_cursor.execute(f"SELECT * FROM {table}")
                    rows = master_cursor.fetchall()
                    columns = [desc[0] for desc in master_cursor.description]

                    recovered_cursor.execute(f"DELETE FROM {table}")

                    for row in rows:
                        placeholders = ', '.join(['%s'] * len(row))
                        columns_str = ', '.join(columns)
                        recovered_cursor.execute(
                            f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", row
                        )

                recovered_connection.commit()

                master_cursor.close()
                master_connection.close()
                recovered_cursor.close()
                recovered_connection.close()
                
                err = (f"Database {db['host']} is back online, data synchronized, and added to the list.")
            except mysql.connector.Error as e:
                err = (f"Error synchronizing database {db['host']}: {str(e)}")
    
    if not check_database_status(current_master):
        if not change_master():
            return jsonify({"error": "No accessible master database available"}), 500

    try:
        for db in databases:
            connection = mysql.connector.connect(**db)
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            cursor.close()
            connection.close()
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"Response": "Succesful insertion in available databases " + str(inaccessible_databases) + " " + str(err)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)