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
    }
    .block-container {
        padding: 2rem !important;
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
    """Desatura un colore in base al fattore di fade (0-1)"""
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
if 'auto_check_interval' not in st.session_state:
    st.session_state.auto_check_interval = 15

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
            "base_color": base_color, "is_new": False
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

# URL corretto per l'immagine
FRAME_IMAGE_URL = "https://raw.githubusercontent.com/riccardoboscariol/luccione-v2/main/frame.png"

# Controllo automatico dei nuovi dati - PRIMA del rendering HTML
current_time = time.time()
if current_time - st.session_state.last_check_time > st.session_state.auto_check_interval:
    try:
        new_df = get_sheet_data()
        new_count = len(new_df)
        new_hash = get_data_hash(new_df)
        
        if new_hash != st.session_state.last_data_hash:
            st.success(f"🎉 Trovati {new_count - st.session_state.spiral_count} nuovi questionari!")
            st.session_state.sheet_data = new_df
            st.session_state.spiral_count = new_count
            st.session_state.last_data_hash = new_hash
            st.session_state.current_spirals = generate_spirals(new_df)
            st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.update_trigger += 1
            st.session_state.last_check_time = current_time
            st.rerun()
        else:
            st.session_state.last_check_time = current_time
            
    except Exception as e:
        st.error(f"Errore durante il controllo: {e}")
        st.session_state.last_check_time = current_time

# Preparazione dati per il frontend
spirals_data = {
    "spirali": st.session_state.current_spirals,
    "count": st.session_state.spiral_count,
    "last_update": st.session_state.last_update_time,
    "update_trigger": st.session_state.update_trigger,
    "next_check": st.session_state.last_check_time + st.session_state.auto_check_interval
}
initial_data_json = json.dumps(spirals_data)

# 📊 HTML + JS con Canvas 2D personalizzato
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<style>
body {{
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #000000;
    font-family: Arial, sans-serif;
}}
#container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: #000000;
}}
#canvas {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}}
#status {{
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 1000;
    background: rgba(0, 0, 0, 0.8);
    color: #ffffff;
    padding: 10px 15px;
    border-radius: 8px;
    font-size: 14px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(5px);
}}
#logo {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
    width: 60px;
    height: 60px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.8);
    opacity: 0.9;
    object-fit: cover;
    transition: all 0.3s ease;
}}
#logo:hover {{
    transform: scale(1.1);
    opacity: 1;
}}
#fullscreen-btn {{
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
    backdrop-filter: blur(5px);
}}
#fullscreen-btn:hover {{
    background: rgba(255, 255, 255, 0.2);
}}
.pulse {{
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4); }}
    70% {{ box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }}
}}
</style>
</head>
<body>
<div id="container">
    <canvas id="canvas"></canvas>
    <div id="status">Spirali: {st.session_state.spiral_count} | Auto-aggiornamento: ATTIVO</div>
    <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
    <img id="logo" src="{FRAME_IMAGE_URL}" alt="Luccione Project">
</div>

<script>
// Dati iniziali
let currentData = {initial_data_json};
let spirals = currentData.spirali || [];
let currentSpiralCount = {st.session_state.spiral_count};
let lastUpdateTrigger = {st.session_state.update_trigger};
let nextCheckTime = {st.session_state.last_check_time + st.session_state.auto_check_interval};

// Elementi DOM
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const statusElement = document.getElementById('status');

// Variabili di rendering
let t0 = Date.now();
let animationId = null;

// Inizializzazione canvas
function initCanvas() {{
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}}

// Funzione di rendering
function render() {{
    const currentTime = Date.now();
    const elapsedTime = (currentTime - t0) / 1000;
    
    // Sfondo nero
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const scale = Math.min(canvas.width, canvas.height) / 20;
    
    // Renderizza spirali
    spirals.forEach(spiral => {{
        if (!spiral.x || !spiral.y) return;
        
        const flicker = 0.6 + 0.4 * Math.sin(2 * Math.PI * spiral.freq * elapsedTime);
        const baseAlpha = spiral.intensity * 0.8;
        
        ctx.beginPath();
        
        for (let i = 0; i < spiral.x.length; i += 2) {{
            if (i >= spiral.x.length || i >= spiral.y.length) continue;
            
            const x = centerX + spiral.x[i] * scale;
            const y = centerY + spiral.y[i] * scale;
            
            if (i === 0) {{
                ctx.moveTo(x, y);
            }} else {{
                ctx.lineTo(x, y);
            }}
        }}
        
        let lineWidth = 1 + spiral.intensity * 3;
        let glowColor = spiral.color;
        
        if (spiral.is_new) {{
            const pulse = 0.5 + 0.5 * Math.sin(elapsedTime * 8);
            lineWidth *= (1 + pulse);
            glowColor = 'rgb(255, 255, 255)';
        }}
        
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = lineWidth;
        ctx.globalAlpha = baseAlpha * flicker;
        ctx.stroke();
    }});
    
    ctx.globalAlpha = 1;
    animationId = requestAnimationFrame(render);
}}

