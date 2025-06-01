from app import app, db
from dotenv import load_dotenv
import os

# .env dosyasından çevresel değişkenleri yükle
load_dotenv()

def setup_database():
    """
    Veritabanı tablolarını oluşturur. Bu script ilk kurulumda veya
    veritabanı değişikliklerinde çalıştırılabilir.
    
    Kullanım:
    python setup_db.py
    """
    print("Veritabanı tablolarını oluşturma işlemi başlatılıyor...")
    with app.app_context():
        db.create_all()
        print("Veritabanı tabloları başarıyla oluşturuldu!")

if __name__ == "__main__":
    setup_database() 