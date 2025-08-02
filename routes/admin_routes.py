from flask import Blueprint, request, jsonify
import jwt
import datetime
from config import get_db_connection, token_secret
from flask_cors import cross_origin

admin_blueprint = Blueprint('admin', __name__)

# Hardcoded Admin Credentials
ADMIN_CREDENTIALS = {
    "email": "admin@gmail.com",
    "password": "Admin@1234",
    "role": "admin"
}

@admin_blueprint.route('/login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if email == ADMIN_CREDENTIALS["email"] and password == ADMIN_CREDENTIALS["password"]:
        token = jwt.encode({
            "email": email,
            "role": "admin",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, token_secret, algorithm="HS256")
        return jsonify({
            "message_key": "admin.login.success",
            "token": token
         }), 200

    return jsonify({
        "message_key": "admin.login.invalid_credentials"
    }), 401

@admin_blueprint.route('/details', methods=['GET'])
@cross_origin()
def admin_details():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({
            "message_key": "auth.token.missing"
        }), 401
    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") == "admin":
            return jsonify({
                "name": "Super Admin",
                "email": ADMIN_CREDENTIALS["email"],
                "role": "admin"
            }), 200
        else:
            return jsonify({
                "message_key": "auth.not_authorized"
            }), 403
    except jwt.ExpiredSignatureError:
        return jsonify({
            "message_key": "auth.token.expired"
        }), 401
    except jwt.InvalidTokenError:
        return jsonify({
            "message_key": "auth.token.invalid"
        }), 401

admin_blueprint.route('/prescriptions/all', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def admin_view_all_prescriptions():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({
            "message_key": "auth.header.missing"
        }), 401
    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "admin":
            return jsonify({
                "message_key": "auth.admin.required"
            }), 403
    except jwt.ExpiredSignatureError:
        return jsonify({
            "message_key": "auth.token.expired"
        }), 401
    except jwt.InvalidTokenError:
        return jsonify({
            "message_key": "auth.token.invalid"
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id, p.medicines, p.status, p.date_prescribed,
               d.name AS doctor_name,
               pt.name AS patient_name,
               ph.name AS pharmacy_name
        FROM prescriptions p
        JOIN users d ON p.doctor_id = d.id
        JOIN users pt ON p.patient_id = pt.id
        LEFT JOIN patient_profiles pp ON p.patient_id = pp.user_id
        LEFT JOIN users ph ON pp.preferred_pharmacy_id = ph.id
        ORDER BY p.date_prescribed DESC
    """)
    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(prescriptions), 200