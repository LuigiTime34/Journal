from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
from sqlalchemy import extract
import mistune
import json
import csv
import io
import zipfile

from config import Config
from models import db, User, JournalEntry
from utils import get_ai_greeting, get_ai_analysis, perform_ai_search

app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        elif email and User.query.filter_by(email=email).first():
            flash('Email address is already in use.', 'error')
        else:
            user = User(username=username, email=email or None)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Core App Routes ---
@app.route('/')
@login_required
def dashboard():
    greeting = get_ai_greeting(app.config['GEMINI_API_KEY'], current_user.user_memories)
    today = date.today()
    on_this_day_entries = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        extract('month', JournalEntry.date) == today.month,
        extract('day', JournalEntry.date) == today.day,
        extract('year', JournalEntry.date) != today.year
    ).order_by(JournalEntry.date.desc()).all()
    return render_template('dashboard.html', greeting=greeting, on_this_day_entries=on_this_day_entries)

@app.route('/entry/choose')
@login_required
def choose_entry_date():
    return render_template('choose_date.html')

@app.route('/journal')
@login_required
def journal_view():
    start_date_str = request.args.get('week_start')
    today = date.today()
    if start_date_str:
        week_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        week_start_date = today - timedelta(days=(today.weekday() + 1) % 7)
    week_end_date = week_start_date + timedelta(days=6)
    prev_week_start, next_week_start = week_start_date - timedelta(days=7), week_start_date + timedelta(days=7)
    entries = JournalEntry.query.filter(JournalEntry.user_id == current_user.id, JournalEntry.date >= week_start_date, JournalEntry.date <= week_end_date).all()
    entries_by_date = {entry.date: entry for entry in entries}
    week_days = [{"date": week_start_date + timedelta(days=i), "entry": entries_by_date.get(week_start_date + timedelta(days=i))} for i in range(7)]
    has_any_entry = JournalEntry.query.filter_by(user_id=current_user.id).first()
    return render_template('journal_view.html', week_days=week_days, week_start_date=week_start_date,
                           prev_week_url=url_for('journal_view', week_start=prev_week_start.strftime('%Y-%m-%d')),
                           next_week_url=url_for('journal_view', week_start=next_week_start.strftime('%Y-%m-%d')),
                           has_any_entry=has_any_entry)

@app.route('/entry/new')
@login_required
def new_entry_today():
    return redirect(url_for('edit_entry', date_str=date.today().strftime('%Y-%m-%d')))

@app.route('/entry/edit/<date_str>', methods=['GET', 'POST'])
@login_required
def edit_entry(date_str):
    entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    entry = JournalEntry.query.filter_by(date=entry_date, user_id=current_user.id).first()
    if request.method == 'POST':
        content = request.form.get('content')
        analysis = get_ai_analysis(app.config['GEMINI_API_KEY'], content, current_user.user_memories, current_user.ai_memories, current_user.forgotten_memories)
        ai_response = analysis.get('response')
        new_memories = analysis.get('new_memory_sentences', [])
        if new_memories:
            updated_ai_memories = current_user.ai_memories
            for mem in new_memories:
                if mem not in updated_ai_memories: updated_ai_memories += f"\n- {mem}"
            current_user.ai_memories = updated_ai_memories.strip()
        if entry:
            entry.content, entry.ai_response = content, ai_response
        else:
            entry = JournalEntry(date=entry_date, content=content, ai_response=ai_response, user_id=current_user.id)
            db.session.add(entry)
        db.session.commit()
        flash('Entry saved!', 'success')
        return redirect(url_for('view_entry', date_str=date_str))
    return render_template('entry.html', entry_date=entry_date, entry=entry)

@app.route('/entry/view/<date_str>')
@login_required
def view_entry(date_str):
    entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    entry = JournalEntry.query.filter_by(date=entry_date, user_id=current_user.id).first_or_404()
    entry.content_html = mistune.html(entry.content)
    if entry.ai_response: entry.ai_response_html = mistune.html(entry.ai_response)
    return render_template('view_entry.html', entry=entry)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    results, query = [], ""
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            all_entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.date.asc()).all()
            all_entries_text = "\n\n---\n\n".join([f"Date: {e.date.strftime('%Y-%m-%d')}\n\n{e.content}" for e in all_entries])
            relevant_dates_str = perform_ai_search(app.config['GEMINI_API_KEY'], query, all_entries_text)
            if relevant_dates_str:
                relevant_dates = [datetime.strptime(d_str, '%Y-%m-%d').date() for d_str in relevant_dates_str]
                results = [e for e in all_entries if e.date in relevant_dates]
    return render_template('search.html', query=query, results=results)

