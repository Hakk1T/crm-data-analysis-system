"""
AÇIK KAYNAK CRM VE VERİ ANALİZ SİSTEMİ (Open Source CRM Dashboard)
-------------------------------------------------------------------
Bu uygulama, otomotiv ve satış sektörleri için geliştirilmiş, veritabanı 
bağlantısı koptuğunda dahi çevrimdışı excel verileriyle kendi tablolarını 
otomatik inşa edebilen (otonom motor) rol bazlı bir CRM sistemidir.

Özellikler:
- Pandas ve Plotly ile dinamik veri analizi
- Overpass API ile harita entegrasyonu (Müşteri ve Şarj İstasyonu analizi)
- Rol bazlı yetkilendirme (Admin / Satış Personeli)
- Akıllı hatırlatıcı sistemi
"""

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime
from sqlalchemy import text
import plotly.graph_objects as go
import requests
from functools import lru_cache
import os
import time
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from werkzeug.security import check_password_hash 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from flask import session
from dotenv import load_dotenv

# --- SİSTEM KONFİGÜRASYONLARI ---
from config import *
from pages.performance import get_performance_layout
from otonom import otonom_sistemi_baslat  

load_dotenv()

LOGIN_ATTEMPTS = {}  
MAX_ATTEMPTS = 5     
LOCKOUT_TIME = 180   

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)
app.title = "CRM ve Veri Analiz Kokpiti"

limiter = Limiter(get_remote_address, app=app.server, storage_uri="memory://")
app.server.secret_key = os.getenv("FLASK_SECRET_KEY")

app.server.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # JavaScript çereze erişemez (XSS'i engeller)
    SESSION_COOKIE_SAMESITE='Lax', # Dış sitelerden gelen sahte istekleri engeller (CSRF'i engeller)
    SESSION_COOKIE_SECURE=True     # Çerezin sadece güvenli (HTTPS) bağlantılarda çalışmasını sağlar
)
app.server.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

login_manager = LoginManager()
login_manager.init_app(app.server)
login_manager.session_protection = "strong"

class User(UserMixin):
    def __init__(self, id, name, role):
        self.id = id
        self.name = name
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user_record = USERS_DB.get(user_id)
    if user_record:
        return User(id=user_id, name=user_record.get("name"), role=user_record.get("role"))
    return None

app.config.suppress_callback_exceptions = True

# --- VERİ ÇEKME & OTONOM MOTOR ---
def get_db_data():
    try:
        df = pd.read_sql('SELECT * FROM customers', con=engine)
        zorunlu_sutunlar = ["Müşteri No", "Müşteri Ad Soyad", "Telefon", "Kapanış Nedeni"]
        eksik_sutunlar = [kolon for kolon in zorunlu_sutunlar if kolon not in df.columns]
        
        if eksik_sutunlar or df.empty:
            raise ValueError("Dış veri kaynağı yapısı bozuk veya uyumsuz.")
        return df

    except Exception as e:
        print(f"🚨 KRİTİK UYARI: {e}")
        print("Otonom kurtarma motoru tetikleniyor...")
        ham_dosya = "saf_musteri_verisi.xlsx" 
        if os.path.exists(ham_dosya):
            otonom_sistemi_baslat(ham_dosya) 
            return pd.read_sql('SELECT * FROM customers', con=engine)
        else:
            return pd.DataFrame()

# --- AKILLI ŞARJ İSTASYONU HAFIZASI ---
_cached_sarj_df = None
_last_sarj_fetch_time = 0

def internetten_canli_sarj_istasyonlarini_cek():
    global _cached_sarj_df, _last_sarj_fetch_time
    now = time.time()
    
    # Eğer son 1 saat içinde veri başarıyla çekildiyse, hafızadakini kullan (sistemi yorma)
    if _cached_sarj_df is not None and not _cached_sarj_df.empty and (now - _last_sarj_fetch_time < 3600):
        return _cached_sarj_df

    try:
        print("⚡ Şarj istasyonları harita için internetten çekiliyor (Bu işlem birkaç saniye sürebilir)...")
        # Alternatif ve daha stabil olan ana Overpass sunucusuna geçildi
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = """[out:json][timeout:25];node["amenity"="charging_station"](35.8, 25.6, 42.1, 44.8);out;"""
        # API kurallarına uygun anonim User-Agent
        headers = {'User-Agent': 'OpenSource_CRM_Dashboard/1.0'}
        response = requests.post(overpass_url, data={'data': overpass_query}, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            lats, lons, names = [], [], []
            for element in data.get('elements', []):
                lats.append(element['lat'])
                lons.append(element['lon'])
                tags = element.get('tags', {})
                isim = tags.get('operator', tags.get('brand', tags.get('name', 'Bilinmeyen Şarj İstasyonu'))).upper()
                names.append(isim)
            
            df = pd.DataFrame({'Lat': lats, 'Lon': lons, 'İstasyon': names})
            
            # Eğer veri başarıyla geldiyse, hafızaya al ki sürekli interneti meşgul etmesin
            if not df.empty:
                _cached_sarj_df = df
                _last_sarj_fetch_time = now
                print(f"✅ BAŞARILI: Türkiye genelinde {len(df)} adet şarj istasyonu bulundu ve haritaya işlendi.")
            return df
        else:
            print(f"❌ Overpass API Hatası: Sunucu {response.status_code} kodu döndürdü. Daha sonra tekrar denenecek.")
            return _cached_sarj_df if _cached_sarj_df is not None else pd.DataFrame(columns=['Lat', 'Lon', 'İstasyon'])
            
    except Exception as e: 
        print(f"❌ Şarj İstasyonu Çekme Hatası: {e}")
        return _cached_sarj_df if _cached_sarj_df is not None else pd.DataFrame(columns=['Lat', 'Lon', 'İstasyon'])

def log_kaydi_ekle(kullanici, islem_tipi, detay):
    try:
        with engine.begin() as conn:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(text('''INSERT INTO system_logs (islem_tarihi, kullanici_adi, islem_tipi, detay) VALUES (:ts, :usr, :tip, :detay)'''), {"ts": ts, "usr": kullanici, "tip": islem_tipi, "detay": detay})
    except Exception as e: 
        print(f"Log Yazma Hatası: {e}")

def generate_individual_bar(staff_name, df):
    today_str = datetime.now().strftime('%Y-%m-%d')
    if "İşlem Tarihi" in df.columns and "İşlem Yapan" in df.columns:
        count = len(df[(df['İşlem Yapan'].astype(str).str.strip() == staff_name) & (df['İşlem Tarihi'] == today_str)])
    else: count = 0
    progress = min(int((count / GUNLUK_HEDEF) * 100), 100)
    
    return html.Div([
        html.Div([html.Strong(staff_name, style={"color": BYD_SHARK_DARK, "fontWeight": "600"}), html.Span(f"{count} / {GUNLUK_HEDEF}", style={"float": "right", "fontWeight": "bold", "color": BYD_SHARK_GREY})], style={"marginBottom": "8px"}),
        dbc.Progress(value=progress, label=f"{count} / {GUNLUK_HEDEF}", color="success" if count >= GUNLUK_HEDEF else "info", style={"height": "24px", "fontSize": "13px", "fontWeight": "bold", "marginBottom": "25px",  "backgroundColor": "rgba(0,0,0,0.05)"})
    ])

# --- ARAYÜZ (LAYOUT) ---
login_layout = html.Div([
    html.Div([
        html.Div([
            html.H1("CRM KOKPİT", style={"color": BYD_RED, "fontFamily": "Segoe UI Black", "fontSize": "45px", "margin": "0", "lineHeight": "1", "letterSpacing": "2px"}),
            html.P("ANALİZ VE YÖNETİM SİSTEMİ", style={"color": "#666", "fontSize": "12px", "letterSpacing": "1px", "marginBottom": "40px"}),
        ], style={"textAlign": "center"}),
        html.Div([
            html.Label("E-posta", style={"color": BYD_SHARK_GREY, "fontWeight": "600", "fontSize": "13px", "marginBottom": "8px"}),
            dcc.Input(id="username-input", type="text", placeholder="Örn: ornek@firma.com", style={"width": "100%", "height": "50px", "padding": "0 15px",  "border": "1px solid rgba(0,0,0,0.1)", "backgroundColor": "rgba(255,255,255,0.6)", "color": BYD_SHARK_DARK, "marginBottom": "20px"}),
            html.Label("Erişim Şifresi", style={"color": BYD_SHARK_GREY, "fontWeight": "600", "fontSize": "13px", "marginBottom": "8px"}),
            dcc.Input(id="password-input", type="password", placeholder="Şifrenizi girin...", style={"width": "100%", "height": "50px", "padding": "0 15px",  "border": "1px solid rgba(0,0,0,0.1)", "backgroundColor": "rgba(255,255,255,0.6)", "color": BYD_SHARK_DARK, "marginBottom": "30px"}),
            dbc.Button("GİRİŞ YAP", id="login-btn", color="danger", className="w-100 glass-btn-red", style={"border": "none", "height": "50px", "fontSize": "15px", "fontWeight": "bold",  "letterSpacing": "1px"})
        ]),
        html.Div(id="login-error", style={"color": BYD_RED, "textAlign": "center", "marginTop": "20px", "fontWeight": "bold", "height": "20px", "fontSize": "14px"})
    ], className="glass-panel", style={"width": "460px", "padding": "50px"})
], id="login-wrapper", className="login-wrapper-bg", style={"display": "flex", "justifyContent": "center", "alignItems": "center", "height": "100vh", "width": "100vw", "position": "fixed", "top": 0, "left": 0, "zIndex": 9999})

action_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Müşteri Paneli", style={"fontWeight": "bold", "color": BYD_SHARK_DARK}), style={"borderBottom": "1px solid rgba(0,0,0,0.05)"}),
    dbc.ModalBody([
        html.Div(id="modal-customer-info", style={"marginBottom": "20px", "padding": "15px", "backgroundColor": "rgba(0,0,0,0.02)", "border": "1px solid rgba(0,0,0,0.08)"}),
        html.Label("Arama Sonucu / Müşteri Durumu:", style={"fontWeight": "600", "color": BYD_SHARK_GREY, "fontSize": "13px", "marginBottom": "8px"}),
        dbc.Select(id="modal-action-status", options=[{"label": "Görüşüldü - Olumlu (Randevu/Satış)", "value": "Olumlu"}, {"label": "Görüşüldü - Kararsız (Düşünecek)", "value": "Kararsız"}, {"label": "Görüşüldü - İlgilenmiyor (Reddedildi)", "value": "İlgilenmiyor"}, {"label": "Ulaşılamadı - Tekrar Aranacak", "value": "Ulaşılamadı"}, {"label": "Test Sürüşü Randevusu", "value": "Test Randevusu"}], placeholder="Müşteri durumunu belirleyiniz...", style={"marginBottom": "20px",  "border": "1px solid #CCC", "height": "40px"}),
        html.Label("Sonraki Arama / Hatırlatma Tarihi:", style={"fontWeight": "600", "color": BYD_WARNING_ORANGE, "fontSize": "13px", "marginBottom": "8px"}),
        dbc.Input(id="modal-reminder-date", type="datetime-local", style={"marginBottom": "20px",  "border": "1px solid #CCC", "height": "40px"}),
        html.Label("Geçmiş Görüşme Kayıtları:", style={"fontWeight": "600", "fontSize": "13px", "color": BYD_RED}),
        html.Div(id="modal-notes-display", style={"marginTop": "5px", "marginBottom": "20px", "maxHeight": "200px", "overflowY": "auto", "backgroundColor": "#f8f9fa", "padding": "10px",  "border": "1px solid #CCC"}),
        html.Label("Yeni Görüşme Notu Ekle:", style={"fontWeight": "600", "color": BYD_SHARK_DARK, "fontSize": "13px", "marginBottom": "8px"}),
        dbc.Textarea(id="modal-notes", placeholder="Müşteri ile yapılan görüşmenin detaylarını buraya giriniz...", style={"height": "90px",  "border": "1px solid #CCC"})
    ]),
    dbc.ModalFooter([dcc.Store(id="modal-customer-id"), dbc.Button("İptal", id="modal-cancel-btn", color="secondary", className="me-2", style={"fontWeight": "500"}), dbc.Button("Sisteme Kaydet", id="modal-save-btn", color="danger", style={"backgroundColor": BYD_RED,  "fontWeight": "bold"})], style={"borderTop": "1px solid rgba(0,0,0,0.05)"})
], id="action-modal", is_open=False, centered=True, backdrop="static", contentClassName="glass-modal")

