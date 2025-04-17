import uuid
from typing import Any, List
from datetime import date
from repositories.db import get_pool
from psycopg.rows import dict_row

def create_application(
    user_id: uuid.UUID,
    program: str,
    education_level: str,
    previous_institution: str,
    gpa: float,
    personal_statement: str,
    prerequisites_completed: bool
) -> dict[str, Any] | None:
    pool = get_pool()
    application_id = uuid.uuid4()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute('''
                    INSERT INTO Applications (
                        applicationID, userID, program, education_level, previous_institution,
                        gpa, personal_statement, prerequisites_completed, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING applicationID, userID, program, status, submission_date
                ''', (
                    application_id, user_id, program, education_level, previous_institution,
                    gpa, personal_statement, prerequisites_completed, 'submitted'
                ))
                new_app = cur.fetchone()
                return new_app
            except Exception as e:
                print(f"Error creating application: {e}") # Basic error logging
                conn.rollback()
                return None

def get_applications_by_user(user_id: uuid.UUID) -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT
                    applicationID, program, status, submission_date, last_updated
                FROM Applications
                WHERE userID = %s
                ORDER BY submission_date DESC
            ''', (user_id,))
            applications = cur.fetchall()
            return applications if applications else []

def get_application_by_id(application_id: uuid.UUID) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT
                    app.*, u.name as student_name, u.email as student_email
                FROM Applications app
                JOIN Users u ON app.userID = u.userID
                WHERE app.applicationID = %s
            ''', (application_id,))
            application = cur.fetchone()
            return application

def get_all_applications() -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT
                    app.applicationID, u.name as student_name, app.program, app.status, app.submission_date
                FROM Applications app
                JOIN Users u ON app.userID = u.userID
                ORDER BY app.submission_date DESC
            ''', )
            applications = cur.fetchall()
            return applications if applications else []

def update_application_status(application_id: uuid.UUID, new_status: str) -> bool:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute('''
                    UPDATE Applications
                    SET status = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE applicationID = %s
                ''', (new_status, application_id))
                return cur.rowcount > 0 # Check if any row was updated
            except Exception as e:
                print(f"Error updating status: {e}")
                conn.rollback()
                return False

def add_feedback(application_id: uuid.UUID, officer_id: uuid.UUID, content: str) -> dict[str, Any] | None:
    pool = get_pool()
    feedback_id = uuid.uuid4()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute('''
                    INSERT INTO Feedback (feedbackID, applicationID, officerID, content)
                    VALUES (%s, %s, %s, %s)
                    RETURNING feedbackID, applicationID, officerID, content, created_at
                ''', (feedback_id, application_id, officer_id, content))
                new_feedback = cur.fetchone()
                return new_feedback
            except Exception as e:
                print(f"Error adding feedback: {e}")
                conn.rollback()
                return None

def get_feedback_for_application(application_id: uuid.UUID) -> List[dict[str, Any]]:
     pool = get_pool()
     with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT f.content, f.created_at, u.name as officer_name
                FROM Feedback f
                JOIN Users u ON f.officerID = u.userID
                WHERE f.applicationID = %s
                ORDER BY f.created_at DESC
            ''', (application_id,))
            feedback = cur.fetchall()
            return feedback if feedback else []

def get_application_stats(start_date: date = None, end_date: date = None) -> dict[str, Any]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            base_query = "SELECT status, COUNT(*) as count FROM Applications"
            filters = []
            params = []

            if start_date:
                filters.append("submission_date >= %s")
                params.append(start_date)
            if end_date:
                # Add 1 day to end_date to include the whole day
                from datetime import timedelta
                end_date_inclusive = end_date + timedelta(days=1)
                filters.append("submission_date < %s")
                params.append(end_date_inclusive)

            if filters:
                base_query += " WHERE " + " AND ".join(filters)

            base_query += " GROUP BY status"

            cur.execute(base_query, params)
            stats_by_status = cur.fetchall()

            # Get total count within the date range
            total_query = "SELECT COUNT(*) as total FROM Applications"
            if filters:
                total_query += " WHERE " + " AND ".join(filters)
            cur.execute(total_query, params)
            total_count = cur.fetchone()['total']

            # Format stats
            stats = {row['status']: row['count'] for row in stats_by_status}
            stats['total'] = total_count
            return stats

def get_applications_by_date_range(start_date: date = None, end_date: date = None) -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = '''
                SELECT app.applicationID, u.name as student_name, app.program, app.status, app.submission_date
                FROM Applications app
                JOIN Users u ON app.userID = u.userID
            '''
            filters = []
            params = []
            if start_date:
                filters.append("app.submission_date >= %s")
                params.append(start_date)
            if end_date:
                from datetime import timedelta
                end_date_inclusive = end_date + timedelta(days=1)
                filters.append("app.submission_date < %s")
                params.append(end_date_inclusive)

            if filters:
                query += " WHERE " + " AND ".join(filters)

            query += " ORDER BY app.submission_date DESC"
            cur.execute(query, params)
            applications = cur.fetchall()
            return applications if applications else []