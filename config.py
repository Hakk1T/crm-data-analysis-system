"""
SİSTEM KONFİGÜRASYON VE AYAR DOSYASI
------------------------------------
Veritabanı bağlantıları, renk temaları ve sabit değişkenlerin tutulduğu dosya.
Güvenlik nedeniyle veritabanı şifreleri burada değil, .env dosyasında saklanmalıdır.
"""

import os
import pandas as pd
import re
from sqlalchemy import create_engine

# --- VERİTABANI BAĞLANTISI ---
# GÜVENLİK: Bağlantı dizesi sadece .env dosyasından okunur. Kodun içine asla şifre yazılmaz.
# Eğer kişi projeyi indirip .env dosyası oluşturmamışsa, sistemin çökmemesi için 
# otomatik olarak bulunduğu klasöre "lokal_veritabani.db" adında çevrimdışı (SQLite) bir dosya oluşturur.
DB_URI = os.environ.get("DATABASE_URL", "sqlite:///lokal_veritabani.db")

engine = create_engine(DB_URI, pool_pre_ping=True, pool_recycle=300)

# --- KULLANICI BİLGİLERİ (Açık Kaynak Şablonu) ---
# GitHub'dan projeyi indirenlerin sistemi test edebilmesi için oluşturulmuş örnek kullanıcılar.
# Güvenlik amacıyla şifreler "Scrypt" ile hash'lenmiştir. (Örnek şifrelerin aslı: "123456")
USERS_DB = {
    "yonetici@firma.com": {
        "password": "scrypt:32768:8:1$MJcv7A8aUl4xkrUM$f40df49e53c89bfc1a22de187d52b75d1545830f321eff78d9707de8ed32548d562181e4ba035704018f7d5e89cfaa68de1ddae491c391afb578694e2c1c9b11", 
        "role": "admin", 
        "name": "Sistem Yöneticisi"
    },
    "satis@firma.com": {
        "password": "scrypt:32768:8:1$MJcv7A8aUl4xkrUM$f40df49e53c89bfc1a22de187d52b75d1545830f321eff78d9707de8ed32548d562181e4ba035704018f7d5e89cfaa68de1ddae491c391afb578694e2c1c9b11", 
        "role": "sales", 
        "name": "Satış Danışmanı"
    }
}

GUNLUK_HEDEF = 35

# --- RENKLER VE TEMA ---
# Projenin kurumsal görünümünü sağlayan renk paleti (Proje genelinde BYD olarak isimlendirilmiştir)
BYD_RED = "#E91B21"
BYD_SHARK_GREY = "#252728"
BYD_OCEAN_BLUE = "#185DF5"
BYD_WHITE = "#FFFFFF"
BYD_LIGHT_BG = "#F4F5F7"
BYD_SHARK_DARK = "#1A1A1A"
BYD_WARNING_ORANGE = "#FD7E14"

# --- STİLLER ---
SIDEBAR_STYLE = {"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "300px", "padding": "30px 15px", "zIndex": 1000}
CONTENT_STYLE = {"margin-left": "300px", "padding": "35px", "min-height": "100vh"}

# --- TELEFON FORMATLAMA ---
def format_phone(phone_raw):
    if pd.isna(phone_raw) or phone_raw is None or str(phone_raw).strip() == "":
        return "-"
    digits = re.sub(r'\D', '', str(phone_raw))
    if len(digits) == 12 and digits.startswith("90"):
        digits = "0" + digits[2:]
    elif len(digits) == 10:
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("0"):
        return f"{digits[0]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"
    return str(phone_raw)

# --- VERİ ÇEKME FONKSİYONU ---
def get_db_data():
    try:
        # Bağlantıyı güvenli bir şekilde açıp, okuma bitince otomatik kapatıyoruz
        with engine.connect() as conn:
            df = pd.read_sql_table("customers", con=conn)
            return df
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        return pd.DataFrame() # Hata anında uygulamanın çökmemesi için boş tablo döner