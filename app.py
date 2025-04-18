import os
import uuid
from dotenv import load_dotenv
from flask import Flask, g, render_template, redirect, request, url_for, session, abort, flash, send_from_directory
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

# Import repositories
from repositories import user_repository, application_repository, document_repository, interview_repository
from datetime import date

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = os.getenv('APP_SECRET_KEY', 'fallback_secret_key_123')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB limit

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    restrict = require_role('student')  # Use require_role for students too
    if restrict:
        return restrict

    userID = session.get('userID')
    return render_template('apply.html', active_page='apply')

@app.post('/apply')
def submit_application():
    restrict = require_role('student')
    if restrict:
        return restrict

    userID = session.get('userID')
    program = request.form.get('program')
    education = request.form.get('education')
    institution = request.form.get('institution')
    gpa_str = request.form.get('gpa')
    statement = request.form.get('statement')
    prereqs = request.form.get('prerequisites')

    # Basic Validation
    if not all([program, education, institution, gpa_str, statement, prereqs]):
        flash('All application fields are required.', 'danger')
        return redirect(url_for('apply_form'))

    try:
        gpa = float(gpa_str)
        if not (0.0 <= gpa <= 4.0):
             raise ValueError("GPA out of range")
    except ValueError:
        flash('Invalid GPA value. Please enter a number between 0.0 and 4.0.', 'danger')
        return redirect(url_for('apply_form'))

    prerequisites_completed = True if prereqs == 'yes' else False

    # Save to DB using repository
    new_app = application_repository.create_application(
        userID, program, education, institution, gpa, statement, prerequisites_completed
    )

    if new_app:
        flash('Application submitted successfully! Please upload required documents.', 'success')
        # Redirect to document upload page for the new application
        return redirect(url_for('upload_documents_form', application_id=new_app['applicationID']))
    else:
        flash('An error occurred while submitting the application.', 'danger')
        return redirect(url_for('apply_form'))

@app.get('/application-status')
def application_status():
    restrict = require_role('student')
    if restrict:
        return restrict

    userID = session.get('userID')
    applications = application_repository.get_applications_by_user(userID)

    if not applications:
        flash('You have not submitted an application yet.', 'info')
        return redirect(url_for('apply_form'))

    application_id = applications[0]['applicationid']
    application = application_repository.get_application_by_id(application_id)

    if not application:
         flash('Error retrieving application details.', 'danger')
         return redirect(url_for('profile'))

    feedback = application_repository.get_feedback_for_application(application['applicationid'])
    interviews = []
    if application and application['status'] == 'interview scheduled':
        interviews = interview_repository.get_interviews_for_application(application['applicationid'])

    return render_template('application_status.html',
                           application=application,
                           feedback=feedback,
                           interviews=interviews,
                           active_page='application')

@app.get('/upload-documents/<uuid:application_id>')
def upload_documents_form(application_id):
    restrict = require_role('student')
    if restrict:
        return restrict

    application = application_repository.get_application_by_id(application_id)
    if not application or application['userid'] != session['userID']:
         flash('Application not found or you do not have permission.', 'danger')
         return redirect(url_for('profile'))

    documents = document_repository.get_documents_by_application(application_id)

    return render_template('upload_documents.html',
                           application=application,
                           documents=documents,
                           active_page='documents')

@app.post('/upload-documents/<uuid:application_id>')
def upload_documents(application_id):
    restrict = require_role('student')
    if restrict:
        return restrict

    application = application_repository.get_application_by_id(application_id)
    if not application or application['userid'] != session['userID']:
         flash('Application not found or you do not have permission.', 'danger')
         return redirect(url_for('profile'))

    document_name = request.form.get('document_name')
    document_type = request.form.get('document_type')

    if 'document_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    file = request.files['document_file']

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)

    if not document_name or not document_type:
        flash('Document name and type are required.', 'danger')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            file.save(file_path)
            new_doc = document_repository.add_document(application_id, document_name, document_type, file_path)
            if new_doc:
                flash('Document uploaded successfully!', 'success')
            else:
                 flash('Failed to save document record to database.', 'danger')
                 if os.path.exists(file_path):
                     os.remove(file_path)
        except Exception as e:
            flash(f'An error occurred during file upload: {e}', 'danger')
            if os.path.exists(file_path):
                os.remove(file_path)

    else:
        flash('Invalid file type or file error.', 'danger')

    return redirect(url_for('upload_documents_form', application_id=application_id))

@app.post('/delete-document/<uuid:document_id>')
def delete_document(document_id):
    restrict = require_role('student')
    if restrict:
        return restrict

    doc = document_repository.get_document_by_id(document_id)
    if not doc:
        flash('Document not found.', 'danger')
        return redirect(url_for('profile'))

    application = application_repository.get_application_by_id(doc['applicationID'])
    if not application or application['userid'] != session['userID']:
        flash('You do not have permission to delete this document.', 'danger')
        return redirect(url_for('profile'))

    if doc['file_path'] and os.path.exists(doc['file_path']):
        try:
            os.remove(doc['file_path'])
        except Exception as e:
            flash(f"Error deleting file from system: {e}", 'warning')

    if document_repository.delete_document(document_id):
        flash('Document deleted successfully.', 'success')
    else:
        flash('Failed to delete document record.', 'danger')

    return redirect(url_for('upload_documents_form', application_id=doc['applicationID']))

