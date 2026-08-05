# CRM & Data Analysis Dashboard | CRM Veri Analiz Sistem

🌍 *Choose Language / Dil Seçimi:*
* [🇬🇧 English](#-english-version)
* [🇹🇷 Türkçe](#-türkçe-sürüm)

---

## 🇬🇧 English Version

A professional Customer Relationship Management (CRM) and data analysis system developed for automotive sales teams, enabling data-driven decision-making. Equipped with an "Autonomous Recovery Engine" that can automatically rebuild its SQL tables from offline backups if the database connection is lost.

### 📸 Project Screenshots

**1. Admin Panel & Analysis Dashboard**
<img width="1920" height="1440" alt="1" src="https://github.com/user-attachments/assets/bc0ce296-df6e-45a5-a2be-3194fd17419c" />


**2. Transaction History & Customer Table**
<img width="1920" height="1440" alt="3" src="https://github.com/user-attachments/assets/517e6479-3e68-4673-8343-9b6769f75670" />


**3. Customer Location & Charging Network Map**
<img width="1920" height="1440" alt="6" src="https://github.com/user-attachments/assets/d622c125-def3-4501-adf9-f6802f253ae2" />


### 🚀 Key Features

*   **🤖 Autonomous Recovery Engine:** If the database connection drops or fails, the system reads the `saf_musteri_verisi.xlsx` offline template and safely rebuilds all required SQL tables from scratch.
*   **📊 Dynamic Data Analysis:** Real-time charts, vehicle model analysis, and sales performance tracking utilizing Pandas and Plotly Dash.
*   **🔒 Enterprise Security:** Role-based authorization (Admin/Sales), secure session management (Secure Cookies), XSS protection, and Rate Limiting for defensive architecture.
*   **🌍 Live API Integration:** Maps customer locations and live electric charging stations across the country using the Overpass API.
*   **🔔 Smart Reminders:** A built-in notification engine that tracks customer meeting notes and alerts the staff for upcoming appointments.

### 💻 Tech Stack

*   **Backend:** Python, Flask, Dash
*   **Database:** PostgreSQL (Neon.tech), SQLAlchemy, SQLite
*   **Data Analysis:** Pandas, NumPy
*   **Frontend:** Dash Bootstrap Components, FontAwesome
*   **Mapping:** Leaflet, Plotly Maps, Overpass API

### ⚙️ Installation

**1. Clone the Repository:**
    git clone https://github.com/USERNAME/repository-name.git
    cd repository-name

**2. Install Dependencies:**
    pip install -r requirements.txt

**3. Set Environment Variables:**
    Create a `.env` file in the root directory and add your database connection:
    DATABASE_URL=postgresql://user:password@host/database
    FLASK_SECRET_KEY=your-super-secret-key

**4. Run the Application:**
    python app_web.py

---

## 🇹🇷 Türkçe Sürüm

Otomotiv satış ekipleri için geliştirilmiş, veriye dayalı karar almayı sağlayan profesyonel bir Müşteri İlişkileri Yönetimi (CRM) ve Analiz sistemidir. Veritabanı bağlantısı koptuğunda dahi çevrimdışı yedeklerinden kendini otomatik inşa edebilen "Otonom Kurtarma Motoru" ile donatılmıştır.

### 📸 Projeden Görüntüler

**1. Yönetici Paneli ve Analiz Kokpiti**
<img width="1920" height="1440" alt="1" src="https://github.com/user-attachments/assets/17f6ffdc-32e6-46f0-8247-1090318dd4f6" />


**2. İşlem Geçmişi ve Müşteri Tablosu**
<img width="1920" height="1440" alt="3" src="https://github.com/user-attachments/assets/98051dcf-82af-4a54-a1a4-f49bcfb0d5a9" />


**3. Müşteri Lokasyon ve Şarj Ağı Haritası**
<img width="1920" height="1440" alt="6" src="https://github.com/user-attachments/assets/93382f34-8e51-4100-8177-00695fda309f" />


### 🚀 Öne Çıkan Özellikler

*   **🤖 Otonom Kurtarma Motoru:** Veritabanı bağlantısı bulunamadığında veya hata oluştuğunda, sistem `saf_musteri_verisi.xlsx` dosyasını okuyarak kendi SQL tablolarını sıfırdan ve hatasız inşa eder.
*   **📊 Dinamik Veri Analizi:** Pandas ve Plotly Dash kullanarak gerçek zamanlı grafikler, araç model analizleri ve satış performans takibi.
*   **🔒 Kurumsal Güvenlik:** Rol bazlı yetkilendirme (Admin/Sales), şifrelenmiş oturum yönetimi (Secure Cookies), XSS koruması ve Rate Limiting ile saldırılara karşı dayanıklı mimari.
*   **🌍 Canlı API Entegrasyonu:** Overpass API kullanarak Türkiye genelindeki müşterilerin konumlarını ve elektrikli şarj istasyonlarını harita üzerinde eşleştirme.
*   **🔔 Akıllı Hatırlatıcı:** Müşteri görüşme notlarını takip eden ve yaklaşan görüşmeleri uyaran bildirim motoru.

### 💻 Teknolojiler

*   **Backend:** Python, Flask, Dash
*   **Veritabanı:** PostgreSQL (Neon.tech), SQLAlchemy, SQLite
*   **Veri Analizi:** Pandas, NumPy
*   **Frontend:** Dash Bootstrap Components, FontAwesome
*   **Harita:** Leaflet, Plotly Maps, Overpass API

### ⚙️ Kurulum

**1. Repoyu Klonlayın:**
    git clone https://github.com/KULLANICI_ADINIZ/proje-adi.git
    cd proje-adi

**2. Kütüphaneleri Kurun:**
    pip install -r requirements.txt

**3. Çevre Değişkenlerini Ayarlayın:**
    Ana dizinde `.env` isimli bir dosya oluşturun ve veritabanı bağlantınızı ekleyin:
    DATABASE_URL=postgresql://kullanici:sifre@sunucu/veritabani
    FLASK_SECRET_KEY=cok-gizli-bir-anahtar

**4. Sistemi Başlatın:**
    python app_web.py

---
*Geliştirici / Developer: Hakkı Tuçtan*
