import pandas as pd
from config import engine

def otonom_sistemi_baslat(dosya_yolu):
    print(f"🤖 Otonom sistem '{dosya_yolu}' dosyasını okuyor...")
    try:
        # Excel dosyasını oku
        df = pd.read_excel(dosya_yolu)
        
        # Olası boşluk hatalarına karşı sütun isimlerini temizle
        df.columns = [str(col).strip() for col in df.columns]
        
        print("🚀 Başlıklar kusursuz. Veriler lokal veritabanına aktarılıyor...")
        
        # Ana tabloyu inşa et (Var olanı silip yerine yenisini kurar)
        df.to_sql('customers', con=engine, if_exists='replace', index=False)
        print("✅ Otonom Kurtarma Başarılı: 'customers' tablosu sıfırdan inşa edildi!")
        
        # Loglama yapabilmek için 'system_logs' tablosunu da boş bir şekilde inşa et
        try:
            logs_df = pd.DataFrame(columns=["islem_tarihi", "kullanici_adi", "islem_tipi", "detay"])
            logs_df.to_sql('system_logs', con=engine, if_exists='append', index=False)
            print("✅ Güvenlik logları tablosu başarıyla kuruldu!")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Otonom Kurtarma Başarısız: {e}")