from functools import wraps
from flask import session, redirect, url_for, flash

def init_security(app):
    """Initialize basic security features"""
    pass

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_admin' not in session:
            flash('Please log in as admin to access this page', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function

def validate_password(password):
    """Basic password validation"""
    return len(password) >= 6

def sanitize_input(text):
    """Basic input sanitization"""
    if not text:
        return ""
    return text.strip() 