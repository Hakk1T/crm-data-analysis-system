import pandas as pd

# Sistemin beklediği tüm kritik sütunlar ve örnek başlangıç verileri
data = {
    "Müşteri No": [1001, 1002],
    "İşlem Tarihi": ["2026-08-03", "2026-08-03"],
    "Müşteri Ad Soyad": ["Ahmet Yılmaz", "Ayşe Demir"],
    "Telefon": ["0532 111 22 33", "0555 444 55 66"],
    "Şehir": ["İSTANBUL", "ANKARA"],
    "Meslek": ["Mühendis", "Öğretmen"],
    "Doğum Tarihi": ["1985-05-12", "1990-11-24"],
    "Ulaşım Kanalı": ["Web Sitesi", "Showroom Ziyareti"],
    "Araç Modeli": ["BYD Atto 3", "-"],
    "Model Yılı": [2023, None],
    "Kilometre": [15000, 0],
    "İlgilendiği Araç": ["BYD Seal U DM-i", "BYD Dolphin"],
    "Satış Tarafından Arandı Mı": ["Evet", "Hayır"],
    "Kapanış Nedeni": ["Kararsız", "-"],
    "Görüşme Notları": ["03.08.2026 11:30 | Sistem Yöneticisi | İlk görüşme yapıldı.", ""], # <-- HATA BURADAYDI, DÜZELTİLDİ
    "Test Surusu Durumu": ["Yapıldı", "-"],
    "Hatırlatma Tarihi": [None, None],
    "İşlem Yapan": ["Sistem Yöneticisi", "Satış Danışmanı"]
}

df = pd.DataFrame(data)

# Klasöre Excel dosyası olarak kaydediyoruz
df.to_excel("saf_musteri_verisi.xlsx", index=False)
print("✅ saf_musteri_verisi.xlsx dosyası başarıyla oluşturuldu!")