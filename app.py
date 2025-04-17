import os
from dotenv import load_dotenv
from flask import Flask, g, render_template, redirect, request, url_for, session, abort, flash
from flask_bcrypt import Bcrypt
from datetime import datetime

from repositories import user_repository
from repositories.user_repository import *
from datetime import date

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = os.getenv('APP_SECRET_KEY')

def require_role(role):
    if 'userID' not in session:
        flash('You must be signed in to access this page.', 'danger')
        return redirect(url_for('signin'))
    
    user = user_repository.get_user_by_id(session['userID'])
    if not user or user.get('role') != role:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    return None

@app.get('/')
def index():
    return render_template('index.html', active_page='home')

@app.get('/signin')
def signin():
    if 'userID' in session:
        flash('You are already signed in.', 'danger')
        return redirect(url_for('profile'))
    return render_template('signin.html', active_page='signin')

@app.get('/signup')
def signup():
    if 'userID' in session:
        flash('You are already signed in.', 'danger')
        return redirect(url_for('profile'))
    return render_template('signup.html', active_page='signup')

@app.get('/profile')
def profile():
    if 'userID' not in session:
        flash('You must be signed in to view your profile.', 'danger')
        return redirect('/')
    userID = session.get('userID')
    user_data = user_repository.get_user_profile_data(userID)
    return render_template('profile.html', user=user_data, active_page='profile')

@app.get('/logout')
def logout():
    flash('You have been successfully signed out.', 'success')
    del session['userID']
    return redirect('/')

@app.get('/editprofile')
def edit_profile():
    if 'userID' not in session:
        flash('You must be signed in to edit your profile.', 'danger')
        return redirect('/')
    
    userID = session.get('userID')
    user = user_repository.get_user_by_id(userID)
    return render_template('editprofile.html', user=user, active_page='profile')

@app.post('/signup')
def signup_account():
    if 'userID' in session:
        flash('You are already logged in.', 'danger')
        return redirect(url_for('profile'))
    
    email = request.form.get('email').lower()
    password = request.form.get('password')
    role = request.form.get('role', 'student')  # Default to student role
    
    if not email or not password:
        flash('Email and password are required.', 'danger')
        return redirect(url_for('signup'))
    
    # Validate role
    if role not in ['student', 'officer', 'admin']:
        flash('Invalid role selection.', 'danger')
        return redirect(url_for('signup'))
    
    does_user_exist = user_repository.does_email_exist(email)
    if does_user_exist:
        flash('User with this email already exists.', 'danger')
        return redirect(url_for('signup'))
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_repository.create_user(email, hashed_password, role)
    user = user_repository.get_user_by_email(email)
    session['userID'] = user['userID']
    session['role'] = user['role']  # Store role in session as well
    flash('Account created successfully! Please complete your profile.', 'success')
    # Redirect to edit profile instead of main profile
    return redirect(url_for('edit_profile'))

@app.post('/signin')
def signin_account():
    if 'userID' in session:
        flash('You are already logged in.', 'danger')
        return redirect(url_for('profile'))
    email = request.form.get('email').lower() 
    password = request.form.get('password')
    user = user_repository.get_user_by_email(email)
    if user is None or not bcrypt.check_password_hash(user['hashed_password'], password):
        flash('Invalid email or password.', 'danger')
        return render_template('signin.html', active_page='signin')  
    else:
        session['userID'] = user['userID']
        flash('You have successfully signed in.', 'success')
        return redirect(url_for('profile'))

