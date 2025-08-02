from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from config import token_secret, get_db_connection
import jwt
from datetime import datetime, timedelta,date
from utils.security import check_jwt_role
from utils.emails import send_email  
def expire_old_slots(cursor):
    cursor.execute("""
        UPDATE appointment_slots
        SET status = 'expired'
        WHERE 
            (
                date < CURDATE()
                OR (date = CURDATE() AND end_time < CURTIME())
            )
            AND status = 'available'
    """)
def auto_complete_overdue_bookings(cursor):
    cursor.execute("""
        UPDATE booked_slots
        SET status = 'completed'
        WHERE status = 'booked'
          AND CONCAT(date, ' ', end_time) < NOW()
    """)

appointment_blueprint = Blueprint('appointment', __name__)

# Doctor Adds Availability Window
@appointment_blueprint.route('/add-slot', methods=['POST','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def add_appointment_slot():
    data = request.json
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    status = "available"

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401

    token = auth_header.split(" ")[1]
    decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
    email = decoded_token.get('email')
    role = decoded_token.get('role')

    if role != 'doctor':
        return jsonify({ "message_key": "auth.role.restricted" }), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    doctor_result = cursor.fetchone()
    if not doctor_result:
        return jsonify({ "message_key": "doctor.not_found" }), 404
    doctor_id = doctor_result[0]

    cursor.execute("""
        INSERT INTO appointment_slots (doctor_id, date, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (doctor_id, date, start_time, end_time, status))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({ "message_key": "appointment.slot.added" }), 200

# Fetch Available 20-Min Slots (No Overlaps)
@appointment_blueprint.route('/available-slots/<int:doctor_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def get_available_slots(doctor_id):
    selected_date = request.args.get('date')
    if not selected_date:
        return jsonify({ "message_key": "appointment.date.required" }), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch all available slots for the doctor on the date
        cursor.execute("""
            SELECT start_time, end_time
            FROM appointment_slots
            WHERE doctor_id = %s AND status = 'available' AND date = %s
        """, (doctor_id, selected_date))
        availability = cursor.fetchall()

        if not availability:
            return jsonify({ "slots": [] }), 200
        # 2. Fetch all booked slots for the doctor on the date
        cursor.execute("""
            SELECT start_time, end_time
            FROM booked_slots
            WHERE doctor_id = %s AND DATE(date) = %s
        """, (doctor_id, selected_date))
        booked = cursor.fetchall()

        # 3. Parse booked ranges into datetime ranges
        booked_ranges = []
        for b in booked:
            b_start = datetime.strptime(str(b['start_time']), '%H:%M:%S')
            b_end = datetime.strptime(str(b['end_time']), '%H:%M:%S')
            booked_ranges.append((b_start, b_end))

        # 4. Generate 20-minute non-overlapping slots
        all_intervals = []
        for slot in availability:
            start = datetime.strptime(str(slot['start_time']), '%H:%M:%S')
            end = datetime.strptime(str(slot['end_time']), '%H:%M:%S')

            while start + timedelta(minutes=20) <= end:
                interval_end = start + timedelta(minutes=20)

                overlapping = any(
                    booked_start < interval_end and start < booked_end
                    for (booked_start, booked_end) in booked_ranges
                )
                if not overlapping:
                    all_intervals.append({
                        "start_time": start.strftime('%H:%M'),
                        "end_time": interval_end.strftime('%H:%M'),
                        "date": selected_date,
                        "doctor_id": doctor_id
                    })

                start += timedelta(minutes=20)

        return jsonify({"slots": all_intervals}), 200

    except Exception as e:
        return jsonify({ "message_key": "server.internal_error", "details": str(e) }), 500
    finally:
        cursor.close()
        conn.close()
# Book 20-Minute Slot
@appointment_blueprint.route('/book-slot', methods=['POST','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def book_20min_slot():
    data = request.get_json()
    doctor_id = data.get("doctor_id")
    date = data.get("date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    # Prevent past bookings
    if datetime.strptime(date, '%Y-%m-%d').date() < datetime.today().date():
        return jsonify({ "message_key": "appointment.cannot_book_past" }), 400

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "patient":
            return jsonify({ "message_key": "auth.role.restricted" }), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": "Token error: " + str(e)}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({ "message_key": "patient.not_found" }), 404
    patient_id = user["id"]

    cursor.execute("""
        SELECT * FROM booked_slots
        WHERE doctor_id = %s AND date = %s
        AND (
            (start_time < %s AND end_time > %s) OR
            (start_time >= %s AND start_time < %s)
        )
    """, (doctor_id, date, end_time, start_time, start_time, end_time))
    overlapping = cursor.fetchall()
    if overlapping:
        return jsonify({ "message_key": "appointment.slot.overlap" }), 400

    cursor.execute("""
        INSERT INTO booked_slots (doctor_id, patient_id, date, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s)
    """, (doctor_id, patient_id, date, start_time, end_time))

    conn.commit()
    # Fetch doctor and patient details
    cursor.execute("SELECT name FROM users WHERE id = %s", (doctor_id,))
    doctor = cursor.fetchone()
    cursor.execute("SELECT name, email FROM users WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()
    cursor.execute("SELECT clinic_address FROM doctor_profiles WHERE user_id = %s", (doctor_id,))
    address_row = cursor.fetchone()
    clinic_address = address_row["clinic_address"] if address_row else "N/A"
# Compose email
    subject = "Appointment Confirmation – Local GP System"
    body = f"""
    Dear {patient['name']},

    We are pleased to confirm that your appointment has been successfully booked.

    Appointment Details:
    -------------------------------
    Doctor   : {doctor['name']}
    Date     : {date}
    Time     : {start_time} to {end_time}
    Location : {clinic_address}

    Please ensure to arrive a few minutes before your scheduled time. If you need to cancel or reschedule, you can do so by logging into your Local GP System account.

    Thank you for choosing our service.

    Best regards,  
    Local GP System Team
    """
    # Send email
    send_email(patient["email"], subject, body)

    cursor.close()
    conn.close()
    return jsonify({ "message_key": "appointment.booked.success" }), 200
# Cancel Booking
@appointment_blueprint.route('/cancel/<int:booking_id>', methods=['DELETE','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def cancel_booking(booking_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401
    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "patient":
            return jsonify({ "message_key": "auth.role.restricted" }), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": "Token error: " + str(e)}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({ "message_key": "appointment.cancel.not_found_or_unauthorized" }), 404
    patient_id = user[0]

    cursor.execute("""
        DELETE FROM booked_slots
        WHERE id = %s AND patient_id = %s
    """, (booking_id, patient_id))

    if cursor.rowcount == 0:
        return jsonify({ "message_key": "appointment.cancel.not_found_or_unauthorized" }), 404

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({ "message_key": "appointment.cancel.success" }), 200


# Patient View Their Booked Appointments
@appointment_blueprint.route('/my-appointments', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def get_my_appointments():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401

    token = auth_header.split(" ")[1]
    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded_token.get("role") != "patient":
            return jsonify({ "message_key": "auth.role.restricted" }), 403

        email = decoded_token.get("email")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get Patient ID
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        patient_id = user["id"]

        # Fetch appointments
        cursor.execute("""
                    SELECT b.id, b.date, b.start_time, b.end_time, b.status, u.name AS doctor_name
                    FROM booked_slots b
                    JOIN users u ON b.doctor_id = u.id
                    WHERE b.patient_id = %s
                    ORDER BY b.date, b.start_time
        """, (patient_id,))
        appointments = cursor.fetchall()

        # Convert all datetime/timedelta values to strings for JSON
        for appt in appointments:
            for key, value in appt.items():
                if isinstance(value, (datetime, timedelta)):
                    appt[key] = str(value)

        cursor.close()
        conn.close()
        return jsonify({"message": "Your upcoming appointments retrieved successfully.", "appointments": appointments}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({ "message_key": "auth.token.expired" }), 401
    except jwt.InvalidTokenError:
        return jsonify({ "message_key": "auth.token.invalid" }), 401
    
@appointment_blueprint.route('/doctor/bookings', methods=['GET','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def doctor_view_bookings():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
            return jsonify({ "message_key": "auth.role.restricted" }), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": "Token error: " + str(e)}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get doctor_id
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "Doctor not found"}), 404
    doctor_id = user["id"]

    # Fetch bookings
    cursor.execute("""
        SELECT b.id, b.date, b.start_time, b.end_time, u.name AS patient_name
        FROM booked_slots b
        JOIN users u ON b.patient_id = u.id
        WHERE b.doctor_id = %s
        ORDER BY b.date, b.start_time
    """, (doctor_id,))
    bookings = cursor.fetchall()

    # Convert datetime/timedelta values to strings
    for booking in bookings:
        for key, value in booking.items():
            if isinstance(value, (datetime, timedelta)):
                booking[key] = str(value)

    cursor.close()
    conn.close()

    return jsonify({"message": "Your scheduled patient appointments are fetched successfully.", "bookings": bookings}), 200

@appointment_blueprint.route('/complete/<int:booking_id>', methods=['PUT','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def mark_booking_completed(booking_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "message_key": "auth.token.missing" }), 401
    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
           return jsonify({ "message_key": "auth.role.restricted" }), 403
    except jwt.ExpiredSignatureError:
        return jsonify({ "message_key": "auth.token.expired" }), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": "Invalid token: " + str(e)}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ensure the booking exists and is linked to this doctor (optional enhancement)
        cursor.execute("""
            SELECT * FROM booked_slots WHERE id = %s
        """, (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            return jsonify({"message_key": "appointment.not_found"}), 404

        cursor.execute("""
            UPDATE booked_slots SET status = 'completed'
            WHERE id = %s
        """, (booking_id,))
        conn.commit()

        return jsonify({ "message_key": "appointment.completed.success"}), 200

    except Exception as e:
         return jsonify({"error": "Internal server error. Please try again later."}), 500

    finally:
        cursor.close()
        conn.close()


@appointment_blueprint.route('/upcoming-appointments', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def get_doctor_upcoming_appointments():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"message_key": "auth.token.missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
            return jsonify({"message_key": "auth.role.restricted"}), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": "Token error: " + str(e)}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    expire_old_slots(cursor)
    auto_complete_overdue_bookings(cursor)
    conn.commit()

    # 2. Get doctor_id
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    doctor = cursor.fetchone()
    if not doctor:
        return jsonify({"error": "doctor_not_found"}), 404
    doctor_id = doctor["id"]

    # 3. Fetch updated list of upcoming appointments
    cursor.execute("""
        SELECT b.id, b.date, b.start_time, b.end_time, b.status, b.patient_id, u.name AS patient_name
        FROM booked_slots b
        JOIN users u ON b.patient_id = u.id
        WHERE b.doctor_id = %s AND b.date >= CURDATE()
        ORDER BY b.date, b.start_time
    """, (doctor_id,))
    appointments = cursor.fetchall()

    for appt in appointments:
        for key, value in appt.items():
            if isinstance(value, (datetime, timedelta)):
                appt[key] = str(value)

    cursor.close()
    conn.close()

    return jsonify({
        "message": "doctor.upcoming_appointments.success",
        "appointments": appointments
    }), 200

@appointment_blueprint.route('/doctor/stats', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def doctor_dashboard_stats():
    auth_header = request.headers.get("Authorization")
    decoded, error, code = check_jwt_role(auth_header, 'doctor')
    if error:
        return jsonify(error), code
    doctor_id = decoded.get("id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # use dictionary=True to return dicts

    try:
        # Total distinct patients
        cursor.execute("""
            SELECT COUNT(DISTINCT patient_id) AS total FROM booked_slots
            WHERE doctor_id = %s
        """, (doctor_id,))
        total_patients = cursor.fetchone()['total']

        #  Completed appointments
        cursor.execute("""
            SELECT COUNT(*) AS total FROM booked_slots
            WHERE doctor_id = %s AND status = 'completed'
        """, (doctor_id,))
        completed = cursor.fetchone()['total']

        #  Weekly slots (count + full list)
        cursor.execute("""
            SELECT COUNT(*) AS total FROM appointment_slots
            WHERE doctor_id = %s
              AND date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 6 DAY)
        """, (doctor_id,))
        slots_this_week = cursor.fetchone()['total']

        cursor.execute("""
                SELECT date, start_time, end_time FROM appointment_slots
                WHERE doctor_id = %s
                AND date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 6 DAY)
                ORDER BY date, start_time
                """, (doctor_id,))
        raw_slots = cursor.fetchall()  # this will be a list of dicts
        weekly_slots = []
        for slot in raw_slots:
            weekly_slots.append({
                "date": slot["date"].strftime("%Y-%m-%d"),
                "start_time": str(slot["start_time"]),
                "end_time": str(slot["end_time"]),
            })
        return jsonify({
            "total_patients": total_patients,
            "completed_appointments": completed,
            "slots_this_week": slots_this_week,
            "weekly_slots": weekly_slots  # new key for frontend
        })

    finally:
        cursor.close()
        conn.close()
@appointment_blueprint.route('/all-for-patient/<int:patient_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def get_all_appointments_for_patient(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.id, b.date, b.start_time, b.end_time, b.status,
               d.name AS doctor_name
        FROM booked_slots b
        JOIN users d ON b.doctor_id = d.id
        WHERE b.patient_id = %s
        ORDER BY b.date DESC
    """, (patient_id,))
    
    appointments = cursor.fetchall()

    for appt in appointments:
        for key, value in appt.items():
            if isinstance(value, (datetime, timedelta)):
                appt[key] = str(value)

    cursor.close()
    conn.close()

    return jsonify({ "appointments": appointments }), 200
