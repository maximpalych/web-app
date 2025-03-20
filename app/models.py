from flask_login import UserMixin
from app import db
from datetime import datetime, timedelta, timezone

note_tags = db.Table('note_tags',
    db.Column('note_id', db.Integer, db.ForeignKey('note.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    events = db.relationship('Event', backref='user', lazy=True)
    avatar = db.Column(db.String(150), nullable=True, default='default.png')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(tz=timezone.utc))
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def should_be_deleted(self):
        """Проверяет, нужно ли удалить задачу (если прошло больше суток после выполнения)."""
        if self.is_completed and self.completed_at:
            completed_at_aware = self.completed_at.replace(tzinfo=timezone.utc) if self.completed_at.tzinfo is None else self.completed_at
            return datetime.now(tz=timezone.utc) > completed_at_aware + timedelta(days=1)
        return False

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.relationship('Tag', secondary=note_tags, backref=db.backref('notes', lazy='dynamic'))
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    