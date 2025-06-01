# Getbelge - CV ve PDF Belge Oluşturucu

Getbelge, OpenAI GPT modeli kullanarak profesyonel CV'ler ve PDF belgeler oluşturmanıza yardımcı olan bir web uygulamasıdır.

## Özellikler

- **CV Oluşturma:** Kişisel bilgilerinizi girerek ATS uyumlu, profesyonel CV'ler oluşturun
- **PDF Belge Oluşturma:** Metinlerinizi profesyonel formatta düzenleyin ve PDF olarak kaydedin
- **Google Hesabı ile Giriş:** Kolay ve güvenli bir şekilde Google hesabınızla giriş yapın
- **Güvenli Hesap Yönetimi:** Güçlü şifre gereksinimleri ve güvenli oturum yönetimi
- **Duyarlı Tasarım:** Mobil ve masaüstü cihazlarda sorunsuz çalışma

## Kurulum

### Gereksinimler

- Python 3.9+
- Flask ve diğer bağımlılıklar (requirements.txt dosyasında listelenmiştir)
- OpenAI API anahtarı
- Google OAuth kimlik bilgileri (isteğe bağlı)

### Yerel Kurulum

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/kullaniciadi/ai-asistanim.git
   cd ai-asistanim
   ```

2. Sanal ortam oluşturun ve etkinleştirin:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. Çevre değişkenlerini ayarlayın:
   ```bash
   cp .env.example .env
   # .env dosyasını düzenleyin ve gerekli API anahtarlarını ekleyin
   ```

5. Uygulamayı çalıştırın:
   ```bash
   python app.py
   ```

## Google OAuth Kurulumu

1. [Google Cloud Console](https://console.cloud.google.com/)'a gidin
2. Yeni bir proje oluşturun
3. "OAuth consent screen" sayfasına gidin ve uygulamanızı yapılandırın
4. "Credentials" sayfasında "Create credentials" > "OAuth client ID" seçin
5. Uygulama türü olarak "Web application" seçin
6. İzin verilen yönlendirme URI'lerini ekleyin (örn. `http://localhost:5000/login/google/authorized`)
7. Oluşturulan client ID ve client secret bilgilerini `.env` dosyanıza ekleyin

## Üretim Ortamına Dağıtım

### Gereksinimleri

- PostgreSQL veya başka bir üretim veritabanı
- HTTPS sertifikası
- Güvenilir bir web sunucusu (Nginx/Apache)

### Adımlar

1. Üretim ortamı için çevre değişkenlerini ayarlayın:
   ```
   FLASK_ENV=production
   DATABASE_URL=postgresql://kullaniciadi:sifre@localhost/veritabani
   ```

2. Veritabanını başlatın:
   ```bash
   python
   >>> from app import app, db
   >>> with app.app_context():
   >>>     db.create_all()
   ```

3. Gunicorn ile çalıştırın:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## Güvenlik Önlemleri

- Oturum çerezleri güvenli ve HTTP-only olarak ayarlanmıştır
- Şifre gereksinimleri: min. 8 karakter, büyük/küçük harf ve rakam
- CSRF koruması
- Giriş denemelerinin loglanması
- Hata sayfaları ve uygun hata yönetimi

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın. 