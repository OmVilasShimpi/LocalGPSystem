from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from config import STRIPE_SECRET_KEY
import stripe
from config import  get_db_connection
import hmac
import hashlib
from flask import request

payment_blueprint = Blueprint('payment', __name__)
stripe.api_key = STRIPE_SECRET_KEY

@payment_blueprint.route('/create-payment-intent', methods=['POST'])
@cross_origin(origins=['http://localhost:4200'])
def create_payment_intent():
    try:
        data = request.get_json()
        amount = data.get("amount")  

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='gbp',
            automatic_payment_methods={"enabled": True}
        )

        return jsonify({
            'clientSecret': intent['client_secret']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@payment_blueprint.route('/create-link/<int:prescription_id>', methods=['POST'])
@cross_origin(origins=['http://localhost:4200'])
def create_payment_link(prescription_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        #  Fetch prescription details
        cursor.execute("""
            SELECT p.id, p.payment_note, p.patient_id, u.email as patient_email
            FROM prescriptions p
            JOIN users u ON p.patient_id = u.id
            WHERE p.id = %s
        """, (prescription_id,))
        prescription = cursor.fetchone()

        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404

        amount = extract_amount_from_payment_note(prescription["payment_note"])
        if not amount:
            return jsonify({"error": "No valid amount in payment note"}), 400

        #  Create Stripe Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Stripe uses cents
            currency="gbp",
            metadata={"prescription_id": prescription_id, "patient_email": prescription["patient_email"]}
        )

        #  Save Payment Intent ID into DB
        cursor.execute("UPDATE prescriptions SET payment_intent_id = %s WHERE id = %s", (intent.id, prescription_id))
        conn.commit()

        return jsonify({
            "client_secret": intent.client_secret,
            "amount": amount,
            "currency": "GBP"
        }), 200

    except Exception as e:
        print(" Payment Error:", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# Helper function
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
@payment_blueprint.route('/start/<int:prescription_id>', methods=['GET'])
@cross_origin(origins=['http://localhost:4200'])
def start_payment_session(prescription_id):
    # Temporary: Just show HTML link or redirect
    html = f"""
    <html>
    <head><title>Redirecting to Payment</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 50px;">
        <h2>Redirecting you to payment for your prescription...</h2>
        <p>If you are not redirected, <a href="http://localhost:4200/pay/{prescription_id}">click here</a>.</p>
        <script>
            setTimeout(function() {{
                window.location.href = "http://localhost:4200/pay/{prescription_id}";
            }}, 1000);
        </script>
    </body>
    </html>
    """
    return html
@payment_blueprint.route('/create-checkout-session/<int:prescription_id>', methods=['POST'])
@cross_origin(origins=['http://localhost:4200'])
def create_checkout_session(prescription_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch payment note
        cursor.execute("""
            SELECT p.id, p.payment_note, u.email AS patient_email
            FROM prescriptions p
            JOIN users u ON p.patient_id = u.id
            WHERE p.id = %s
        """, (prescription_id,))
        prescription = cursor.fetchone()

        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404

        amount = extract_amount_from_payment_note(prescription["payment_note"])
        if not amount:
            return jsonify({"error": "No valid amount in payment note"}), 400

        # 1️ Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': 'Prescription Payment',
                    },
                    'unit_amount': int(amount * 100),  # Stripe expects pence
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"http://localhost:4200/pay-success/{prescription_id}",
            cancel_url=f"http://localhost:4200/pay-cancel/{prescription_id}",
            metadata={
                "prescription_id": prescription_id,
                "patient_email": prescription["patient_email"]
            }
        )

        return jsonify({
            'checkout_url': session.url
        }), 200

    except Exception as e:
        print(" Checkout error:", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

@payment_blueprint.route('/payment-success/<payment_intent_id>', methods=['POST'])
@cross_origin(origins=['http://localhost:4200'])
def payment_success(payment_intent_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Find prescription
        cursor.execute("SELECT id FROM prescriptions WHERE payment_intent_id = %s", (payment_intent_id,))
        prescription = cursor.fetchone()

        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404

        # Update status
        cursor.execute("UPDATE prescriptions SET status = %s WHERE payment_intent_id = %s", ('Paid', payment_intent_id))
        conn.commit()

        return jsonify({"message": "Prescription marked as Paid!"}), 200

    except Exception as e:
        conn.rollback()
        print(" Payment success update error:", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
