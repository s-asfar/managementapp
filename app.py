import os
from dotenv import load_dotenv
from flask import Flask, g, render_template, redirect, request, url_for, session, abort, flash
from flask_bcrypt import Bcrypt
from datetime import date as dt

from repositories import user_repository
from repositories.user_repository import *
from datetime import date

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = os.getenv('APP_SECRET_KEY')

#index
@app.get('/')
def index():
    userID = session.get('userID')
    return render_template('index.html', active_page='home')

#user get
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


#user post
@app.post('/signup')
def signup_account():
    if 'userID' in session:
        flash('You are already logged in.', 'danger')
        return redirect(url_for('profile'))
    
    email = request.form.get('email').lower()
    password = request.form.get('password')
    if not email or not password:
        flash('Email and password are required.', 'danger')
        return redirect(url_for('signup'))
    
    does_user_exist = user_repository.does_email_exist(email)
    if does_user_exist:
        flash('User with this email already exists.', 'danger')
        return redirect(url_for('signup'))
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_repository.create_user(email, hashed_password)
    user = user_repository.get_user_by_email(email)
    session['userID'] = user['userID']
    flash('Account created successfully!', 'success')
    return redirect(url_for('profile'))

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
    age = request.form.get('age')
    height = request.form.get('height')
    weight = request.form.get('weight')
    goal = request.form.get('goal')
    if not name or not age or not height or not weight or not goal:
        flash('All fields are required.', 'danger')
        return render_template('editprofile.html', user=user_repository.get_user_by_id(userID), active_page='profile')
    updated_user = user_repository.update_user(userID, name, age, height, weight, goal)
    if updated_user is None:
        flash('An error occurred while updating the profile.', 'danger')
        return redirect(url_for('profile'))
    user_data = user_repository.get_user_profile_data(userID)
    flash('Profile updated successfully!', 'success')
    return render_template('profile.html', user=user_data, active_page='profile')