admin_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Yönetici Kontrol Paneli", style={"fontWeight": "bold", "color": BYD_SHARK_DARK}), style={"borderBottom": "1px solid rgba(0,0,0,0.05)"}),
    dbc.ModalBody([
        html.Div(id="admin-customer-info", style={"marginBottom": "20px", "padding": "15px", "backgroundColor": "rgba(0,0,0,0.02)", "border": "1px solid rgba(0,0,0,0.08)"}),
        html.Label("Müşteri Ad Soyad:", style={"fontWeight": "600", "fontSize": "13px"}), dcc.Input(id="admin-edit-name", type="text", style={"width": "100%", "marginBottom": "15px", "padding": "10px",  "border": "1px solid #CCC"}),
        html.Label("Telefon Numarası:", style={"fontWeight": "600", "fontSize": "13px"}), dcc.Input(id="admin-edit-phone", type="text", style={"width": "100%", "marginBottom": "15px", "padding": "10px",  "border": "1px solid #CCC"}),
        html.Label("Kapanış Nedeni (Durum):", style={"fontWeight": "600", "fontSize": "13px"}), dcc.Input(id="admin-edit-status", type="text", style={"width": "100%", "marginBottom": "15px", "padding": "10px",  "border": "1px solid #CCC"}),
        html.Label("Geçmiş Görüşme Kayıtları:", style={"fontWeight": "600", "fontSize": "13px", "color": BYD_RED}), html.Div(id="admin-notes-display", style={"marginTop": "5px", "marginBottom": "15px", "maxHeight": "150px", "overflowY": "auto", "backgroundColor": "#f8f9fa", "padding": "10px",  "border": "1px solid #CCC"}),
        html.Label("Yönetici Yeni Not Ekle:", style={"fontWeight": "600", "fontSize": "13px", "color": BYD_SHARK_DARK}), dbc.Textarea(id="admin-new-notes", placeholder="Yönetici olarak yeni not ekleyin...", style={"height": "80px",  "border": "1px solid #CCC"})
    ]),
    dbc.ModalFooter([dcc.Store(id="admin-modal-id"), dbc.Button("İptal", id="admin-cancel-btn", color="secondary", className="me-2", style={"fontWeight": "500"}), dbc.Button("Değişiklikleri Uygula", id="admin-save-btn", color="dark", style={"backgroundColor": BYD_SHARK_DARK,  "fontWeight": "bold"})], style={"borderTop": "1px solid rgba(0,0,0,0.05)"})
], id="admin-modal", is_open=False, centered=True, backdrop="static", contentClassName="glass-modal")

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Download(id="download-excel"),
    dcc.Store(id='user-session', storage_type='session'), 
    dcc.Store(id='notified-reminders', data=[]),
    dcc.Store(id='raw-table-data', data=[]),
    dcc.Interval(id='reminder-interval', interval=20*1000, n_intervals=0),
    html.Div(id="db-refresh-trigger", children=0, style={"display": "none"}), 
    
    login_layout,
    action_modal,
    admin_modal,
    
    html.Div(id="sidebar-container", className="glass-sidebar", children=[
        html.Div([
            html.H1("CRM", style={"color": BYD_RED, "fontFamily": "Segoe UI Black", "fontSize": "56px", "margin": "0", "textAlign": "center", "letterSpacing": "1px"}),
            html.P(id="user-badge", style={"color": "rgba(255,255,255,0.7)", "fontSize": "12px", "fontWeight": "600", "textAlign": "center", "textTransform": "uppercase", "letterSpacing": "2px", "marginTop": "5px"})
        ], style={"marginBottom": "40px"}),
        html.Div("Sistem Anlık Güncel", style={"color": "rgba(255,255,255,0.9)", "fontSize": "12px", "textAlign": "center", "marginBottom": "25px", "fontWeight": "bold", "padding": "8px", "border": "1px solid rgba(255,255,255,0.2)",  "backgroundColor": "rgba(255,255,255,0.05)", "letterSpacing": "0.5px"}),
        html.Div(id="dynamic-nav-links", style={"maxHeight": "calc(100vh - 320px)", "overflowY": "auto", "overflowX": "hidden", "paddingRight": "5px"}),
        dbc.Button("Güvenli Çıkış", id="logout-btn", color="link", size="sm", style={"position": "absolute", "bottom": "30px", "left": "50%", "transform": "translateX(-50%)", "color": "rgba(255,255,255,0.5)", "textDecoration": "none", "fontWeight": "600", "letterSpacing": "1px"})
    ], style=SIDEBAR_STYLE),

    html.Div(id="page-content-wrapper", className="content-wrapper-bg", children=[
        html.Div([
            dbc.Button("☰", id="sidebar-toggle-btn", n_clicks=0, style={"backgroundColor": "rgba(255,255,255,0.7)", "border": "1px solid rgba(0,0,0,0.1)", "color": "#333", "fontSize": "22px",  "padding": "4px 15px", "marginRight": "15px", "boxShadow": "0 2px 8px rgba(0,0,0,0.05)", "cursor": "pointer"}),
            dcc.Loading(
                id="global-loader", type="dot", color="#E91B21", fullscreen=True,
                children=[html.H2(id="page-title", style={"fontWeight": "bold", "margin": "0", "color": BYD_SHARK_DARK, "letterSpacing": "-0.5px"})]
            )
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "90px"}),
        
        html.Div(id="unauthorized-view", children=[html.H3("Yetkisiz Erişim", style={"fontWeight":"bold", "color": BYD_RED})], style={"display": "none"}),
        html.Div(id="dashboard-view", children=[html.Div(id="gamification-container", className="mb-4"), dbc.Row(id="metric-row-1", className="mb-4"), dbc.Row(id="metric-row-2", className="mb-4"), html.Div(id="chart-container")], style={"display": "none"}),
        
        dbc.Toast(id="login-toast", header="Sistem Bildirimi", is_open=False, dismissable=True, duration=3500, icon="danger", style={"position": "fixed", "top": "30px", "right": "30px", "zIndex": 9999, "background": "rgba(255, 255, 255, 0.65)", "backdropFilter": "blur(16px)", "border": "1px solid rgba(255, 255, 255, 0.9)",  "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.1)", "minWidth": "300px", "fontFamily": "Segoe UI"}, header_style={"background": "transparent", "borderBottom": "1px solid rgba(0,0,0,0.08)", "fontWeight": "800", "color": "#252728"}),
        dbc.Toast(id="crm-toast", header="İşlem Başarılı", is_open=False, dismissable=True, duration=3500, icon="danger", style={"position": "fixed", "top": "30px", "right": "30px", "zIndex": 9999, "background": "rgba(255, 255, 255, 0.65)", "backdropFilter": "blur(16px)", "border": "1px solid rgba(255, 255, 255, 0.9)",  "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.1)", "minWidth": "300px", "fontFamily": "Segoe UI"}, header_style={"background": "transparent", "borderBottom": "1px solid rgba(0,0,0,0.08)", "fontWeight": "800", "color": "#252728"}),
        dbc.Toast(id="reminder-toast", header="Hatırlatıcı Zamanı!", is_open=False, dismissable=True, duration=15000, icon="warning", style={"position": "fixed", "bottom": "40px", "right": "30px", "zIndex": 9999, "background": "rgba(255, 255, 255, 0.9)", "backdropFilter": "blur(20px)", "border": "1px solid rgba(255, 152, 0, 0.4)", "borderLeft": "6px solid #ff9800", "boxShadow": "0 15px 40px rgba(0, 0, 0, 0.15)", "minWidth": "360px", "fontFamily": "Segoe UI"}, header_style={"background": "transparent", "borderBottom": "1px solid rgba(0,0,0,0.05)", "fontWeight": "900", "color": "#e65100"}),

        html.Div(id="table-view", children=[
            html.Div("Detayları okumak veya yeni not eklemek için listedeki ilgili satıra tıklayınız.", style={"backgroundColor": "rgba(255,255,255,0.6)", "backdropFilter": "blur(5px)", "padding": "15px",  "color": "#444", "fontWeight": "600", "marginBottom": "20px", "borderLeft": f"4px solid {BYD_SHARK_GREY}", "borderTop": "1px solid rgba(255,255,255,0.8)"}),
            html.Div([
                html.Div([
                    dbc.Button("Tabloyu İndir", id="btn-export-excel", color="success", style={"fontWeight": "bold", "marginRight": "15px",  "display": "none", "height": "50px", "padding": "0 25px", "boxShadow": "0 4px 10px rgba(25, 135, 84, 0.2)"}),
                    dcc.Input(id="global-search", type="text", placeholder="🔍 İsim, Soyisim veya Telefon Ara...", style={"width": "100%", "height": "50px", "padding": "0px 25px",  "border": "1px solid rgba(255,255,255,0.7)", "background": "rgba(255,255,255,0.6)", "backdropFilter": "blur(12px)", "boxShadow": "0 8px 20px rgba(0,0,0,0.06)", "fontSize": "16px", "outline": "none", "color": "#333", "fontWeight": "600"})
                ], style={"marginBottom": "20px", "display": "flex", "justifyContent": "flex-end", "alignItems": "center", "maxWidth": "700px", "marginLeft": "auto"}),
    
                dash_table.DataTable(
                    id='crm-table', page_size=12, sort_action="native", filter_action="native", style_filter={'display': 'none'},
                    style_as_list_view=True, 
                    style_table={'borderRadius': '10px', 'overflowX': 'auto', 'backgroundColor': 'transparent', 'minWidth': '100%'},
                    style_header={'backgroundColor': 'rgba(255,255,255,0.8)', 'fontWeight': 'bold', 'color': BYD_SHARK_DARK, 'padding': '14px', 'borderBottom': '2px solid rgba(0,0,0,0.1)', 'borderTop': 'none', 'textAlign': 'left'},
                    style_cell={'textAlign': 'left', 'padding': '14px', 'fontFamily': 'Segoe UI', 'fontSize': '14px', 'cursor': 'pointer', 'backgroundColor': 'transparent', 'borderBottom': '1px solid rgba(0,0,0,0.04)', 'color': '#333'},
                    style_cell_conditional=[{'if': {'column_id': 'Kapanış Nedeni'}, 'maxWidth': '200px'}, {'if': {'column_id': 'Görüşme Notları'}, 'maxWidth': '350px'}],
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255,255,255,0.3)'}, 
                        {'if': {'state': 'active'}, 'backgroundColor': 'rgba(233, 27, 33, 0.05)', 'border': f'1px solid {BYD_RED}'},
                        
                        # --- YUMUŞATILMIŞ GARANTİ SÜRESİ RENKLENDİRMELERİ ---
                        {
                            'if': {'filter_query': '{Kalan Süre} = "Süresi Doldu"', 'column_id': 'Kalan Süre'},
                            'color': '#d32f2f', 'fontWeight': 'bold', 'textShadow': '0px 0px 4px rgba(211, 47, 47, 0.25)'
                        },
                        {
                            'if': {'filter_query': '{Kalan Süre} = "Bu Yıl Bitiyor"', 'column_id': 'Kalan Süre'},
                            'color': '#ef6c00', 'fontWeight': 'bold', 'textShadow': '0px 0px 4px rgba(239, 108, 0, 0.25)'
                        },
                        {
                            'if': {'filter_query': '{Kalan Süre} contains "Yıl Kaldı"', 'column_id': 'Kalan Süre'},
                            'color': '#2e7d32', 'fontWeight': 'bold', 'textShadow': '0px 0px 4px rgba(46, 125, 50, 0.25)'
                        }
                    ],
                    css=[{'selector': '.dash-spreadsheet td div', 'rule': 'overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important;'}]
                )
            ], className="glass-panel")
        ], style={"display": "none"}),

        html.Div(id="dogum-gunleri-view", style={"display": "none"})
    ], style=CONTENT_STYLE)
])

