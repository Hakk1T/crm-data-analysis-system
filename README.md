# 🚗 CRM & Data Analysis Dashboard | CRM ve Veri Analiz Kokpiti

🌍 *Choose Language / Dil Seçimi:*
* [🇬🇧 English](#-english-version)
* [🇹🇷 Türkçe](#-türkçe-sürüm)

---

## 🇬🇧 English Version

A professional Customer Relationship Management (CRM) and data analysis system developed for automotive sales teams, enabling data-driven decision-making. Equipped with an "Autonomous Recovery Engine" that can automatically rebuild its SQL tables from offline backups if the database connection is lost.

### 📸 Project Screenshots

*(Ensure your images are uploaded to the `images/` folder)*

**1. Admin Panel & Analysis Dashboard**
<img width="1920" height="1440" alt="1" src="https://github.com/user-attachments/assets/b6c9c2ec-fb83-4278-a776-007c02225a46" />


**2. Transaction History & Customer Table**
<img width="1920" height="1440" alt="3" src="https://github.com/user-attachments/assets/234c2194-96ae-4490-aca0-b7c5c1ba7e17" />


**3. Customer Location & Charging Network Map**
<img width="1920" height="1440" alt="6" src="https://github.com/user-attachments/assets/6eaf3c46-eea1-4ba6-8f1c-ee5a6e50f6f2" />


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
```bash
git clone https://github.com/USERNAME/repository-name.git
cd repository-name
2. Install Dependencies:

Bash
pip install -r requirements.txt
3. Set Environment Variables:
Create a .env file in the root directory and add your database connection:

Plaintext
DATABASE_URL=postgresql://user:password@host/database
FLASK_SECRET_KEY=your-super-secret-key
(If the .env file is not created, the system will automatically default to a local SQLite database for quick testing.)

4. Run the Application:

Bash
python app_web.py
🇹🇷 Türkçe Sürüm
Otomotiv satış ekipleri için geliştirilmiş, veriye dayalı karar almayı sağlayan profesyonel bir Müşteri İlişkileri Yönetimi (CRM) ve Analiz sistemidir. Veritabanı bağlantısı koptuğunda dahi çevrimdışı yedeklerinden kendini otomatik inşa edebilen "Otonom Kurtarma Motoru" ile donatılmıştır.

📸 Projeden Görüntüler
(Görsellerin images/ klasörüne yüklendiğinden emin olun)

1. Yönetici Paneli ve Analiz Kokpiti

2. İşlem Geçmişi ve Müşteri Tablosu

3. Müşteri Lokasyon ve Şarj Ağı Haritası

🚀 Öne Çıkan Özellikler
🤖 Otonom Kurtarma Motoru: Veritabanı bağlantısı bulunamadığında veya hata oluştuğunda, sistem saf_musteri_verisi.xlsx dosyasını okuyarak kendi SQL tablolarını sıfırdan ve hatasız inşa eder.

📊 Dinamik Veri Analizi: Pandas ve Plotly Dash kullanarak gerçek zamanlı grafikler, araç model analizleri ve satış performans takibi.

🔒 Kurumsal Güvenlik: Rol bazlı yetkilendirme (Admin/Sales), şifrelenmiş oturum yönetimi (Secure Cookies), XSS koruması ve Rate Limiting ile saldırılara karşı dayanıklı mimari.

🌍 Canlı API Entegrasyonu: Overpass API kullanarak Türkiye genelindeki müşterilerin konumlarını ve elektrikli şarj istasyonlarını harita üzerinde eşleştirme.

🔔 Akıllı Hatırlatıcı: Müşteri görüşme notlarını takip eden ve yaklaşan görüşmeleri uyaran bildirim motoru.

💻 Teknolojiler
Backend: Python, Flask, Dash

Veritabanı: PostgreSQL (Neon.tech), SQLAlchemy, SQLite

Veri Analizi: Pandas, NumPy

Frontend: Dash Bootstrap Components, FontAwesome

Harita: Leaflet, Plotly Maps, Overpass API

⚙️ Kurulum
1. Repoyu Klonlayın:

Bash
git clone https://github.com/KULLANICI_ADINIZ/proje-adi.git
cd proje-adi
2. Kütüphaneleri Kurun:

Bash
pip install -r requirements.txt
3. Çevre Değişkenlerini Ayarlayın:
Ana dizinde .env isimli bir dosya oluşturun ve veritabanı bağlantınızı ekleyin:

Plaintext
DATABASE_URL=postgresql://kullanici:sifre@sunucu/veritabani
FLASK_SECRET_KEY=cok-gizli-bir-anahtar
(Eğer .env oluşturmazsanız sistem otomatik olarak yerel bir SQLite veritabanı ile çalışacaktır.)

4. Sistemi Başlatın:

Bash
python app_web.py
Geliştirici / Developer: Hakkı Tuçtan
