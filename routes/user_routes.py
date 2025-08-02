from flask import Blueprint, app, request, jsonify
import jwt
import bcrypt
import datetime
import re
from config import token_secret, get_db_connection, MAIL_USERNAME, MAIL_PASSWORD
from flask_mail import Mail, Message
from utils.security import is_secure_password, hash_password, is_token_blacklisted
from flask_cors import cross_origin
import requests

mail = Mail()
user_blueprint = Blueprint('user', __name__)

def setup_mail(app):
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=johnsmith179805@gmail.com,
        MAIL_PASSWORD="lismxmspsqzzjqph",
        MAIL_DEFAULT_SENDER=johnsmith179805@gmail.com
    )
    mail.init_app(app)

# Patient signup
@user_blueprint.route('/patient-signup', methods=['POST'])
def patient_signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    contact_number = data.get('contact_number')

    if not all([name, email, password, contact_number]):
        return jsonify({"error": "all_fields_required"}), 400

    password_error = is_secure_password(password)
    if password_error:
        return jsonify({"error": password_error}), 400

    hashed_password = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "user_already_exists"}), 400

        cursor.execute("INSERT INTO users (name, email, password, role, contact_number) VALUES (%s, %s, %s, %s, %s)",
                       (name, email, hashed_password, 'patient', contact_number))
        conn.commit()
        return jsonify({"message": "patient_registered_successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# admin adds doctor and patients
@user_blueprint.route('/add-user', methods=['POST'])
def add_user():
    data = request.json
    token = request.headers.get('Authorization')

    if not token:
        return jsonify({"error": "admin_auth_required"}), 401

    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get('role') != 'admin':
            return jsonify({"error": "only_admin_can_add_users"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip()

    if role not in ['doctor', 'pharmacist']:
        return jsonify({"error": "invalid_role"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "user_already_exists"}), 400

        # Insert into users table
        cursor.execute("INSERT INTO users (name, email, role) VALUES (%s, %s, %s)", (name, email, role))
        user_id = cursor.lastrowid

        # Generate secure reset token
        reset_token = jwt.encode({
            "email": email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }, token_secret, algorithm="HS256")

        reset_link = f"http://localhost:4200/set-password?token={reset_token}"


        subject = f"Welcome to Local GP System - Set Your Password"
        message_body = f"""
        Hello {name},<br><br>
        Your account as a {role} has been created in the Local GP System.<br>
        <a href="{reset_link}">Click here</a> to set your password and complete your profile.<br><br>
        Thank you,<br>
        Local GP System Admin
        """

        #  Send email before committing
        msg = Message(subject, recipients=[email], html=message_body)
        mail.send(msg)
        print(f" Email sent to {email}")

        # Insert placeholder profile in doctor or pharmacist table
        if role == 'doctor':
            cursor.execute("INSERT INTO doctor_profiles (user_id, specialization) VALUES (%s, '')", (user_id,))
        elif role == 'pharmacist':
            cursor.execute("INSERT INTO pharmacist_profiles (user_id, license_number) VALUES (%s, '')", (user_id,))

        conn.commit()
        return jsonify({"message": "user_added_and_email_sent"}), 201
    except Exception as err:
        conn.rollback()
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()
        
@user_blueprint.route('/update-doctor-profile', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def update_doctor_profile():
    data = request.json
    specialization = data.get('specialization')
    experience = data.get('experience')
    clinic_address = data.get('clinic_address')
    registration_no = data.get('registration_no')

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
    email = decoded_token.get('email')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user_id = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE doctor_profiles
        SET specialization=%s, experience=%s, clinic_address=%s, registration_no=%s
        WHERE user_id=%s
    """, (specialization, experience, clinic_address, registration_no, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "doctor_profile_updated_successfully"}), 200

@user_blueprint.route('/update-pharmacist-profile', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def update_pharmacist_profile():
    data = request.json
    license_number = data.get('license_number')
    store_name = data.get('store_name')
    store_address = data.get('store_address')
    store_postcode = data.get('store_postcode')

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
    email = decoded_token.get('email')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user_id = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE pharmacist_profiles
        SET license_number=%s, store_name=%s, store_address=%s,store_postcode=%s
        WHERE user_id=%s
    """, (license_number, store_name, store_address,store_postcode, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "pharmacist_profile_updated_successfully"}), 200

@user_blueprint.route('/get-all-patients', methods=['GET'])
def get_all_patients():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "admin_auth_required"}), 401

    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") != "admin":
            return jsonify({"error": "only_admin_can_access"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, email, contact_number, role FROM users WHERE role = 'patient'")
        patients = cursor.fetchall()
        return jsonify(patients), 200
    except Exception as err:
        return jsonify({"error": "internal_server_error"}), 500
    finally:
        cursor.close()
        conn.close()

@user_blueprint.route('/get-all-doctors', methods=['GET'])
def get_all_doctors():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "admin_auth_required"}), 401

    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") != "admin":
            return jsonify({"error": "only_admin_can_access"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.contact_number, d.specialization, d.experience, d.clinic_address
            FROM users u JOIN doctor_profiles d ON u.id = d.user_id
        """)
        doctors = cursor.fetchall()
        return jsonify(doctors), 200
    except Exception as err:
        return jsonify({"error": "internal_server_error"}), 500
    finally:
        cursor.close()
        conn.close()

@user_blueprint.route('/get-all-pharmacists', methods=['GET'])
def get_all_pharmacists():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "admin_auth_required"}), 401

    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") != "admin":
            return jsonify({"error": "only_admin_can_access"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.contact_number, p.license_number, p.store_name, p.store_address
            FROM users u JOIN pharmacist_profiles p ON u.id = p.user_id
        """)
        pharmacists = cursor.fetchall()
        return jsonify(pharmacists), 200
    except Exception as err:
        return jsonify({"error": "internal_server_error"}), 500
    finally:
        cursor.close()
        conn.close()

@user_blueprint.route('/details', methods=['GET'])
#@cross_origin()
def get_user_details():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]

    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        email = decoded_token.get('email')
        role = decoded_token.get('role')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if role == 'admin':
            return jsonify({
                "name": "Admin",
                "email": email,
                "role": "admin"
            }), 200
        elif role == 'doctor':
            cursor.execute("""
                SELECT u.id, u.name, u.email, u.contact_number, d.specialization, d.experience, d.clinic_address,d.registration_no
                FROM users u JOIN doctor_profiles d ON u.id = d.user_id
                WHERE u.email = %s
            """, (email,))
            doctor = cursor.fetchone()
            cursor.close()
            conn.close()
            if doctor:
                doctor["role"] = "doctor"
                return jsonify(doctor), 200
            else:
                return jsonify({"error": "doctor_profile_not_found"}), 404
        elif role == 'pharmacist':
            cursor.execute("""
                SELECT u.name, u.email, u.contact_number, p.license_number, p.store_name, p.store_address
                FROM users u JOIN pharmacist_profiles p ON u.id = p.user_id
                WHERE u.email = %s
            """, (email,))
            pharmacist = cursor.fetchone()
            cursor.close()
            conn.close()
            if pharmacist:
                pharmacist["role"] = "pharmacist"
                return jsonify(pharmacist), 200
            else:
                return jsonify({"error": "pharmacist_profile_not_found"}), 404
        else:
            cursor.execute("SELECT name, email, contact_number, role FROM users WHERE email = %s", (email,))
            patient = cursor.fetchone()
            cursor.close()
            conn.close()
            if patient:
                return jsonify(patient), 200
            else:
                return jsonify({"error": "patient_not_found"}), 404

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "session_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401
    
@user_blueprint.route('/set-password', methods=['POST'])
def set_password():
    data = request.json
    token = data.get('token')  #  Receive token, not email
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({"error": "token_and_password_required"}), 400

    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        email = decoded.get("email")  #  Extract email securely from token
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    password_error = is_secure_password(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    hashed_password = hash_password(new_password)

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
            conn.commit()
            return jsonify({"message": "password_set_successfully"}), 200
        except Exception as err:
            return jsonify({"error": str(err)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "Database connection failed"}), 500

@user_blueprint.route('/generate-reset-token', methods=['POST'])
def generate_reset_token():
    data = request.json
    email = data.get('email')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            reset_token = jwt.encode({
                "email": email,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            }, token_secret, algorithm="HS256")

            # Compose email with reset link
            reset_link = f"http://localhost:4200/reset-password?token={reset_token}"
            subject = "Reset Your Password"
            body = f"Hi,\n\nClick the link below to reset your password:\n{reset_link}\n\nThis link expires in 30 minutes."

            # Send email using Flask-Mail
            try:
                msg = Message(subject, recipients=[email], body=body)
                mail.send(msg)
                return jsonify({"message": "reset_email_sent"}), 200
            except Exception as e:
                return jsonify({"error": "email_send_failed"}), 500

        else:
            return jsonify({"error": "user_not_found"}), 404

    return jsonify({"error": "db_connection_failed"}), 500

@user_blueprint.route('/reset-password', methods=['POST','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def reset_password():
    data = request.json
    reset_token = data.get('token')
    new_password = data.get('new_password')

    if not reset_token or not new_password:
        return jsonify({"error": "token_and_password_required"}), 400

    try:
        decoded_token = jwt.decode(reset_token, token_secret, algorithms=["HS256"])
        email = decoded_token.get("email")

        hashed_password = hash_password(new_password)

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"message": "password_reset_successful"}), 200
        else:
            return jsonify({"error": "db_connection_failed"}), 500

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

@user_blueprint.route('/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "auth_required"}), 401

    try:
        if is_token_blacklisted(token):
            return jsonify({"error": "token_revoked"}), 401
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") != "admin":
            return jsonify({"error": "only_admin_can_delete"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check user role before deletion
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "user_not_found"}), 404

        role = user[0]
        # Manually delete profile from doctors or pharmacists table if needed
        if role == 'doctor':
            cursor.execute("DELETE FROM doctor_profiles WHERE user_id = %s", (user_id,))
        elif role == 'pharmacist':
            cursor.execute("DELETE FROM pharmacist_profiles WHERE user_id = %s", (user_id,))

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({"message": "user_deleted"}), 200
    except Exception as err:
        return jsonify({"error": "server_error", "details": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@user_blueprint.route('/get-all-doctors-dropdown', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'], supports_credentials=True)
def get_all_doctors_dropdown():
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    try:
        jwt.decode(token.split(" ")[1], token_secret, algorithms=["HS256"])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT u.id, u.name, d.clinic_address
            FROM users u
            JOIN doctor_profiles d ON u.id = d.user_id
        """)

        doctors = cursor.fetchall()
        return jsonify(doctors), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
@user_blueprint.route('/search-doctors', methods=['GET'])
def search_doctors_by_postcode_proximity():
    import requests

    full_postcode = request.args.get('postcode_prefix', '').strip().upper()
    print("🔎 User input postcode:", full_postcode)

    if not full_postcode:
        return jsonify({"error": "postcode_prefix_required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Step 1: Use Postcodes.io autocomplete to find valid postcode
        geo_resp = requests.get(f"https://api.postcodes.io/postcodes?q={full_postcode}")
        geo_data = geo_resp.json()

        if not geo_data.get("result"):
            return jsonify({"error": "invalid_postcode"}), 400

        first_valid_postcode = geo_data["result"][0]["postcode"]
        print(" Using closest valid postcode:", first_valid_postcode)

        # Step 2: Get lat/lon
        details_resp = requests.get(f"https://api.postcodes.io/postcodes/{first_valid_postcode}")
        if details_resp.status_code != 200:
            return jsonify({"error": "invalid_postcode"}), 400

        geo = details_resp.json()["result"]
        lat, lon = geo["latitude"], geo["longitude"]

        # Step 3: Find nearby postcode prefixes
        nearby_resp = requests.get(f"https://api.postcodes.io/postcodes?lon={lon}&lat={lat}&limit=10")
        nearby_postcodes = nearby_resp.json().get("result", [])

        seen_prefixes = set()
        for p in nearby_postcodes:
            postcode_prefix = p["postcode"].split(" ")[0]
            if postcode_prefix in seen_prefixes:
                continue
            seen_prefixes.add(postcode_prefix)

            # Check for doctors in this prefix
            cursor.execute("""
                SELECT u.id, u.name, u.email, d.specialization, d.experience, d.clinic_address
                FROM users u
                JOIN doctor_profiles d ON u.id = d.user_id
                WHERE d.clinic_address LIKE %s
                LIMIT 4
            """, (f"%{postcode_prefix}%",))
            matches = cursor.fetchall()
            if matches:
                print(f" Found doctors in postcode: {postcode_prefix}")
                return jsonify({
                    "doctors": matches,
                    "fallback": False,
                    "searched_postcode": first_valid_postcode,
                    "checked_prefixes": list(seen_prefixes)
                }), 200

        # Step 4: No matches in nearby → return all doctors as fallback
        print(" No nearby doctors found. Returning all doctors.")
        cursor.execute("""
            SELECT u.id, u.name, u.email, d.specialization, d.experience, d.clinic_address
            FROM users u
            JOIN doctor_profiles d ON u.id = d.user_id
            LIMIT 10
        """)
        all_doctors = cursor.fetchall()

        return jsonify({
            "doctors": all_doctors,
            "fallback": True,
            "fallback_reason": "No doctors found in nearby postcodes",
            "searched_postcode": first_valid_postcode,
            "checked_prefixes": list(seen_prefixes)
        }), 200

    except Exception as e:
        print(f" Error in postcode proximity search: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
@user_blueprint.route('/get-all-pharmacists-dropdown', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'], supports_credentials=True)
def get_all_pharmacists_dropdown():
    token = request.headers.get('Authorization')
    if not token or not token.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    try:
        decoded_token = jwt.decode(token.split(" ")[1], token_secret, algorithms=["HS256"])
        email = decoded_token.get("email")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        #  Step 1: Get patient postcode
        cursor.execute("SELECT pincode FROM patient_profiles WHERE user_id = (SELECT id FROM users WHERE email = %s)", (email,))
        row = cursor.fetchone()
        if not row or not row['pincode']:
            return jsonify({"error": "patient_postcode_missing"}), 400

        patient_pin = row['pincode'].strip().upper()
        patient_area = patient_pin.split()[0]  # e.g., 'LE6'

        #  Step 2: Get all pharmacists with postcodes
        cursor.execute("""
            SELECT u.id, u.name, p.store_name, p.store_address, p.store_postcode
            FROM users u
            JOIN pharmacist_profiles p ON u.id = p.user_id
            WHERE p.store_postcode IS NOT NULL
        """)
        all_pharmacies = cursor.fetchall()

        #  Step 3: Exact area match
        exact_matches = [p for p in all_pharmacies if p['store_postcode'].strip().upper().startswith(patient_area)]
        if exact_matches:
            return jsonify(exact_matches), 200

        #  Step 4: Fallback to 2 closest areas by character distance
        def area_only(postcode):
            return (postcode or "").strip().split()[0].upper()

        def area_distance(pharm):
            pharm_area = area_only(pharm['store_postcode'])
            # Match on prefix (e.g. 'LE') and measure distance of numeric part (e.g. '6')
            try:
                return abs(int(''.join(filter(str.isdigit, pharm_area))) - int(''.join(filter(str.isdigit, patient_area))))
            except:
                return 9999

        sorted_pharms = sorted(all_pharmacies, key=area_distance)

        return jsonify(sorted_pharms[:2]), 200  #  Return top 2 closest matches

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
@user_blueprint.route('/update-patient-profile', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def update_patient_profile():
    data = request.json
    address = data.get('address')
    city = data.get('city')
    pincode = data.get('pincode')
    preferred_pharmacy_id = data.get('preferred_pharmacy_id')

    #  Get user from token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        email = decoded.get("email")
        role = decoded.get("role")

        if role != "patient":
            return jsonify({"error": "only_patients_can_update"}), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user_id
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "user_not_found"}), 404
        user_id = user_row[0]

        # Check if profile exists
        cursor.execute("SELECT id FROM patient_profiles WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()

        if exists:
            # Fetch current data
            cursor.execute("SELECT address, city, pincode, preferred_pharmacy_id FROM patient_profiles WHERE user_id = %s", (user_id,))
            current = cursor.fetchone()

            # Preserve old values if new ones not provided
            address = address or current[0]
            city = city or current[1]
            pincode = pincode or current[2]
            preferred_pharmacy_id = preferred_pharmacy_id or current[3]

            cursor.execute("""
                UPDATE patient_profiles
                SET address = %s, city = %s, pincode = %s, preferred_pharmacy_id = %s
                WHERE user_id = %s
            """, (address, city, pincode, preferred_pharmacy_id, user_id))

        else:
            # Insert new profile
            cursor.execute("""
                INSERT INTO patient_profiles (user_id, address, city, pincode, preferred_pharmacy_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, address, city, pincode, preferred_pharmacy_id))

        conn.commit()
        return jsonify({"message": "patient_profile_updated"}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@user_blueprint.route('/patient-profile-status', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'], supports_credentials=True)
def patient_profile_status():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        email = decoded.get("email")
        role = decoded.get("role")

        if role != "patient":
            return jsonify({"error": "only_patients_can_check_profile_status"}), 403

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        #  Get user ID using email
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "user_not_found"}), 404

        user_id = user_row["id"]

        #  Check if patient profile exists
        cursor.execute("SELECT id FROM patient_profiles WHERE user_id = %s", (user_id,))
        profile_exists = cursor.fetchone()

        return jsonify({"profile_complete": bool(profile_exists)}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@user_blueprint.route('/get-patient-pharmacy/<int:patient_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def get_patient_pharmacy_id(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT preferred_pharmacy_id FROM patient_profiles WHERE user_id = %s", (patient_id,))
        result = cursor.fetchone()
        if result:
            return jsonify({"pharmacy_id": result[0]}), 200
        else:
            return jsonify({"pharmacy_id": None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

