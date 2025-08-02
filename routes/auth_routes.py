from flask import Blueprint, request, jsonify
import bcrypt
import jwt
import datetime
from config import token_secret, get_db_connection
from utils.security import is_secure_password

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    #  Check if admin login
    if email == "admin@gmail.com" and password == "Admin@1234":
        token = jwt.encode({
            "email": email,
            "role": "admin",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, token_secret, algorithm="HS256")

        return jsonify({
            "message": "auth.login.admin_success",
            "token": token,
            "role": "admin"
        }), 200

    #  Otherwise, check for other users
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            token = jwt.encode({
                "email": user['email'],
                "role": user['role'],
                 "id": user["id"], 
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, token_secret, algorithm="HS256")
            return jsonify({
                "message": "auth.login.success",
                "token": token,
                "role": user['role']
            }), 200
        else:
            return jsonify({"error": "auth.login.invalid_credentials"}), 401
    else:
        return jsonify({"error": "common.db_connection_failed"}), 500


@auth_blueprint.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "auth.logout.auth_required"}), 401

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO blacklisted_tokens (token) VALUES (%s)", (token,))
            conn.commit()
            return jsonify({"message": "auth.logout.success"}), 200
        except Exception as err:
            return jsonify({"error": "auth.logout.server_error"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "common.db_connection_failed"}), 500
