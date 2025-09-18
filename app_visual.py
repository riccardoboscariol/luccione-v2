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
if 'update_trigger' not in st.session_state:
    st.session_state.update_trigger = 0

# Funzione per ottenere i dati dal Google Sheet
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
        
        # Debug: mostra i primi record
        st.sidebar.write("Ultimi dati ricevuti:", records[:2] if records else "Nessun dato")
        
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Errore nel recupero dati: {e}")
        return pd.DataFrame()

# Funzione per generare un hash dei dati
def get_data_hash(df):
    return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()

# Funzione per generare le spirali con movimento dinamico
def generate_spirals(df):
    if df.empty:
        return []
        
    palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
    theta = np.linspace(0, 12 * np.pi, 1200)
    spirali = []

    for idx, row in df.iterrows():
        # Estrai i punteggi dalle colonne del Google Sheet
        scores = [
            row.get("PT", 3), 
            row.get("Fantasy", 3), 
            row.get("Empathic Concern", 3), 
            row.get("Personal Distress", 3)
        ]
        
        # Debug: mostra i punteggi
        if idx == 0:
            st.sidebar.write(f"Prima riga punteggi: {scores}")
        
        media = np.mean(scores)
        size_factor = media / 5
        intensity = np.clip(size_factor, 0.2, 1.0)
        
        # Frequenza basata sulla variabilità
        std_dev = np.std(scores) if len(scores) > 1 else 0
        freq = 0.2 + (std_dev / 2) * 0.8
        
        # Ampiezza del movimento basata sull'intensità
        movement_amp = 0.3 + intensity * 1.2
        
        coherence = 1 - min(std_dev / 2, 1)
        
        dominant_dim = np.argmax(scores) if len(scores) > 0 else 0
        base_color = palette[dominant_dim % len(palette)]
        
        if coherence > 0.7:
            color = base_color
        else:
            color = fade_color(base_color, 1 - coherence)

        # Genera la spirale base
        r = 0.3 + idx * 0.08
        radius = r * (theta / max(theta)) * intensity * 4.5
        x = radius * np.cos(theta + idx)
        y = radius * np.sin(theta + idx)

        # Proiezione per alternanza
        if idx % 2 == 0:
            y_proj = y * 0.5 + x * 0.2
        else:
            y_proj = y * 0.5 - x * 0.2

        spirali.append({
            "x": x.tolist(), 
            "y": y_proj.tolist(), 
            "color": color,
            "intensity": float(intensity), 
            "freq": float(freq),
            "movement_amp": float(movement_amp),
            "id": idx,
            "base_color": base_color,
            "pulse_phase": float(idx * 0.5),
            "rotation_speed": float(0.1 + intensity * 0.3)
        })

    # Centra le spirali
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

# URL per il frame.png (QR code)
FRAME_IMAGE_URL = "https://raw.githubusercontent.com/riccardoboscariol/luccione-v2/main/frame.png"

# Controllo automatico dei nuovi dati
current_time = time.time()
if current_time - st.session_state.last_check_time > 15:
    try:
        new_df = get_sheet_data()
        new_hash = get_data_hash(new_df)
        
        if new_hash != st.session_state.last_data_hash:
            st.session_state.sheet_data = new_df
            st.session_state.spiral_count = len(new_df)
            st.session_state.last_data_hash = new_hash
            st.session_state.current_spirals = generate_spirals(new_df)
            st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.update_trigger += 1
            st.session_state.last_check_time = current_time
            st.rerun()
        else:
            st.session_state.last_check_time = current_time
            
    except Exception as e:
        st.session_state.last_check_time = current_time

# Preparazione dati per il frontend
spirals_data = {
    "spirali": st.session_state.current_spirals,
    "count": st.session_state.spiral_count,
    "update_trigger": st.session_state.update_trigger
}
data_json = json.dumps(spirals_data)

# 📊 HTML + JS con movimento visibile e fullscreen
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
#qr-code {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    z-index: 10000;
    width: 60px;
    height: 60px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.8);
    opacity: 0.9;
    object-fit: cover;
    transition: all 0.3s ease;
}}
#qr-code:hover {{
    transform: scale(1.1);
    opacity: 1;
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
    <img id="qr-code" src="{FRAME_IMAGE_URL}" alt="QR Code">
    <div id="graph"></div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();
