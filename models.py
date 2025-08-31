from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # NEW: Added fields for settings
    email = db.Column(db.String(120), unique=True, nullable=True)
    theme = db.Column(db.String(20), nullable=False, default='nebula')
    reminder_time = db.Column(db.Integer, nullable=True) # Will store the hour (0-23)

    user_memories = db.Column(db.Text, nullable=False, default="My name is...")
    ai_memories = db.Column(db.Text, nullable=False, default="")
    forgotten_memories_json = db.Column(db.Text, nullable=False, default="[]")

    entries = db.relationship('JournalEntry', backref='author', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def forgotten_memories(self):
        return json.loads(self.forgotten_memories_json)

    @forgotten_memories.setter
    def forgotten_memories(self, memories_list):
        self.forgotten_memories_json = json.dumps(memories_list)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (UniqueConstraint('date', 'user_id', name='_date_user_uc'),)