from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from config import token_secret, get_db_connection, STRIPE_SECRET_KEY
import jwt
from datetime import datetime
from utils.security import check_jwt_role
from utils.emails import send_email 
import stripe 

prescription_blueprint = Blueprint('prescription', __name__)

@prescription_blueprint.route('/add', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def add_prescription():
    import re

    data = request.get_json()
    conn = get_db_connection()         
    cursor = conn.cursor(dictionary=True)

    doctor_id = data.get("doctor_id")
    patient_id = data.get("patient_id")
    appointment_id = data.get("appointment_id")
    medicines = data.get("medicines")
    instructions = data.get("instructions", "")
    status = data.get("status", "Ready for Pickup")
    payment_note = data.get("payment_note", "")
    pharmacy_id = data.get("pharmacy_id") or None

    print("Prescription Add Payload:", data)

    if not all([appointment_id, doctor_id, patient_id, medicines]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Step 1: Check patient preferred pharmacy
        if not pharmacy_id:
            cursor.execute("SELECT preferred_pharmacy_id FROM patient_profiles WHERE user_id = %s", (patient_id,))
            pharmacy_row = cursor.fetchone()
            if pharmacy_row and pharmacy_row['preferred_pharmacy_id']:
                pharmacy_id = pharmacy_row['preferred_pharmacy_id']

        # Step 2: If still no pharmacy, auto-match using doctor's area
        if not pharmacy_id:
            cursor.execute("SELECT clinic_address FROM users WHERE id = %s", (doctor_id,))
            doctor_row = cursor.fetchone()
            if doctor_row:
                clinic_address = doctor_row['clinic_address']
                area_prefix = clinic_address.split()[0]  # Example: "LE3"
                cursor.execute("SELECT user_id FROM pharmacist_profiles WHERE store_address LIKE %s LIMIT 1", (f"%{area_prefix}%",))
                pharmacy_match = cursor.fetchone()
                if pharmacy_match:
                    pharmacy_id = pharmacy_match['user_id']
                else:
                    print("⚠️ No nearby pharmacy found.")
            else:
                print("⚠️ Doctor not found.")

        # Step 3: Insert into prescriptions table
        insert_cursor = conn.cursor()
        insert_cursor.execute("""
            INSERT INTO prescriptions (
                appointment_id,
                doctor_id,
                patient_id,
                pharmacy_id,
                medicines,
                instructions,
                status,
                payment_note,
                date_prescribed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
        """, (
            appointment_id,
            doctor_id,
            patient_id,
            pharmacy_id,
            medicines,
            instructions,
            status,
            payment_note
        ))

        # Step 4: Update inventory (increment 20 units per medicine)
        med_list = [m.strip().lower() for m in re.split(r",|\n", medicines) if m.strip()]
        for med in med_list:
            cursor.execute("""
                INSERT INTO pharmacy_inventory (pharmacist_id, medicine_name, quantity)
                VALUES (%s, %s, 20)
                ON DUPLICATE KEY UPDATE quantity = quantity + 20, last_updated = NOW()
            """, (pharmacy_id, med))

        conn.commit()
        insert_cursor.close()
        cursor.close()
        conn.close()

        return jsonify({"message": "Prescription added successfully"}), 200

    except Exception as e:
        print(" DB error:", e)
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

@prescription_blueprint.route('/my', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def get_patient_prescriptions():
    auth_header = request.headers.get("Authorization")
    decoded, error_response, status = check_jwt_role(auth_header, "patient")
    if error_response:
        return jsonify(error_response), status

    email = decoded.get("email")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    patient = cursor.fetchone()
    if not patient:
        return jsonify({"error": "patient_not_found"}), 404

    patient_id = patient["id"]

    cursor.execute("""
        SELECT p.id, p.medicines, p.status, p.date_prescribed, u.name AS doctor_name
        FROM prescriptions p
        JOIN users u ON p.doctor_id = u.id
        WHERE p.patient_id = %s
    """, (patient_id,))
    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(prescriptions), 200

@prescription_blueprint.route('/pharmacy', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def get_pharmacy_prescriptions():
    auth_header = request.headers.get("Authorization")
    decoded, error_response, status = check_jwt_role(auth_header, "pharmacist")
    if error_response:
        return jsonify(error_response), status

    email = decoded.get("email")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    pharmacist = cursor.fetchone()
    if not pharmacist:
        return jsonify({"error": "pharmacist_not_found"}), 404

    pharmacist_id = pharmacist["id"]

    cursor.execute("""
    SELECT p1.id,p1.patient_id, p1.medicines, p1.status, p1.date_prescribed, u.name AS patient_name
    FROM prescriptions p1
    JOIN users u ON p1.patient_id = u.id
    JOIN patient_profiles pp ON pp.user_id = p1.patient_id
    WHERE pp.preferred_pharmacy_id = %s
      AND p1.date_prescribed = (
        SELECT MAX(p2.date_prescribed)
        FROM prescriptions p2
        WHERE p2.patient_id = p1.patient_id
      )
""", (pharmacist_id,))

    prescriptions = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(prescriptions), 200
@prescription_blueprint.route('/edit/<int:prescription_id>', methods=['PUT'])
@cross_origin(origins=['http://localhost:4200'])
def update_prescription(prescription_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "authorization_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
            return jsonify({"error": "only_doctors_can_edit"}), 403
        doctor_email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": "Token error: " + str(e)}), 401

    data = request.get_json()
    updated_medicines = data.get("medicines")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure doctor is editing their own prescription
    cursor.execute("SELECT id FROM users WHERE email = %s", (doctor_email,))
    doctor = cursor.fetchone()
    if not doctor:
        return jsonify({"error": "doctor_not_found"}), 404
    doctor_id = doctor[0]

    cursor.execute("""
        UPDATE prescriptions
        SET medicines = %s
        WHERE id = %s AND doctor_id = %s
    """, (updated_medicines, prescription_id, doctor_id))

    if cursor.rowcount == 0:
        return jsonify({"error": "prescription_edit_denied"}), 404

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "prescription_updated"}), 200

@prescription_blueprint.route('/status/<int:prescription_id>', methods=['PUT', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def update_prescription_status(prescription_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "authorization_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "pharmacist":
            return jsonify({"error": "only_pharmacists_can_update"}), 403
        pharmacist_email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": f"token_invalid: {str(e)}"}), 401

    data = request.get_json()
    new_status = data.get("status")
    payment_note = data.get("payment_note", "")
    print("🛠️ Received from frontend - payment_note:", repr(payment_note))
    if not new_status:
        return jsonify({"error": "missing_status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get pharmacist ID
        cursor.execute("SELECT id FROM users WHERE email = %s", (pharmacist_email,))
        pharmacist = cursor.fetchone()
        if not pharmacist:
            return jsonify({"error": "pharmacist_not_found"}), 404
        pharmacist_id = pharmacist[0]

        # Ensure pharmacist is assigned to this prescription
        cursor.execute("""
            SELECT p.id
            FROM prescriptions p
            JOIN patient_profiles pp ON p.patient_id = pp.user_id
            WHERE p.id = %s AND pp.preferred_pharmacy_id = %s
        """, (prescription_id, pharmacist_id))
        match = cursor.fetchone()
        if not match:
            return jsonify({"error": "prescription_not_authorized"}), 403

        # Update prescription
        cursor.execute("""
            UPDATE prescriptions
            SET status = %s, payment_note = %s
            WHERE id = %s
        """, (new_status, payment_note, prescription_id))
        conn.commit()
        if new_status.lower() == 'dispensed':
            send_dispense_email_to_patient(prescription_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT medicines, pharmacy_id, payment_note
                FROM prescriptions
                WHERE id = %s
            """, (prescription_id,))
            prescription = cursor.fetchone()

            if prescription:
                med_list = [m.strip().lower() for m in prescription["medicines"].split(',') if m.strip()]
                print(" Medicines to decrement:", med_list)

                # Extract quantity (default to 1 if not found)
                import re
                note = prescription["payment_note"] or ""
                unit_match = re.search(r"(\d+)\s*units?", note, re.IGNORECASE)
                fallback_match = re.search(r"(\d+)", note)

                if unit_match:
                    quantity_to_decrease = int(unit_match.group(1))
                    print(f" Decreasing each medicine by (from 'units'): {quantity_to_decrease}")
                elif fallback_match:
                    quantity_to_decrease = int(fallback_match.group(1))
                    print(f" Decreasing each medicine by (fallback number): {quantity_to_decrease}")
                else:
                    quantity_to_decrease = 1
                    print(" No number found, defaulting to 1 unit")

                for med in med_list:
                    print(f" Updating inventory for: {med}")
                    cursor.execute("""
                        UPDATE pharmacy_inventory
                        SET quantity = GREATEST(quantity - %s, 0), last_updated = NOW()
                        WHERE pharmacist_id = %s AND medicine_name = %s
                    """, (quantity_to_decrease, prescription["pharmacy_id"], med))
                conn.commit()
            else:
                print(" No prescription found for inventory update.")
        return jsonify({"message": "prescription_status_updated"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"update_failed: {str(e)}"}), 500

    finally:
        cursor.close()
        conn.close()

@prescription_blueprint.route('/by-patient/<int:patient_id>', methods=['GET','OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def prescriptions_by_patient(patient_id):
    auth_header = request.headers.get("Authorization")
    decoded, error_response, status = check_jwt_role(auth_header, "doctor")
    if error_response:
        return jsonify(error_response), status

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id, p.medicines, p.status, p.date_prescribed,
               u.name AS doctor_name
        FROM prescriptions p
        JOIN users u ON p.doctor_id = u.id
        WHERE p.patient_id = %s
        ORDER BY p.date_prescribed DESC
    """, (patient_id,))
    
    prescriptions = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({ "prescriptions": prescriptions }), 200
@prescription_blueprint.route('/by-appointment/<int:appointment_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:4200'])
def get_prescription_by_appointment(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, doctor_id, patient_id, medicines, status, payment_note
        FROM prescriptions
        WHERE appointment_id = %s
    """, (appointment_id,))
    
    prescription = cursor.fetchone()

    #  Fix unread result error
    while cursor.nextset():
        pass

    cursor.close()
    conn.close()

    return jsonify({ "prescription": prescription }), 200
def extract_amount_from_payment_note(payment_note):
    try:
        # Example format: "£200 to be paid via UPI or Cash"
        import re
        match = re.search(r"(\d+)", payment_note)
        if match:
            return int(match.group(1))
        else:
            return None
    except:
        return None
def send_dispense_email_to_patient(prescription_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch prescription + patient details
        cursor.execute("""
            SELECT 
                p.medicines,
                p.payment_note,
                u_patient.email AS patient_email,
                pp.store_name AS pharmacy_store_name
            FROM prescriptions p
            JOIN users u_patient ON p.patient_id = u_patient.id
            JOIN users u_pharmacy ON p.pharmacy_id = u_pharmacy.id
            JOIN pharmacist_profiles pp ON p.pharmacy_id = pp.user_id           
            WHERE p.id = %s
        """, (prescription_id,))
        prescription = cursor.fetchone()

        if not prescription:
            print(f" No prescription found for ID {prescription_id}")
            return

        patient_email = prescription["patient_email"]
        pharmacy_store_name = prescription["pharmacy_store_name"]
        medicines = prescription["medicines"]
        payment_note = prescription["payment_note"]

        #  Create Stripe Checkout Session
        amount = extract_amount_from_payment_note(payment_note)
        if not amount:
            print(f" No valid amount found in payment_note")
            return

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {'name': 'Prescription Payment'},
                    'unit_amount': int(amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"http://localhost:4200/pay-success/{prescription_id}",
            cancel_url=f"http://localhost:4200/pay-cancel/{prescription_id}",
            metadata={
                "prescription_id": prescription_id,
                "patient_email": patient_email
            }
        )
        checkout_url = session.url

        # Build new Email
        subject = f"Your Prescription is Ready for Pickup at {pharmacy_store_name}"
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 30px;">
    <div style="background: white; padding: 20px; border-radius: 8px;">
        <h2 style="color: #6c63ff;">Prescription Ready!</h2>
        <p>Dear Patient,</p>
        <p>Your prescription is ready for pickup at <strong>{pharmacy_store_name}</strong>.</p>

        <h3 style="color: #3b82f6;">Medicines:</h3>
        <p>{medicines}</p>

        <h3 style="color: #3b82f6;">Payment Instructions:</h3>
        <p>{payment_note or 'Please check with the pharmacy counter for payment.'}</p>

        <h3 style="color: #3b82f6;">Quick Payment:</h3>
        <div style="margin: 20px 0;">
            <a href="{checkout_url}" 
               style="background: #3b82f6; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                 Pay Now
            </a>
        </div>

        <p>After payment, collect your medicines at the pharmacy.</p>

        <p style="margin-top: 20px;">Thank you for using our healthcare services!</p>
        <p style="font-size: 13px; color: #999;">This is an automated message. Please do not reply.</p>
    </div>
</body>
</html>
"""
        # Send email
        send_email(
            to_email=patient_email,
            subject=subject,
            html_body=html_body
        )

        print(f" Dispense email sent with Stripe link to {patient_email}")

    except Exception as e:
        print(f" Failed to send dispense email: {str(e)}")

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
@prescription_blueprint.route('/mark-collected/<int:prescription_id>', methods=['PUT'])
@cross_origin(origins=['http://localhost:4200'])
def mark_prescription_collected(prescription_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE prescriptions
            SET status = %s
            WHERE id = %s
        """, ('Collected', prescription_id))

        conn.commit()

        return jsonify({"message": "Prescription marked as collected."}), 200

    except Exception as e:
        conn.rollback()
        print
@prescription_blueprint.route('/pharmacy/inventory', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def get_pharmacy_inventory():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        email = decoded.get("email")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "pharmacist_not_found"}), 404
        pharmacist_id = user["id"]

        cursor.execute("""
            SELECT medicine_name, quantity
            FROM pharmacy_inventory
            WHERE pharmacist_id = %s
        """, (pharmacist_id,))
        raw_inventory = cursor.fetchall()

        #  Normalize names and merge
        deduped_inventory = {}
        for item in raw_inventory:
            normalized = item['medicine_name'].lower().replace(" ", "")
            if normalized in deduped_inventory:
                deduped_inventory[normalized]['quantity'] += item['quantity']
            else:
                deduped_inventory[normalized] = {
                    'medicine_name': item['medicine_name'],
                    'quantity': item['quantity']
                }

        return jsonify({"inventory": list(deduped_inventory.values())}), 200

    except Exception as e:
        print(" Inventory fetch error:", e)
        return jsonify({"error": str(e)}), 500
@prescription_blueprint.route('/pharmacist/dashboard', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def pharmacist_dashboard():
    auth_header = request.headers.get("Authorization")
    decoded, error_response, status = check_jwt_role(auth_header, "pharmacist")
    if error_response:
        return jsonify(error_response), status

    email = decoded.get("email")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get pharmacist ID
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        pharmacist = cursor.fetchone()
        if not pharmacist:
            return jsonify({"error": "pharmacist_not_found"}), 404
        pharmacist_id = pharmacist["id"]

        # Get prescriptions
        cursor.execute("""
            SELECT p1.id,p1.patient_id, p1.medicines, p1.status, p1.date_prescribed, u.name AS patient_name
            FROM prescriptions p1
            JOIN users u ON p1.patient_id = u.id
            JOIN patient_profiles pp ON pp.user_id = p1.patient_id
            WHERE pp.preferred_pharmacy_id = %s
              AND p1.date_prescribed = (
                SELECT MAX(p2.date_prescribed)
                FROM prescriptions p2
                WHERE p2.patient_id = p1.patient_id
              )
        """, (pharmacist_id,))
        prescriptions = cursor.fetchall()

        # Get inventory
        cursor.execute("""
            SELECT medicine_name, quantity
            FROM pharmacy_inventory
            WHERE pharmacist_id = %s
            ORDER BY medicine_name ASC
        """, (pharmacist_id,))
        inventory = cursor.fetchall()

        return jsonify({
            "prescriptions": prescriptions,
            "inventory": inventory
        }), 200

    except Exception as e:
        print(f" pharmacist_dashboard error: {str(e)}")
        return jsonify({"error": "dashboard_fetch_failed"}), 500

    finally:
        cursor.close()
        conn.close()