# --- GİRİŞ / LOGİN CALLBACK ---
@limiter.limit("5 per minute")
@app.callback(
    [Output("login-wrapper", "style"), Output("user-session", "data"), Output("user-badge", "children"), Output("login-error", "children"), Output("login-toast", "is_open"), Output("login-toast", "children")], 
    [Input("login-btn", "n_clicks"), Input("logout-btn", "n_clicks"), Input("username-input", "n_submit"), Input("password-input", "n_submit")], 
    [State("username-input", "value"), State("password-input", "value")] 
)
def handle_login(login_clicks, logout_clicks, user_submit, pass_submit, username, password):
    ctx = dash.callback_context
    login_style = {"display": "flex", "justifyContent": "center", "alignItems": "center", "height": "100vh", "width": "100vw", "position": "fixed", "top": 0, "left": 0, "zIndex": 9999}
    
    if not ctx.triggered:
        if current_user.is_authenticated: return {"display": "none"}, {"name": current_user.name, "role": current_user.role}, f"Aktif: {current_user.name.upper()}", "", False, ""
        return login_style, None, "", "", False, ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "logout-btn":
        logout_user()
        return login_style, None, "", "", False, ""

    if button_id in ["login-btn", "username-input", "password-input"]:
        if not username or not password: return dash.no_update, dash.no_update, dash.no_update, html.Div("Bilgiler eksik!"), False, ""
        kullanici_mail = username.strip().lower()
        now = time.time()
        
        if kullanici_mail in LOGIN_ATTEMPTS:
            attempts, unlock_time = LOGIN_ATTEMPTS[kullanici_mail]
            if attempts >= MAX_ATTEMPTS and now < unlock_time:
                return dash.no_update, dash.no_update, dash.no_update, html.Div(f"Hesap kilitli: {int((unlock_time-now)//60)+1} dk bekleyin."), False, ""
        
        user_record = USERS_DB.get(kullanici_mail)
        if user_record and check_password_hash(user_record.get("password"), password):
            LOGIN_ATTEMPTS.pop(kullanici_mail, None)
            login_user(User(id=kullanici_mail, name=user_record.get("name"), role=user_record.get("role")))
            session.permanent = True
            return {"display": "none"}, {"name": user_record.get("name"), "role": user_record.get("role")}, f"Aktif: {user_record.get('name').upper()}", "", True, "Giriş başarılı!"
        else:
            LOGIN_ATTEMPTS[kullanici_mail] = [LOGIN_ATTEMPTS.get(kullanici_mail, [0,0])[0] + 1, now + LOCKOUT_TIME]
            hak = MAX_ATTEMPTS - LOGIN_ATTEMPTS[kullanici_mail][0]
            msg = "Hesap kilitlendi!" if hak <= 0 else f"Hatalı şifre! Kalan hak: {hak}"
            return dash.no_update, dash.no_update, dash.no_update, html.Div(msg), False, ""
    return dash.no_update, dash.no_update, dash.no_update, "", False, ""
    
