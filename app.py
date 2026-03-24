import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "life_journey_ultra_pro_max_v3"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///life_journey_mega.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 # 100MB for High-Quality Videos

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- ADVANCED DATABASE ARCHITECTURE ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.String(500), default="Live your life, share your journey.")
    is_verified = db.Column(db.Boolean, default=True) # Sabhi ko initial Blue Tick (Twitter Style)
    posts = db.relationship('Entry', backref='author', lazy=True, cascade="all, delete-orphan")
    stories = db.relationship('Story', backref='owner', lazy=True, cascade="all, delete-orphan")

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    media_file = db.Column(db.String(100))
    music_file = db.Column(db.String(100)) # Instagram Music
    media_type = db.Column(db.String(20)) # 'image' or 'video'
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media = db.Column(db.String(100))
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# --- SMART LOGIC ROUTES ---
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user: return redirect(url_for('logout'))
    
    # Global Feed (Twitter Style)
    posts = Entry.query.order_by(Entry.date_posted.desc()).all()
    # Active Stories only (Insta Style)
    stories = Story.query.filter(Story.expires_at > datetime.utcnow()).all()
    return render_template('home.html', user=user, posts=posts, stories=stories)

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session: return redirect(url_for('login'))
    content = request.form.get('content')
    media = request.files.get('media')
    music = request.files.get('music')
    
    m_fn = secure_filename(media.filename) if media and media.filename != '' else None
    s_fn = secure_filename(music.filename) if music and music.filename != '' else None
    m_type = 'image'
    
    if media:
        media.save(os.path.join(app.config['UPLOAD_FOLDER'], m_fn))
        if m_fn.lower().endswith(('.mp4', '.mov', '.avi')): m_type = 'video'
        
    if music: music.save(os.path.join(app.config['UPLOAD_FOLDER'], s_fn))
    
    new_post = Entry(content=content, media_file=m_fn, music_file=s_fn, media_type=m_type, user_id=session['user_id'])
    db.session.add(new_post)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/post_story', methods=['POST'])
def post_story():
    file = request.files.get('story_file')
    if file:
        fn = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
        db.session.add(Story(media=fn, user_id=session['user_id']))
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = User(username=request.form['username'], password=request.form['password'])
        db.session.add(u)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if u:
            session['user_id'] = u.id
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)