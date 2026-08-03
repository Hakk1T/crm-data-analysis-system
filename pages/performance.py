from config import engine
import pandas as pd
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px


def _load_customers_df():
    """
    Tüm performans sorgularının kullandığı ortak, GÜVENLİ veri çekme fonksiyonu.
    Veritabanı bağlantısı koparsa veya beklenmeyen bir hata olursa uygulamayı
    çökertmek yerine boş bir DataFrame döner; çağıran taraf bunu kontrol eder.
    """
    try:
        df = pd.read_sql('SELECT * FROM customers', con=engine)
        return df, None
    except Exception as e:
        print(f"[performance.py] Veri çekme hatası: {e}")
        return pd.DataFrame(), str(e)


def _error_box(msg):
    return html.Div(
        f"⚠️ Rapor verisi yüklenemedi: {msg}",
        style={"color": "#dc3545", "fontWeight": "600", "padding": "15px",
               "backgroundColor": "rgba(220,53,69,0.08)", "borderRadius": "8px"}
    )


def get_performance_layout():
    df, err = _load_customers_df()

    if err:
        return html.Div([
            html.H3("Yönetici Performans Analiz Paneli", style={"fontWeight": "bold", "color": "#1A1A1A", "marginBottom": "25px"}),
            _error_box(err)
        ])

    if "Satış Tarafından Arandı Mı" not in df.columns:
        return html.Div([
            html.H3("Yönetici Performans Analiz Paneli", style={"fontWeight": "bold", "color": "#1A1A1A", "marginBottom": "25px"}),
            _error_box('Veritabanı tablosunda "Satış Tarafından Arandı Mı" sütunu bulunamadı. Sütun adlarını kontrol edin.')
        ])

    df_arandi = df[df["Satış Tarafından Arandı Mı"] == 'Evet'].copy()
    danismanlar = df_arandi["İşlem Yapan"].dropna().unique() if "İşlem Yapan" in df_arandi.columns else []

    return html.Div([
        html.H3("Yönetici Performans Analiz Paneli", style={"fontWeight": "bold", "color": "#1A1A1A", "marginBottom": "25px"}),
        
        html.Div([
            html.Div([
                html.H5("Danışman Arama Hacimleri", style={"fontWeight": "bold", "color": "#333", "marginBottom": "15px"}),
                dbc.RadioItems(
                    id="perf-time-filter",
                    options=[
                        {"label": "Son 7 Gün", "value": "7"},
                        {"label": "Son 30 Gün", "value": "30"},
                        {"label": "Son 365 Gün", "value": "365"}
                    ],
                    value="30", inline=True, style={"marginBottom": "20px", "fontWeight": "600", "color": "#555"}
                ),
                dcc.Graph(id="perf-call-graph")
            ], className="glass-panel", style={"flex": "1", "minWidth": "450px", "marginRight": "20px", "padding": "20px"}),
            
            html.Div([
                html.H5("Sistem Analizi ve Kapanış Nedenleri", style={"fontWeight": "bold", "color": "#333", "marginBottom": "15px"}),
                html.Div(id="smart-analysis-container", style={"marginBottom": "15px"}),
                html.Hr(style={"borderColor": "rgba(0,0,0,0.1)", "marginBottom": "20px"}),
                
                dcc.Dropdown(
                    id="perf-staff-dropdown",
                    options=[{"label": name, "value": name} for name in danismanlar] + [{"label": "Tüm Ekip", "value": "HEPSİ"}],
                    value="HEPSİ", clearable=False, style={"marginBottom": "20px", "borderRadius": "8px", "fontWeight": "600"}
                ),
                dcc.Graph(id="perf-reason-graph")
            ], className="glass-panel", style={"flex": "1", "minWidth": "450px", "padding": "20px"})
            
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "20px"})
    ])

@callback(
    Output("perf-call-graph", "figure"),
    [Input("perf-time-filter", "value"), Input("db-refresh-trigger", "children")] 
)
def update_call_graph(days_filter, refresh):
    df, err = _load_customers_df()
    if err or "Satış Tarafından Arandı Mı" not in df.columns:
        return px.bar(title="Veri yüklenemedi (bağlantı/sütun hatası).")

    df_arandi = df[df["Satış Tarafından Arandı Mı"] == 'Evet'].copy()
    if df_arandi.empty or "İşlem Yapan" not in df_arandi.columns or "İşlem Tarihi" not in df_arandi.columns:
        return px.bar(title="Kayıtlı veri bulunmamaktadır.")

    df_arandi["İşlem Tarihi"] = pd.to_datetime(df_arandi["İşlem Tarihi"], errors='coerce')
    limit_date = pd.Timestamp.now() - pd.Timedelta(days=int(days_filter))
    df_filtered = df_arandi[df_arandi["İşlem Tarihi"] >= limit_date]
    
    if df_filtered.empty:
        return px.bar(title="Seçilen dönemde arama kaydı yok.")
        
    perf_df = df_filtered.groupby("İşlem Yapan").size().reset_index(name="Toplam Arama")
    fig = px.bar(
        perf_df, x="İşlem Yapan", y="Toplam Arama", text="Toplam Arama",
        labels={"İşlem Yapan": "Satış Danışmanı", "Toplam Arama": "Aranan Kişi Sayısı"},
        color_discrete_sequence=["#E91B21"]
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin={"t":20, "b":20, "l":20, "r":20}, font=dict(family="Segoe UI", size=12))
    return fig

