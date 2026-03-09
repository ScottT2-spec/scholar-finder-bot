"""
ScholarFinder Web App — Flask Backend
Built by Scott Antwi | Alpha Global Minds 🌍

Features:
- User signup/login with sessions
- User profiles (country, field, education level)
- Scholarship matching based on profile
- Save/bookmark scholarships
- Dashboard with saved items + upcoming deadlines
- API endpoints for all data
- Admin panel
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, session, flash, g, send_from_directory
)
import urllib.request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
# Persistent secret key (survives restarts)
_secret_path = os.path.join(os.path.dirname(__file__), '.secret_key')
if os.path.exists(_secret_path):
    with open(_secret_path, 'r') as _f:
        app.secret_key = _f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(_secret_path, 'w') as _f:
        _f.write(app.secret_key)

# Security settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# Webhook secret for scholarship management
WEBHOOK_SECRET = 'sf_whk_' + hashlib.sha256(app.secret_key.encode()).hexdigest()[:32]

# ============================================
# DATABASE
# ============================================
DB_PATH = os.path.join(os.path.dirname(__file__), 'scholarweb.db')
# Use local data/ folder (works on PythonAnywhere and local)
_local_data = os.path.join(os.path.dirname(__file__), 'data')
_bot_data = os.path.join(os.path.dirname(__file__), '..', 'scholarbot')
DATA_DIR = _local_data if os.path.isdir(_local_data) else _bot_data

ADMIN_EMAIL = 'scottantwi930@gmail.com'

# ============================================
# RATE LIMITING (in-memory)
# ============================================
from collections import defaultdict
import time as _time

_login_attempts = defaultdict(list)  # ip -> [timestamps]
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW = 300  # 5 minutes

def check_rate_limit(ip):
    now = _time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _LOGIN_WINDOW]
    if len(_login_attempts[ip]) >= _MAX_LOGIN_ATTEMPTS:
        return False
    _login_attempts[ip].append(now)
    return True


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            country TEXT DEFAULT '',
            field_of_study TEXT DEFAULT '',
            education_level TEXT DEFAULT '',
            gpa TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_data TEXT DEFAULT '{}',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'interested',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, item_type, item_name)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()
    db.close()

# ============================================
# AUTH HELPERS
# ============================================
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt

def verify_password(password, password_hash, salt):
    hashed, _ = hash_password(password, salt)
    return hashed == password_hash

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Login required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        db = get_db()
        user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or not user['is_admin']:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

def log_activity(user_id, action, details=''):
    try:
        db = get_db()
        ip = request.remote_addr or ''
        db.execute(
            'INSERT INTO activity_log (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
            (user_id, action, details, ip)
        )
        db.commit()
    except Exception:
        pass

# ============================================
# LOAD DATA FILES
# ============================================
def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_scholarships():
    return load_json('scholarships.json')

def get_universities():
    return load_json('universities.json')

def get_opportunities():
    return load_json('opportunities.json')

def get_cost_of_living():
    return load_json('cost_data.json')

def get_visa_guides():
    return load_json('visa_data.json')

def get_faq():
    return load_json('faq_data.json')

def get_test_prep():
    return load_json('test_prep_data.json')

def get_essay_guides():
    return load_json('essay_guides.json')

# ============================================
# SCHOLARSHIP MATCHING
# ============================================
def match_scholarships(user):
    """Match scholarships to user profile — returns sorted by relevance"""
    scholarships = get_scholarships()
    if not user:
        return scholarships

    scored = []
    user_country = (user['country'] or '').lower()
    user_field = (user['field_of_study'] or '').lower()
    user_level = (user['education_level'] or '').lower()
    user_interests = (user['interests'] or '').lower()

    for s in scholarships:
        score = 0
        s_str = json.dumps(s).lower()

        # Country match
        if user_country and user_country in s_str:
            score += 30

        # Field match
        if user_field:
            fields = [f.strip() for f in user_field.split(',')]
            for field in fields:
                if field and field in s_str:
                    score += 25
                    break

        # Education level match
        if user_level:
            level_map = {
                'undergraduate': ['undergraduate', 'bachelor', 'bsc', 'ba'],
                'masters': ['masters', 'master', 'msc', 'ma', 'graduate'],
                'phd': ['phd', 'doctoral', 'doctorate', 'research'],
            }
            for key, terms in level_map.items():
                if key in user_level:
                    for term in terms:
                        if term in s_str:
                            score += 20
                            break
                    break

        # Interest match
        if user_interests:
            interests = [i.strip() for i in user_interests.split(',')]
            for interest in interests:
                if interest and interest in s_str:
                    score += 10

        # Fully funded bonus
        if 'full' in s_str and ('tuition' in s_str or 'funded' in s_str):
            score += 5

        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]


# ============================================
# CSRF PROTECTION
# ============================================
@app.before_request
def csrf_protect():
    if request.method == 'POST' and not request.path.startswith('/api/'):
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or token != form_token:
            # Skip CSRF for API and webhook endpoints
            if not request.is_json and not request.path.startswith('/webhook'):
                flash('Session expired. Please try again.', 'error')
                return redirect(request.url)

@app.before_request
def generate_csrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)

@app.context_processor
def inject_csrf():
    return dict(csrf_token=session.get('csrf_token', ''))

# ============================================
# PAGE ROUTES
# ============================================
@app.route('/')
def index():
    user = get_current_user()
    stats = {
        'scholarships': len(get_scholarships()),
        'universities': len(get_universities()),
        'opportunities': len(get_opportunities()),
        'cities': len(get_cost_of_living()),
    }
    return render_template('index.html', user=user, stats=stats)

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        if not email or not username or not password:
            flash('All fields are required', 'error')
            return render_template('signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template('signup.html')

        db = get_db()
        existing = db.execute(
            'SELECT id FROM users WHERE email = ? OR username = ?',
            (email, username)
        ).fetchone()

        if existing:
            flash('Email or username already taken', 'error')
            return render_template('signup.html')

        country = request.form.get('country', '').strip()
        education_level = request.form.get('education_level', '').strip()
        field_of_study = request.form.get('field_of_study', '').strip()

        if not country or not education_level or not field_of_study:
            flash('All fields are required', 'error')
            return render_template('signup.html')

        if not request.form.get('terms'):
            flash('You must agree to the Terms & Conditions', 'error')
            return render_template('signup.html')

        dob_day = request.form.get('dob_day', '')
        dob_month = request.form.get('dob_month', '')
        dob_year = request.form.get('dob_year', '')
        dob = f"{dob_day}/{dob_month}/{dob_year}" if dob_day and dob_month and dob_year else ''
        hear_about = request.form.get('hear_about', '').strip()
        friend_name = request.form.get('friend_name', '').strip()

        password_hash, salt = hash_password(password)
        is_admin = 1 if email == ADMIN_EMAIL else 0

        db.execute(
            'INSERT INTO users (email, username, password_hash, salt, full_name, is_admin, country, education_level, field_of_study, dob, hear_about, friend_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (email, username, password_hash, salt, full_name, is_admin, country, education_level, field_of_study, dob, hear_about, friend_name)
        )
        db.commit()

        user = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = username
        log_activity(user['id'], 'signup')

        # Handle avatar upload during signup
        if 'avatar' in request.files:
            f = request.files['avatar']
            if f.filename:
                ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'jpg'
                if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    fname = f"avatar_{user['id']}.{ext}"
                    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'avatars')
                    os.makedirs(upload_dir, exist_ok=True)
                    f.save(os.path.join(upload_dir, fname))
                    db.execute('UPDATE users SET avatar = ? WHERE id = ?', (f"/uploads/avatars/{fname}", user['id']))
                    db.commit()

        return redirect(url_for('dashboard_page') + '?welcome=1')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE email = ? OR username = ?',
            (login_id, login_id)
        ).fetchone()

        # Rate limiting
        client_ip = request.remote_addr or 'unknown'
        if not check_rate_limit(client_ip):
            flash('Too many login attempts. Please wait 5 minutes.', 'error')
            return render_template('login.html')

        if not user or not verify_password(password, user['password_hash'], user['salt']):
            flash('Invalid email/username or password', 'error')
            return render_template('login.html')

        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        db.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
        db.commit()
        log_activity(user['id'], 'login')

        return redirect(url_for('dashboard_page'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    log_activity(session.get('user_id'), 'logout')
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_page():
    db = get_db()
    user = get_current_user()

    if request.method == 'POST':
        db.execute("""
            UPDATE users SET
                full_name = ?, country = ?, field_of_study = ?,
                education_level = ?, gpa = ?, interests = ?, bio = ?
            WHERE id = ?
        """, (
            request.form.get('full_name', ''),
            request.form.get('country', ''),
            request.form.get('field_of_study', ''),
            request.form.get('education_level', ''),
            request.form.get('gpa', ''),
            request.form.get('interests', ''),
            request.form.get('bio', ''),
            session['user_id']
        ))
        db.commit()
        log_activity(session['user_id'], 'profile_update')
        flash('Profile updated!', 'success')
        return redirect(url_for('dashboard_page'))

    return render_template('profile.html', user=user)

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile_page'))
    f = request.files['avatar']
    if f.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile_page'))
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        flash('Only image files allowed', 'error')
        return redirect(url_for('profile_page'))
    fname = f"avatar_{session['user_id']}.{ext}"
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, fname))
    db = get_db()
    db.execute('UPDATE users SET avatar = ? WHERE id = ?', (f"/uploads/avatars/{fname}", session['user_id']))
    db.commit()
    flash('Profile picture updated!', 'success')
    return redirect(url_for('profile_page'))

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'uploads'), filename)

@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['resume']
    if f.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'pdf'
    if ext not in ('pdf', 'doc', 'docx', 'txt'):
        return jsonify({'error': 'Only PDF, DOC, DOCX, TXT allowed'}), 400
    fname = f"resume_{session['user_id']}.{ext}"
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'resumes')
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, fname))
    # Read text for analysis
    content = ''
    fpath = os.path.join(upload_dir, fname)
    if ext == 'txt':
        with open(fpath, 'r', errors='ignore') as rf: content = rf.read()
    elif ext == 'pdf':
        try:
            import subprocess
            result = subprocess.run(['pdftotext', fpath, '-'], capture_output=True, text=True, timeout=10)
            content = result.stdout
        except: content = '[PDF uploaded — text extraction not available]'
    else:
        content = '[Document uploaded — please paste text for detailed analysis]'
    return jsonify({'success': True, 'text': content, 'filename': fname})

@app.route('/api/admin/send-email', methods=['POST'])
@admin_required
def api_admin_send_email():
    data = request.get_json()
    to_emails = data.get('to', [])
    subject = data.get('subject', '')
    body = data.get('body', '')
    if not to_emails or not subject or not body:
        return jsonify({'error': 'Missing to, subject, or body'}), 400
    # Store emails in DB for now (actual SMTP can be configured later)
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS sent_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        to_email TEXT, subject TEXT, body TEXT, sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    sent = 0
    for email in to_emails:
        db.execute('INSERT INTO sent_emails (to_email, subject, body) VALUES (?, ?, ?)', (email, subject, body))
        sent += 1
    db.commit()
    return jsonify({'success': True, 'sent': sent, 'note': 'Emails queued. Configure SMTP in settings to actually deliver.'})

@app.route('/api/admin/users-full')
@admin_required
def api_admin_users_full():
    db = get_db()
    users = db.execute('''
        SELECT u.*, COUNT(b.id) as bookmark_count
        FROM users u LEFT JOIN bookmarks b ON u.id = b.user_id
        GROUP BY u.id ORDER BY u.created_at DESC
    ''').fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/dashboard')
@login_required
def dashboard_page():
    user = get_current_user()
    db = get_db()

    bookmarks = db.execute(
        'SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()

    matched = match_scholarships(user)[:10]

    stats = {
        'bookmarks': len(bookmarks),
        'applied': len([b for b in bookmarks if b['status'] == 'applied']),
        'interested': len([b for b in bookmarks if b['status'] == 'interested']),
    }

    return render_template('dashboard.html', user=user, bookmarks=bookmarks, matched=matched, stats=stats)

@app.route('/scholarships')
def scholarships_page():
    user = get_current_user()
    return render_template('scholarships.html', user=user)

@app.route('/universities')
def universities_page():
    user = get_current_user()
    return render_template('universities.html', user=user)

@app.route('/opportunities')
def opportunities_page():
    user = get_current_user()
    return render_template('opportunities.html', user=user)

@app.route('/cost-of-living')
def cost_page():
    user = get_current_user()
    return render_template('cost.html', user=user)

@app.route('/visa-guide')
def visa_page():
    user = get_current_user()
    return render_template('visa.html', user=user)

@app.route('/test-prep')
def testprep_page():
    user = get_current_user()
    return render_template('testprep.html', user=user)

@app.route('/faq')
def faq_page():
    user = get_current_user()
    return render_template('faq.html', user=user)

# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/scholarships')
def api_scholarships():
    q = request.args.get('q', '').lower()
    level = request.args.get('level', '').lower()
    country = request.args.get('country', '').lower()
    field = request.args.get('field', '').lower()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    user = get_current_user()
    if user:
        scholarships = match_scholarships(user)
    else:
        scholarships = get_scholarships()

    # Filter
    results = []
    for s in scholarships:
        s_str = json.dumps(s).lower()
        if q and q not in s_str:
            continue
        if level and level not in s_str:
            continue
        if country and country not in s_str:
            continue
        if field and field not in s_str:
            continue
        results.append(s)

    # Log search
    if q and session.get('user_id'):
        try:
            db = get_db()
            db.execute(
                'INSERT INTO search_log (user_id, query, results_count, category) VALUES (?, ?, ?, ?)',
                (session['user_id'], q, len(results), 'scholarships')
            )
            db.commit()
        except Exception:
            pass

    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': results[start:end]
    })

@app.route('/api/universities')
def api_universities():
    q = request.args.get('q', '').lower()
    country = request.args.get('country', '').lower()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    universities = get_universities()
    results = []
    for u in universities:
        u_str = json.dumps(u).lower()
        if q and q not in u_str:
            continue
        if country and country not in u_str:
            continue
        results.append(u)

    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': results[start:end]
    })

@app.route('/api/opportunities')
def api_opportunities():
    q = request.args.get('q', '').lower()
    otype = request.args.get('type', '').lower()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    opportunities = get_opportunities()
    results = []
    for o in opportunities:
        o_str = json.dumps(o).lower()
        if q and q not in o_str:
            continue
        if otype and otype not in o_str:
            continue
        results.append(o)

    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': results[start:end]
    })

@app.route('/api/cost')
def api_cost():
    return jsonify(get_cost_of_living())

@app.route('/api/visa')
def api_visa():
    return jsonify(get_visa_guides())

@app.route('/api/faq')
def api_faq():
    return jsonify(get_faq())

@app.route('/api/testprep')
def api_testprep():
    return jsonify(get_test_prep())

@app.route('/api/essays')
def api_essays():
    return jsonify(get_essay_guides())

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'scholarships': len(get_scholarships()),
        'universities': len(get_universities()),
        'opportunities': len(get_opportunities()),
        'cities': len(get_cost_of_living()),
        'visa_countries': len(get_visa_guides()),
        'faq': len(get_faq()),
    })

# ============================================
# BOOKMARK API
# ============================================
@app.route('/api/bookmarks', methods=['GET'])
@login_required
def api_get_bookmarks():
    db = get_db()
    bookmarks = db.execute(
        'SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    return jsonify([dict(b) for b in bookmarks])

@app.route('/api/bookmarks', methods=['POST'])
@login_required
def api_add_bookmark():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    item_type = data.get('type', '')
    item_name = data.get('name', '')

    if not item_type or not item_name:
        return jsonify({'error': 'Type and name required'}), 400

    db = get_db()
    try:
        db.execute(
            'INSERT INTO bookmarks (user_id, item_type, item_name, item_data) VALUES (?, ?, ?, ?)',
            (session['user_id'], item_type, item_name, json.dumps(data.get('data', {})))
        )
        db.commit()
        log_activity(session['user_id'], 'bookmark_add', f'{item_type}: {item_name}')
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Already bookmarked'}), 409

@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def api_remove_bookmark(bookmark_id):
    db = get_db()
    db.execute(
        'DELETE FROM bookmarks WHERE id = ? AND user_id = ?',
        (bookmark_id, session['user_id'])
    )
    db.commit()
    return jsonify({'success': True})

@app.route('/api/bookmarks/<int:bookmark_id>/status', methods=['PUT'])
@login_required
def api_update_bookmark_status(bookmark_id):
    data = request.get_json()
    status = data.get('status', 'interested')
    db = get_db()
    db.execute(
        'UPDATE bookmarks SET status = ? WHERE id = ? AND user_id = ?',
        (status, bookmark_id, session['user_id'])
    )
    db.commit()
    return jsonify({'success': True})

# ============================================
# MATCHING API
# ============================================
@app.route('/api/match')
@login_required
def api_match():
    user = get_current_user()
    matched = match_scholarships(user)
    limit = int(request.args.get('limit', 20))
    return jsonify({
        'total': len(matched),
        'results': matched[:limit]
    })

# ============================================
# ADMIN API
# ============================================
@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    db = get_db()
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_bookmarks = db.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]
    total_searches = db.execute('SELECT COUNT(*) FROM search_log').fetchone()[0]

    recent_users = db.execute(
        'SELECT username, email, country, created_at FROM users ORDER BY created_at DESC LIMIT 20'
    ).fetchall()

    top_searches = db.execute(
        'SELECT query, COUNT(*) as cnt FROM search_log GROUP BY query ORDER BY cnt DESC LIMIT 20'
    ).fetchall()

    daily_signups = db.execute(
        "SELECT date(created_at) as day, COUNT(*) as cnt FROM users GROUP BY day ORDER BY day DESC LIMIT 30"
    ).fetchall()

    return jsonify({
        'total_users': total_users,
        'total_bookmarks': total_bookmarks,
        'total_searches': total_searches,
        'recent_users': [dict(u) for u in recent_users],
        'top_searches': [dict(s) for s in top_searches],
        'daily_signups': [dict(d) for d in daily_signups],
    })

@app.route('/admin')
@login_required
def admin_page():
    user = get_current_user()
    if not user['is_admin']:
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard_page'))
    stats = {
        'scholarships': len(get_scholarships()),
        'opportunities': len(get_opportunities()),
    }
    return render_template('admin.html', user=user, stats=stats)

@app.route('/api/admin/delete-user', methods=['POST'])
@admin_required
def api_admin_delete_user():
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({'error': 'No username provided'}), 400
    db = get_db()
    user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    db.execute('DELETE FROM bookmarks WHERE user_id = ?', (user['id'],))
    db.execute('DELETE FROM search_log WHERE user_id = ?', (user['id'],))
    db.execute('DELETE FROM users WHERE id = ?', (user['id'],))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/clear-searches', methods=['POST'])
@admin_required
def api_admin_clear_searches():
    db = get_db()
    db.execute('DELETE FROM search_log')
    db.commit()
    return jsonify({'success': True, 'message': 'Search logs cleared'})

# ============================================
# TOOLS — Essay Rater, School Matcher, Resume Review
# ============================================
@app.route('/tools/essay-rater', methods=['GET'])
def essay_rater_page():
    user = get_current_user()
    return render_template('tool_essay.html', user=user)

@app.route('/api/tools/rate-essay', methods=['POST'])
def api_rate_essay():
    data = request.get_json()
    essay = data.get('essay', '').strip()
    essay_type = data.get('type', 'personal_statement')
    if not essay:
        return jsonify({'error': 'No essay provided'}), 400

    words = essay.split()
    word_count = len(words)
    sentences = [s.strip() for s in essay.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_len = word_count / max(sentence_count, 1)
    paragraphs = [p.strip() for p in essay.split('\n\n') if p.strip()]

    score = 30  # Base score — strict grading
    feedback = []

    # Word count
    if essay_type == 'personal_statement':
        if 500 <= word_count <= 650: score += 15; feedback.append(('✅', 'Word count is perfect for a personal statement'))
        elif 400 <= word_count < 500: score += 8; feedback.append(('⚠️', f'At {word_count} words, consider expanding slightly (aim for 500-650)'))
        elif word_count > 650: score += 5; feedback.append(('⚠️', f'At {word_count} words, you might want to trim (aim for 500-650)'))
        else: feedback.append(('❌', f'At {word_count} words, this is too short for a personal statement (aim for 500-650)'))
    else:
        if word_count >= 200: score += 10
        else: feedback.append(('⚠️', f'At {word_count} words, consider adding more detail'))

    # Paragraphs
    if len(paragraphs) >= 3: score += 10; feedback.append(('✅', f'Good structure with {len(paragraphs)} paragraphs'))
    elif len(paragraphs) == 1: feedback.append(('❌', 'Break your essay into multiple paragraphs for readability'))
    else: score += 5; feedback.append(('⚠️', 'Consider adding more paragraphs for better structure'))

    # Sentence variety
    if 12 <= avg_sentence_len <= 22: score += 8; feedback.append(('✅', 'Good sentence length variety'))
    elif avg_sentence_len > 25: feedback.append(('⚠️', 'Some sentences are very long — try breaking them up'))
    elif avg_sentence_len < 10: feedback.append(('⚠️', 'Sentences are quite short — try combining some for flow'))

    # Personal voice
    personal_words = sum(1 for w in words if w.lower() in ['i', 'my', 'me', 'myself'])
    if personal_words >= 5: score += 8; feedback.append(('✅', 'Strong personal voice — good use of first person'))
    else: feedback.append(('⚠️', 'Consider using more personal pronouns (I, my) to make it feel authentic'))

    # Specific details
    has_numbers = any(w.isdigit() or any(c.isdigit() for c in w) for w in words)
    if has_numbers: score += 5; feedback.append(('✅', 'Good use of specific numbers/data'))
    else: feedback.append(('💡', 'Add specific numbers or data to strengthen claims'))

    # Strong verbs
    strong_verbs = ['built', 'created', 'led', 'designed', 'developed', 'founded', 'organized', 'launched', 'achieved', 'improved', 'managed', 'grew', 'taught', 'researched', 'implemented']
    used_strong = [v for v in strong_verbs if v in essay.lower()]
    if len(used_strong) >= 3: score += 7; feedback.append(('✅', f'Great action verbs: {", ".join(used_strong[:5])}'))
    elif len(used_strong) >= 1: score += 3; feedback.append(('💡', 'Try using more action verbs (built, created, led, designed)'))
    else: feedback.append(('❌', 'Use strong action verbs to show impact (built, created, led, designed, improved)'))

    # Passive voice check
    passive_indicators = ['was ', 'were ', 'been ', 'being ']
    passive_count = sum(essay.lower().count(p) for p in passive_indicators)
    if passive_count <= 3: score += 5
    else: feedback.append(('⚠️', f'High passive voice usage ({passive_count} instances) — try active voice'))

    # Opening hook
    first_sentence = sentences[0] if sentences else ''
    boring_starts = ['my name is', 'i am writing', 'this essay', 'in this essay', 'i want to']
    if any(first_sentence.lower().startswith(b) for b in boring_starts):
        feedback.append(('❌', 'Weak opening — avoid starting with "My name is" or "I am writing". Hook the reader!'))
    elif len(first_sentence.split()) > 5:
        score += 5; feedback.append(('✅', 'Good opening sentence'))

    # Penalize generic/cliché language
    cliches = ['passionate about', 'ever since i was', 'from a young age', 'always wanted', 'dream of', 'make the world a better', 'unique perspective', 'thinking outside the box', 'at the end of the day', 'changed my life forever']
    cliche_count = sum(1 for c in cliches if c in essay.lower())
    if cliche_count >= 3: score -= 10; feedback.append(('❌', f'Too many clichés ({cliche_count} found) — be more original'))
    elif cliche_count >= 1: score -= 5; feedback.append(('⚠️', f'Found {cliche_count} cliché(s) — try to express ideas more originally'))
    else: score += 3; feedback.append(('✅', 'Good — avoids common clichés'))

    # Penalize repetitive words
    word_freq = {}
    for w in words:
        wl = w.lower().strip('.,!?;:')
        if len(wl) > 4:
            word_freq[wl] = word_freq.get(wl, 0) + 1
    repeated = [(w, c) for w, c in word_freq.items() if c >= 4 and w not in ['their', 'there', 'these', 'those', 'which', 'would', 'could', 'should', 'about', 'other']]
    if repeated:
        score -= 5
        feedback.append(('⚠️', f'Repeated words: {", ".join(w+"("+str(c)+"x)" for w,c in repeated[:3])} — vary your vocabulary'))

    # Penalize lack of conclusion/reflection
    last_para = paragraphs[-1].lower() if paragraphs else ''
    conclusion_signals = ['future', 'forward', 'goal', 'aspire', 'hope', 'continue', 'plan', 'commit', 'contribute', 'impact']
    if any(s in last_para for s in conclusion_signals):
        score += 3
    else:
        feedback.append(('💡', 'Consider ending with a forward-looking statement about your goals'))

    # STRICT CAP: max score is 90 (only world-class essays get close)
    score = min(90, max(10, score))

    # Stricter rating labels
    if score >= 85: label = 'Outstanding — Near Perfect'
    elif score >= 75: label = 'Very Good'
    elif score >= 65: label = 'Good — Room to Improve'
    elif score >= 50: label = 'Average — Needs Work'
    elif score >= 35: label = 'Below Average — Needs Significant Revision'
    else: label = 'Poor — Major Rewrite Needed'

    return jsonify({
        'score': score,
        'label': label,
        'word_count': word_count,
        'sentence_count': sentence_count,
        'paragraph_count': len(paragraphs),
        'feedback': feedback
    })

@app.route('/tools/school-matcher', methods=['GET'])
def school_matcher_page():
    user = get_current_user()
    return render_template('tool_school.html', user=user)

@app.route('/api/tools/match-schools', methods=['POST'])
def api_match_schools():
    data = request.get_json()
    gpa = data.get('gpa', '').strip()
    country_pref = data.get('country', '').lower()
    field = data.get('field', '').lower()
    budget = data.get('budget', '').lower()

    universities = get_universities()
    results = []

    for u in universities:
        u_str = json.dumps(u).lower()
        score = 0

        # Country match
        if country_pref and country_pref in u_str:
            score += 30

        # Field match
        if field and field in u_str:
            score += 25

        # Budget consideration
        tuition = u_str
        if budget == 'low' and ('free' in tuition or 'low' in tuition or 'no tuition' in tuition):
            score += 20
        elif budget == 'medium' and ('moderate' in tuition or 'medium' in tuition):
            score += 15

        # Ranking-based GPA matching
        ranking = u.get('ranking', 999)
        try:
            rank_num = int(str(ranking).replace('#', '').replace('+', '').split('-')[0])
        except (ValueError, TypeError):
            rank_num = 500

        # GPA matching logic
        try:
            gpa_val = float(gpa.split('/')[0]) if '/' in gpa else float(gpa)
            gpa_scale = float(gpa.split('/')[1]) if '/' in gpa else 4.0
            gpa_pct = gpa_val / gpa_scale
        except (ValueError, TypeError):
            gpa_pct = 0.75  # default

        if gpa_pct >= 0.9 and rank_num <= 50: score += 20
        elif gpa_pct >= 0.8 and rank_num <= 100: score += 20
        elif gpa_pct >= 0.7 and rank_num <= 200: score += 20
        elif gpa_pct >= 0.6: score += 10

        if score > 0:
            chance = 'High' if gpa_pct >= 0.85 and rank_num > 100 else 'Medium' if gpa_pct >= 0.7 else 'Reach'
            if rank_num <= 20: chance = 'Reach' if gpa_pct < 0.95 else 'Medium'
            results.append({**u, 'match_score': score, 'chance': chance})

    results.sort(key=lambda x: x['match_score'], reverse=True)
    return jsonify({'results': results[:15]})

@app.route('/tools/resume-review', methods=['GET'])
def resume_review_page():
    user = get_current_user()
    return render_template('tool_resume.html', user=user)

@app.route('/api/tools/rate-resume', methods=['POST'])
def api_rate_resume():
    data = request.get_json()
    resume = data.get('resume', '').strip()
    if not resume:
        return jsonify({'error': 'No resume provided'}), 400

    words = resume.split()
    word_count = len(words)
    lines = [l.strip() for l in resume.split('\n') if l.strip()]
    resume_lower = resume.lower()

    score = 25  # Strict base
    feedback = []

    # Key sections check
    sections = {
        'education': ['education', 'university', 'school', 'degree', 'gpa', 'major'],
        'experience': ['experience', 'work', 'intern', 'job', 'position', 'role'],
        'skills': ['skills', 'proficient', 'languages', 'tools', 'technologies', 'programming'],
        'projects': ['project', 'built', 'developed', 'created', 'designed'],
        'activities': ['activities', 'extracurricular', 'volunteer', 'leadership', 'club', 'organization']
    }

    found_sections = []
    for section, keywords in sections.items():
        if any(k in resume_lower for k in keywords):
            found_sections.append(section)
            score += 8

    if len(found_sections) >= 4: feedback.append(('✅', f'Great structure — includes: {", ".join(found_sections)}'))
    elif len(found_sections) >= 2: feedback.append(('⚠️', f'Found sections: {", ".join(found_sections)}. Consider adding: {", ".join([s for s in sections if s not in found_sections])}'))
    else: feedback.append(('❌', f'Missing key sections. Include: Education, Experience, Skills, Projects'))

    # Length
    if 300 <= word_count <= 700: score += 10; feedback.append(('✅', f'Good length ({word_count} words)'))
    elif word_count < 200: feedback.append(('❌', f'Too short ({word_count} words) — add more detail'))
    elif word_count > 800: feedback.append(('⚠️', f'Quite long ({word_count} words) — try to be more concise'))

    # Action verbs
    action_verbs = ['led', 'managed', 'developed', 'created', 'built', 'designed', 'organized', 'implemented', 'achieved', 'improved', 'grew', 'launched', 'analyzed', 'researched', 'taught', 'coordinated']
    used = [v for v in action_verbs if v in resume_lower]
    if len(used) >= 4: score += 10; feedback.append(('✅', f'Strong action verbs: {", ".join(used[:6])}'))
    elif len(used) >= 1: score += 5; feedback.append(('💡', 'Use more action verbs (led, built, developed, improved, managed)'))
    else: feedback.append(('❌', 'Start bullet points with strong action verbs'))

    # Quantification
    import re
    numbers = re.findall(r'\d+', resume)
    if len(numbers) >= 5: score += 10; feedback.append(('✅', 'Good quantification — numbers strengthen your claims'))
    elif len(numbers) >= 2: score += 5; feedback.append(('💡', 'Add more numbers to quantify achievements (e.g., "led team of 10", "increased by 40%")'))
    else: feedback.append(('❌', 'Quantify your achievements with numbers'))

    # Contact info
    if '@' in resume: score += 3; feedback.append(('✅', 'Email included'))
    else: feedback.append(('⚠️', 'Add your email address'))

    # Links
    if 'github' in resume_lower or 'linkedin' in resume_lower or 'http' in resume_lower:
        score += 5; feedback.append(('✅', 'Good — includes links (GitHub/LinkedIn/portfolio)'))
    else:
        feedback.append(('💡', 'Add links to GitHub, LinkedIn, or portfolio'))

    # Penalize weak formatting
    bullet_count = resume.count('•') + resume.count('-') + resume.count('*')
    if bullet_count >= 6: score += 5; feedback.append(('✅', 'Good use of bullet points'))
    elif bullet_count >= 2: score += 2
    else: feedback.append(('⚠️', 'Use bullet points for achievements — easier to scan'))

    # Penalize vague language
    vague = ['responsible for', 'helped with', 'worked on', 'assisted in', 'was involved', 'participated in']
    vague_count = sum(1 for v in vague if v in resume_lower)
    if vague_count >= 3: score -= 8; feedback.append(('❌', f'Too much vague language ({vague_count} instances) — be specific about what YOU did'))
    elif vague_count >= 1: score -= 3; feedback.append(('⚠️', 'Replace vague phrases like "responsible for" with action verbs'))

    # STRICT CAP: max 90
    score = min(90, max(10, score))

    if score >= 82: label = 'Outstanding Resume'
    elif score >= 70: label = 'Strong — Minor Polish Needed'
    elif score >= 55: label = 'Good — Needs Improvement'
    elif score >= 40: label = 'Average — Needs Work'
    else: label = 'Weak — Major Revision Needed'

    return jsonify({
        'score': score,
        'label': label,
        'word_count': word_count,
        'sections_found': found_sections,
        'feedback': feedback
    })

# Google OAuth placeholder
@app.route('/auth/google')
def google_auth():
    flash('Google login coming soon! Use email signup for now.', 'error')
    return redirect(url_for('signup_page'))

# ============================================
# AI CHATBOT API
# ============================================
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Smart chatbot — searches all data to answer questions"""
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'No message'}), 400

    query = data['message'].strip().lower()
    user = get_current_user()

    # Log the question
    if user:
        try:
            db = get_db()
            db.execute(
                'INSERT INTO search_log (user_id, query, category) VALUES (?, ?, ?)',
                (session.get('user_id'), query, 'chat')
            )
            db.commit()
        except Exception:
            pass

    # 1. Check FAQ first
    faqs = get_faq()
    for faq in faqs:
        q_text = (faq.get('question', '') or '').lower()
        keywords = [w for w in query.split() if len(w) > 2]
        matches = sum(1 for k in keywords if k in q_text)
        if matches >= 2 or (len(keywords) == 1 and keywords[0] in q_text):
            return jsonify({
                'reply': faq.get('answer', 'I found a match but no answer is available.'),
                'source': 'FAQ',
                'related': []
            })

    # 2. Check for scholarship queries
    scholarship_keywords = ['scholarship', 'fund', 'grant', 'financial', 'tuition', 'aid', 'free', 'money', 'pay', 'afford']
    if any(k in query for k in scholarship_keywords):
        scholarships = get_scholarships()
        matches = []
        for s in scholarships:
            s_str = json.dumps(s).lower()
            score = sum(1 for w in query.split() if len(w) > 2 and w in s_str)
            if score > 0:
                matches.append((score, s))
        matches.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in matches[:5]]

        if top:
            names = '\n'.join([f"• **{s.get('name', s.get('title', 'Unknown'))}** — {s.get('country', 'Various')} ({s.get('level', 'All levels')})" for s in top])
            reply = f"Here are some scholarships matching your question:\n\n{names}\n\nUse the Scholarships page to search and filter all {len(scholarships)} scholarships!"
        else:
            reply = f"I have {len(scholarships)} scholarships in the database. Try searching on the Scholarships page with specific keywords like a country or field of study."

        return jsonify({'reply': reply, 'source': 'Scholarships', 'related': [s.get('name', '') for s in top[:3]]})

    # 3. Check for university queries
    uni_keywords = ['university', 'universities', 'college', 'school', 'campus', 'ranking', 'admission']
    if any(k in query for k in uni_keywords):
        universities = get_universities()
        matches = []
        for u in universities:
            u_str = json.dumps(u).lower()
            score = sum(1 for w in query.split() if len(w) > 2 and w in u_str)
            if score > 0:
                matches.append((score, u))
        matches.sort(key=lambda x: x[0], reverse=True)
        top = [u for _, u in matches[:5]]

        if top:
            names = '\n'.join([f"• **{u.get('name', u.get('university', 'Unknown'))}** — {u.get('country', '')} (Rank: {u.get('ranking', 'N/A')})" for u in top])
            reply = f"Here are universities matching your query:\n\n{names}\n\nBrowse all {len(universities)} universities on the Universities page!"
        else:
            reply = f"I have {len(universities)} universities in the database. Try the Universities page to search by country or ranking."

        return jsonify({'reply': reply, 'source': 'Universities', 'related': [u.get('name', '') for u in top[:3]]})

    # 4. Check for opportunity queries
    opp_keywords = ['internship', 'research', 'competition', 'fellowship', 'exchange', 'summer', 'program', 'opportunity']
    if any(k in query for k in opp_keywords):
        opportunities = get_opportunities()
        matches = []
        for o in opportunities:
            o_str = json.dumps(o).lower()
            score = sum(1 for w in query.split() if len(w) > 2 and w in o_str)
            if score > 0:
                matches.append((score, o))
        matches.sort(key=lambda x: x[0], reverse=True)
        top = [o for _, o in matches[:5]]

        if top:
            names = '\n'.join([f"• **{o.get('name', o.get('title', 'Unknown'))}** — {o.get('type', 'Opportunity')}" for o in top])
            reply = f"Here are opportunities matching your query:\n\n{names}\n\nCheck the Opportunities page for all {len(opportunities)} listings!"
        else:
            reply = f"I have {len(opportunities)} opportunities including internships, research programs, competitions, and fellowships. Browse them on the Opportunities page."

        return jsonify({'reply': reply, 'source': 'Opportunities', 'related': [o.get('name', '') for o in top[:3]]})

    # 5. Check for visa queries
    visa_keywords = ['visa', 'passport', 'travel', 'immigration', 'permit']
    if any(k in query for k in visa_keywords):
        visas = get_visa_guides()
        matches = []
        for v in visas:
            v_str = json.dumps(v).lower()
            if any(w in v_str for w in query.split() if len(w) > 2):
                matches.append(v)
        if matches:
            countries = ', '.join([v.get('country', 'Unknown') for v in matches[:5]])
            reply = f"I have visa guides for: {countries}. Visit the Visa Guide section on the Telegram bot for detailed step-by-step info."
        else:
            reply = f"I have student visa guides for {len(visas)} countries. What country are you interested in?"
        return jsonify({'reply': reply, 'source': 'Visa Guides', 'related': []})

    # 6. Check for test prep queries
    test_keywords = ['ielts', 'toefl', 'sat', 'gre', 'gmat', 'duolingo', 'test', 'exam', 'english']
    if any(k in query for k in test_keywords):
        tests = get_test_prep()
        reply = "We have test prep guides for IELTS, TOEFL, SAT, GRE, and Duolingo English Test. Each includes format overview, tips, free resources, and score requirements. Check the Test Prep section for details!"
        return jsonify({'reply': reply, 'source': 'Test Prep', 'related': []})

    # 7. Check for cost/living queries
    cost_keywords = ['cost', 'living', 'expensive', 'cheap', 'rent', 'budget', 'afford', 'city', 'cities']
    if any(k in query for k in cost_keywords):
        costs = get_cost_of_living()
        matches = []
        for c in costs:
            c_str = json.dumps(c).lower()
            if any(w in c_str for w in query.split() if len(w) > 2):
                matches.append(c)
        if matches:
            cities = '\n'.join([f"• **{c.get('city', 'Unknown')}**, {c.get('country', '')} — ~${c.get('monthly_total', c.get('total', 'N/A'))}/month" for c in matches[:5]])
            reply = f"Here's what I found:\n\n{cities}\n\nCompare all {len(costs)} cities on our platform!"
        else:
            reply = f"I have cost of living data for {len(costs)} student cities worldwide. Which city or country are you interested in?"
        return jsonify({'reply': reply, 'source': 'Cost of Living', 'related': []})

    # 8. Greetings
    greetings = ['hi', 'hello', 'hey', 'sup', 'yo', 'good morning', 'good afternoon', 'good evening']
    if any(g in query for g in greetings):
        stats = {
            'scholarships': len(get_scholarships()),
            'universities': len(get_universities()),
            'opportunities': len(get_opportunities()),
        }
        reply = f"Hey there! 👋 Welcome to ScholarFinder!\n\nI can help you find:\n• 🎯 {stats['scholarships']} Scholarships\n• 🏫 {stats['universities']} Universities\n• 🚀 {stats['opportunities']} Opportunities\n• 💰 Cost of living comparisons\n• 🛂 Visa guides\n• 📝 Test prep tips\n\nJust ask me anything — like \"scholarships in Canada\" or \"engineering universities\"!"
        return jsonify({'reply': reply, 'source': 'Welcome', 'related': []})

    # 9. Help / what can you do
    help_keywords = ['help', 'what can', 'what do', 'how do', 'features', 'guide']
    if any(k in query for k in help_keywords):
        reply = "Here's what I can help with:\n\n• 🎯 **Scholarship search** — \"Find scholarships for engineering in Europe\"\n• 🏫 **University info** — \"Top universities in Canada\"\n• 🚀 **Opportunities** — \"Internships in tech\"\n• 💰 **Cost of living** — \"How much to live in London?\"\n• 🛂 **Visa info** — \"Student visa for USA\"\n• 📝 **Test prep** — \"IELTS tips\"\n\nTry asking a specific question!"
        return jsonify({'reply': reply, 'source': 'Help', 'related': []})

    # 10. Global search fallback — search everything
    all_data = []
    for s in get_scholarships():
        all_data.append(('scholarship', s.get('name', s.get('title', '')), json.dumps(s).lower()))
    for u in get_universities():
        all_data.append(('university', u.get('name', u.get('university', '')), json.dumps(u).lower()))
    for o in get_opportunities():
        all_data.append(('opportunity', o.get('name', o.get('title', '')), json.dumps(o).lower()))

    words = [w for w in query.split() if len(w) > 2]
    results = []
    for dtype, name, data_str in all_data:
        score = sum(1 for w in words if w in data_str)
        if score > 0:
            results.append((score, dtype, name))
    results.sort(key=lambda x: x[0], reverse=True)

    if results:
        top5 = results[:5]
        lines = [f"• {r[2]} ({r[1]})" for r in top5]
        reply = f"Here's what I found for \"{data['message']}\":\n\n" + '\n'.join(lines) + f"\n\n{len(results)} total results. Use the search pages for more!"
        return jsonify({'reply': reply, 'source': 'Search', 'related': []})

    # Nothing found
    reply = "I'm not sure about that one. Try asking about:\n• Scholarships (e.g., \"scholarships in Germany\")\n• Universities (e.g., \"top engineering schools\")\n• Opportunities, visa guides, test prep, or cost of living\n\nOr browse the pages above!"
    return jsonify({'reply': reply, 'source': 'Default', 'related': []})