let currentTraces = [];

function buildTraces(time){{
    const traces = [];
    
    DATA.spirali.forEach(s => {{
        const step = 3;
        const pulse = 0.6 + 0.4 * Math.sin(2 * Math.PI * s.freq * time + s.pulse_phase);
        const movement = s.movement_amp * Math.sin(2 * Math.PI * s.freq * 0.5 * time + s.id * 0.7);
        const rotation = s.rotation_speed * time;
        
        for(let j = 1; j < s.x.length; j += step){{
            const segmentProgress = j / s.x.length;
            const alpha = (0.3 + 0.6 * segmentProgress) * pulse;
            const glow = s.intensity > 0.7 ? 3 : 1;
            
            // Applica movimento e rotazione
            const moveX = movement * Math.cos(segmentProgress * Math.PI * 2 + rotation);
            const moveY = movement * Math.sin(segmentProgress * Math.PI * 2 + rotation);
            
            const xCoords = [
                s.x[j-1] + moveX * 0.8,
                s.x[j] + moveX
            ];
            
            const yCoords = [
                s.y[j-1] + moveY * 0.8,
                s.y[j] + moveY
            ];
            
            traces.push({{
                x: xCoords,
                y: yCoords,
                mode: "lines",
                line: {{
                    color: s.color, 
                    width: 2 + s.intensity * 4 * pulse + glow,
                    shape: 'spline'
                }},
                opacity: Math.max(0.15, Math.min(0.95, alpha)),
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
        xaxis: {{visible: false, range: [-12, 12], fixedrange: true}},
        yaxis: {{visible: false, range: [-8, 8], fixedrange: true}},
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

// Aggiorna il contatore
setInterval(() => {{
    document.querySelector('.glow-text').textContent = `Spirali: {st.session_state.spiral_count}`;
}}, 5000);

// Nascondi QR code in fullscreen
document.addEventListener('fullscreenchange', function() {{
    const qrCode = document.getElementById('qr-code');
    const infoPanel = document.getElementById('info-panel');
    if (document.fullscreenElement) {{
        qrCode.style.opacity = '0.3';
        infoPanel.style.opacity = '0.5';
    }} else {{
        qrCode.style.opacity = '0.9';
        infoPanel.style.opacity = '1';
    }}
}});

// Doppio click per fullscreen
document.getElementById('graph-container').addEventListener('dblclick', function() {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen();
    }} else {{
        document.exitFullscreen();
    }}
}});

// Auto-refresh ogni 30 secondi per controllare nuovi dati
setTimeout(() => {{
    window.location.reload();
}}, 30000);
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# Sidebar per debug e controllo
with st.sidebar:
    st.title("⚙️ Controllo Opera")
    st.metric("Spirali attive", st.session_state.spiral_count)
    st.metric("Ultimo aggiornamento", st.session_state.last_update_time)
    
    if st.button("🔄 Aggiorna manualmente"):
        new_df = get_sheet_data()
        new_hash = get_data_hash(new_df)
        if new_hash != st.session_state.last_data_hash:
            st.session_state.sheet_data = new_df
            st.session_state.spiral_count = len(new_df)
            st.session_state.last_data_hash = new_hash
            st.session_state.current_spirals = generate_spirals(new_df)
            st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.update_trigger += 1
            st.rerun()
        else:
            st.info("Nessun nuovo dato trovato")
    
    st.info("""
    **📊 Dati Google Sheet:**
    - PT, Fantasy, Empathic Concern, Personal Distress
    - Ogni riga = una spirale
    - Punteggi 1-5 influenzano movimento e colore
    """)

# ℹ️ Descrizione artistica
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 2rem;'>
    <h3 style='color: #e84393; margin-bottom: 1rem;'>🎨 SPECCHIO EMPATICO - OPERA VIVA</h3>
    <p style='opacity: 0.8; font-style: italic;'>
        Ogni spirale danza al ritmo unico delle risposte empatiche.<br>
        Movimento, pulsazione e colore generati in tempo reale dai dati.
    </p>
</div>
""", unsafe_allow_html=True)