@callback(
    Output("perf-reason-graph", "figure"),
    [Input("perf-staff-dropdown", "value"), Input("db-refresh-trigger", "children")]
)
def update_reason_graph(selected_staff, refresh):
    df, err = _load_customers_df()
    if err or "Satış Tarafından Arandı Mı" not in df.columns or "Kapanış Nedeni" not in df.columns:
        return px.pie(title="Veri yüklenemedi (bağlantı/sütun hatası).")

    df_arandi = df[df["Satış Tarafından Arandı Mı"] == 'Evet'].copy()
    df_arandi = df_arandi[df_arandi["Kapanış Nedeni"].notna() & (df_arandi["Kapanış Nedeni"] != "")]
    
    if df_arandi.empty:
        return px.pie(title="Kapanış nedeni verisi bulunamadı.")
        
    if selected_staff != "HEPSİ":
        df_arandi = df_arandi[df_arandi["İşlem Yapan"] == selected_staff]
        
    if df_arandi.empty:
        return px.pie(title="Bu danışmana ait kapanış kaydı yok.")
        
    reason_df = df_arandi.groupby("Kapanış Nedeni").size().reset_index(name="Adet")
    fig = px.pie(reason_df, names="Kapanış Nedeni", values="Adet", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_traces(textinfo='percent+label', textposition='inside')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin={"t":20, "b":20, "l":20, "r":20}, showlegend=False, font=dict(family="Segoe UI", size=12))
    return fig

@callback(
    Output("smart-analysis-container", "children"),
    [Input("perf-time-filter", "value"), Input("perf-staff-dropdown", "value"), Input("db-refresh-trigger", "children")]
)
def update_smart_analysis(days_filter, selected_staff, refresh):
    df, err = _load_customers_df()
    if err:
        return _error_box(err)
    if "Satış Tarafından Arandı Mı" not in df.columns:
        return _error_box('"Satış Tarafından Arandı Mı" sütunu veritabanında bulunamadı.')

    df_arandi = df[df["Satış Tarafından Arandı Mı"] == 'Evet'].copy()
    if df_arandi.empty or "İşlem Tarihi" not in df_arandi.columns:
        return html.Div("Henüz değerlendirme yapmak için yeterli veri yok.", style={"color": "#666"})

    df_arandi["İşlem Tarihi"] = pd.to_datetime(df_arandi["İşlem Tarihi"], errors='coerce')
    limit_date = pd.Timestamp.now() - pd.Timedelta(days=int(days_filter))
    df_filtered = df_arandi[df_arandi["İşlem Tarihi"] >= limit_date]

    if df_filtered.empty:
        return html.Div("Seçilen tarih aralığında değerlendirilecek arama bulunamadı.", style={"color": "#666"})

    if selected_staff != "HEPSİ" and "İşlem Yapan" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["İşlem Yapan"] == selected_staff]

    total_calls = len(df_filtered)
    if "Kapanış Nedeni" in df_filtered.columns:
        df_kapanis = df_filtered[df_filtered["Kapanış Nedeni"].notna() & (df_filtered["Kapanış Nedeni"] != "")]
    else:
        df_kapanis = pd.DataFrame()
    if not df_kapanis.empty:
        top_reason = df_kapanis["Kapanış Nedeni"].value_counts().idxmax()
        top_count = df_kapanis["Kapanış Nedeni"].value_counts().max()
        reason_insight = f"En çok '{top_reason}' sebebiyle ({top_count} kez) kapanış yapılmış."
    else:
        reason_insight = "Müşterilerin net bir kapanış veya reddedilme sebebi henüz girilmemiş."

    days = int(days_filter)
    daily_avg = total_calls / days if days > 0 else 0

    if selected_staff == "HEPSİ":
        title = "Tüm Ekip Genel Değerlendirme"
        if daily_avg > 5:
            color = "#28a745" 
            yorum = f"Seçilen dönemde toplam {total_calls} arama ile aktif ve yoğun bir performans sergileniyor."
        else:
            color = "#ffc107" 
            yorum = f"Seçilen dönemde toplam {total_calls} arama yapıldı. Arama hacmi artırılabilir."
    else:
        title = f"{selected_staff} - Performans Özeti"
        if daily_avg >= 3: 
            color = "#28a745"
            yorum = f"🌟 Çok İyi: Toplam {total_calls} görüşme ile oldukça yüksek efor sarf ediyor. Motivasyonu desteklenmeli."
        elif daily_avg >= 1:
            color = "#17a2b8" 
            yorum = f"👍 İyi: Toplam {total_calls} arama ile istikrarlı bir ilerleyişi var."
        else:
            color = "#dc3545" 
            yorum = f"⚠️ Gelişime Açık: Toplam {total_calls} aramada kaldı. Görüşme hacmini artırması önerilir."

    return html.Div([
        html.H5(title, style={"fontWeight": "bold", "color": color}),
        html.P(yorum, style={"fontSize": "15px", "color": "#444", "marginTop": "10px"}),
        html.Div([
            html.Span("💡 Sistem İçgörüsü: ", style={"fontWeight": "bold", "color": "#E91B21"}), 
            reason_insight
        ], style={"backgroundColor": "rgba(233, 27, 33, 0.05)", "padding": "15px", "borderRadius": "8px", "borderLeft": "4px solid #E91B21", "marginTop": "15px", "fontSize": "15px"})
    ])