# ============================================
# SCHOLARSHIP DATABASE MANAGEMENT
# ============================================
def init_scholarship_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS scholarship_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            scholarship_name TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            source TEXT DEFAULT 'webhook',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS link_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scholarship_name TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT DEFAULT 'unknown',
            last_checked DATETIME,
            fail_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scholarship_name)
        );
    """)
    db.commit()
    db.close()

init_scholarship_db()

def save_scholarships(data):
    path = os.path.join(DATA_DIR, 'scholarships.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================
# WEBHOOK — Scholarship Management
# ============================================
def verify_webhook(req):
    token = req.headers.get('X-Webhook-Secret') or req.args.get('secret')
    return token == WEBHOOK_SECRET

@app.route('/webhook/scholarships', methods=['POST'])
def webhook_scholarships():
    if not verify_webhook(request):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    action = data.get('action', '')  # add, update, remove, check_links, bulk_add
    result = {'action': action}

    scholarships = get_scholarships()

    if action == 'add':
        # Add a new scholarship
        new_schol = data.get('scholarship', {})
        if not new_schol.get('name'):
            return jsonify({'error': 'Scholarship name required'}), 400

        # Check for duplicates
        existing = [s for s in scholarships if s.get('name', '').lower() == new_schol['name'].lower()]
        if existing:
            return jsonify({'error': 'Scholarship already exists', 'name': new_schol['name']}), 409

        scholarships.append(new_schol)
        save_scholarships(scholarships)

        # Log
        db = get_db()
        db.execute('INSERT INTO scholarship_updates (action, scholarship_name, data, source) VALUES (?, ?, ?, ?)',
                   ('add', new_schol['name'], json.dumps(new_schol), data.get('source', 'webhook')))
        db.commit()

        result['success'] = True
        result['total'] = len(scholarships)
        result['message'] = f"Added: {new_schol['name']}"

    elif action == 'bulk_add':
        # Add multiple scholarships
        new_schols = data.get('scholarships', [])
        if not new_schols:
            return jsonify({'error': 'No scholarships provided'}), 400

        added = 0
        skipped = 0
        existing_names = {s.get('name', '').lower() for s in scholarships}

        for s in new_schols:
            if not s.get('name'):
                skipped += 1
                continue
            if s['name'].lower() in existing_names:
                skipped += 1
                continue
            scholarships.append(s)
            existing_names.add(s['name'].lower())
            added += 1

        save_scholarships(scholarships)
        result['success'] = True
        result['added'] = added
        result['skipped'] = skipped
        result['total'] = len(scholarships)

    elif action == 'update':
        # Update an existing scholarship
        name = data.get('name', '')
        updates = data.get('updates', {})
        if not name:
            return jsonify({'error': 'Scholarship name required'}), 400

        found = False
        for i, s in enumerate(scholarships):
            if s.get('name', '').lower() == name.lower():
                scholarships[i].update(updates)
                found = True
                break

        if not found:
            return jsonify({'error': 'Scholarship not found', 'name': name}), 404

        save_scholarships(scholarships)

        db = get_db()
        db.execute('INSERT INTO scholarship_updates (action, scholarship_name, data, source) VALUES (?, ?, ?, ?)',
                   ('update', name, json.dumps(updates), data.get('source', 'webhook')))
        db.commit()

        result['success'] = True
        result['message'] = f"Updated: {name}"

    elif action == 'remove':
        # Remove a scholarship
        name = data.get('name', '')
        if not name:
            return jsonify({'error': 'Scholarship name required'}), 400

        original_len = len(scholarships)
        scholarships = [s for s in scholarships if s.get('name', '').lower() != name.lower()]

        if len(scholarships) == original_len:
            return jsonify({'error': 'Scholarship not found', 'name': name}), 404

        save_scholarships(scholarships)

        db = get_db()
        db.execute('INSERT INTO scholarship_updates (action, scholarship_name, source) VALUES (?, ?, ?)',
                   ('remove', name, data.get('source', 'webhook')))
        db.commit()

        result['success'] = True
        result['total'] = len(scholarships)
        result['message'] = f"Removed: {name}"

    elif action == 'check_links':
        # Check which scholarship links are broken
        broken = []
        checked = 0
        for s in scholarships:
            link = s.get('link', '')
            if not link or not link.startswith('http'):
                continue
            try:
                req = urllib.request.Request(link, method='HEAD')
                req.add_header('User-Agent', 'ScholarFinder-LinkChecker/1.0')
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status >= 400:
                        broken.append({'name': s.get('name', '?'), 'link': link, 'status': resp.status})
                checked += 1
            except Exception as e:
                broken.append({'name': s.get('name', '?'), 'link': link, 'error': str(e)})
                checked += 1
            if checked >= 20:  # Limit per request to avoid timeout
                break

        result['success'] = True
        result['checked'] = checked
        result['broken'] = broken
        result['broken_count'] = len(broken)

    elif action == 'stats':
        # Get scholarship stats
        countries = {}
        levels = {}
        for s in scholarships:
            c = s.get('country', 'Unknown')
            countries[c] = countries.get(c, 0) + 1
            for l in (s.get('level', []) if isinstance(s.get('level'), list) else [s.get('level', 'Unknown')]):
                levels[l] = levels.get(l, 0) + 1

        result['success'] = True
        result['total'] = len(scholarships)
        result['countries'] = dict(sorted(countries.items(), key=lambda x: x[1], reverse=True))
        result['levels'] = levels
        result['with_links'] = len([s for s in scholarships if s.get('link')])
        result['with_deadlines'] = len([s for s in scholarships if s.get('deadline')])

    elif action == 'list_expired':
        # List scholarships with passed deadlines
        now = datetime.now()
        expired = []
        for s in scholarships:
            dl = s.get('deadline', '')
            if not dl or dl.lower() in ('varies', 'rolling', 'varies by university', 'ongoing'):
                continue
            try:
                dl_date = datetime.strptime(dl, '%B %d, %Y')
                if dl_date < now:
                    expired.append({'name': s.get('name', '?'), 'deadline': dl, 'country': s.get('country', '?')})
            except:
                pass

        result['success'] = True
        result['expired'] = expired
        result['expired_count'] = len(expired)

    else:
        return jsonify({'error': f'Unknown action: {action}', 'valid_actions': ['add', 'bulk_add', 'update', 'remove', 'check_links', 'stats', 'list_expired']}), 400

    return jsonify(result)


@app.route('/webhook/scholarships/secret', methods=['GET'])
@admin_required
def get_webhook_secret():
    return jsonify({'webhook_secret': WEBHOOK_SECRET, 'endpoint': request.host_url.rstrip('/') + '/webhook/scholarships'})


# ============================================
# ERROR HANDLERS
# ============================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Server error'}), 500
    return render_template('500.html'), 500

# ============================================
# INIT & RUN
# ============================================
# SEO ROUTES
# ============================================
@app.route('/robots.txt')
def robots():
    return """User-agent: *
