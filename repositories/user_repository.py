import uuid
from typing import Any, List
from repositories.db import get_pool
from psycopg.rows import dict_row
from flask_bcrypt import Bcrypt 


def does_email_exist(email: str) -> bool:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                        SELECT
                            userID
                        FROM
                            users
                        WHERE email = %s
                        ''', [email])
            userID = cur.fetchone()
            return userID is not None

def create_user(email: str, password: str, role: str = 'student') -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                        INSERT INTO users (userID, email, password, role)
                        VALUES (%s, %s, %s, %s)
                        RETURNING userID
                        ''', [user_id, email, password, role])
            return {'userID': user_id, 'email': email, 'role': role}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                        SELECT
                            userid,
                            email,
                            password AS hashed_password,
                            role
                        FROM
                            users
                        WHERE email = %s
                        ''', [email])
            user = cur.fetchone()
            if user:
                return {
                    'userID': user.get('userid'),
                    'email': user.get('email'),
                    'hashed_password': user.get('hashed_password'),
                    'role': user.get('role')
                }
            return None


def get_user_by_id(userID: uuid.UUID) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                        SELECT
                            userID,
                            email,
                            name,
                            role,
                            phone,
                            address,
                            age, -- Add age here
                            date_created
                        FROM
                            users
                        WHERE userID = %s
                        ''', [userID])
            user = cur.fetchone()
            return user

def update_user(userID: uuid.UUID, name: str, phone: str = None, address: str = None, age: int = None) -> dict[str, Any] | None: 
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                UPDATE users
                SET name = %s, phone = %s, address = %s, age = %s -- Add age to SET
                WHERE userID = %s
                RETURNING userID, email, name, role, phone, address, age, date_created -- Add age to RETURNING
            ''', (name, phone, address, age, userID)) 
            updated_user = cur.fetchone()
            return updated_user

def get_user_profile_data(userID: uuid.UUID) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                        SELECT
                            u.userID,
                            u.email,
                            u.name,
                            u.role,
                            u.phone,
                            u.address,
                            u.age, -- Add age here
                            u.date_created,
                            (SELECT COUNT(*) FROM Applications WHERE userID = u.userID) AS applications_count
                        FROM
                            users u
                        WHERE u.userID = %s
                        ''', [userID])
            user_data = cur.fetchone()
            return user_data

def update_password(email: str, new_hashed_password: str) -> bool:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('''
                    UPDATE users
                    SET password = %s
                    WHERE email = %s
                ''', (new_hashed_password, email))
                return cur.rowcount > 0
            except Exception as e:
                print(f"Error updating password: {e}")
                conn.rollback()
                return False

def get_all_users() -> List[dict[str, Any]]:
    """Fetches all users from the database."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT userID, email, name, role, date_created
                FROM Users
                ORDER BY date_created DESC
            ''')
            users = cur.fetchall()
            return users if users else []

def update_user_role(user_id: uuid.UUID, new_role: str) -> bool:
    """Updates the role of a specific user."""
    pool = get_pool()
    
    if new_role not in ['student', 'officer', 'admin']:
        print(f"Error: Invalid role '{new_role}' provided for update.")
        return False

    with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('''
                    UPDATE Users
                    SET role = %s
                    WHERE userID = %s
                ''', (new_role, user_id))
                
                return cur.rowcount > 0
            except Exception as e:
                print(f"Error updating user role: {e}")
                conn.rollback()
                return False

def delete_user(user_id: uuid.UUID) -> bool:
    """
    Deletes a user and handles their related data (applications, documents, feedback).
    Uses a transaction to ensure atomicity.
    """
    pool = get_pool()
    with pool.connection() as conn:
        
        with conn.transaction():
            try:
                
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT role FROM Users WHERE userID = %s", (user_id,))
                    user_info = cur.fetchone()
                    if not user_info:
                        print(f"User {user_id} not found for deletion.")
                        return False 
                    user_role = user_info['role']

                if user_role == 'student':
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute("SELECT applicationID FROM Applications WHERE userID = %s", (user_id,))
                        applications = cur.fetchall()
                        application_ids = [app['applicationid'] for app in applications]

                    if application_ids:
                        app_ids_tuple = tuple(application_ids)

                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM Documents WHERE applicationID = ANY(%s)", (application_ids,))
                            print(f"Deleted {cur.rowcount} documents for student {user_id}")

                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM Feedback WHERE applicationID = ANY(%s)", (application_ids,))
                            print(f"Deleted {cur.rowcount} feedback entries for student {user_id}'s applications")

                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM Applications WHERE applicationID = ANY(%s)", (application_ids,))
                            print(f"Deleted {cur.rowcount} applications for student {user_id}")

                elif user_role == 'officer':
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM Feedback WHERE officerID = %s", (user_id,))
                        print(f"Deleted {cur.rowcount} feedback entries written by officer {user_id}")

                with conn.cursor() as cur:
                    cur.execute("DELETE FROM Users WHERE userID = %s", (user_id,))
                    deleted_count = cur.rowcount
                    print(f"Deleted {deleted_count} user record for {user_id}")
                    return deleted_count > 0

            except Exception as e:
                print(f"Error during user deletion transaction for {user_id}: {e}")
                return False