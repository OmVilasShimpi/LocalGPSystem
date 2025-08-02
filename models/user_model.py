from config import get_db_connection

# User Model Class
class User:
    @staticmethod
    def create_user(name, email, password, role):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                               (name, email, password, role))
                conn.commit()
                return True
            except Exception as err:
                print(f"Failed to create user: {str(err)}")
                return {"success": False, "message": "Failed to create user."}
            finally:
                cursor.close()
                conn.close()
        return False

    @staticmethod
    def get_user_by_email(email):
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                return user
            except Exception as err:
                print(f"Error retrieving user by email: {str(err)}")
                return None
            finally:
                cursor.close()
                conn.close()
        return None