@app.callback(Output("dynamic-nav-links", "children"), Input("user-session", "data"))
def render_nav(user_session):
    if not current_user.is_authenticated: return html.Div()
    role = current_user.role
    
    if role == 'admin':
        return dbc.Nav([
            dbc.NavLink([html.I(className="fa-solid fa-chart-pie me-2"), "Yönetim Paneli"], href="/", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-users-gear me-2"), "Ekip Performansı"], href="/ekip-performansi", active="exact"),  
            dbc.NavLink([html.I(className="fa-solid fa-list-check me-2"), "Kayıtlar"], href="/islem-gecmisi", active="exact"), 
            dbc.NavLink([html.I(className="fa-regular fa-bell me-2"), "Hatırlatıcılar"], href="/hatirlaticilar", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-right-left me-2"), "Takas Fırsatları"], href="/takas", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-shield-halved me-2"), "Garanti Süreleri"], href="/garanti", active="exact"),
            dbc.NavLink([html.I(className="fa-solid fa-user-clock me-2"), "İşlemsiz Kayıtlar"], href="/hayalet", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-key me-2"), "Test Sürüşü Takipleri"], href="/test", active="exact"),
            dbc.NavLink([html.I(className="fa-solid fa-trash-can me-2"), "Kalitesiz Veri Tespiti"], href="/cop", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-cake-candles me-2"), "Müşteri Doğum Günleri"], href="/dogum-gunleri", active="exact"),
            dbc.NavLink([html.I(className="fa-solid fa-server me-2"), "Sistem Logları (Güvenlik)"], href="/loglar", active="exact"), 
            dbc.NavLink([html.I(className="fa-solid fa-map-location-dot me-2"), "Müşteri Haritası"], href="/harita", active="exact")
        ], vertical=True, pills=True, style={"gap": "2px"}, className="glass-nav")
        
    return dbc.Nav([
        dbc.NavLink([html.I(className="fa-solid fa-chart-line me-2"), "Günlük Operasyon Paneli"], href="/", active="exact"), 
        dbc.NavLink([html.I(className="fa-solid fa-list-check me-2"), "İşlem Kayıtlarım"], href="/islem-gecmisi", active="exact"),
        dbc.NavLink([html.I(className="fa-regular fa-bell me-2"), "Hatırlatıcılar"], href="/hatirlaticilar", active="exact"), 
        dbc.NavLink([html.I(className="fa-solid fa-right-left me-2"), "Hedef Takas Listesi"], href="/takas", active="exact"),
        dbc.NavLink([html.I(className="fa-solid fa-shield-halved me-2"), "Garanti Uzatma Fırsatları"], href="/garanti", active="exact"), 
        dbc.NavLink([html.I(className="fa-solid fa-key me-2"), "Test Sürüşü Takipleri"], href="/test", active="exact"),
        dbc.NavLink([html.I(className="fa-solid fa-cake-candles me-2"), "Müşteri Doğum Günleri"], href="/dogum-gunleri", active="exact"), 
        dbc.NavLink([html.I(className="fa-solid fa-map-location-dot me-2"), "Müşteri Haritası"], href="/harita", active="exact")
    ], vertical=True, pills=True, style={"gap": "2px"}, className="glass-nav")

# --- MÜŞTERİ PANELİ VE KAYIT (HAYALET VERİ ÇÖZÜMÜ DAHİL) ---
@app.callback(
    [Output("action-modal", "is_open"), Output("admin-modal", "is_open"), Output("modal-notes-display", "children"), Output("modal-customer-info", "children"), Output("modal-customer-id", "data"), Output("admin-edit-name", "value"), Output("admin-edit-phone", "value"), Output("admin-edit-status", "value"), Output("admin-notes-display", "children"), Output("admin-new-notes", "value"), Output("admin-modal-id", "data"), Output("db-refresh-trigger", "children"), Output("crm-toast", "is_open"), Output("crm-toast", "children"), Output("admin-customer-info", "children"), Output("modal-action-status", "value"), Output("modal-reminder-date", "value"), Output("modal-notes", "value")],
    [Input("crm-table", "active_cell"), Input("modal-cancel-btn", "n_clicks"), Input("modal-save-btn", "n_clicks"), Input("admin-cancel-btn", "n_clicks"), Input("admin-save-btn", "n_clicks"), Input({"type": "del-note", "index": dash.ALL}, "n_clicks"), Input({"type": "dogum-gunu-btn", "index": dash.ALL}, "n_clicks")],
    [State("crm-table", "derived_viewport_data"), State("user-session", "data"), State("url", "pathname"), State("modal-customer-id", "data"), State("modal-action-status", "value"), State("modal-notes", "value"), State("modal-reminder-date", "value"), State("admin-modal-id", "data"), State("admin-edit-name", "value"), State("admin-edit-phone", "value"), State("admin-edit-status", "value"), State("admin-new-notes", "value"), State("db-refresh-trigger", "children")]
)
def handle_modals_and_db(active_cell, m_cancel, m_save, ad_cancel, ad_save, del_clicks, dogum_clicks, viewport_data, user, pathname, c_id, a_status, a_notes, a_rem_date, ad_id, ad_name, ad_phone, ad_status, ad_new_notes, refresh_val):
    if not user: return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update
    ctx = dash.callback_context
    if not ctx.triggered: return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    user_name = current_user.name
    is_admin = (current_user.role == 'admin')
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    triggered_id = ctx.triggered_id 

    if trigger_id in ["modal-cancel-btn", "admin-cancel-btn"]:
        return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, False, "", dash.no_update, None, None, ""

    if "modal-save-btn" in trigger_id and c_id:
        with engine.begin() as conn: 
            today_str = datetime.now().strftime('%Y-%m-%d')
            conn.execute(text('UPDATE customers SET "Satış Tarafından Arandı Mı" = \'Evet\', "İşlem Yapan" = :usr, "İşlem Tarihi" = :dt, "Kapanış Nedeni" = COALESCE(:sts, "Kapanış Nedeni"), "Hatırlatma Tarihi" = COALESCE(:rem, "Hatırlatma Tarihi") WHERE "Müşteri No" = :cid'), {"usr": user_name, "dt": today_str, "sts": a_status, "rem": (a_rem_date if a_rem_date else None), "cid": c_id})
            if a_notes:
                ek_not = f" (⏰ Hatırlatıcı Kuruldu: {a_rem_date.replace('T', ' ')})" if a_rem_date else ""
                new_entry = f"{datetime.now().strftime('%d.%m.%Y %H:%M')} | {user_name} | {a_notes.strip()}{ek_not}"
                res = conn.execute(text('SELECT "Görüşme Notları" FROM customers WHERE "Müşteri No" = :cid'), {"cid": c_id}).fetchone()
                old = res[0] if res and res[0] else ""
                conn.execute(text('UPDATE customers SET "Görüşme Notları" = :n WHERE "Müşteri No" = :cid'), {"n": (f"{old}\n{new_entry}" if str(old) != "nan" and old else new_entry).strip(), "cid": c_id})
            kisi = conn.execute(text('SELECT "Müşteri Ad Soyad" FROM customers WHERE "Müşteri No" = :id'), {"id": c_id}).fetchone()
            isim = kisi[0] if kisi else "Bilinmeyen Müşteri"
            
        log_kaydi_ekle(user_name, "Müşteri İşlemi", f"Müşteri: {isim} (No: {c_id}) paneli üzerinden güncelleme yapıldı.")
        return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, (refresh_val or 0) + 1, True, "Başarıyla kaydedildi!", dash.no_update, None, None, ""
    
    if "admin-save-btn" in trigger_id and ad_id and is_admin:
        with engine.begin() as conn:
            res = conn.execute(text('SELECT "Görüşme Notları" FROM customers WHERE "Müşteri No" = :id'), {"id": ad_id}).fetchone()
            old = res[0] if res and res[0] else ""
            final_notes = f"{old}\n{datetime.now().strftime('%d.%m.%Y %H:%M')} | {user_name} | {ad_new_notes.strip()}" if ad_new_notes else old
            conn.execute(text('UPDATE customers SET "Müşteri Ad Soyad" = :n, "Telefon" = :t, "Kapanış Nedeni" = :s, "Görüşme Notları" = :notes WHERE "Müşteri No" = :id'), {"n": ad_name, "t": ad_phone, "s": ad_status, "notes": final_notes, "id": ad_id})
            
        log_kaydi_ekle(user_name, "Yönetici Düzenlemesi", f"Müşteri (No: {ad_id}) bilgileri yönetici tarafından güncellendi.")
        return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, "", None, (refresh_val or 0) + 1, True, "Not güncellendi!", dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if "del-note" in trigger_id:
        target_id = c_id if c_id else ad_id
        if target_id:
            with engine.begin() as conn:
                res = conn.execute(text('SELECT "Görüşme Notları" FROM customers WHERE "Müşteri No" = :id'), {"id": target_id}).fetchone()
                if res and res[0]:
                    lines = str(res[0]).split('\n')
                    if ctx.triggered_id['index'] < len(lines):
                        p = lines[ctx.triggered_id['index']].split('|', 2)
                        if len(p) >= 2: lines[ctx.triggered_id['index']] = f"{p[0].strip()} | {p[1].strip()} | MESAJ SİLİNDİ"
                        conn.execute(text('UPDATE customers SET "Görüşme Notları" = :n WHERE "Müşteri No" = :id'), {"n": "\n".join(lines), "id": target_id})
            
            log_kaydi_ekle(user_name, "Not Silme İşlemi", f"{target_id} numaralı müşterinin geçmiş notu silindi.")
        return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, (refresh_val or 0) + 1, True, "Görüşme notu silindi!", dash.no_update, dash.no_update, dash.no_update, dash.no_update

    target_musteri_no = None
    if isinstance(triggered_id, dict) and triggered_id.get("type") == "dogum-gunu-btn" and ctx.triggered[0].get('value'): target_musteri_no = triggered_id.get("index") 
    elif triggered_id == "crm-table" and active_cell and viewport_data: target_musteri_no = viewport_data[active_cell['row']].get("Müşteri No")
        
    if target_musteri_no:
        with engine.connect() as conn:
            res = conn.execute(text('SELECT * FROM customers WHERE "Müşteri No" = :id'), {"id": target_musteri_no}).mappings().fetchone()
            if res:
                r_id, r_name, r_phone, r_status, r_notes = res.get("Müşteri No"), res.get("Müşteri Ad Soyad", "Bilinmiyor"), res.get("Telefon", "-"), res.get("Kapanış Nedeni", ""), str(res.get("Görüşme Notları", ""))
                def temizle(deger):
                    d = str(deger).strip()
                    return d.split(" ")[0] if "00:00:00" in d else ("-" if not d or d.lower() in ["none", "nan", "nat", ""] else d)
                r_model, r_dogum, r_meslek, r_sehir = temizle(res.get("Araç Modeli")), temizle(res.get("Doğum Tarihi")), temizle(res.get("Meslek")), temizle(res.get("Şehir"))
                
                profil_detay = html.Div([
                    html.Div([html.H5(f"👤 {r_name}", style={"color": "#E91B21", "fontWeight": "bold", "margin": "0"}), html.Span(f"Müşteri No: {r_id}", style={"fontSize": "11px", "color": "#888", "fontWeight": "bold"})], style={"borderBottom": "2px solid #eee", "paddingBottom": "10px", "marginBottom": "15px", "display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                    html.Div([html.Div([html.Strong("İletişim: ", style={"color": "#555"}), html.Span(r_phone)]), html.Div([html.Strong("Model: ", style={"color": "#555"}), html.Span(r_model)]), html.Div([html.Strong("Doğum Tarihi: ", style={"color": "#555"}), html.Span(r_dogum)]), html.Div([html.Strong("Meslek: ", style={"color": "#555"}), html.Span(r_meslek)]), html.Div([html.Strong("Şehir: ", style={"color": "#555"}), html.Span(r_sehir)]), html.Div([html.Strong("Durum: ", style={"color": "#555"}), html.Span(r_status if r_status else "İşlem Bekliyor", style={"color": "#E91B21", "fontWeight": "bold"})])], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "fontSize": "13px", "color": "#333"})
                ])

                formatted_notes = []
                for i, line in enumerate(r_notes.split('\n')):
                    if "|" in line:
                        p = line.split('|', 2)
                        if len(p) == 3:
                            is_del = "MESAJ SİLİNDİ" in p[2]
                            formatted_notes.append(html.Div([html.Div(f"{p[0].strip()} • {p[1].strip()}", style={"fontSize": "11px", "color": "#888", "fontWeight": "600", "userSelect": "none"}), html.Div(p[2].strip(), style={"padding": "10px", "backgroundColor": "#fff", "border": "1px solid rgba(0,0,0,0.08)",  "fontSize": "13px", "color": "#333"}), html.Button("Sil", id={"type": "del-note", "index": i}, style={"fontSize": "11px", "color": "#ff4d4d", "cursor": "pointer", "border": "none", "background": "transparent", "textDecoration": "underline", "padding": "0", "marginTop": "4px"}) if (is_admin and not is_del) else None], style={"marginBottom":"12px"}))
                if not formatted_notes: formatted_notes = [html.Div("Kayıtlı geçmiş görüşme notu bulunmamaktadır.", style={"fontSize": "13px", "color": "#999", "fontStyle": "italic", "padding": "5px 0"})]
                
                if is_admin and pathname == '/islem-gecmisi': 
                    return False, True, dash.no_update, dash.no_update, None, r_name, r_phone, r_status, formatted_notes, "", r_id, dash.no_update, False, "", profil_detay, dash.no_update, dash.no_update, dash.no_update
                else: 
                    return True, False, formatted_notes, profil_detay, r_id, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, False, "", dash.no_update, None, None, ""

    return False, False, dash.no_update, dash.no_update, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, None, dash.no_update, False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update

# --- ANA SAYFA YÜKLEYİCİSİ (ARAMADAN KOPARILMIŞ HALİ) ---
@app.callback(
    [Output("page-title", "children"), Output("unauthorized-view", "style"), Output("dashboard-view", "style"), Output("table-view", "style"),
     Output("metric-row-1", "children"), Output("metric-row-2", "children"), Output("chart-container", "children"),
     Output("raw-table-data", "data"), Output("crm-table", "columns"), Output("gamification-container", "children"), Output("dogum-gunleri-view", "children"), Output("dogum-gunleri-view", "style"), Output("btn-export-excel", "style")],
    [Input("url", "pathname"), Input("user-session", "data"), Input("db-refresh-trigger", "children")]
)
def display_page(pathname, user_session, refresh_trigger):
    hidden = {"display": "none"}
    try:
        return _display_page_impl(pathname, user_session, refresh_trigger)
    except Exception as e:
        print(f"display_page hata: {e}")
        return (f"Sistem Hatası: Sayfa yüklenemedi ({e})", hidden, hidden, hidden, [], [], [], [], [], html.Div(), None, hidden, {"display": "none"})

def _display_page_impl(pathname, user_session, refresh_trigger):
    hidden, visible, bar_layout_final = {"display": "none"}, {"display": "block"}, html.Div()
    
    if not current_user.is_authenticated: 
        return "", hidden, hidden, hidden, [], [], [], [], [], bar_layout_final, None, hidden, hidden
        
    role = current_user.role
    user_name = current_user.name
    
    if pathname == '/ekip-performansi' and role == 'admin':
        try: performans_ui = get_performance_layout()
        except Exception as e: performans_ui = html.Div(f"⚠️ Hata: {e}", style={"color": "#dc3545", "fontWeight": "600", "padding": "20px"})
        return "Ekip Performans Analizi", hidden, visible, hidden, performans_ui, None, None, [], [], None, None, hidden, hidden
    
    df = get_db_data()
    if df.empty: return "Sistem Hatası: Analiz edilecek veri bulunamadı.", hidden, hidden, hidden, [], [], [], [], [], bar_layout_final, None, hidden, hidden

    mevcut_yil = datetime.now().year
    bugun_doganlar_ui = html.Div() 
    
    if "Doğum Tarihi" in df.columns:
        today = datetime.now()
        dogum_gunu_olanlar = []
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(str(row.get("Doğum Tarihi", "")), errors='coerce')
                if pd.notna(dt) and dt.month == today.month and dt.day == today.day:
                    dogum_gunu_olanlar.append(f" {row.get('Müşteri Ad Soyad', 'Kayıtlı Müşteri')}")
            except: pass
        if dogum_gunu_olanlar:
            bugun_doganlar_ui = html.Div([
                 html.Div("BUGÜN DOĞUM GÜNÜ OLAN MÜŞTERİLER", style={"fontWeight": "bold", "color": "#E91B21", "fontSize": "13px", "marginBottom": "5px"}),
                 html.Div(" • ".join(dogum_gunu_olanlar), style={"fontWeight": "600", "color": "#252728", "fontSize": "15px"})
               ], style={"background": "rgba(233, 27, 33, 0.08)", "backdropFilter": "blur(10px)", "border": "1px solid rgba(233, 27, 33, 0.3)", "padding": "15px", "marginBottom": "20px"})

    if role == 'admin':
       sales_staff = [u['name'] for u in USERS_DB.values() if u['role'] == 'sales']
       bar_layout_final = html.Div([bugun_doganlar_ui, html.H4("Ekip Bireysel Performans Paneli", style={"marginBottom": "25px", "fontWeight": "bold"}), html.Div([generate_individual_bar(staff, df) for staff in sales_staff])], className="glass-panel", style={"marginBottom": "20px"})
    else:
       bar_layout_final = html.Div([bugun_doganlar_ui, html.H4("Günlük Operasyon Paneli", style={"fontWeight": "bold", "marginBottom": "15px"}), html.Div("Müşteri görüşme verilerini işleyerek günlük hedeflerinize ulaşabilirsiniz.", style={"color": "#666", "marginBottom": "25px", "fontSize": "14px"}), generate_individual_bar(user_name, df)], className="glass-panel", style={"marginBottom": "20px"})
    
    def safe_col(c, d=""): return df[c] if c in df.columns else pd.Series([d] * len(df), index=df.index)

    km_s = pd.to_numeric(safe_col("Kilometre", 0), errors='coerce').fillna(0)
    yil_s = pd.to_numeric(safe_col("Model Yılı", mevcut_yil), errors='coerce').fillna(mevcut_yil)
    arandi_s = safe_col("Satış Tarafından Arandı Mı").astype(str).str.strip().str.lower()
    cop_s = safe_col("Kapanış Nedeni").astype(str).str.strip().str.lower()
    notlar_s = safe_col("Görüşme Notları").fillna("").str.strip()

    islem_df = df[(arandi_s.isin(["evet", "yes", "1"])) | (notlar_s != "")]
    takas_df = df[(km_s > 60000) & (arandi_s.isin(["hayır", "hayir", "no", ""]))]
    garanti_df = df[(yil_s <= (mevcut_yil - 3)) & (arandi_s.isin(["hayır", "hayir", "no", ""]))]
    hayalet_df = df[arandi_s.isin(["hayır", "hayir", "no", ""])]
    cop_df = df[cop_s.isin(["bilgi verildi", "bilgi"])]
    test_df = df[safe_col("Test Surusu Durumu").astype(str).str.strip().str.lower().isin(["yapıldı", "yapildi"])]

    if role == 'sales' and pathname in ["/hayalet", "/cop", "/kvkk"]: return "", visible, hidden, hidden, [], [], [], [], [], bar_layout_final, None, hidden, hidden

    if pathname == "/dogum-gunleri":
        import calendar
        mevcut_ay, mevcut_yil = datetime.now().month, datetime.now().year
        ay_isimleri = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        dogum_df = df.copy() if not df.empty else pd.DataFrame()
        if "Doğum Tarihi" in dogum_df.columns and not dogum_df.empty:
            dogum_df = dogum_df[dogum_df["Doğum Tarihi"].notna() & (dogum_df["Doğum Tarihi"].astype(str).str.strip() != "")]
            dogum_df['Gizli_Tarih'] = pd.to_datetime(dogum_df['Doğum Tarihi'].astype(str), errors='coerce')
            bu_ay_df = dogum_df.dropna(subset=['Gizli_Tarih'])
            bu_ay_df = bu_ay_df[bu_ay_df['Gizli_Tarih'].dt.month == mevcut_ay]
        else: bu_ay_df = pd.DataFrame()

        takvim_satirlari = [html.Div([html.Div(g, style={"textAlign": "center", "fontWeight": "bold", "padding": "10px", "borderBottom": "3px solid #E91B21"}) for g in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]], style={"display": "grid", "gridTemplateColumns": "repeat(7, 1fr)", "gap": "10px", "marginBottom": "10px"})]
        for hafta in calendar.monthcalendar(mevcut_yil, mevcut_ay):
            hafta_ui = []
            for gun in hafta:
                if gun == 0: hafta_ui.append(html.Div(style={"backgroundColor": "transparent"}))
                else:
                    gunun_musterileri = [html.Button(f"{kisi.get('Müşteri Ad Soyad', 'Bilinmiyor')}", id={"type": "dogum-gunu-btn", "index": str(kisi.get("Müşteri No", ""))}, style={"fontSize": "11px", "backgroundColor": "#E91B21", "color": "white", "padding": "6px", "marginBottom": "4px", "width": "100%", "textAlign": "left", "display": "block"}) for _, kisi in (bu_ay_df[bu_ay_df['Gizli_Tarih'].dt.day == gun] if not bu_ay_df.empty else pd.DataFrame()).iterrows()]
                    hafta_ui.append(html.Div([html.Div(str(gun), style={"fontWeight": "900", "fontSize": "18px", "color": "#E91B21" if (gun == datetime.now().day) else "#94a3b8", "marginBottom": "6px", "textAlign": "right"}), html.Div(gunun_musterileri, style={"flex": "1", "overflowY": "auto"})], style={"backgroundColor": "rgba(255,255,255,0.7)", "border": "1px solid rgba(0,0,0,0.08)", "height": "130px", "padding": "10px", "display": "flex", "flexDirection": "column"}))
            takvim_satirlari.append(html.Div(hafta_ui, style={"display": "grid", "gridTemplateColumns": "repeat(7, 1fr)", "gap": "10px", "marginBottom": "10px"}))
            
        takvim_arayuzu = html.Div([html.Div([html.H3(f"🗓️ {ay_isimleri[mevcut_ay]} {mevcut_yil} - Doğum Günü Takvimi", style={"fontWeight": "bold"})], style={"marginBottom": "25px"}), html.Div(takvim_satirlari, className="glass-panel", style={"padding": "25px"})])
        return "Müşteri Doğum Günleri", hidden, hidden, hidden, [], [], [], [], [], html.Div(), takvim_arayuzu, visible, {"display": "none"}

    if pathname == "/":
        # --- YENİ GRAFİKLERİN VERİ HAZIRLIĞI (GÜÇLENDİRİLMİŞ FİLTRE) ---
        mevcut_df = df[df["Araç Modeli"].notna() & (df["Araç Modeli"] != "-") & (df["Araç Modeli"].astype(str).str.strip() != "") & (df["Araç Modeli"].astype(str).str.lower() != "nan")].copy()
        ilgi_df = df[df["İlgilendiği Araç"].notna() & (df["İlgilendiği Araç"] != "-") & (df["İlgilendiği Araç"].astype(str).str.strip() != "") & (df["İlgilendiği Araç"].astype(str).str.lower() != "nan")].copy()
        
        # Ulaşım Kanalı Verisi 
        ulasim_df = pd.DataFrame()
        if "Ulaşım Kanalı" in df.columns:
            ulasim_df = df[df["Ulaşım Kanalı"].notna() & (df["Ulaşım Kanalı"] != "-") & (df["Ulaşım Kanalı"].astype(str).str.strip() != "") & (df["Ulaşım Kanalı"].astype(str).str.lower() != "nan")].copy()
        
        # 1. Grafik: Mevcut Araçlar
        if len(mevcut_df) == 0:
            fig_mevcut = go.Figure()
            fig_mevcut.add_annotation(text="Mevcut araç verisi bulunmuyor.", showarrow=False, font=dict(size=14, color="#999", style="italic"))
            fig_mevcut.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10, l=10, r=10))
        else:
            fig_mevcut = px.pie(mevcut_df, names="Araç Modeli", hole=0.6, color_discrete_sequence=['#E91B21', '#333333', '#777777', '#aaaaaa', '#dddddd'])
            fig_mevcut.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        # 2. Grafik: İlgilenilen Araçlar
        ilgi_sayilari = ilgi_df["İlgilendiği Araç"].value_counts().reset_index()
        ilgi_sayilari.columns = ["İlgilendiği Araç", "Kişi Sayısı"]
        
        if len(ilgi_sayilari) == 0:
            fig_ilgi = go.Figure()
            fig_ilgi.add_annotation(text="Henüz ilgilenilen araç verisi girilmemiş.", showarrow=False, font=dict(size=14, color="#999", style="italic"))
            fig_ilgi.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10, l=10, r=10))
        else:
            fig_ilgi = px.bar(ilgi_sayilari, x="İlgilendiği Araç", y="Kişi Sayısı", text="Kişi Sayısı", color="İlgilendiği Araç", color_discrete_sequence=['#E91B21', '#333333', '#777777', '#aaaaaa', '#dddddd'])
            fig_ilgi.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, xaxis_title="", yaxis_title="")
            fig_ilgi.update_traces(textposition='outside', marker_line_width=0, opacity=0.9, textfont=dict(size=14, color='#333', weight='bold'))

        # 3. Grafik: Ulaşım Kanalı
        if len(ulasim_df) == 0:
            fig_ulasim = go.Figure()
            fig_ulasim.add_annotation(text="Henüz ulaşım kanalı verisi bulunmuyor.", showarrow=False, font=dict(size=14, color="#999", style="italic"))
            fig_ulasim.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10, l=10, r=10))
        else:
            ulasim_sayilari = ulasim_df["Ulaşım Kanalı"].value_counts().reset_index()
            ulasim_sayilari.columns = ['Kanal', 'Sayı']
            fig_ulasim = px.pie(ulasim_sayilari, values='Sayı', names='Kanal', hole=0.5, color_discrete_sequence=['#185DF5', '#E91B21', '#FD7E14', '#198754', '#252728', '#777777'])
            fig_ulasim.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

        
        # --- HTML TASARIMI (ALT BLOK: ARAÇ GRAFİKLERİ) ---
        grafik_tasarimi_araclar = html.Div([
            html.Div([
                html.H4("Müşterilerin Mevcut Araçları", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
                dcc.Graph(figure=fig_mevcut, config={'displayModeBar': False})
            ], style={'flex': '1', 'marginRight': '10px', 'backgroundColor': '#fff', 'borderRadius': '12px', 'boxShadow': '0 8px 16px rgba(0,0,0,0.06)', 'padding': '20px'}),
            
            html.Div([
                html.H4("Hangi Araçlarla İlgileniliyor?", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
                dcc.Graph(figure=fig_ilgi, config={'displayModeBar': False})
            ], style={'flex': '1', 'marginLeft': '10px', 'backgroundColor': '#fff', 'borderRadius': '12px', 'boxShadow': '0 8px 16px rgba(0,0,0,0.06)', 'padding': '20px'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'width': '100%'})


        if role == 'admin':
            temiz_df = df.dropna(subset=["Kapanış Nedeni"])
            dagilim = pd.DataFrame([{"Neden": "Veri Yok", "Sayı": 1}]) if temiz_df.empty else temiz_df["Kapanış Nedeni"].value_counts().reset_index()
            dagilim.columns = ['Neden', 'Sayı']
            fig_admin = px.pie(dagilim, values='Sayı', names='Neden', hole=0.5, color_discrete_sequence=[BYD_RED, BYD_OCEAN_BLUE, BYD_SHARK_GREY])
            fig_admin.update_layout(transition_duration=0, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10, l=10, r=10))
            
            m1 = [
                dbc.Col(html.A([html.Span("Hedef Takas Fırsatı"), html.H3(len(takas_df))], href="/takas", className="glass-metric", style={"borderLeft": "5px solid #198754", "textDecoration": "none", "color": "inherit"}), width=4), 
                dbc.Col(html.A([html.Span("İşlemsiz Kayıtlar"), html.H3(len(hayalet_df))], href="/hayalet", className="glass-metric", style={"borderLeft": f"5px solid {BYD_OCEAN_BLUE}", "textDecoration": "none", "color": "inherit"}), width=4), 
                dbc.Col(html.A([html.Span("Sistem Toplam Kayıt"), html.H3(len(df))], href="/islem-gecmisi", className="glass-metric", style={"borderLeft": f"5px solid {BYD_SHARK_GREY}", "textDecoration": "none", "color": "inherit"}), width=4)
            ]
            
            admin_grafikler = html.Div([
                html.Div([
                    html.Div([
                        html.H4("Kapanış Nedeni / Karar Dağılımı", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
                        dcc.Graph(figure=fig_admin, config={'displayModeBar': False})
                    ], style={'flex': '1', 'marginRight': '10px', 'backgroundColor': '#fff', 'borderRadius': '12px', 'boxShadow': '0 8px 16px rgba(0,0,0,0.06)', 'padding': '20px'}),
                    
                    html.Div([
                        html.H4("Ulaşım Kanalı Dağılımı", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
                        dcc.Graph(figure=fig_ulasim, config={'displayModeBar': False})
                    ], style={'flex': '1', 'marginLeft': '10px', 'backgroundColor': '#fff', 'borderRadius': '12px', 'boxShadow': '0 8px 16px rgba(0,0,0,0.06)', 'padding': '20px'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'width': '100%', 'marginBottom': '25px'}),
                
                grafik_tasarimi_araclar
            ])
            return "Sistem Yöneticisi Paneli", hidden, visible, hidden, m1, [], admin_grafikler, [], [], bar_layout_final, None, hidden, hidden
            
        else:
            m1 = [
                dbc.Col(html.A([html.Span("Planlanan Takas"), html.H3(len(takas_df))], href="/takas", className="glass-metric", style={"borderLeft": "5px solid #198754", "textDecoration": "none", "color": "inherit"}), width=6), 
                dbc.Col(html.A([html.Span("Garanti Görüşmeleri"), html.H3(len(garanti_df))], href="/garanti", className="glass-metric", style={"borderLeft": f"5px solid {BYD_WARNING_ORANGE}", "textDecoration": "none", "color": "inherit"}), width=6)
            ]
            
            satis_grafikler = html.Div([
                html.Div([
                    html.H4("Ulaşım Kanalı Dağılımı", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
                    dcc.Graph(figure=fig_ulasim, config={'displayModeBar': False})
                ], style={'backgroundColor': '#fff', 'borderRadius': '12px', 'boxShadow': '0 8px 16px rgba(0,0,0,0.06)', 'padding': '20px', 'marginBottom': '25px'}),
                
                grafik_tasarimi_araclar
            ])
            return "Günlük Operasyon Paneli", hidden, visible, hidden, m1, [], satis_grafikler, [], [], bar_layout_final, None, hidden, hidden
    
    title, sub_df, cols = html.Span([html.I(className="fa-solid fa-database", style={"color": BYD_RED, "marginRight": "10px"}), "Sistem Veri Tablosu"]), pd.DataFrame(), []
    if pathname == "/islem-gecmisi": 
        islem_df = islem_df.copy() 
        if "Görüşme Notları" in islem_df.columns:
            islem_df['Gizli_Tarih'] = pd.to_datetime(islem_df['Görüşme Notları'].astype(str).str.findall(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}').apply(lambda x: x[-1] if isinstance(x, list) and len(x) > 0 else None), format='%d.%m.%Y %H:%M', errors='coerce')
            islem_df = islem_df.sort_values(by='Gizli_Tarih', ascending=False, na_position='last')
            
        title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-file-signature", style={"color": BYD_RED, "marginRight": "10px"}), "İşlem Kayıtları Arşivi"]), islem_df, [
            "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
            "Araç Modeli", "İlgilendiği Araç", "Kapanış Nedeni", "Görüşme Notları", "İşlem Yapan"
        ])
    elif pathname == "/takas": title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-right-left", style={"color": BYD_RED, "marginRight": "10px"}), "Hedef Takas Radarı"]), takas_df, [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "Araç Modeli", "Kilometre", "Model Yılı", "İlgilendiği Araç", 
        "Görüşme Notları", "İşlem Yapan"
    ])
    elif pathname == "/garanti": 
        garanti_df = garanti_df.copy()
        mevcut_yil_sayi = datetime.now().year
        
        # 6 Yıllık Garanti Hesaplama Motoru
        garanti_df["Geçici_Yıl"] = pd.to_numeric(garanti_df["Model Yılı"], errors='coerce')
        garanti_df["Kalan Süre"] = garanti_df["Geçici_Yıl"].apply(
            lambda y: f"{int((y + 6) - mevcut_yil_sayi)} Yıl Kaldı" if pd.notna(y) and ((y + 6) - mevcut_yil_sayi) > 0 
            else ("Bu Yıl Bitiyor" if pd.notna(y) and ((y + 6) - mevcut_yil_sayi) == 0 else ("Süresi Doldu" if pd.notna(y) else "-"))
        )
        
        title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-shield-halved", style={"color": BYD_RED, "marginRight": "10px"}), "Garanti Uzatma Listesi"]), garanti_df, [
            "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
            "Araç Modeli", "Kilometre", "Model Yılı", "Kalan Süre", 
            "İlgilendiği Araç", "Görüşme Notları", "İşlem Yapan"
        ])
    elif pathname == "/hayalet": title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-user-clock", style={"color": BYD_RED, "marginRight": "10px"}), "İşlemsiz Müşteri Kayıtları"]), hayalet_df, [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "Satış Tarafından Arandı Mı", "Kapanış Nedeni", "Görüşme Notları", "İşlem Yapan"
    ])
    elif pathname == "/cop": title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-trash-can", style={"color": BYD_RED, "marginRight": "10px"}), "Kalitesiz Veri Tespit Arşivi"]), cop_df, [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Ulaşım Kanalı", "Kapanış Nedeni"
    ])
    elif pathname == "/test": title, sub_df, cols = (html.Span([html.I(className="fa-solid fa-key", style={"color": BYD_RED, "marginRight": "10px"}), "Test Sürüşü Takipleri"]), test_df, [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "İlgilendiği Araç", "Satış Tarafından Arandı Mı", "Kapanış Nedeni", 
        "Görüşme Notları", "İşlem Yapan"
    ])
    elif pathname == "/hatirlaticilar": 
         hatirlatici_df = df[df["Hatırlatma Tarihi"].notna() & (df["Hatırlatma Tarihi"].astype(str).str.strip() != "") & (df["Hatırlatma Tarihi"].astype(str).str.lower() != "nan")].copy()
         hatirlatici_df['Gizli_Tarih'] = pd.to_datetime(hatirlatici_df["Hatırlatma Tarihi"].astype(str).str.replace('T', ' '), errors='coerce')
         hatirlatici_df = hatirlatici_df.dropna(subset=['Gizli_Tarih']).sort_values(by="Gizli_Tarih", ascending=True)
         hatirlatici_df["Hatırlatma Tarihi"] = hatirlatici_df["Gizli_Tarih"].dt.strftime('%d-%m-%Y %H:%M')

         title, sub_df, cols = (html.Span([html.I(className="fa-regular fa-bell", style={"color": BYD_RED, "marginRight": "10px"}), "Yaklaşan Müşteri Hatırlatıcıları"]), hatirlatici_df, [
             "Müşteri No", "Hatırlatma Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
             "Kapanış Nedeni", "Görüşme Notları", "İşlem Yapan"
         ])
    elif pathname == "/harita":
        import numpy as np
        def standart_sehir(s): return str(s).strip().upper().replace("İ", "I").replace("I", "I").replace("Ş", "S").replace("Ç", "C").replace("Ğ", "G").replace("Ü", "U").replace("Ö", "O")
        iller = {"ADANA": [37.0, 35.32], "MERSIN": [36.82, 34.61], "HATAY": [36.2, 36.15], "OSMANIYE": [37.07, 36.24], "GAZIANTEP": [37.06, 37.38], "ISTANBUL": [41.01, 28.97], "ANKARA": [39.92, 32.85], "IZMIR": [38.42, 27.14], "ANTALYA": [36.89, 30.71], "BURSA": [40.18, 29.06]}
        
        map_df = pd.DataFrame(columns=["Lat", "Lon", "Müşteri Ad Soyad", "Araç Modeli", "Şehir"])
        if "Şehir" in df.columns:
            map_df = df[df["Şehir"].notna() & (df["Şehir"] != "") & (df["Şehir"] != "-")].copy()
            map_df["Şehir_Temiz"] = map_df["Şehir"].apply(standart_sehir)
            map_df["Lat"] = [iller[s][0] + np.random.uniform(-0.008, 0.008) if s in iller else np.nan for s in map_df["Şehir_Temiz"]]
            map_df["Lon"] = [iller[s][1] + np.random.uniform(-0.008, 0.008) if s in iller else np.nan for s in map_df["Şehir_Temiz"]]
            map_df = map_df.dropna(subset=["Lat", "Lon"])

        fig_map = go.Figure()
        if not map_df.empty: fig_map.add_trace(go.Scattermap(lat=map_df["Lat"], lon=map_df["Lon"], mode='markers', marker=dict(size=10, color=BYD_RED, opacity=0.85), text=map_df["Müşteri Ad Soyad"] + "<br>Model: " + map_df["Araç Modeli"] + "<br>Şehir: " + map_df["Şehir"], hoverinfo='text', name="Müşteriler"))
        sarj_df = internetten_canli_sarj_istasyonlarini_cek()
        if not sarj_df.empty: fig_map.add_trace(go.Scattermap(lat=sarj_df["Lat"], lon=sarj_df["Lon"], mode='markers', marker=dict(size=8, color="#005CFF", opacity=0.7), text="⚡ " + sarj_df["İstasyon"], hoverinfo='text', name=f"Şarj İstasyonları ({len(sarj_df)} Adet)"))

        fig_map.update_layout(map=dict(style="carto-positron", center=dict(lat=39.0, lon=35.2), zoom=4.9, bounds={"west": 25.0, "east": 45.0, "south": 35.0, "north": 43.0}), margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(0,0,0,0.1)", borderwidth=1))
        map_container = html.Div([html.Div([html.H4("Türkiye Geneli Müşteri ve Şarj Ağı Haritası", style={"fontWeight": "bold", "color": BYD_SHARK_DARK, "marginBottom": "5px"})], style={"marginBottom": "20px"}), dcc.Graph(figure=fig_map, config={'scrollZoom': True, 'displayModeBar': False, 'doubleClick': 'reset'}, style={"height": "650px", "borderRadius": "12px", "overflow": "hidden", "boxShadow": "0 8px 25px rgba(0,0,0,0.08)", "border": "1px solid rgba(0,0,0,0.1)"})], className="glass-panel")
        return html.Span([html.I(className="fa-solid fa-map-location-dot", style={"color": BYD_RED, "marginRight": "10px"}), "Müşteri Haritası"]), hidden, visible, hidden, [], [], map_container, [], [], html.Div(), None, hidden, {"display": "none"}
    elif pathname == "/loglar":
        if role == 'admin':
            try: log_df = pd.read_sql_table("system_logs", con=engine).sort_values(by="islem_tarihi", ascending=False)
            except: log_df = pd.DataFrame(columns=["islem_tarihi", "kullanici_adi", "islem_tipi", "detay"])
            return html.Span([html.I(className="fa-solid fa-server", style={"color": BYD_RED, "marginRight": "10px"}), "Sistem Güvenlik Logları"]), hidden, hidden, visible, [], [], [], log_df.to_dict('records'), [{"name": c, "id": c} for c in ["islem_tarihi", "kullanici_adi", "islem_tipi", "detay"]], bar_layout_final, None, hidden, {"display": "none"}
        return "Yetkisiz Erişim", visible, hidden, hidden, [], [], [], [], [], bar_layout_final, None, hidden, {"display": "none"}
    
    # --- YENİ EKLENEN GLOBAL TARİH MOTORU ---
    # Bu kod, sistemin neresinde olursa olsun tarihleri bulup Gün-Ay-Yıl formatına çevirir
    tarih_sutunlari = ["İşlem Tarihi", "Doğum Tarihi", "Son Servis Tarihi"]
    for sutun in tarih_sutunlari:
        if sutun in sub_df.columns:
            sub_df[sutun] = pd.to_datetime(sub_df[sutun], errors='coerce').dt.strftime('%d-%m-%Y').fillna("-")

            
    table_data = sub_df.to_dict('records')
    table_cols = [{"name": c, "id": c} for c in cols if c in sub_df.columns]
    rapor_sayfalari = ["/", "/islem-gecmisi", "/takas", "/garanti", "/hayalet", "/cop", "/test", "/hatirlaticilar", "/loglar"]
    btn_style = {"fontWeight": "bold", "marginRight": "15px", "display": "block"} if pathname in rapor_sayfalari else {"display": "none"}
    
    return title, hidden, hidden, visible, [], [], [], table_data, table_cols, bar_layout_final, None, hidden, btn_style

# --- 🚀 YEPYENİ BAĞIMSIZ VE ŞİMŞEK HIZINDA ARAMA MOTORU ---
@app.callback(
    [Output("crm-table", "data"), Output("crm-table", "tooltip_data")],
    [Input("global-search", "value"), Input("raw-table-data", "data")],
    State("crm-table", "columns")
)
def update_table_search(search_text, raw_data, cols):
    if not raw_data:
        return [], []
        
    df = pd.DataFrame(raw_data)
    
    if search_text:
        search_text = str(search_text).lower()
        mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search_text, na=False)).any(axis=1)
        df = df[mask]

    table_data = df.to_dict('records')
    
    tooltip_data = []
    col_names = [c['name'] for c in cols] if cols else []
    
    for row in table_data:
        if "Müşteri Ad Soyad" in col_names:
            tooltip_data.append({"Müşteri Ad Soyad": {"value": f"**İletişim:** {row.get('Telefon', '-')}\n\n**Meslek:** {row.get('Meslek', '-')}\n\n**Bölge:** {row.get('Şehir', '-')}", "type": "markdown"}})
        elif "detay" in col_names:
            val = row.get("detay", "")
            if val and str(val).lower() != "nan": tooltip_data.append({"detay": {"value": str(val), "type": "markdown"}})
            else: tooltip_data.append({})
        else:
            tooltip_data.append({})
            
    return table_data, tooltip_data

