import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "life_journey_pro_edition_2026"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///life_journey.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.String(500), default="Sharing my journey...")
    posts = db.relationship('Entry', backref='author', lazy=True)
    followed = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(100), nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Feed Logic: Own posts + Followed posts
    f_posts = Entry.query.join(followers, (followers.c.followed_id == Entry.user_id)).filter(followers.c.follower_id == user.id)
    o_posts = Entry.query.filter_by(user_id=user.id)
    posts = f_posts.union(o_posts).order_by(Entry.date_posted.desc()).all()
    # Suggestions
    all_u = User.query.filter(User.id != user.id).all()
    sugg = [u for u in all_u if u not in user.followed]
    return render_template('home.html', posts=posts, user=user, all_users=sugg)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.bio = request.form.get('bio')
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit_profile.html', user=user)

@app.route('/save_journey', methods=['POST'])
def save_journey():
    if 'user_id' not in session: return redirect(url_for('login'))
    content = request.form.get('content')
    file = request.files.get('file')
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    db.session.add(Entry(content=content, image_file=filename, user_id=session['user_id']))
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session: return redirect(url_for('login'))
    q = request.form.get('search_query')
    res = User.query.filter(User.username.contains(q)).all()
    return render_template('home.html', posts=[], user=User.query.get(session['user_id']), all_users=[], search_results=res)

@app.route('/follow/<int:user_id>')
def follow(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    u_to_f = User.query.get(user_id)
    me = User.query.get(session['user_id'])
    if u_to_f and u_to_f not in me.followed:
        me.followed.append(u_to_f)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db.session.add(User(username=request.form['username'], email=request.form['email'], password=request.form['password']))
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
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)