@app.post('/editprofile')
def update_profile():
    if 'userID' not in session:
        flash('You must be signed in to edit your profile.', 'danger')
        return redirect('/')
    
    userID = session.get('userID')
    name = request.form.get('name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    age_str = request.form.get('age')  # Get age as string
    
    if not name:
        flash('Name is required.', 'danger')
        # Fetch user data again for rendering the template
        user = user_repository.get_user_by_id(userID)
        return render_template('editprofile.html', user=user, active_page='profile')
    
    # Validate and convert age
    age = None
    if age_str:
        try:
            age = int(age_str)
            if age <= 0:  # Basic validation
                flash('Please enter a valid age.', 'danger')
                user = user_repository.get_user_by_id(userID)
                return render_template('editprofile.html', user=user, active_page='profile')
        except ValueError:
            flash('Age must be a number.', 'danger')
            user = user_repository.get_user_by_id(userID)
            return render_template('editprofile.html', user=user, active_page='profile')
    
    # Pass age to the update function
    updated_user = user_repository.update_user(userID, name, phone, address, age)
    
    if updated_user is None:
        flash('An error occurred while updating the profile.', 'danger')
    else:
        flash('Profile updated successfully!', 'success')
    
    # Redirect to the main profile page after updating
    return redirect(url_for('profile'))

@app.get('/apply')
def apply_form():
    if 'userID' not in session:
        flash('You must be signed in to apply.', 'danger')
        return redirect(url_for('signin'))
    
    userID = session.get('userID')
    
    return render_template('apply.html', active_page='apply')

@app.post('/apply')
def submit_application():
    if 'userID' not in session:
        flash('You must be signed in to apply.', 'danger')
        return redirect(url_for('signin'))
    
    userID = session.get('userID')
    program = request.form.get('program')
    
    if not program:
        flash('Program selection is required.', 'danger')
        return redirect(url_for('apply_form'))
        
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('application_status'))

@app.get('/application-status')
def application_status():
    if 'userID' not in session:
        flash('You must be signed in to view application status.', 'danger')
        return redirect(url_for('signin'))
    
    userID = session.get('userID')
    return render_template('application_status.html', active_page='application')

@app.get('/upload-documents')
def upload_documents_form():
    if 'userID' not in session:
        flash('You must be signed in to upload documents.', 'danger')
        return redirect(url_for('signin'))
    
    return render_template('upload_documents.html', active_page='documents')

@app.post('/upload-documents')
def upload_documents():
    if 'userID' not in session:
        flash('You must be signed in to upload documents.', 'danger')
        return redirect(url_for('signin'))
    
    flash('Document uploaded successfully!', 'success')
    return redirect(url_for('upload_documents_form'))

@app.get('/officer-dashboard')
def officer_dashboard():
    if 'userID' not in session:
        flash('You must be signed in to access the officer dashboard.', 'danger')
        return redirect(url_for('signin'))
    
    userID = session.get('userID')
    user = user_repository.get_user_by_id(userID)
    if not user or user.get('role') != 'officer':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    return render_template('officer_dashboard.html', active_page='officer_dashboard')

@app.get('/review-application/<application_id>')
def review_application(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict
    
    return render_template('review_application.html', active_page='officer_dashboard')

@app.post('/update-application-status/<application_id>')
def update_application_status(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict
    
    new_status = request.form.get('status')
    feedback = request.form.get('feedback')
    
    flash('Application status updated successfully!', 'success')
    return redirect(url_for('officer_dashboard'))

@app.get('/schedule-interview/<application_id>')
def schedule_interview_form(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict 
    return render_template('schedule_interview.html', active_page='officer_dashboard')

@app.post('/schedule-interview/<application_id>')
def schedule_interview(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict
    
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    notes = request.form.get('notes')
    
    flash('Interview scheduled successfully!', 'success')
    return redirect(url_for('officer_dashboard'))

@app.get('/admin-dashboard')
def admin_dashboard():
    restrict = require_role('admin')
    if restrict:
        return restrict
    
    return render_template('admin_dashboard.html', active_page='admin_dashboard')

@app.get('/generate-report')
def generate_report_form():
    restrict = require_role('admin')
    if restrict:
        return restrict
    
    return render_template('generate_report.html', active_page='admin_dashboard')

@app.post('/generate-report')
def generate_report():
    restrict = require_role('admin')
    if restrict:
        return restrict
    
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    # This would need to be replaced with actual data from the database
    
    return render_template('report_result.html', active_page='admin_dashboard')

if __name__ == '__main__':
    app.run(debug=True)
