import sys
import os

# Python yolunu ayarla (ihtiyaca göre değiştirilebilir)
PYTHON_PATH = '/usr/local/bin/python3.9'
if os.path.exists(PYTHON_PATH):
    sys.path.insert(0, PYTHON_PATH)

# Virtualenv yolunu ekle (varsa)
VENV_PATH = os.path.join(os.getcwd(), 'venv/lib/python3.9/site-packages')
if os.path.exists(VENV_PATH):
    sys.path.insert(0, VENV_PATH)

# Proje dizinini ekle
sys.path.insert(0, os.getcwd())

# Uygulama nesnesini içe aktarın
from app import app as application 