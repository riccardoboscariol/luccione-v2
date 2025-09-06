import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time
import colorsys

# 🖥 Configurazione Streamlit
st.set_page_config(page_title="Specchio Empatico - Opera", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    html, body, [class*="css"] {
        margin: 0;
        padding: 0;
        height: 100%;
        width: 100%;
        background-color: black;
        overflow: hidden;
    }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .stApp {
        overflow: hidden;
    }
    iframe {
        height: 100vh !important;
        width: 100vw !important;
        border: none;
    }
    /* Nascondi tutto tranne la visualizzazione */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Checkbox style */
    .stCheckbox > label {
        color: white !important;
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Funzione per desaturare i colori
def fade_color(hex_color, fade_factor):
    """Desatura un colore in base al fattore di fade (0-1)"""
    try:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Converti RGB a HSL
        r, g, b = [x/255.0 for x in rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        
        # Riduci la saturazione
        s = max(0.3, s * (1 - fade_factor * 0.7))
        
        # Converti nuovamente a RGB
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        
        # Ritorna in HEX
        return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
    except:
        return hex_color  # Fallback al colore originale

# Gestione della cache in session_state
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'record_count' not in st.session_state:
    st.session_state.record_count = 0

def get_sheet_data():
    """Recupera i dati dal foglio Google con gestione degli errori"""
    try:
        # 🔐 Connessione Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["credentials"])
        if isinstance(creds_dict, str):
            creds_dict = json.loads(creds_dict)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Apri il foglio e recupera i dati
        sheet = client.open_by_key("16amhP4JqU5GsGg253F2WJn9rZQIpx1XsP3BHIwXq1EA").sheet1
        records = sheet.get_all_records()
        
        return pd.DataFrame(records), len(records)
    
    except Exception as e:
        # In caso di errore, mantieni i dati precedenti
        if st.session_state.sheet_data is not None:
            return st.session_state.sheet_data, st.session_state.record_count
        # Dati di esempio per la prima volta
        sample_data = pd.DataFrame({
            "PT": [3, 4, 2, 5, 4, 3],
            "Fantasy": [4, 3, 5, 2, 4, 3],
            "Empathic Concern": [3, 5, 2, 4, 3, 4],
            "Personal Distress": [2, 3, 4, 5, 2, 3]
        })
        return sample_data, len(sample_data)

# 📥 Controlla se è necessario aggiornare i dati (solo ogni 10 minuti)
current_time = time.time()
if current_time - st.session_state.last_update > 600:  # 600 secondi = 10 minuti
    df, record_count = get_sheet_data()
    st.session_state.sheet_data = df
    st.session_state.record_count = record_count
    st.session_state.last_update = current_time
    st.session_state.data_updated = True
else:
    df = st.session_state.sheet_data
    record_count = st.session_state.record_count
    st.session_state.data_updated = False

# 🎨 Genera dati spirali
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
theta = np.linspace(0, 12 * np.pi, 1200)
spirali = []

for idx, row in df.iterrows():
    # Calcola la media dei punteggi
    scores = [row.get("PT", 3), row.get("Fantasy", 3), 
              row.get("Empathic Concern", 3), row.get("Personal Distress", 3)]
    media = np.mean(scores)
    
    # 1. DIMENSIONE: spirali più grandi per punteggi più alti
    size_factor = media / 5  # 0.2-1.0
    intensity = np.clip(size_factor, 0.2, 1.0)

    # 2. FREQUENZA: pulsazione più veloce per punteggi più alti
    freq = 0.5 + size_factor * (3.0 - 0.5)

    # 3. COLORE: basato sulla coerenza tra le 4 dimensioni
    std_dev = np.std(scores)  # Deviazione standard tra le dimensioni
    coherence = 1 - min(std_dev / 2, 1)  # 0-1, dove 1 = massima coerenza
    
    # Scegli il colore in base alla dimensione predominante
    dominant_dim = np.argmax(scores)
    base_color = palette[dominant_dim % len(palette)]
    
    # Modifica la saturazione in base alla coerenza
    if coherence > 0.7:  # Alta coerenza
        color = base_color  # Colore puro e saturo
    else:  # Bassa coerenza
        # Desatura il colore in base all'incoerenza
        color = fade_color(base_color, 1 - coherence)

    # 4. RAGGIO: dimensioni proporzionali al punteggio
    r = 0.2 + size_factor * 0.3  # Base + proporzionale al punteggio
    radius = r * (theta / max(theta)) * 5.0  # Moltiplicatore aumentato

    x = radius * np.cos(theta + idx)
    y = radius * np.sin(theta + idx)

    # 5. FORMA: inclinazione basata sul pattern di risposte
    pattern_score = (scores[0] - scores[2]) + (scores[1] - scores[3])  # PT-EC + Fantasy-PD
    if pattern_score > 1:
        y_proj = y * 0.4 + x * 0.3  # Inclinazione marcata destra
    elif pattern_score < -1:
        y_proj = y * 0.4 - x * 0.3  # Inclinazione marcata sinistra
    else:
        y_proj = y * 0.5  # Quasi verticale (bilanciato)

    spirali.append({
        "x": x.tolist(),
        "y": y_proj.tolist(),
        "color": color,
        "intensity": float(intensity),
        "freq": float(freq),
        "id": idx,
        "size_factor": float(size_factor),
        "coherence": float(coherence)
    })

# 📏 Calcolo offset verticale per centratura perfetta
if spirali:
    all_y = np.concatenate([np.array(s["y"]) for s in spirali])
    y_min, y_max = all_y.min(), all_y.max()
    y_range = y_max - y_min
    OFFSET = -0.06 * y_range
    for s in spirali:
        s["y"] = (np.array(s["y"]) + OFFSET).tolist()

data_json = json.dumps({"spirali": spirali})

# 📊 HTML + JS con effetto sfarfallio
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
body {{ 
    margin: 0; 
    padding: 0; 
    background: black; 
    overflow: hidden;
    width: 100vw;
    height: 100vh;
}}
#graph {{ 
    width: 100vw; 
    height: 100vh; 
    position: fixed;
    top: 0;
    left: 0;
}}
.legend {{
    position: fixed;
    bottom: 20px;
    left: 20px;
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 15px;
    border-radius: 10px;
    z-index: 1000;
    max-width: 300px;
    border: 1px solid #333;
}}
.legend h3 {{
    margin-top: 0;
    color: #fff;
    border-bottom: 1px solid #444;
    padding-bottom: 8px;
}}
.legend-item {{
    margin: 8px 0;
    display: flex;
    align-items: center;
}}
.color-dot {{
    width: 15px;
    height: 15px;
    border-radius: 50%;
    margin-right: 10px;
    display: inline-block;
}}
</style>
</head>
<body>
<div id="graph"></div>

<div class="legend">
    <h3>🎨 Legenda dell'Opera</h3>
    <div class="legend-item">
        <span class="color-dot" style="background: white"></span>
        <span>Dimensione: Maggiore empatia → Spirale più grande</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: #e84393"></span>
        <span>Perspective Taking</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: #e67e22"></span>
        <span>Fantasy</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: #3498db"></span>
        <span>Empathic Concern</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: #9b59b6"></span>
        <span>Personal Distress</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: linear-gradient(to right, #e84393, #cccccc)"></span>
        <span>Saturazione: Colori puri → Risposte coerenti</span>
    </div>
    <div class="legend-item">
        <span class="color-dot" style="background: white; animation: pulse 1s infinite"></span>
        <span>Pulsazione: Più veloce → Maggiore intensità</span>
    </div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();

function buildTraces(time){{
    const traces = [];
    DATA.spirali.forEach(s => {{
        const step = 4;
        // Calcolo opacità variabile in base alla frequenza
        const flicker = 0.5 + 0.5 * Math.sin(2 * Math.PI * s.freq * time);
        
        // Aggiungi glow effect per spirali con alta coerenza
        const glow = s.coherence > 0.8 ? 3 : 0;
        
        for(let j=1; j < s.x.length; j += step){{
            const alpha = (0.2 + 0.7 * (j / s.x.length)) * flicker;
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{
                    color: s.color, 
                    width: 1.5 + s.intensity * 3 + glow,
                    shape: 'spline'
                }},
                opacity: Math.max(0, alpha),
                hoverinfo: "none",
                showlegend: false,
                type: "scatter"
            }});
        }}
    }});
    return traces;
}}

