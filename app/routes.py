from random import choice
import requests
import os
from faker import Faker
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db, ALLOWED_EXTENSIONS
from app.models import Tag, Task, Note, Event, User
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    try:
        today = datetime.now()
        upcoming_events = Event.query.filter(
            Event.date >= today.date(),
            Event.date <= (today + timedelta(days=7)).date(),
            Event.user_id == current_user.id,
        ).order_by(Event.date).all()
        tasks = Task.query.filter(Task.user_id == current_user.id).order_by(Task.date_created).limit(5).all()

        exchange_rates = {}
        try:
            response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
            if response.status_code == 200:
                data = response.json()
                exchange_rates = {
                    'EUR': data['rates']['EUR'],
                    'GBP': data['rates']['GBP'],
                    'JPY': data['rates']['JPY'],
                    'RUB': data['rates']['RUB']
                }
        except Exception as e:
            print(f"Error fetching exchange rates: {e}")

        weather = {}
        try:
            api_key = '464e82d61abce416c1062d5ad2b87032'
            location = 'Moscow'
            weather_url = f'http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric'
            response = requests.get(weather_url)
            if response.status_code == 200:
                data = response.json()
                weather = {
                    'location': data['name'],
                    'temperature': data['main']['temp'],
                    'condition': data['weather'][0]['description']
                }
        except Exception as e:
            print(f"Error fetching weather data: {e}")

        return render_template('index.html', 
                            upcoming_events=upcoming_events, 
                            tasks=tasks, 
                            exchange_rates=exchange_rates, 
                            weather=weather)

    except Exception as e:
        print(f"Ошибка в маршруте /: {e}")
        return "An error occurred while processing your request.", 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_tasks = Task.query.filter_by(user_id=current_user.id).count()
    user_events = Event.query.filter_by(user_id=current_user.id).count()
    user_notes = Note.query.filter_by(user_id=current_user.id).count()

    if request.method == 'POST':
        if 'avatar' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['avatar']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = f"{current_user.username}_{current_user.id}_{secure_filename(file.filename)}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            current_user.avatar = filename
            db.session.commit()
            return redirect(url_for('main.profile'))
    return render_template('profile.html',
                           user=current_user,
                           user_tasks=user_tasks,
                           user_events=user_events,
                           user_notes=user_notes)


@bp.route('/profile/change_email', methods=['POST'])
@login_required
def change_email():
    new_email = request.form.get('new_email')
    if not new_email:
        flash('Email cannot be empty.', 'error')
        return redirect(url_for('main.profile'))
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user:
        flash('This email is already in use.', 'error')
        return redirect(url_for('main.profile'))

    current_user.email = new_email
    db.session.commit()
    flash('Your email has been updated successfully.', 'success')
    return redirect(url_for('main.profile'))

@bp.route('/profile/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not check_password_hash(current_user.password, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('main.profile'))
    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'error')
        return redirect(url_for('main.profile'))
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Your password has been updated successfully.', 'success')
    return redirect(url_for('main.profile'))

@bp.context_processor
@login_required
def inject_current_time():
    return {'current_time': datetime.now()}

# todo
@bp.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = Task(content=task_content, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('main.todo'))
    delete_expired_tasks()
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('todo.html', tasks=tasks)

def delete_expired_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    for task in tasks:
        if task.should_be_deleted():
            db.session.delete(task)
    db.session.commit()

@bp.route('/delete_task/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to delete this task.', 'error')
        return redirect(url_for('main.todo'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('main.todo'))

@bp.route('/complete_task/<int:id>', methods=['POST'])
@login_required
def complete_task(id):
    task = Task.query.get_or_404(id)
    task.is_completed = True
    task.completed_at = datetime.now(tz=timezone.utc)  # Осведомлённый datetime
    db.session.commit()
    flash("Задача отмечена как выполненная!", "success")
    return redirect(url_for('main.todo'))

# calendar
@bp.route('/calendar', methods=['GET', 'POST'])
@login_required
def calendar():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        new_event = Event(title=title, date=datetime.strptime(date, '%Y-%m-%d'), user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('calendar'))
    events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template('calendar.html', events=events)

@bp.route('/api/events')
@login_required
def api_events():
    events = Event.query.filter_by(user_id=current_user.id).all()
    events_data = [
        {
            "title": event.title,
            "start": event.date.isoformat(),
            "category": event.category
        }
        for event in events
    ]
    return jsonify(events_data)

@bp.route('/api/add_event', methods=['POST'])
@login_required
def add_event():
    try:
        data = request.get_json()
        print("Received data:", data)
        if not data or 'title' not in data or 'date' not in data:
            return jsonify({"error": "Invalid data"}), 400
        event_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        category = data.get('category', 'General')
        new_event = Event(title=data['title'], date=event_date, category=category, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"message": "Event added successfully"}), 200
    except Exception as e:
        print(f"Error adding event: {e}")
        return jsonify({"error": "Failed to add event"}), 500