// Schermo intero
function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
    }} else {{
        document.exitFullscreen();
    }}
}}

// Gestione resize
function handleResize() {{
    initCanvas();
}}

// Aggiorna il contatore di tempo
function updateStatus() {{
    const now = Date.now() / 1000;
    const timeLeft = Math.max(0, nextCheckTime - now);
    const minutes = Math.floor(timeLeft / 60);
    const seconds = Math.floor(timeLeft % 60);
    
    statusElement.textContent = `Spirali: ${{currentSpiralCount}} | Prossimo controllo: ${{minutes}}m ${{seconds}}s`;
}}

// Controlla aggiornamenti
function checkForUpdates() {{
    const now = Date.now() / 1000;
    
    if (now >= nextCheckTime) {{
        statusElement.textContent = "Controllo nuovi dati...";
        statusElement.classList.add('pulse');
        
        // Forza il refresh per controllare nuovi dati
        setTimeout(() => {{
            window.location.reload();
        }}, 1500);
        
        // Resetta il timer
        nextCheckTime = now + {st.session_state.auto_check_interval};
    }}
    
    updateStatus();
}}

// Inizializzazione
window.addEventListener('load', function() {{
    initCanvas();
    render();
    
    // Controllo aggiornamenti ogni secondo
    setInterval(checkForUpdates, 1000);
    
    // Aggiorna status iniziale
    updateStatus();
    
    // Verifica se ci sono aggiornamenti pendenti
    if (window.updateTrigger !== undefined && window.updateTrigger !== lastUpdateTrigger) {{
        statusElement.textContent = "Aggiornamento in corso...";
        setTimeout(() => {{
            window.location.reload();
        }}, 1000);
    }}
}});

window.addEventListener('resize', handleResize);

// Eventi fullscreen
document.addEventListener('fullscreenchange', handleResize);

// Doppio click per fullscreen
canvas.addEventListener('dblclick', toggleFullscreen);

// Esponi il trigger per aggiornamenti
window.updateTrigger = {st.session_state.update_trigger};
window.currentSpiralCount = {st.session_state.spiral_count};
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# LEGENDA
st.markdown("---")
st.markdown("## 🎯 SISTEMA AUTO-AGGIORNAMENTO")

col1, col2 = st.columns(2)

with col1:
    st.metric("Spirali Totali", st.session_state.spiral_count)
    next_check = st.session_state.last_check_time + st.session_state.auto_check_interval
    time_left = max(0, next_check - time.time())
    st.metric("Prossimo controllo", f"{int(time_left)}s")
    st.info(f"""
    **✨ Sistema ATTIVO**
    - Controllo ogni {st.session_state.auto_check_interval}s
    - Ultimo aggiornamento: {st.session_state.last_update_time}
    - Sfondo nero garantito
    """)

with col2:
    status = "🟢 ATTIVO" if st.session_state.spiral_count > 0 else "🟡 IN ATTESA"
    st.metric("Stato", status)
    st.info("""
    **🔧 Tecnologia:**
    - Controllo automatico ogni 15s
    - Refresh automatico quando nuovi dati
    - Canvas 2D nativo
    - Schermo intero funzionante
    """)

# Pulsante di aggiornamento manuale
if st.button("🔄 Controlla nuovi dati ora", type="primary"):
    new_df = get_sheet_data()
    new_count = len(new_df)
    new_hash = get_data_hash(new_df)
    
    if new_hash != st.session_state.last_data_hash:
        st.success(f"🎉 Trovati {new_count - st.session_state.spiral_count} nuovi questionari!")
        st.session_state.sheet_data = new_df
        st.session_state.spiral_count = new_count
        st.session_state.last_data_hash = new_hash
        st.session_state.current_spirals = generate_spirals(new_df)
        st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
        st.session_state.update_trigger += 1
        st.session_state.last_check_time = time.time()
        st.rerun()
    else:
        st.info("📭 Nessun nuovo questionario trovato.")
        st.session_state.last_check_time = time.time()

# Configurazione intervallo di controllo
st.slider("Intervallo di controllo (secondi)", 5, 60, st.session_state.auto_check_interval, 5, 
          key="auto_check_interval", help="Imposta ogni quanti secondi controllare nuovi dati")

# Istruzioni
st.markdown("---")
st.success("""
**✅ Istruzioni:**
- **Doppio click** sulla visualizzazione per schermo intero
- **Click sul pulsante ⛶** per schermo intero
- **ESC** per uscire dallo schermo intero
- Il sistema controlla automaticamente ogni 15 secondi
- I nuovi dati appariranno automaticamente dopo il refresh
""")

# JavaScript per forzare l'aggiornamento se necessario
st.markdown(f"""
<script>
// Forza l'aggiornamento se ci sono nuovi dati
if (window.updateTrigger !== {st.session_state.update_trigger} || window.currentSpiralCount !== {st.session_state.spiral_count}) {{
    setTimeout(() => {{
        window.location.reload();
    }}, 500);
}}
</script>
""", unsafe_allow_html=True)