function render(){{
    const time = (Date.now() - t0) / 1000;
    const traces = buildTraces(time);
    const layout = {{
        xaxis: {{visible: false, autorange: true, scaleanchor: 'y'}},
        yaxis: {{visible: false, autorange: true}},
        margin: {{t:0,b:0,l:0,r:0}},
        paper_bgcolor: 'black',
        plot_bgcolor: 'black',
        autosize: true
    }};
    Plotly.react('graph', traces, layout, {{
        displayModeBar: false,
        scrollZoom: false,
        responsive: true,
        staticPlot: false
    }});
    
    requestAnimationFrame(render);
}}

// Inizia il rendering
render();

// Fullscreen con doppio click
document.addEventListener('dblclick', function() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}});
</script>
</body>
</html>
"""

# Mostra la visualizzazione a schermo intero
st.components.v1.html(html_code, height=800, scrolling=False)

# Checkbox per mostrare/nascondere l'analisi dati
show_analysis = st.checkbox("📊 Mostra analisi dati collettivi", False, key="analysis_toggle")

if show_analysis:
    st.markdown("---")
    st.subheader("Analisi Collettiva dell'Empatia")
    
    # Calcola statistiche
    if not df.empty:
        avg_scores = {{
            "Perspective Taking": df["PT"].mean(),
            "Fantasy": df["Fantasy"].mean(),
            "Empathic Concern": df["Empathic Concern"].mean(),
            "Personal Distress": df["Personal Distress"].mean()
        }}
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Partecipanti Totali", len(df))
            st.metric("💫 Empatia Media", f"{np.mean(list(avg_scores.values())):.2f}/5")
            
        with col2:
            st.write("**📈 Medie per Dimensioni:**")
            for dim, score in avg_scores.items():
                st.write(f"{dim}: {score:.2f}/5")
        
        with col3:
            st.write("**🎯 Interpretazione:**")
            overall_avg = np.mean(list(avg_scores.values()))
            if overall_avg > 4.0:
                st.success("Alta empatia collettiva")
            elif overall_avg > 3.0:
                st.info("Empatia media collettiva")
            else:
                st.warning("Empatia bassa collettiva")
        
        # Visualizza distribuzione
        st.bar_chart(avg_scores)
    else:
        st.info("Nessun dato disponibile per l'analisi")

# Informazioni nascoste (visibili solo se si scorre)
st.markdown("---")
st.markdown("""
<div style='color: white; text-align: center; padding: 10px;'>
    <p>Opera d'arte generativa "Specchio Empatico"</p>
    <p>Scansiona il QR code per contribuire con la tua empatia</p>
</div>
""", unsafe_allow_html=True)





