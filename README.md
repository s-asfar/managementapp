# ManagementApp

A Flask‑based admissions management system.  
Features:
- Student: sign up, apply, upload documents, track status  
- Officer: review applications, update status, add feedback  
- Admin: view stats, generate reports, manage users  

## Prerequisites

- Python 3.9 or above  
- PostgreSQL  

## Clone & Install

```bash
git clone https://your.repo.url/managementapp.git
cd managementapp
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt

create postgresql db, for example I used datagrip to make one.

create .env file

.env
DATABASE_URL = "postgresql://postgres:<password>@localhost:5432/<database_name>"

**RUN THE SQL IN THE SCHEMA SQL FILE IN YOUR CREATED DB