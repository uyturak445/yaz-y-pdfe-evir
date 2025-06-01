import os
import secrets
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from openai import OpenAI
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import re
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Argon2 password hasher
password_hasher = PasswordHasher()

# .env dosyasından çevresel değişkenleri yükle
load_dotenv()

# Flask uygulamasını başlat
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Veritabanı yapılandırması - Natro hosting için SQLite veya MySQL
if os.getenv('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cv_creator.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Güvenlik ayarları
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Loglama ayarları
log_dir = os.getenv('LOG_DIR', 'logs')
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
file_handler = RotatingFileHandler(f'{log_dir}/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Getbelge başlatılıyor')

# Bootstrap'i başlat
bootstrap = Bootstrap(app)

# OpenAI API anahtarını ayarla
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    app.logger.error('OpenAI API anahtarı bulunamadı')
    raise ValueError("OpenAI API anahtarı sağlanmalıdır")

# OpenAI istemcisini başlat
client = OpenAI(api_key=api_key)

# Veritabanı bağlantısını oluştur
db = SQLAlchemy(app)

# Veritabanı modelleri
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    resumes = db.relationship('Resume', backref='user', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('Document', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = password_hasher.hash(password)
    
    def check_password(self, password):
        try:
            return password_hasher.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False
        
    def rehash_password_if_needed(self, password):
        if password_hasher.check_needs_rehash(self.password_hash):
            self.set_password(password)
            db.session.commit()

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    formatted_content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

# Uygulama bağlamında veritabanını oluştur
with app.app_context():
    db.create_all()

# Yardımcı fonksiyonlar
def current_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_active:
            return user
    return None

# IP bazlı rate limiting için sözlük
login_attempts = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_rate_limited(ip_address):
    current_time = time.time()
    if ip_address in login_attempts:
        attempts, last_attempt_time = login_attempts[ip_address]
        # Son 15 dakika içinde 5'ten fazla başarısız deneme varsa
        if attempts >= 5 and current_time - last_attempt_time < 900:  # 15 dakika = 900 saniye
            return True
        # 15 dakikadan fazla zaman geçtiyse sayacı sıfırla
        elif current_time - last_attempt_time >= 900:
            login_attempts[ip_address] = (1, current_time)
        else:
            login_attempts[ip_address] = (attempts + 1, last_attempt_time)
    else:
        login_attempts[ip_address] = (1, current_time)
    return False

def validate_password(password):
    """
    Şifre en az 10 karakter uzunluğunda, en az bir büyük harf, 
    bir küçük harf, bir rakam ve bir özel karakter içermelidir.
    """
    if len(password) < 10:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

# Ana sayfa
@app.route('/')
def index():
    return render_template('index.html')

# Kayıt olma
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # Gerekli alanların kontrolü
        if not username or not email or not password or not password_confirm:
            flash('Tüm alanları doldurun.', 'danger')
            return render_template('register.html')
            
        # Şifre kontrolü
        if password != password_confirm:
            flash('Şifreler eşleşmiyor.', 'danger')
            return render_template('register.html')
            
        # Şifre güvenlik kontrolü
        if not validate_password(password):
            flash('Şifre en az 10 karakter uzunluğunda olmalı ve en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter (!@#$%^&*(),.?":{}|<>) içermelidir.', 'danger')
            return render_template('register.html')
        
        # Kullanıcı adı ve email kontrolü
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            flash('Bu kullanıcı adı veya e-posta adresi zaten alınmış!', 'danger')
            return render_template('register.html')
        
        try:
            # Yeni kullanıcı oluştur
            new_user = User(
                username=username, 
                email=email,
                last_login=db.func.current_timestamp()
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            # Kullanıcıyı oturum açık olarak ayarla
            session['user_id'] = new_user.id
            session.permanent = True
            
            app.logger.info(f'Yeni kullanıcı kaydedildi: {username}')
            flash('Başarıyla kayıt oldunuz!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Kullanıcı kaydı sırasında hata: {str(e)}')
            flash('Kayıt sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
    
    return render_template('register.html')

# Giriş yapma
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        ip_address = request.remote_addr
        
        # Rate limiting kontrolü
        if is_rate_limited(ip_address):
            app.logger.warning(f'IP adresi rate-limited: {ip_address}')
            flash('Çok fazla başarısız giriş denemesi. Lütfen 15 dakika sonra tekrar deneyin.', 'danger')
            return render_template('login.html')
        
        if not username_or_email or not password:
            flash('Kullanıcı adı/e-posta ve şifre gereklidir.', 'danger')
            return render_template('login.html')
        
        # Kullanıcı adı veya e-posta ile kullanıcıyı bul
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        # Kullanıcı kilitli mi kontrol et
        if user and user.locked_until and user.locked_until > db.func.current_timestamp():
            flash('Hesabınız kilitlendi. Lütfen daha sonra tekrar deneyin.', 'danger')
            return render_template('login.html')
        
        if not user or not user.check_password(password):
            # Başarısız giriş denemelerini izle
            if user:
                user.login_attempts += 1
                # 5 başarısız denemeden sonra hesabı kilitle (30 dakika)
                if user.login_attempts >= 5:
                    user.locked_until = db.func.current_timestamp() + timedelta(minutes=30)
                    app.logger.warning(f'Hesap kilitlendi: {user.username}')
                    flash('Çok fazla başarısız giriş denemesi. Hesabınız 30 dakika kilitlendi.', 'danger')
                db.session.commit()
            
            app.logger.warning(f'Başarısız giriş denemesi: {username_or_email}')
            flash('Geçersiz kullanıcı adı/e-posta veya şifre.', 'danger')
            return render_template('login.html')
        
        if not user.is_active:
            flash('Bu hesap devre dışı bırakılmış. Lütfen yönetici ile iletişime geçin.', 'danger')
            return render_template('login.html')
        
        # Şifre hashleme algoritması güncellenmeli mi kontrol et
        user.rehash_password_if_needed(password)
        
        # Başarılı giriş - login_attempts ve locked_until sıfırla
        user.login_attempts = 0
        user.locked_until = None
        
        # Kullanıcı giriş bilgilerini güncelle
        user.last_login = db.func.current_timestamp()
        user.login_count = User.login_count + 1
        db.session.commit()
        
        # Kullanıcıyı oturum açık olarak ayarla
        session['user_id'] = user.id
        session.permanent = remember
        
        app.logger.info(f'Kullanıcı giriş yaptı: {user.username}')
        flash('Başarıyla giriş yaptınız!', 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

# Çıkış yapma
@app.route('/logout')
def logout():
    user = current_user()
    if user:
        app.logger.info(f'Kullanıcı çıkış yaptı: {user.username}')
    
    # Flask oturumunu temizle
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('index'))

# Kontrol Paneli
@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    resumes = Resume.query.filter_by(user_id=user.id).order_by(Resume.updated_at.desc()).all()
    documents = Document.query.filter_by(user_id=user.id).order_by(Document.updated_at.desc()).all()
    
    return render_template('dashboard.html', user=user, resumes=resumes, documents=documents)

# Yeni CV oluşturma
@app.route('/create-resume', methods=['GET', 'POST'])
@login_required
def create_resume():
    if request.method == 'POST':
        title = request.form.get('title')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        education = request.form.get('education')
        experience = request.form.get('experience')
        skills = request.form.get('skills')
        
        # Gerekli alanların kontrolü
        if not title or not name:
            flash('Başlık ve ad alanları gereklidir.', 'danger')
            return render_template('create_resume.html')
        
        # OpenAI API kullanarak özgeçmiş oluştur
        try:
            # Gerçek API çağrısı - daha modern ve profesyonel CV için geliştirilmiş prompt
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen profesyonel bir CV yazarısın. Verilen bilgilere göre modern, profesyonel ve ATS uyumlu bir CV oluştur. CV, iş veren dikkatini çekecek şekilde güzel formatlanmış olmalı. Bölümleri (Kişisel Bilgiler, Eğitim, Deneyim, Beceriler) net bir şekilde ayır ve görsel olarak düzenli olmalı. Markdown formatını kullan ve başlıkları, alt başlıkları belirgin hale getir. İş deneyimlerini madde işaretleri ile listele ve somut başarıları vurgula."},
                    {"role": "user", "content": f"Ad Soyad: {name}\nE-posta: {email}\nTelefon: {phone}\nEğitim: {education}\nDeneyim: {experience}\nBeceriler: {skills}"}
                ]
            )
            ai_content = response.choices[0].message.content
            
            # Veritabanına kaydet
            user = current_user()
            new_resume = Resume(
                title=title,
                content=ai_content,
                user_id=user.id
            )
            db.session.add(new_resume)
            db.session.commit()
            
            app.logger.info(f'Kullanıcı {user.username} yeni CV oluşturdu: {title}')
            flash('CV başarıyla oluşturuldu!', 'success')
            return redirect(url_for('view_resume', resume_id=new_resume.id))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'CV oluşturma sırasında hata: {str(e)}')
            flash(f'CV oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
            return render_template('create_resume.html')
    
    return render_template('create_resume.html')

# CV görüntüleme
@app.route('/resume/<int:resume_id>')
@login_required
def view_resume(resume_id):
    user = current_user()
    resume = Resume.query.get_or_404(resume_id)
    
    if resume.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının CV\'sine erişmeye çalıştı: {resume_id}')
        abort(403)
    
    return render_template('view_resume.html', resume=resume)

# CV silme
@app.route('/delete-resume/<int:resume_id>')
@login_required
def delete_resume(resume_id):
    user = current_user()
    resume = Resume.query.get_or_404(resume_id)
    
    if resume.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının CV\'sini silmeye çalıştı: {resume_id}')
        abort(403)
    
    try:
        db.session.delete(resume)
        db.session.commit()
        app.logger.info(f'Kullanıcı {user.username} CV sildi: {resume.title}')
        flash('CV başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'CV silme sırasında hata: {str(e)}')
        flash('CV silinirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
    
    return redirect(url_for('dashboard'))

# CV PDF olarak indirme
@app.route('/download-resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    user = current_user()
    resume = Resume.query.get_or_404(resume_id)
    
    if resume.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının CV\'sini indirmeye çalıştı: {resume_id}')
        abort(403)
    
    # Stil parametrelerini URL'den al
    color_scheme = request.args.get('color_scheme', 'blue')
    font_style = request.args.get('font_style', 'segoe')
    layout_style = request.args.get('layout_style', 'classic')
    header_style = request.args.get('header_style', 'standard')
    
    app.logger.info(f'Kullanıcı {user.username} CV indirme sayfasını görüntüledi: {resume.title} (Stil: {color_scheme}, {font_style}, {layout_style}, {header_style})')
    # CV içeriğini özel bir yazdırma şablonuyla göster ve stil parametrelerini ilet
    return render_template('print_resume.html', resume=resume, 
                          color_scheme=color_scheme, 
                          font_style=font_style, 
                          layout_style=layout_style, 
                          header_style=header_style)

# Doküman oluşturma
@app.route('/create-document', methods=['GET', 'POST'])
@login_required
def create_document():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Gerekli alanların kontrolü
        if not title or not content:
            flash('Başlık ve içerik alanları gereklidir.', 'danger')
            return render_template('create_document.html')
        
        try:
            # OpenAI API kullanarak metni düzenle ve formatla
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen profesyonel bir metin düzenleyicisin. Verilen metni düzelt, biçimlendir ve HTML formatında güzel bir şekilde yeniden yaz. Metnin yapısını, bölümlerini ve önemli noktalarını vurgula. Metni daha profesyonel hale getir. Cümleleri düzelt ve akıcılığı artır. HTML başlıkları (<h1>, <h2>), paragraflar (<p>), listeler (<ul>, <li>) ve gerekli diğer HTML etiketlerini kullan. Belgenin yapısı temiz, profesyonel ve okunması kolay olmalı."},
                    {"role": "user", "content": content}
                ]
            )
            formatted_content = response.choices[0].message.content
            
            # Veritabanına kaydet
            user = current_user()
            new_document = Document(
                title=title,
                content=content,
                formatted_content=formatted_content,
                user_id=user.id
            )
            db.session.add(new_document)
            db.session.commit()
            
            app.logger.info(f'Kullanıcı {user.username} yeni belge oluşturdu: {title}')
            flash('PDF belge başarıyla oluşturuldu!', 'success')
            return redirect(url_for('view_document', document_id=new_document.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Belge oluşturma sırasında hata: {str(e)}')
            flash(f'Belge oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
            return render_template('create_document.html')
    
    return render_template('create_document.html')

# Doküman görüntüleme
@app.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    user = current_user()
    document = Document.query.get_or_404(document_id)
    
    if document.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının belgesine erişmeye çalıştı: {document_id}')
        abort(403)
    
    return render_template('view_document.html', document=document)

# Doküman silme
@app.route('/delete-document/<int:document_id>')
@login_required
def delete_document(document_id):
    user = current_user()
    document = Document.query.get_or_404(document_id)
    
    if document.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının belgesini silmeye çalıştı: {document_id}')
        abort(403)
    
    try:
        db.session.delete(document)
        db.session.commit()
        app.logger.info(f'Kullanıcı {user.username} belge sildi: {document.title}')
        flash('Belge başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Belge silme sırasında hata: {str(e)}')
        flash('Belge silinirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
    
    return redirect(url_for('dashboard'))

# Doküman PDF olarak indirme
@app.route('/download-document/<int:document_id>')
@login_required
def download_document(document_id):
    user = current_user()
    document = Document.query.get_or_404(document_id)
    
    if document.user_id != user.id:
        app.logger.warning(f'Kullanıcı {user.username} başka bir kullanıcının belgesini indirmeye çalıştı: {document_id}')
        abort(403)
    
    # HTML sayfasını döndür ve otomatik yazdırmayı tetikle
    return render_template('print_document.html', document=document)

# Hata sayfaları
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f'Sunucu hatası: {str(e)}')
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    
    app.run(host=host, port=port, debug=debug) 