@app.get('/uploads/<filename>')
def uploaded_file(filename):
    if 'userID' not in session:
        abort(403)

    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        abort(404)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename)

@app.get('/officer-dashboard')
def officer_dashboard():
    restrict = require_role('officer')
    if restrict:
        return restrict

    officer_id = session['userID'] # Get current officer's ID
    applications = application_repository.get_all_applications()
    # Fetch interviews scheduled for this officer
    scheduled_interviews = interview_repository.get_scheduled_interviews_for_officer(officer_id)

    return render_template('officer_dashboard.html',
                           applications=applications,
                           scheduled_interviews=scheduled_interviews, # Pass interviews to template
                           active_page='officer_dashboard')

@app.get('/review-application/<uuid:application_id>')
def review_application_form(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict

    application = application_repository.get_application_by_id(application_id)
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('officer_dashboard'))

    documents = document_repository.get_documents_by_application(application_id)
    feedback = application_repository.get_feedback_for_application(application_id)

    statuses = ['submitted', 'under review', 'interview scheduled', 'accepted', 'rejected', 'more info required']

    return render_template('review_application.html',
                           application=application,
                           documents=documents,
                           feedback=feedback,
                           statuses=statuses,
                           active_page='officer_dashboard')

@app.post('/update-application-status/<uuid:application_id>')
def update_application_status(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict

    new_status = request.form.get('status')
    feedback_content = request.form.get('feedback')
    officer_id = session['userID']

    if not new_status:
        flash('Status is required.', 'danger')
        return redirect(url_for('review_application_form', application_id=application_id))

    status_updated = application_repository.update_application_status(application_id, new_status)

    feedback_added = None
    if feedback_content:
        feedback_added = application_repository.add_feedback(application_id, officer_id, feedback_content)

    if status_updated:
        flash('Application status updated successfully!', 'success')
        if feedback_content and not feedback_added:
             flash('Status updated, but failed to add feedback.', 'warning')
    else:
        flash('Failed to update application status.', 'danger')

    return redirect(url_for('review_application_form', application_id=application_id))

@app.get('/schedule-interview/<uuid:application_id>')
def schedule_interview_form(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict

    application = application_repository.get_application_by_id(application_id)
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('officer_dashboard'))

    return render_template('schedule_interview.html',
                           application=application,
                           active_page='officer_dashboard')

@app.post('/schedule-interview/<uuid:application_id>')
def schedule_interview_post(application_id):
    restrict = require_role('officer')
    if restrict:
        return restrict

    officer_id = session['userID']
    schedule_date_str = request.form.get('schedule_date')
    location = request.form.get('location')
    notes = request.form.get('notes')

    if not schedule_date_str or not location:
        flash('Interview date/time and location are required.', 'danger')
        return redirect(url_for('schedule_interview_form', application_id=application_id))

    try:
        schedule_date = datetime.fromisoformat(schedule_date_str)
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(url_for('schedule_interview_form', application_id=application_id))

    new_interview = interview_repository.schedule_interview(
        application_id, officer_id, schedule_date, location, notes
    )

    if new_interview:
        flash('Interview scheduled successfully! Application status updated.', 'success')
        return redirect(url_for('review_application_form', application_id=application_id))
    else:
        flash('Failed to schedule interview.', 'danger')
        return redirect(url_for('schedule_interview_form', application_id=application_id))

@app.route('/view-interview/<uuid:interview_id>', methods=['GET', 'POST'])
def view_interview(interview_id):
    restrict = require_role('officer')
    if restrict:
        return restrict

    officer_id = session['userID']
    interview = interview_repository.get_interview_by_id(interview_id)

    # Security check: Ensure the interview exists and belongs to this officer
    if not interview or interview['officerid'] != officer_id:
        flash('Interview not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('officer_dashboard'))

    # Fetch related application and student info for display
    application = application_repository.get_application_by_id(interview['applicationid'])
    student = user_repository.get_user_by_id(application['userid']) if application else None

    if request.method == 'POST':
        new_status = request.form.get('status')
        notes = request.form.get('notes', interview.get('notes')) # Keep existing notes if not updated

        if not new_status or new_status not in ['scheduled', 'completed', 'cancelled']:
            flash('Invalid status selected.', 'danger')
        else:
            updated = interview_repository.update_interview_status(interview_id, new_status, notes)
            if updated:
                flash(f'Interview status updated to {new_status}.', 'success')
                # Fetch the updated interview data to display
                interview = interview_repository.get_interview_by_id(interview_id)
            else:
                flash('Failed to update interview status.', 'danger')
        # Re-render the same page after POST to show updated status or errors
        return render_template('view_interview.html',
                               interview=interview,
                               application=application,
                               student=student,
                               active_page='officer_dashboard')

    # GET request
    return render_template('view_interview.html',
                           interview=interview,
                           application=application,
                           student=student,
                           active_page='officer_dashboard')

@app.get('/admin-dashboard')
def admin_dashboard():
    restrict = require_role('admin')
    if restrict:
        return restrict

    stats = application_repository.get_application_stats()
    recent_apps = application_repository.get_all_applications()[:10]

    return render_template('admin_dashboard.html',
                           stats=stats,
                           recent_apps=recent_apps,
                           active_page='admin_dashboard')

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
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return redirect(url_for('generate_report_form'))

    report_data = None
    template_name = 'report_result.html'

    if report_type == 'summary':
        report_data = application_repository.get_application_stats(start_date, end_date)
        template_name = 'report_summary.html'
    elif report_type == 'detailed_list':
        report_data = application_repository.get_applications_by_date_range(start_date, end_date)
        template_name = 'report_detailed.html'
    else:
        flash('Invalid report type selected.', 'danger')
        return redirect(url_for('generate_report_form'))

    return render_template(template_name,
                           report_data=report_data,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           report_type=report_type,
                           active_page='admin_dashboard')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        user = user_repository.get_user_by_email(email)

        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)

            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request then simply ignore this email and no changes will be made.
This link will expire in 1 hour.
'''
            try:
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'success')
            except Exception as e:
                print(f"Mail sending error: {e}")
                flash('Failed to send reset email. Please try again later or contact support.', 'danger')
        else:
            flash('Email address not found.', 'danger')

        return redirect(url_for('signin'))

    return render_template('forgot_password.html', active_page='signin')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The password reset link has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadTimeSignature:
        flash('Invalid password reset link.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
             flash('Both password fields are required.', 'danger')
             return render_template('reset_password.html', token=token, active_page='signin')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token, active_page='signin')

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        if user_repository.update_password(email, hashed_password):
            flash('Your password has been updated successfully!', 'success')
            return redirect(url_for('signin'))
        else:
            flash('An error occurred while updating your password.', 'danger')
            return render_template('reset_password.html', token=token, active_page='signin')

    return render_template('reset_password.html', token=token, active_page='signin')

# --- Admin User Management Routes ---

@app.get('/admin/users')
def admin_list_users():
    restrict = require_role('admin')
    if restrict:
        return restrict

    users = user_repository.get_all_users()
    return render_template('admin_users.html', users=users, active_page='admin_dashboard')

@app.route('/admin/user/<uuid:user_id>/edit', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    restrict = require_role('admin')
    if restrict:
        return restrict

    user_to_edit = user_repository.get_user_by_id(user_id)
    if not user_to_edit:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_list_users'))

    if request.method == 'POST':
        new_role = request.form.get('role')
        allowed_roles = ['student', 'officer', 'admin']

        if not new_role or new_role not in allowed_roles:
            flash('Invalid role selected.', 'danger')
        # Prevent admin from accidentally demoting themselves if they are the only admin (optional check)
        elif user_id == session['userID'] and new_role != 'admin':
             flash('You cannot change your own role.', 'warning')
        else:
            updated = user_repository.update_user_role(user_id, new_role)
            if updated:
                flash(f"User {user_to_edit['email']}'s role updated to {new_role}.", 'success')
                return redirect(url_for('admin_list_users'))
            else:
                flash('Failed to update user role.', 'danger')

        # Re-render form on POST error
        return render_template('admin_edit_user.html',
                               user=user_to_edit,
                               allowed_roles=allowed_roles,
                               active_page='admin_dashboard')

    # GET request
    allowed_roles = ['student', 'officer', 'admin']
    return render_template('admin_edit_user.html',
                           user=user_to_edit,
                           allowed_roles=allowed_roles,
                           active_page='admin_dashboard')

@app.post('/admin/user/<uuid:user_id>/delete')
def admin_delete_user(user_id):
    restrict = require_role('admin')
    if restrict:
        return restrict

    # Critical check: Prevent admin from deleting themselves
    if user_id == session['userID']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_list_users'))

    user_to_delete = user_repository.get_user_by_id(user_id)
    if not user_to_delete:
         flash('User not found.', 'danger')
         return redirect(url_for('admin_list_users'))

    # Add extra confirmation step here if desired (e.g., type username)

    # Perform deletion (BE CAREFUL - consider related data implications)
    deleted = user_repository.delete_user(user_id)
    if deleted:
        flash(f"User {user_to_delete.get('email', user_id)} deleted successfully.", 'success')
    else:
        flash(f"Failed to delete user {user_to_delete.get('email', user_id)}. Check logs for details.", 'danger')

    return redirect(url_for('admin_list_users'))

# --- End Admin User Management Routes ---

if __name__ == '__main__':
    app.run(debug=True, port=5001)