@app.route('/memories')
@login_required
def memories_page():
    return render_template('memories.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

# --- Settings Page and Actions ---
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    if request.method == 'POST':
        action = request.form.get('action')
        # Update Account Info
        if action == 'update_account':
            current_user.email = request.form.get('email') or None
            reminder_time_str = request.form.get('reminder_time')
            current_user.reminder_time = int(reminder_time_str) if reminder_time_str != 'disabled' else None
            db.session.commit()
            flash('Account settings updated.', 'success')
        # Change Password
        elif action == 'change_password':
            if not current_user.check_password(request.form.get('current_password')):
                flash('Current password is incorrect.', 'error')
            elif request.form.get('new_password') != request.form.get('confirm_password'):
                flash('New passwords do not match.', 'error')
            else:
                current_user.set_password(request.form.get('new_password'))
                db.session.commit()
                flash('Password changed successfully.', 'success')
        # Change Theme
        elif action == 'change_theme':
            current_user.theme = request.form.get('theme')
            db.session.commit()
            flash('Theme updated!', 'success')
        # Clear AI Memories
        elif action == 'clear_ai_memories':
            current_user.ai_memories = ""
            current_user.forgotten_memories_json = "[]"
            db.session.commit()
            flash('AI memories have been cleared.', 'success')
        # Clear All Entries
        elif action == 'clear_entries':
            if request.form.get('confirm_text') == 'destroyer_of_worlds':
                JournalEntry.query.filter_by(user_id=current_user.id).delete()
                db.session.commit()
                flash('All journal entries have been deleted.', 'success')
            else:
                flash('Confirmation text was incorrect.', 'error')
        # Delete Account
        elif action == 'delete_account':
            if request.form.get('confirm_text') == 'destroyer_of_worlds':
                user_to_delete = User.query.get(current_user.id)
                db.session.delete(user_to_delete)
                db.session.commit()
                flash('Your account has been permanently deleted.', 'success')
                return redirect(url_for('register'))
            else:
                flash('Confirmation text was incorrect.', 'error')
        return redirect(url_for('settings_page'))
    return render_template('settings.html')

@app.route('/export')
@login_required
def export_data():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('user_memories.txt', current_user.user_memories)
        zf.writestr('ai_memories.txt', current_user.ai_memories)
        entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.date.asc()).all()
        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['date', 'content', 'ai_response'])
        for entry in entries:
            writer.writerow([entry.date.isoformat(), entry.content, entry.ai_response])
        zf.writestr('journal.csv', csv_output.getvalue())
    memory_file.seek(0)
    return send_file(memory_file, download_name=f'JournAI_Export_{date.today()}.zip', as_attachment=True)

# --- API Routes for Memories ---
@app.route('/api/memories', methods=['GET'])
@login_required
def get_memories():
    return jsonify({'user_memories': current_user.user_memories, 'ai_memories': current_user.ai_memories, 'forgotten_memories': current_user.forgotten_memories})

@app.route('/api/memories', methods=['POST'])
@login_required
def save_memories():
    data = request.json
    current_user.user_memories = data.get('user_memories', '')
    current_user.ai_memories = data.get('ai_memories', '')
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Memories saved!'})

@app.route('/api/memories/forget', methods=['POST'])
@login_required
def forget_memory():
    data = request.json
    memory_to_forget = data.get('memory')
    if memory_to_forget:
        current_user.ai_memories = '\n'.join([line for line in current_user.ai_memories.split('\n') if memory_to_forget not in line])
        forgotten = current_user.forgotten_memories
        if memory_to_forget not in forgotten:
            forgotten.append(memory_to_forget)
            current_user.forgotten_memories = forgotten
        db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/memories/reinstate', methods=['POST'])
@login_required
def reinstate_memory():
    data = request.json
    memory_to_reinstate = data.get('memory')
    if memory_to_reinstate:
        current_user.ai_memories += f"\n- {memory_to_reinstate}"
        forgotten = current_user.forgotten_memories
        if memory_to_reinstate in forgotten:
            forgotten.remove(memory_to_reinstate)
            current_user.forgotten_memories = forgotten
        db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)