# --- DİĞER ARAÇLAR ---
@app.callback(
    Output("download-excel", "data"),
    Input("btn-export-excel", "n_clicks"),
    [State("crm-table", "derived_virtual_data"), State("user-session", "data"), State("url", "pathname")],
    prevent_initial_call=True
)
def export_to_excel(n_clicks, table_data, user_session, pathname):
    if not table_data: return dash.no_update
    user_name = user_session.get("name", "Bilinmeyen Kullanıcı") if user_session else "Bilinmeyen Kullanıcı"
    df_export = pd.DataFrame(table_data)
    bugun = datetime.now().strftime("%d_%m_%Y")
    
    dosya_adi = f"Rapor_{bugun}.xlsx"
    istenen_sutunlar = []

    if pathname == "/test": dosya_adi, istenen_sutunlar = f"Test_Surusu_Takip_{bugun}.xlsx", [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "İlgilendiği Araç", "Satış Tarafından Arandı Mı", "Kapanış Nedeni", 
        "Görüşme Notları", "İşlem Yapan"
    ]
    elif pathname == "/takas": dosya_adi, istenen_sutunlar = f"Takas_Firsatlari_Raporu_{bugun}.xlsx", [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "Araç Modeli", "Kilometre", "Model Yılı", "İlgilendiği Araç", 
        "Görüşme Notları", "İşlem Yapan"
    ]
    elif pathname == "/garanti": dosya_adi, istenen_sutunlar = f"Garanti_Uzatma_Firsatlari_{bugun}.xlsx", [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "Araç Modeli", "Kilometre", "Model Yılı", "Kalan Süre", "İlgilendiği Araç", 
        "Görüşme Notları", "İşlem Yapan"
    ]
    elif pathname == "/islem-gecmisi": dosya_adi, istenen_sutunlar = f"Islem_Gecmisi_Arsivi_{bugun}.xlsx", ["Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı", "Araç Modeli", "İlgilendiği Araç", "Kapanış Nedeni", "Görüşme Notları", "İşlem Yapan"]
    elif pathname == "/hayalet": dosya_adi, istenen_sutunlar = f"Islemsiz_Kayitlar_Raporu_{bugun}.xlsx", [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı",
        "Satış Tarafından Arandı Mı", "Kapanış Nedeni", "Görüşme Notları", "İşlem Yapan"
    ]
    elif pathname == "/cop": dosya_adi, istenen_sutunlar = f"Kalitesiz_Veri_Raporu_{bugun}.xlsx", [
        "Müşteri No", "İşlem Tarihi", "Müşteri Ad Soyad", "Ulaşım Kanalı", "Kapanış Nedeni"
    ]
    elif pathname == "/hatirlaticilar": dosya_adi, istenen_sutunlar = f"Aktif_Hatirlaticilar_{bugun}.xlsx", ["Müşteri No", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı", "Hatırlatma Tarihi", "İşlem Yapan", "Görüşme Notları"]
    elif pathname == "/loglar":
        log_df = pd.DataFrame(table_data)
        log_kaydi_ekle(user_name, "Logları Dışa Aktardı", "Sistem logları excele aktarıldı.")
        return dcc.send_data_frame(log_df.to_excel, f"Sistem_Güvenlik_Loglari_{bugun}.xlsx", index=False)
    else: dosya_adi, istenen_sutunlar = f"Genel_Analiz_Raporu_{bugun}.xlsx", ["Müşteri No", "Müşteri Ad Soyad", "Telefon", "Ulaşım Kanalı", "Araç Modeli", "Meslek", "Şehir", "Kapanış Nedeni"]
    
    mevcut_sutunlar = [col for col in istenen_sutunlar if col in df_export.columns]
    if mevcut_sutunlar: df_export = df_export[mevcut_sutunlar]
    log_kaydi_ekle(user_name, "Excel Dışa Aktarım", f"'{dosya_adi}' isimli tablo bilgisayara indirildi.")
    return dcc.send_data_frame(df_export.to_excel, dosya_adi, index=False)

@app.callback(
    [Output("reminder-toast", "is_open"), Output("reminder-toast", "children"), Output("notified-reminders", "data")],
    [Input("reminder-interval", "n_intervals"), Input({"type": "done-rem-btn", "index": dash.ALL}, "n_clicks")],
    [State("user-session", "data"), State("notified-reminders", "data")]
)
def check_active_reminders(n, done_clicks, user_session, notified_list):
    ctx = dash.callback_context
    if not user_session: return dash.no_update, dash.no_update, dash.no_update
    user_name = user_session.get("name", "Kurumsal Kullanıcı")
    
    if ctx.triggered and "done-rem-btn" in ctx.triggered[0]['prop_id']:
            m_id = ctx.triggered_id['index']
            with engine.connect() as conn:
                kisi = conn.execute(text('SELECT "Müşteri Ad Soyad" FROM customers WHERE "Müşteri No" = :id'), {"id": m_id}).fetchone()
                isim = kisi[0] if kisi else "Bilinmeyen Müşteri"
            with engine.begin() as conn:
                conn.execute(text('UPDATE customers SET "Hatırlatma Tarihi" = NULL WHERE "Müşteri No" = :id'), {"id": m_id})
                log_kaydi_ekle(user_name, "Hatırlatıcı Tamamlandı", f"Müşteri: {isim} (No: {m_id}) için kurulan hatırlatıcı danışman tarafından onaylandı ve kapatıldı.")
            return False, dash.no_update, [x for x in notified_list if x != m_id]

    if not notified_list: notified_list = []
        
    try:
        with engine.connect() as conn:
            res = conn.execute(text('SELECT "Müşteri No", "Müşteri Ad Soyad", "Telefon", "Hatırlatma Tarihi" FROM customers WHERE "İşlem Yapan" = :usr AND "Hatırlatma Tarihi" IS NOT NULL AND "Hatırlatma Tarihi" != \'\''), {"usr": user_name}).mappings().fetchall()
            simdi = datetime.now()
            for row in res:
                m_id = str(row.get("Müşteri No"))
                if m_id in notified_list: continue 
                
                tarih_str = str(row.get("Hatırlatma Tarihi")).replace('T', ' ')
                h_tarih = pd.to_datetime(tarih_str, errors='coerce')
                if pd.isna(h_tarih): continue
                
                if -300 <= (simdi - h_tarih).total_seconds() <= 7200: 
                    isim = row.get("Müşteri Ad Soyad", "Bilinmeyen Müşteri")
                    icerik = html.Div([
                        html.Div("Müşteri ile görüşme vaktiniz geldi.", style={"fontWeight": "600", "color": "#333", "marginBottom": "12px", "fontSize": "14px"}),
                        html.Div([html.Strong("👤 İsim: ", style={"color": "#666"}), html.Span(isim)], style={"fontSize": "13px"}),
                        html.Div([html.Strong("Planlanan: ", style={"color": "#666"}), html.Span(h_tarih.strftime("%d.%m.%Y %H:%M"), style={"color": "#E91B21", "fontWeight": "bold"})], style={"fontSize": "13px", "marginBottom": "15px"}),
                        dbc.Button("Hatırlatıcıyı Tamamla", id={"type": "done-rem-btn", "index": m_id}, color="success", size="sm", style={"width": "100%", "fontWeight": "bold"})
                    ])
                    notified_list.append(m_id)
                    return True, icerik, notified_list
    except Exception as e: print(f"Hatırlatıcı Timer Hatası: {e}")
    return False, dash.no_update, notified_list

@app.callback(
    [Output("sidebar-container", "style"), Output("page-content-wrapper", "style")],
    [Input("sidebar-toggle-btn", "n_clicks")]
)
def toggle_sidebar(n_clicks):
    sidebar_style = SIDEBAR_STYLE.copy()
    content_style = CONTENT_STYLE.copy()
    sidebar_style["transition"] = "transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)"
    content_style["transition"] = "margin-left 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)"
    
    if n_clicks and n_clicks % 2 != 0:
        sidebar_style["transform"], content_style["marginLeft"] = "translateX(-100%)", "0px"
    else:
        sidebar_style["transform"], content_style["marginLeft"] = "translateX(0)", "300px"
        
    return sidebar_style, content_style

@app.server.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__ == "__main__":
    app.run(debug=False, port=8050)