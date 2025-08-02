from flask import Blueprint, request, jsonify
from flask_mail import Message

# Define the blueprint
contact_blueprint = Blueprint('contact', __name__)

# Placeholder for mail, to be initialized from app.py
mail = None

# Called from app.py to inject the Mail() object
def init_mail(m):
    global mail
    mail = m

# Contact form POST endpoint
@contact_blueprint.route('/contact', methods=['POST'])
def handle_contact():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    if not name or not email or not message:
        return jsonify({'error': 'Missing fields'}), 400

    try:
        msg = Message(
            subject=f"New Contact Form Message from {name}",
            sender="johnsmith179805@gmail.com",  # Must match your MAIL_USERNAME
            recipients=["johnsmith179805@gmail.com"],
            body=f"""This user has sent you a message via the contact form.

Name: {name}
Email: {email}

Message:
{message}

Please respond to the user directly."""
        )
        mail.send(msg)
        return jsonify({'message': 'Email sent successfully'}), 200
    except Exception as e:
        print(" Email sending failed:", e)
        return jsonify({'error': 'Failed to send email'}), 500
