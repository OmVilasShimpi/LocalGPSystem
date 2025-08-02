import bcrypt
import re
import jwt
import datetime
from config import token_secret
from config import token_secret, get_db_connection

# Function to Validate Password Strength
def is_secure_password(password):
    if len(password) < 12:
        return "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"\d", password):
        return "Password must contain at least one number (0-9)."
    if not re.search(r"[!@#$%^&*()_+]", password):
        return "Password must contain at least one special character (!@#$%^&*()_+)."
    return None

# Function to Hash Passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Function to Verify Passwords
def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Function to Generate JWT Token
def generate_token(username):
    return jwt.encode({
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, token_secret, algorithm="HS256")

def is_token_blacklisted(token):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM blacklisted_tokens WHERE token = %s", (token,))
            result = cursor.fetchone()
            return result is not None  # If token exists, it's blacklisted
        except Exception as err:
            print("Error checking blacklisted token:", err)
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def check_jwt_role(auth_header, required_role):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, {"error": "Authorization header missing"}, 401
    try:
        token = auth_header.split(" ")[1]
        decoded = jwt.decode(token, token_secret, algorithms=["HS256"])
        if decoded.get("role") != required_role:
            return None, {"error": f"Only {required_role}s allowed"}, 403
        return decoded, None, 200
    except jwt.ExpiredSignatureError:
        return None, {"error": "Token expired"}, 401
    except jwt.InvalidTokenError as e:
        return None, {"error": f"Invalid token: {str(e)}"}, 401

