# Natro Hosting Kurulum Kılavuzu

Bu belge, Getbelge Flask uygulamasını Natro hosting üzerinde nasıl kuracağınızı adım adım açıklar.

## Önkoşullar

1. Natro hosting hesabı (Python ve MySQL desteği olmalı)
2. FTP erişimi (FileZilla gibi bir FTP istemcisi kullanabilirsiniz)
3. Natro kontrol paneline erişim

## Adım 1: Veritabanı Oluşturma

1. Natro kontrol panelinize giriş yapın
2. "MySQL Veritabanları" bölümüne gidin
3. Yeni bir veritabanı oluşturun ve bilgilerini not edin:
   - Veritabanı adı
   - Veritabanı kullanıcısı
   - Veritabanı şifresi
   - Veritabanı sunucusu (genellikle localhost)

## Adım 2: FTP ile Dosyaları Yükleme

1. FileZilla veya başka bir FTP istemcisi ile sunucunuza bağlanın
2. Tüm proje dosyalarını sunucuya yükleyin
3. Dosya izinlerini kontrol edin:
   - Python dosyaları için: 644
   - Klasörler için: 755
   - wsgi.py ve passenger_wsgi.py için: 755

## Adım 3: Python Sanal Ortamı Oluşturma (İsteğe Bağlı)

SSH erişiminiz varsa:

```bash
cd /path/to/your/application
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Adım 4: .env Dosyasını Yapılandırma

1. env.example dosyasını .env olarak kopyalayın
2. Aşağıdaki bilgileri düzenleyin:
   - SECRET_KEY: Güvenli rastgele bir değer (örn: `openssl rand -hex 16` komutuyla oluşturabilirsiniz)
   - DATABASE_URL: `mysql://username:password@localhost/database_name` formatında MySQL bağlantı URL'nizi yazın
   - OPENAI_API_KEY: OpenAI API anahtarınızı ekleyin

## Adım 5: Veritabanı Tablolarını Oluşturma

1. SSH erişiminiz varsa:
   ```bash
   cd /path/to/your/application
   python setup_db.py
   ```

2. SSH erişiminiz yoksa:
   - setup_db.py dosyasını bir kez çalıştırmak için Natro destek ekibine başvurun

## Adım 6: Passenger Yapılandırması

1. passenger_wsgi.py dosyasında PYTHON_PATH değişkenini Natro'daki Python yolunuza göre ayarlayın
2. Natro kontrol panelinde "Python Uygulamaları" bölümünden uygulamanızı yapılandırın:
   - Uygulama dizini: Uygulamanızın yüklendiği dizin
   - WSGI dosyası: passenger_wsgi.py

## Adım 7: Test Etme

1. Tarayıcınızdan alan adınızı ziyaret edin
2. Uygulamanın doğru çalıştığını doğrulayın

## Sorun Giderme

- **500 Internal Server Error**: logs/app.log dosyasını kontrol edin
- **Veritabanı bağlantı hataları**: .env dosyasındaki DATABASE_URL bilgilerini kontrol edin
- **Modül bulunamadı hataları**: requirements.txt dosyasının doğru şekilde yüklendiğinden emin olun

## Önemli Notlar

- Natro hosting'de PHP+Python birlikte çalışabilir
- .htaccess dosyasındaki yönlendirmeler, PHP ve Python uygulamalarının birlikte çalışmasını sağlar
- Uygulamanın güvenlik ayarları için env.example dosyasındaki tüm parametreleri dikkatle gözden geçirin

## Yardım ve Destek

Natro destek ekibi, Python uygulamanızın kurulumunda size yardımcı olabilir. Sorun yaşarsanız destek biletleri açarak yardım isteyebilirsiniz.

## Klasör Boyutunu Azaltma (25MB Sınırı İçin)

Eğer Natro hosting'in 25MB yükleme sınırına uymak istiyorsanız, aşağıdaki adımları izleyebilirsiniz:

1. `wkhtmltox-installer.exe` dosyasını silin (27MB): Bu dosya sadece PDF dönüştürme için kullanılan bir araç ve sunucuda gerekli değildir.

2. `.venv` klasörünü yüklemeyin: Virtual environment klasörünü hariç tutun. Sunucuda gereken paketleri `requirements.txt` ile yükleyebilirsiniz.

3. `__pycache__` klasörlerini temizleyin: Bu derleme dosyaları gereksizdir ve sunucuda otomatik oluşturulacaktır.

4. `logs` klasörünü silin: Sunucu yüklemeden önce log dosyalarını temizleyin, sunucuda otomatik oluşturulacaktır.

5. `instance` klasöründeki SQLite veritabanlarını temizleyin: Eğer MySQL kullanacaksanız, SQLite veritabanlarını silmek boyutu azaltacaktır.

6. Gereksiz geliştirme dosyalarını çıkarın: `.git`, `.gitignore`, `.idea`, `.vscode` gibi klasörleri ve dosyaları silebilirsiniz.

Yukarıdaki adımları uyguladıktan sonra, yükleme boyutunuz 25MB sınırının altına düşecektir. 