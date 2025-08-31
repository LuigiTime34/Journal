from datetime import datetime
from app import app, db, mail  # Import the app, db, and mail instances from your main app
from models import User, JournalEntry
from flask_mail import Message

def send_daily_reminders():
    """
    This script is run by a scheduler (like PythonAnywhere's tasks).
    It checks the current time and sends reminders to users.
    """
    # Use the app context to access the database and configuration
    with app.app_context():
        # Get the current hour in UTC (servers run on UTC time)
        current_utc_hour = datetime.utcnow().hour
        
        print(f"[{datetime.utcnow()}] Running reminder job for UTC hour: {current_utc_hour}")

        # Find users who have set a reminder for the current hour and have an email
        users_to_remind = User.query.filter_by(reminder_time=current_utc_hour).filter(User.email != None).all()
        
        if not users_to_remind:
            print("No users to remind this hour.")
            return

        print(f"Found {len(users_to_remind)} user(s) to remind.")

        for user in users_to_remind:
            # Check if the user has already written an entry today
            today = datetime.utcnow().date()
            entry_today = JournalEntry.query.filter_by(user_id=user.id, date=today).first()

            if not entry_today:
                try:
                    msg = Message(
                        subject="Your Daily JournAI Reminder",
                        sender=("JournAI", app.config['MAIL_USERNAME']),
                        recipients=[user.email]
                    )
                    # The body of the email can be plain text or HTML
                    msg.body = f"Hi {user.username},\n\nJust a friendly reminder to take a moment for yourself and capture your thoughts for the day.\n\nWrite your entry here: https://journai.pythonanywhere.com/\n\nBest,\nThe JournAI Companion"
                    # msg.html = "<b>You can also use HTML for fancier emails!</b>"
                    
                    mail.send(msg)
                    print(f"Reminder sent successfully to {user.username} at {user.email}")

                except Exception as e:
                    print(f"!!! FAILED to send email to {user.username}: {e}")
            else:
                print(f"User {user.username} has already written an entry today. No reminder sent.")

if __name__ == '__main__':
    send_daily_reminders()