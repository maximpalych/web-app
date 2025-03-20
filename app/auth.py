from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Task, Event, Note
from app import db, bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    total_users = User.query.count()
    total_tasks = Task.query.count()
    total_events = Event.query.count()
    total_notes = Note.query.count()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('auth.login'))
        if not check_password_hash(user.password, password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('auth.login'))
        login_user(user)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('main.index'))
    return render_template('login.html',
                           total_users=total_users, 
                           total_tasks=total_tasks, 
                           total_events=total_events, 
                           total_notes=total_notes)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists. Please use a different email.', 'error')
            return redirect(url_for('auth.signup'))
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('auth.signup'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))