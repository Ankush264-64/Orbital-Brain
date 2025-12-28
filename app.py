import os
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mediavault.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['COVER_FOLDER'] = 'static/covers'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB Limit

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COVER_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300))
    original_name = db.Column(db.String(300))
    file_type = db.Column(db.String(50))  # 'audio', 'image', 'doc'
    title = db.Column(db.String(150), default="Unknown Title")
    artist = db.Column(db.String(150), default="Unknown Artist")
    cover_art = db.Column(db.String(200), default='default_cover.png')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPERS ---
def extract_metadata(filepath, filename):
    metadata = {'title': filename, 'artist': 'Unknown', 'cover': 'default_album.png'}
    try:
        audio = MP3(filepath, ID3=ID3)
        if 'TIT2' in audio: metadata['title'] = str(audio['TIT2'])
        if 'TPE1' in audio: metadata['artist'] = str(audio['TPE1'])
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                cover_name = f"cover_{uuid.uuid4().hex}.jpg"
                with open(os.path.join(app.config['COVER_FOLDER'], cover_name), 'wb') as img:
                    img.write(tag.data)
                metadata['cover'] = cover_name
                break
    except Exception as e:
        print(f"Metadata error: {e}")
    return metadata

# --- ROUTES ---
@app.route('/', methods=['GET'])
@login_required
def dashboard():
    query = request.args.get('q')
    if query:
        # Search Logic
        search = f"%{query}%"
        files = File.query.filter(
            (File.title.like(search) | File.artist.like(search) | File.filename.like(search)) 
            & (File.user_id == current_user.id)
        ).all()
    else:
        # Default View
        files = File.query.filter_by(user_id=current_user.id).order_by(File.id.desc()).all()
    return render_template('dashboard.html', files=files, name=current_user.username)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    if file.filename == '': return redirect(request.url)

    if file:
        safe_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)

        ftype = 'other'
        if safe_name.lower().endswith(('.mp3', '.wav')): ftype = 'audio'
        elif safe_name.lower().endswith(('.jpg', '.png', '.jpeg')): ftype = 'image'
        elif safe_name.lower().endswith('.pdf'): ftype = 'pdf'

        meta = {'title': safe_name, 'artist': 'Unknown', 'cover': 'default_album.png'}
        if ftype == 'audio':
            meta = extract_metadata(save_path, safe_name)

        new_file = File(
            filename=unique_name, original_name=safe_name, file_type=ftype,
            title=meta['title'], artist=meta['artist'], cover_art=meta['cover'],
            user_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
@login_required
def delete_file(id):
    file = File.query.get_or_404(id)
    if file.user_id == current_user.id:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            if file.cover_art != 'default_album.png':
                cover_path = os.path.join(app.config['COVER_FOLDER'], file.cover_art)
                if os.path.exists(cover_path): os.remove(cover_path)
        except: pass
        db.session.delete(file)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/files/<filename>')
@login_required
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- AUTH ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']: 
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('auth.html')

@app.route('/register', methods=['POST'])
def register():
    new_user = User(username=request.form['username'], password=request.form['password'])
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- PWA ---
@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')
@app.route('/sw.js')
def service_worker(): return send_from_directory('static', 'sw.js')

if __name__ == '__main__':
    # host="0.0.0.0" is critical to allow your phone to talk to your PC
    app.run(debug=True, host="0.0.0.0", port=5000)
    