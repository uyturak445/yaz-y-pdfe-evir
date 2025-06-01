from app import app, db

if __name__ == "__main__":
    with app.app_context():
        print("Veritabanı tabloları siliniyor...")
        db.drop_all()
        print("Veritabanı tabloları yeniden oluşturuluyor...")
        db.create_all()
        print("Veritabanı başarıyla sıfırlandı!") 