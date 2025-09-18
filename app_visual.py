import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time
import colorsys
import hashlib
from datetime import datetime

# 🔄 Auto-refresh ogni 10 secondi
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 10:
    st.session_state.last_refresh = time.time()
    st.rerun()

# 🖥 Configurazione Streamlit
st.set_page_config(page_title="Specchio Empatico - Opera", layout="wide")
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
        background: black;
    }
    /* Nascondi elementi non necessari */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Funzione per desaturare i colori
def fade_color(hex_color, fade_factor):
    """Desatura un colore in base al fattore de fade (0-1)"""
    try:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = [x/255.0 for x in rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        s = max(0.4, s * (1 - fade_factor * 0.6))
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
    except:
        return hex_color

# Inizializzazione session state
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = pd.DataFrame()
if 'last_data_hash' not in st.session_state:
    st.session_state.last_data_hash = ""
if 'current_spirals' not in st.session_state:
    st.session_state.current_spirals = []
if 'spiral_count' not in st.session_state:
    st.session_state.spiral_count = 0
if 'last_check_time' not in st.session_state:
    st.session_state.last_check_time = time.time()
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")

# Funzione per ottenere i dati
def get_sheet_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["credentials"])
        if isinstance(creds_dict, str):
            creds_dict = json.loads(creds_dict)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("16amhP4JqU5GsGg253F2WJn9rZQIpx1XsP3BHIwXq1EA").sheet1
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Errore nel recupero dati: {e}")
        return pd.DataFrame()

# Funzione per generare un hash dei dati
def get_data_hash(df):
    return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()

# Funzione per generare le spirali
def generate_spirals(df):
    palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
    theta = np.linspace(0, 12 * np.pi, 1200)
    spirali = []

    for idx, row in df.iterrows():
        scores = [row.get("PT", 3), row.get("Fantasy", 3), 
                  row.get("Empathic Concern", 3), row.get("Personal Distress", 3)]
        media = np.mean(scores)
        
        size_factor = media / 5
        intensity = np.clip(size_factor, 0.2, 1.0)
        freq = 0.5 + (media / 5) * (3.0 - 0.5)

        std_dev = np.std(scores) if len(scores) > 1 else 0
        coherence = 1 - min(std_dev / 2, 1)
        
        dominant_dim = np.argmax(scores) if len(scores) > 0 else 0
        base_color = palette[dominant_dim % len(palette)]
        
        if coherence > 0.7:
            color = base_color
        else:
            color = fade_color(base_color, 1 - coherence)

        r = 0.3 + idx * 0.08
        radius = r * (theta / max(theta)) * intensity * 4.5

        x = radius * np.cos(theta + idx)
        y = radius * np.sin(theta + idx)

        if idx % 2 == 0:
            y_proj = y * 0.5 + x * 0.2
        else:
            y_proj = y * 0.5 - x * 0.2

        spirali.append({
            "x": x.tolist(), "y": y_proj.tolist(), "color": color,
            "intensity": float(intensity), "freq": float(freq), "id": idx,
            "base_color": base_color
        })

    if spirali:
        all_y = np.concatenate([np.array(s["y"]) for s in spirali])
        y_min, y_max = all_y.min(), all_y.max()
        y_range = y_max - y_min
        OFFSET = -0.06 * y_range
        for s in spirali: 
            s["y"] = (np.array(s["y"]) + OFFSET).tolist()
    
    return spirali

# Carica i dati iniziali
df = get_sheet_data()
initial_count = len(df)
st.session_state.spiral_count = initial_count
st.session_state.sheet_data = df
st.session_state.last_data_hash = get_data_hash(df)

# Genera le spirali
spirali = generate_spirals(df)
st.session_state.current_spirals = spirali

# Controllo automatico dei nuovi dati
current_time = time.time()
if current_time - st.session_state.last_check_time > 10:
    try:
        new_df = get_sheet_data()
        new_hash = get_data_hash(new_df)
        
        if new_hash != st.session_state.last_data_hash:
            st.session_state.sheet_data = new_df
            st.session_state.spiral_count = len(new_df)
            st.session_state.last_data_hash = new_hash
            st.session_state.current_spirals = generate_spirals(new_df)
            st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.last_check_time = current_time
            st.rerun()
        else:
            st.session_state.last_check_time = current_time
            
    except Exception as e:
        st.session_state.last_check_time = current_time