@bp.route('/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('main.calendar'))

# notes
@bp.route('/notes')
@login_required
def notes():
    notes = Note.query.filter_by(user_id=current_user.id).all()
    return render_template('notes.html', notes=notes)

@bp.route('/api/notes')
@login_required
def get_notes():
    notes = Note.query.filter_by(user_id=current_user.id).all()
    notes_data = [
        {
            "title": note.title,
            "content": note.content,
            "tags": [tag.name for tag in note.tags]  # Возвращаем теги
        }
        for note in notes
    ]
    return jsonify(notes_data)

@bp.route('/api/delete_note/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({"error": "You do not have permission to delete this note."}), 403
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted successfully!"}), 200

@bp.route('/api/add_note', methods=['POST'])
@login_required
def add_note():
    try:
        data = request.get_json()
        print("Received data:", data)
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({"error": "Invalid data"}), 400
        new_note = Note(title=data['title'], content=data['content'], user_id=current_user.id)
        if 'tags' in data:
            for tag_name in data['tags']:
                tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
                if not tag:
                    tag = Tag(name=tag_name, user_id=current_user.id)
                new_note.tags.append(tag)
        db.session.add(new_note)
        db.session.commit()
        return jsonify({"message": "Note added successfully"}), 200
    except Exception as e:
        print(f"Error adding note: {e}")
        return jsonify({"error": "Failed to add note"}), 500

@bp.route('/notes/search', methods=['GET'])
@login_required
def search_notes():
    query = request.args.get('q', '').strip()
    if not query:
        return render_template('notes.html', notes=[], search_query=query)

    notes = Note.query.filter(
        (Note.title.ilike(f'%{query}%')) |
        (Note.content.ilike(f'%{query}%')) |
        (Note.tags.any(Tag.name.ilike(f'%{query}%')))
    ).all()

    return render_template('notes.html', notes=notes, search_query=query)

# generator
fake = Faker()
@bp.route('/generate_test_data')
@login_required
def generate_test_data():
    Task.query.delete()
    Event.query.delete()
    Note.query.delete()
    Tag.query.delete()
    db.session.commit()

    for _ in range(1000):
        task_content = fake.sentence(nb_words=30)
        new_task = Task(content=task_content, user_id=current_user.id)
        db.session.add(new_task)

    today = datetime.now().date()
    for i in range(4):
        event_title = fake.sentence(nb_words=10)
        event_date = today + timedelta(days=i + 1)
        new_event = Event(title=event_title, date=event_date, user_id=current_user.id)
        db.session.add(new_event)

    categories = ["Work", "Personal", "Urgent", "General"]
    for _ in range(150):
        event_title = fake.sentence(nb_words=4)
        event_date = fake.date_this_year()
        event_category = choice(categories)
        new_event = Event(title=event_title, date=event_date, category=event_category, user_id=current_user.id)
        db.session.add(new_event)

    for _ in range(1000):
        note_title = fake.sentence(nb_words=5)
        note_content = fake.paragraph(nb_sentences=30)
        new_note = Note(title=note_title, content=note_content, user_id=current_user.id)
        tags = [fake.word() for _ in range(fake.random_int(min=1, max=5))]

        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
            if not tag:
                tag = Tag(name=tag_name, user_id=current_user.id)
            new_note.tags.append(tag)

        db.session.add(new_note)

    db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/generate_test_users')
def generate_test_users():
    for user_cnt in range(1000):
        try:
            print(f"Try generate user {user_cnt}")
            email = f"test{user_cnt}@test"
            password = f"testpass{user_cnt}"
            username = f"user{user_cnt}"
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                break
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                break
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)


            user = User.query.filter_by(username=username).first()
            for _ in range(20):
                task_content = fake.sentence(nb_words=30)
                new_task = Task(content=task_content, user_id=user.id)
                db.session.add(new_task)

            today = datetime.now().date()
            for i in range(3):
                event_title = fake.sentence(nb_words=10)
                event_date = today + timedelta(days=i + 1)
                new_event = Event(title=event_title, date=event_date, user_id=user.id)
                db.session.add(new_event)

            categories = ["Work", "Personal", "Urgent", "General"]
            for _ in range(47):
                event_title = fake.sentence(nb_words=4)
                event_date = fake.date_this_year()
                event_category = choice(categories)
                new_event = Event(title=event_title, date=event_date, category=event_category, user_id=user.id)
                db.session.add(new_event)

            for _ in range(20):
                note_title = fake.sentence(nb_words=5)
                note_content = fake.paragraph(nb_sentences=30)
                new_note = Note(title=note_title, content=note_content, user_id=user.id)
                tags = [fake.word() for _ in range(fake.random_int(min=1, max=5))]

                for tag_name in tags:
                    tag = Tag.query.filter_by(name=tag_name, user_id=user.id).first()
                    if not tag:
                        tag = Tag(name=tag_name, user_id=user.id)
                    new_note.tags.append(tag)

                db.session.add(new_note)
                db.session.commit()
        except Exception as e:
            print(f"Error generate user {user_cnt}: {e}")

    return redirect(url_for('auth.login'))