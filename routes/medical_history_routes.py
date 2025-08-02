from flask import Blueprint, request, jsonify,Response
from flask_cors import cross_origin
from config import get_db_connection, token_secret
from datetime import datetime
import jwt
from fpdf import FPDF
from flask import send_file
import io

medical_blueprint = Blueprint('medical_history', __name__)

@medical_blueprint.route('/medical-history/add', methods=['POST'])
@cross_origin(origins=['http://localhost:4200'])
def add_medical_history():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401
    token = auth_header.split(" ")[1]

    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
            return jsonify({"error": "only_doctors_can_add_history"}), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": f"Token error: {str(e)}"}), 401

    data = request.json
    patient_id = data.get("patient_id")
    diagnosis = data.get("diagnosis")
    treatment = data.get("treatment")
    medicines = data.get("medicines")
    notes = data.get("notes")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    doctor = cursor.fetchone()
    if not doctor:
        return jsonify({{"error": "doctor_not_found"}}), 404
    doctor_id = doctor[0]

    today = datetime.today().strftime('%Y-%m-%d')

    cursor.execute("""
        INSERT INTO medical_history (patient_id, doctor_id, date, diagnosis, treatment, medicines, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (patient_id, doctor_id, today, diagnosis, treatment, medicines, notes))

    entry_id = cursor.lastrowid  #  Capture new inserted ID

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "medical_history_added",
        "entry_id": entry_id  #  Return it
    }), 200
@medical_blueprint.route('/medical-history/my', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def get_my_medical_history():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "patient":
            return jsonify({"error": "only_patients_can_view_history"}), 403
        email = decoded.get("email")
    except Exception as e:
        return jsonify({"error": f"Token error: {str(e)}"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    patient = cursor.fetchone()
    if not patient:
        return jsonify({"error": "patient_not_found"}), 404

    patient_id = patient["id"]

    cursor.execute("""
        SELECT mh.date, mh.diagnosis, mh.treatment, mh.medicines, mh.notes, u.name AS doctor_name
        FROM medical_history mh
        JOIN users u ON mh.doctor_id = u.id
        WHERE mh.patient_id = %s
        ORDER BY mh.date DESC
    """, (patient_id,))
    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(history), 200
@medical_blueprint.route('/medical-history/patient/<int:patient_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def doctor_view_patient_history(patient_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401
    token = auth_header.split(" ")[1]

    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != "doctor":
            return jsonify({"error": "only_doctors_can_view_history"}), 403
    except Exception as e:
        return jsonify({"error": f"Token error: {str(e)}"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT mh.id, mh.date, mh.diagnosis, mh.treatment, mh.medicines, mh.notes,
               u.name AS doctor_name
        FROM medical_history mh
        JOIN users u ON mh.doctor_id = u.id
        WHERE mh.patient_id = %s
        ORDER BY mh.date DESC, mh.id DESC
    """, (patient_id,))

    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(history), 200
@medical_blueprint.route('/medical-history/download-all/<int:patient_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def download_full_medical_history(patient_id):
    from fpdf import FPDF
    from flask import Response

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "auth_header_missing"}), 401

    token = auth_header.split(" ")[1]

    try:
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        role = decoded.get("role")
        email = decoded.get("email")
        if role not in ["doctor", "patient"]:
            return jsonify({"error": "access_denied"}), 403
    except Exception as e:
        return jsonify({"error": f"Token error: {str(e)}"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    user_id = user["id"]
    if role == "patient" and user_id != patient_id:
        return jsonify({"error": "unauthorized_access"}), 403

    cursor.execute("""
        SELECT mh.date, mh.diagnosis, mh.treatment, mh.medicines, mh.notes,
               u1.name AS doctor_name, u2.name AS patient_name
        FROM medical_history mh
        JOIN users u1 ON mh.doctor_id = u1.id
        JOIN users u2 ON mh.patient_id = u2.id
        WHERE mh.patient_id = %s
        ORDER BY mh.date DESC
    """, (patient_id,))
    records = cursor.fetchall()

    if not records:
        return jsonify({"error": "no_medical_history"}), 404

    def safe_text(text):
        return str(text).replace("–", "-").replace("—", "-").encode('latin-1', errors='replace').decode('latin-1')

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Local GP System", border=False, ln=True, align='C')
            self.set_font("Arial", "I", 10)
            self.cell(0, 10, "Comprehensive Patient Medical History", ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)

    #  Patient Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Patient Name:", ln=0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(100, 10, safe_text(records[0]["patient_name"]), ln=1)
    pdf.ln(3)

    #  Each Record
    for i, record in enumerate(records, start=1):
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, safe_text(f"Record {i} - Date: {record['date']}"), ln=True, fill=True)

        fields = [
            ("Doctor Name", record["doctor_name"]),
            ("Diagnosis", record["diagnosis"]),
            ("Treatment", record["treatment"]),
            ("Medicines", record["medicines"]),
            ("Notes", record["notes"]),
        ]

        for label, value in fields:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(45, 8, f"{label}:", ln=0)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, safe_text(value))
            pdf.ln(1)

        pdf.ln(3)
        if pdf.get_y() > 250:
            pdf.add_page()

    pdf_binary = bytes(pdf.output(dest='S'))
    cursor.close()
    conn.close()

    return Response(
        pdf_binary,
        mimetype='application/pdf',
        headers={
            "Content-Disposition": "attachment; filename=full_medical_history.pdf"
        }
    )
@medical_blueprint.route('/medical-history/view/<int:patient_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def view_full_medical_history_html(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT mh.date, mh.diagnosis, mh.treatment, mh.medicines, mh.notes,
               u1.name AS doctor_name, u2.name AS patient_name
        FROM medical_history mh
        JOIN users u1 ON mh.doctor_id = u1.id
        JOIN users u2 ON mh.patient_id = u2.id
        WHERE mh.patient_id = %s
        ORDER BY mh.date DESC
    """, (patient_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    if not records:
        return "<h3>No medical history found.</h3>"

    patient_name = records[0]["patient_name"]

    # Build HTML dynamically
    html = f"""
    <html>
    <head>
        <title>Full Medical History</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #333;
                background-color: #fdfdfd;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .record {{
                border: 1px solid #ccc;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 25px;
                background-color: #f9f9f9;
            }}
            h2, h3 {{
                color: #007BFF;
                margin-bottom: 5px;
            }}
            .label {{
                font-weight: bold;
                color: #444;
            }}
            .section {{
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🩺 Local GP System</h2>
            <h3>Comprehensive Medical History</h3>
            <p><strong>Patient:</strong> {patient_name}</p>
        </div>
    """

    for i, record in enumerate(records, start=1):
        html += f"""
        <div class="record">
            <div class="section"><span class="label">Record {i} – Date:</span> {record['date']}</div>
            <div class="section"><span class="label">Doctor:</span> {record['doctor_name']}</div>
            <div class="section"><span class="label">Diagnosis:</span><br>{record['diagnosis']}</div>
            <div class="section"><span class="label">Treatment:</span><br>{record['treatment']}</div>
            <div class="section"><span class="label">Medicines:</span><br>{record['medicines']}</div>
            <div class="section"><span class="label">Notes:</span><br>{record['notes']}</div>
        </div>
        """

    html += "</body></html>"
    return html
