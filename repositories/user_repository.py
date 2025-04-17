import uuid
from typing import Any
from repositories.db import get_pool
from psycopg.rows import dict_row
from flask_bcrypt import Bcrypt # Add this import if not already present


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

def update_user(userID: uuid.UUID, name: str, phone: str = None, address: str = None, age: int = None) -> dict[str, Any] | None: # Add age parameter
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                UPDATE users
                SET name = %s, phone = %s, address = %s, age = %s -- Add age to SET
                WHERE userID = %s
                RETURNING userID, email, name, role, phone, address, age, date_created -- Add age to RETURNING
            ''', (name, phone, address, age, userID)) # Add age to tuple
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