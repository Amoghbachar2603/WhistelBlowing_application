from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import random
import string
from gemini_utils import extract_fields
from security import init_security, admin_required, validate_password, sanitize_input
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reports.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key'  # Simplified secret key
db = SQLAlchemy(app)

# Initialize security features
init_security(app)

# Models
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_id = db.Column(db.String(10), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    time = db.Column(db.String(100))
    category = db.Column(db.String(100))
    accused = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')
    trackings = db.relationship('Tracking', backref='report', lazy=True)

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    last_login = db.Column(db.DateTime)

# Utility functions
def generate_reference_id():
    while True:
        ref_id = 'REP' + ''.join(random.choices(string.digits, k=3))
        if not Report.query.filter_by(reference_id=ref_id).first():
            return ref_id

def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        try:
            description = sanitize_input(request.form['description'])
            if not description:
                flash('Please provide a description', 'error')
                return render_template('report.html')
            
            # Extract information using Gemini
            extracted_info = extract_fields(description)
            
            # Generate reference ID and password
            ref_id = generate_reference_id()
            password = generate_password()
            
            # Create new report
            report = Report(
                reference_id=ref_id,
                password=password,
                description=description,
                location=extracted_info.get('location', 'Not specified'),
                time=extracted_info.get('time', 'Not specified'),
                category=extracted_info.get('category', 'Other'),
                accused=extracted_info.get('accused', 'Not specified')
            )
            
            db.session.add(report)
            db.session.commit()
            
            # Store credentials in session for reporter view
            session['report_id'] = report.id
            session['report_ref'] = ref_id
            session['report_password'] = password
            
            flash('Report submitted successfully!', 'success')
            return redirect(url_for('reporter_view'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error submitting report: {str(e)}")
            flash('Error submitting report. Please try again.', 'error')
            return render_template('report.html')
    
    return render_template('report.html')

@app.route('/reporter/view')
def reporter_view():
    if not session.get('report_id'):
        flash('No active report found', 'error')
        return redirect(url_for('home'))
    
    report = Report.query.get(session['report_id'])
    if not report:
        flash('Report not found', 'error')
        return redirect(url_for('home'))
    
    trackings = Tracking.query.filter_by(report_id=report.id).all()
    return render_template('reporter_view.html', 
                         report=report,
                         trackings=trackings,
                         reference_id=session['report_ref'],
                         password=session['report_password'])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['user_id'] = admin.id
            session['is_admin'] = True
            admin.last_login = datetime.now(timezone.utc)
            db.session.commit()
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin_view.html', reports=reports)

@app.route('/admin/update_status/<int:report_id>', methods=['POST'])
@admin_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'in_progress', 'resolved']:
        report.status = new_status
        db.session.commit()
        flash('Status updated successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_tracking/<int:report_id>', methods=['POST'])
@admin_required
def add_tracking(report_id):
    report = Report.query.get_or_404(report_id)
    message = sanitize_input(request.form['message'])
    if message:
        tracking = Tracking(
            report_id=report.id,
            message=message,
            admin_id=session['user_id']
        )
        db.session.add(tracking)
        db.session.commit()
        flash('Tracking message added successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_report/<int:report_id>', methods=['POST'])
@admin_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/extract_fields', methods=['POST'])
def extract_fields_route():
    try:
        data = request.get_json()
        description = data.get('description', '')
        if not description:
            return jsonify({'success': False, 'error': 'No description provided'})
        
        extracted_info = extract_fields(description)
        return jsonify({'success': True, 'fields': extracted_info})
    except Exception as e:
        print(f"Error extracting fields: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/track-report', methods=['GET', 'POST'])
def track_report():
    if request.method == 'POST':
        reference_id = request.form.get('reference_id')
        password = request.form.get('password')
        
        if not reference_id or not password:
            flash('Please provide both reference ID and password', 'error')
            return redirect(url_for('track_report'))
        
        report = Report.query.filter_by(reference_id=reference_id).first()
        if report and report.password == password:
            trackings = Tracking.query.filter_by(report_id=report.id).all()
            return render_template('reporter_view.html',
                                report=report,
                                trackings=trackings,
                                reference_id=reference_id,
                                password=password)
        else:
            flash('Invalid reference ID or password', 'error')
            return redirect(url_for('track_report'))
    
    return render_template('track.html')

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)