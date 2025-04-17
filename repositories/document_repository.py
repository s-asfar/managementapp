import uuid
from typing import Any, List
from repositories.db import get_pool
from psycopg.rows import dict_row

def add_document(application_id: uuid.UUID, document_name: str, document_type: str, file_path: str) -> dict[str, Any] | None:
    pool = get_pool()
    document_id = uuid.uuid4()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute('''
                    INSERT INTO Documents (documentID, applicationID, document_name, document_type, file_path)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING documentID, applicationID, document_name, document_type, upload_date
                ''', (document_id, application_id, document_name, document_type, file_path))
                new_doc = cur.fetchone()
                return new_doc
            except Exception as e:
                print(f"Error adding document: {e}")
                conn.rollback()
                return None

def get_documents_by_application(application_id: uuid.UUID) -> List[dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT documentID, document_name, document_type, file_path, upload_date
                FROM Documents
                WHERE applicationID = %s
                ORDER BY upload_date DESC
            ''', (application_id,))
            documents = cur.fetchall()
            return documents if documents else []

def delete_document(document_id: uuid.UUID) -> bool:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                # Consider also deleting the file from the filesystem here
                cur.execute('''
                    DELETE FROM Documents WHERE documentID = %s
                ''', (document_id,))
                return cur.rowcount > 0
            except Exception as e:
                print(f"Error deleting document: {e}")
                conn.rollback()
                return False

def get_document_by_id(document_id: uuid.UUID) -> dict[str, Any] | None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('''
                SELECT documentID, applicationID, document_name, document_type, file_path, upload_date
                FROM Documents
                WHERE documentID = %s
            ''', (document_id,))
            doc = cur.fetchone()
            return doc