# Preparazione dati per il frontend
spirals_data = {
    "spirali": st.session_state.current_spirals,
    "count": st.session_state.spiral_count
}
data_json = json.dumps(spirals_data)

# 📊 HTML + JS con effetto sfarfallio migliorato
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
body {{ 
    margin: 0; 
    padding: 0; 
    background: #000000;
    overflow: hidden;
    font-family: 'Arial', sans-serif;
}}
#graph-container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: #000000;
}}
#graph {{ 
    width: 100%;
    height: 100%;
}}
#fullscreen-btn {{
    position: absolute;
    top: 15px;
    right: 15px;
    z-index: 10000;
    background: rgba(255, 255, 255, 0.15);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 20px;
    backdrop-filter: blur(5px);
    transition: all 0.3s ease;
}}
#fullscreen-btn:hover {{
    background: rgba(255, 255, 255, 0.25);
    transform: scale(1.05);
}}
#info-panel {{
    position: absolute;
    top: 15px;
    left: 15px;
    z-index: 10000;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(5px);
    font-size: 14px;
}}
.glow-text {{
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}}
:fullscreen {{
    cursor: none;
}}
/* Effetti di luce */
.light-pulse {{
    animation: lightPulse 3s ease-in-out infinite;
}}
@keyframes lightPulse {{
    0% {{ opacity: 0.3; }}
    50% {{ opacity: 0.7; }}
    100% {{ opacity: 0.3; }}
}}
</style>
</head>
<body>
<div id="graph-container">
    <div id="info-panel" class="light-pulse">
        <span class="glow-text">Spirali: {st.session_state.spiral_count}</span>
    </div>
    <button id="fullscreen-btn">⛶</button>
    <div id="graph"></div>
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
        
        for(let j = 1; j < s.x.length; j += step){{
            const segmentProgress = j / s.x.length;
            const alpha = (0.2 + 0.7 * segmentProgress) * flicker;
            
            // Effetto glow per le spirali più intense
            const glow = s.intensity > 0.8 ? 2 : 0;
            
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{
                    color: s.color, 
                    width: 1.8 + s.intensity * 3.5 + glow,
                    shape: 'spline'
                }},
                opacity: Math.max(0.1, Math.min(0.95, alpha)),
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
        margin: {{t:0, b:0, l:0, r:0}},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
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

// Gestione fullscreen
document.getElementById('fullscreen-btn').addEventListener('click', () => {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen().catch(err => {{
            console.log('Error attempting to enable fullscreen:', err);
        }});
    }} else {{
        document.exitFullscreen();
    }}
}});

// Aggiorna il contatore ogni 5 secondi
setInterval(() => {{
    document.querySelector('.glow-text').textContent = `Spirali: {st.session_state.spiral_count}`;
}}, 5000);

// Effetto di entrata
setTimeout(() => {{
    document.getElementById('info-panel').style.animation = 'none';
}}, 3000);
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# ℹ️ Caption + descrizione artistica
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 2rem;'>
    <h3 style='color: #e84393; margin-bottom: 1rem;'>🎨 SPECCHIO EMPATICO</h3>
    <p style='opacity: 0.8; font-style: italic;'>
        Ogni spirale rappresenta un individuo, pulsante al ritmo della sua empatia.<br>
        L'inclinazione alternata e lo sfarfallio personalizzato creano un'opera viva e ritmica.
    </p>
    <p style='margin-top: 1rem; font-size: 0.9rem; opacity: 0.6;'>
        ⛶ Premi per il fullscreen totale • 🔄 Auto-aggiornamento ogni 10s
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧭 *Empatia come consapevolezza dell'impatto*

> *"L'empatia non è solo sentire l'altro, ma riconoscere il proprio impatto sul mondo e sulla realtà condivisa. È un atto di presenza responsabile."*

**Interpretazione visiva:**  
- **Colori vibranti**: Diverse dimensioni dell'empatia  
- **Sfarfallio ritmico**: Intensità emotiva individuale  
- **Spirali intrecciate**: Connessioni empatiche tra partecipanti  
- **Movimento fluido**: Natura dinamica delle relazioni umane
""")


