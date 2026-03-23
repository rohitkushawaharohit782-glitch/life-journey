import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "life_journey_pro_edition_2026"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///life_journey.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

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
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    entry_id = db.Column(db.Integer, db.ForeignKey('entry.id'))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Twitter Feed Logic: Own + Followed Posts
    followed_posts = Entry.query.join(followers, (followers.c.followed_id == Entry.user_id)).filter(followers.c.follower_id == user.id)
    own_posts = Entry.query.filter_by(user_id=user.id)
    posts = followed_posts.union(own_posts).order_by(Entry.date_posted.desc()).all()
    
    # Suggestions Logic
    all_users = User.query.filter(User.id != user.id).all()
    suggestions = [u for u in all_users if u not in user.followed]
    
    return render_template('home.html', posts=posts, user=user, all_users=suggestions)

@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session: return redirect(url_for('login'))
    query = request.form.get('search_query')
    user = User.query.get(session['user_id'])
    results = User.query.filter(User.username.contains(query)).all()
    return render_template('home.html', posts=[], user=user, all_users=[], search_results=results)

@app.route('/save_journey', methods=['POST'])
def save_journey():
    if 'user_id' not in session: return redirect(url_for('login'))
    content = request.form.get('content')
    file = request.files.get('file')
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if content:
        new_post = Entry(content=content, image_file=filename, user_id=session['user_id'])
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/follow/<int:user_id>')
def follow(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_to_follow = User.query.get(user_id)
    me = User.query.get(session['user_id'])
    if user_to_follow and user_to_follow not in me.followed:
        me.followed.append(user_to_follow)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    file = request.files.get('profile_pic')
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = filename
    user.username = request.form.get('username', user.username)
    user.bio = request.form.get('bio', user.bio)
    db.session.commit()
    return redirect(url_for('home'))

# --- AUTH ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form['username'], email=request.form['email'], password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# --- CHAT & DELETE ---
@app.route('/chat/<int:receiver_id>', methods=['GET', 'POST'])
def chat(receiver_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    receiver = User.query.get_or_404(receiver_id)
    if request.method == 'POST':
        msg_body = request.form.get('message')
        if msg_body:
            msg = Message(sender_id=session['user_id'], receiver_id=receiver_id, body=msg_body)
            db.session.add(msg)
            db.session.commit()
    messages = Message.query.filter(
        ((Message.sender_id == session['user_id']) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == session['user_id']))
    ).order_by(Message.timestamp.asc()).all()
    return render_template('chat.html', receiver=receiver, messages=messages)

@app.route('/delete_message/<int:msg_id>')
def delete_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id == session['user_id']:
        db.session.delete(msg)
        db.session.commit()
    return redirect(request.referrer)

@app.route('/clear_chat/<int:receiver_id>')
def clear_chat(receiver_id):
    me = session['user_id']
    Message.query.filter(
        ((Message.sender_id == me) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == me))
    ).delete()
    db.session.commit()
    return redirect(url_for('chat', receiver_id=receiver_id))

@app.route('/chat_list')
def chat_list():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    friends = user.followed.all()
    return render_template('chat_list.html', friends=friends)

@app.route('/like/<int:post_id>')
def like(post_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    existing_like = Like.query.filter_by(user_id=session['user_id'], entry_id=post_id).first()
    if existing_like:
        db.session.delete(existing_like)
    else:
        db.session.add(Like(user_id=session['user_id'], entry_id=post_id))
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    post = Entry.query.get_or_404(post_id)
    if post.user_id == session['user_id']:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('home'))

# --- MAIN BLOCK ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)