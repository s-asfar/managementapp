import uuid
from typing import Any
from repositories.db import get_pool
from psycopg.rows import dict_row


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

def create_user(email: str, password: str) -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                        INSERT INTO users (userID, email, password)
                        VALUES (%s, %s, %s)
                        RETURNING userID
                        ''', [user_id, email, password])
            return {'userID': user_id, 'email': email}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                        SELECT
                            userid,
                            email,
                            password AS hashed_password
                        FROM
                            users
                        WHERE email = %s
                        ''', [email])
            user = cur.fetchone()
            if user:
                return {'userID': user.get('userid'), 'email': user.get('email'), 'hashed_password': user.get('hashed_password')}
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
                            age,
                            height,
                            weight,
                            goal
                        FROM
                            users
                        WHERE userID = %s
                        ''', [userID])
            user = cur.fetchone()
            return user

def update_user(userID: uuid.UUID, name: str, age: int, height: str, weight: float, goal: str) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                UPDATE users
                SET name = %s, age = %s, height = %s, weight = %s, goal = %s
                WHERE userID = %s
                RETURNING userID, email, name, age, height, weight, goal,
                    (SELECT COUNT(*) FROM Food WHERE createdByID = userID) AS created_foods_count,
                    (SELECT COUNT(*) FROM Workout WHERE userID = userID) AS workouts_count
            ''', (name, age, height, weight, goal, userID))
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
                            u.age,
                            u.height,
                            u.weight,
                            u.goal,
                            (SELECT COUNT(*) FROM Food WHERE createdByID = u.userID) AS created_foods_count,
                            (SELECT COUNT(*) FROM Workout WHERE userID = u.userID) AS workouts_count
                        FROM
                            users u
                        WHERE u.userID = %s
                        ''', [userID])
            user_data = cur.fetchone()
            return user_data