Allow: /
Sitemap: /sitemap.xml
""", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    from flask import make_response
    base = request.host_url.rstrip('/')
    pages = ['/', '/scholarships', '/universities', '/opportunities', '/cost-of-living',
             '/visa-guide', '/test-prep', '/faq', '/tools/essay-rater', '/tools/resume-review', '/tools/school-matcher']
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append(f'<url><loc>{base}{p}</loc><changefreq>weekly</changefreq></url>')
    xml.append('</urlset>')
    resp = make_response('\n'.join(xml))
    resp.headers['Content-Type'] = 'application/xml'
    return resp

# ============================================
init_db()

init_db()


# ─── Malaria Cell Scanner ───
import joblib
import numpy as np
from PIL import Image
import io, base64

MALARIA_MODEL_PATH = '/home/scholarfinder/malaria-app/malaria_model.pkl'
MALARIA_IMG_SIZE = 32
malaria_model = None

try:
    malaria_model = joblib.load(MALARIA_MODEL_PATH)
except:
    pass

@app.route('/malaria')
def malaria_scanner():
    return send_from_directory('/home/scholarfinder/malaria-app/templates', 'index.html')

@app.route('/predict', methods=['POST'])
def malaria_predict():
    if malaria_model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image'}), 400
    try:
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img = Image.open(io.BytesIO(base64.b64decode(image_data))).convert('RGB').resize((MALARIA_IMG_SIZE, MALARIA_IMG_SIZE))
        X = (np.array(img, dtype=np.float32) / 255.0).flatten().reshape(1, -1)
        proba = malaria_model.predict_proba(X)[0]
        parasitized_prob = float(proba[1])
        uninfected_prob = float(proba[0])
        is_malaria = parasitized_prob > 0.5
        return jsonify({
            'parasitized': round(parasitized_prob * 100, 1),
            'uninfected': round(uninfected_prob * 100, 1),
            'diagnosis': 'Parasitized — Malaria Detected' if is_malaria else 'Uninfected — No Malaria',
            'confidence': round(max(parasitized_prob, uninfected_prob) * 100, 1),
            'is_malaria': is_malaria
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# AI AGENT PROXY — keeps API key server-side
# ============================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')  # Set via environment variable on PythonAnywhere
GROQ_MODEL = 'llama-3.3-70b-versatile'

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    """Proxy AI requests through the server so API key stays hidden"""
    data = request.get_json()
    if not data or not data.get('messages'):
        return jsonify({'error': 'No messages provided'}), 400

    messages = data['messages']
    max_tokens = min(data.get('max_tokens', 1024), 2500)

    try:
        import urllib.request
        req_data = json.dumps({
            'model': GROQ_MODEL,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': 0.7
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=req_data,
            headers={
                'Authorization': 'Bearer ' + GROQ_API_KEY,
                'Content-Type': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


