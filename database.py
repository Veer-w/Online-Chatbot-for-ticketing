import os
import mysql.connector

def create_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '1234'),
        auth_plugin='mysql_native_password',
        database=os.getenv('DB_NAME', 'museum_tickets')
    )

