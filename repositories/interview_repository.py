import uuid
from typing import Any, List
from datetime import datetime
from repositories.db import get_pool
from psycopg.rows import dict_row

def schedule_interview(application_id: uuid.UUID, officer_id: uuid.UUID, schedule_date: datetime, location: str, notes: str = None) -> dict[str, Any] | None:
    pool = get_pool()
    interview_id = uuid.uuid4()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute('''
                    INSERT INTO Interviews (interviewID, applicationID, officerID, schedule_date, location, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING interviewID, applicationID, schedule_date, status
                ''', (interview_id, application_id, officer_id, schedule_date, location, notes, 'scheduled'))
                new_interview = cur.fetchone()
                # Optionally update application status
                cur.execute("UPDATE Applications SET status = 'interview scheduled', last_updated = CURRENT_TIMESTAMP WHERE applicationID = %s", (application_id,))
                return new_interview
            except Exception as e:
                print(f"Error scheduling interview: {e}")
                conn.rollback()
                return None

def get_interviews_for_application(application_id: uuid.UUID) -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT i.interviewID, i.schedule_date, i.location, i.status, u.name as officer_name
                FROM Interviews i
                JOIN Users u ON i.officerID = u.userID
                WHERE i.applicationID = %s
                ORDER BY i.schedule_date DESC
            ''', (application_id,))
            interviews = cur.fetchall()
            return interviews if interviews else []

def get_interview_by_id(interview_id: uuid.UUID) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT i.*, u.name as officer_name, app.userID as student_userID
                FROM Interviews i
                JOIN Users u ON i.officerID = u.userID
                JOIN Applications app ON i.applicationID = app.applicationID
                WHERE i.interviewID = %s
            ''', (interview_id,))
            interview = cur.fetchone()
            return interview

def update_interview_status(interview_id: uuid.UUID, status: str, notes: str = None) -> bool:
     pool = get_pool()
     with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                if notes:
                     cur.execute('''
                        UPDATE Interviews SET status = %s, notes = %s WHERE interviewID = %s
                     ''', (status, notes, interview_id))
                else:
                     cur.execute('''
                        UPDATE Interviews SET status = %s WHERE interviewID = %s
                     ''', (status, interview_id))
                return cur.rowcount > 0
            except Exception as e:
                print(f"Error updating interview status: {e}")
                conn.rollback()
                return False

def get_scheduled_interviews_for_officer(officer_id: uuid.UUID) -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT i.interviewID, i.schedule_date, i.location, i.status, app.program, u_student.name as student_name
                FROM Interviews i
                JOIN Applications app ON i.applicationID = app.applicationID
                JOIN Users u_student ON app.userID = u_student.userID
                WHERE i.officerID = %s AND i.status = 'scheduled'
                ORDER BY i.schedule_date ASC
            ''', (officer_id,))
            interviews = cur.fetchall()
            return interviews if interviews else []