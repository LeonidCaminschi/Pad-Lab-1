import unittest
import json
from flask import Flask
from main import app, get_db_connection, close_db_connection

import time

class ServiceATestCase(unittest.TestCase):

    def setUp(self):
        app.config.from_object('config.TestConfig')
        self.app = app.test_client()
        self.app.testing = True

        self.connection = get_db_connection()
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS test_ServiceA")
        self.cursor.execute("USE ServiceA")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                password VARCHAR(50) NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                token VARCHAR(50) NOT NULL
            )
        """)
        self.connection.commit()

    def tearDown(self):
        self.cursor.execute("DROP DATABASE test_ServiceA")
        close_db_connection(self.cursor, self.connection)

    def test_register(self):
        self.connection.commit()
        response = self.app.post('/register', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass'
        }), content_type='application/json')
        self.assertIn('Account created', response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)

    def test_register_existing_user(self):
        #self.cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('testuser', 'testpass'))
        self.connection.commit()
        response = self.app.post('/register', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertIn('username already exists', response.get_data(as_text=True))

    def test_login(self):
        #self.cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('testuser', 'testpass'))
        self.connection.commit()
        response = self.app.post('/login', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('"Loged in succesful', response.get_data(as_text=True))

    def test_login_invalid_user(self):
        response = self.app.post('/login', data=json.dumps({
            'username': 'invaliduser',
            'password': 'invalidpass'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid username/password please try again', response.get_data(as_text=True))

        self.cursor.execute("DELETE FROM tokens WHERE username = 'testuser'")
        self.cursor.execute("DELETE FROM users WHERE username = 'testuser'")

def suite():
    suite = unittest.TestSuite()
    suite.addTest(ServiceATestCase('test_register'))
    suite.addTest(ServiceATestCase('test_register_existing_user'))
    suite.addTest(ServiceATestCase('test_login'))
    suite.addTest(ServiceATestCase('test_login_invalid_user'))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())