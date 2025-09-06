import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time
import colorsys

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
if 'new_spiral_time' not in st.session_state:
    st.session_state.new_spiral_time = 0
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()

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
        return st.session_state.sheet_data

# Pulsante per aggiornamento manuale
if st.button("🔄 Aggiorna Manualmente", key="manual_refresh"):
    st.session_state.last_data_hash = ""  # Forza aggiornamento
    st.session_state.last_update_time = time.time()
    st.rerun()

# Carica i dati
current_time = time.time()
df = get_sheet_data()
current_data_hash = str(hash(str(df.values.tobytes()))) if not df.empty else "empty"

# Verifica se ci sono nuove spirale
new_spiral_detected = False
spiral_count_change = 0

if current_data_hash != st.session_state.last_data_hash:
    old_count = len(st.session_state.sheet_data) if not st.session_state.sheet_data.empty else 0
    new_count = len(df)
    spiral_count_change = new_count - old_count
    
    if spiral_count_change > 0:
        st.session_state.new_spiral_time = current_time
        new_spiral_detected = True
        st.success(f"✨ {spiral_count_change} nuova(e) spirale(e) aggiunta(e)!")
    
    st.session_state.sheet_data = df
    st.session_state.last_data_hash = current_data_hash
    st.session_state.last_update_time = current_time

# Genera le spirali - ESTETICA ORIGINALE
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
theta = np.linspace(0, 12 * np.pi, 1200)  # Tornato a 1200 punti
spirali = []

for idx, row in df.iterrows():
    scores = [row.get("PT", 3), row.get("Fantasy", 3), 
              row.get("Empathic Concern", 3), row.get("Personal Distress", 3)]
    media = np.mean(scores)
    
    # LOGICA ORIGINALE
    size_factor = media / 5
    intensity = np.clip(size_factor, 0.2, 1.0)
    freq = 0.5 + (media / 5) * (3.0 - 0.5)

    std_dev = np.std(scores) if len(scores) > 1 else 0
    coherence = 1 - min(std_dev / 2, 1)  # Formula originale
    
    dominant_dim = np.argmax(scores) if len(scores) > 0 else 0
    base_color = palette[dominant_dim % len(palette)]
    
    if coherence > 0.7:  # Soglia originale
        color = base_color
    else:
        color = fade_color(base_color, 1 - coherence)

    # Dimensioni originali
    r = 0.3 + idx * 0.08
    radius = r * (theta / max(theta)) * intensity * 4.5

    x = radius * np.cos(theta + idx)
    y = radius * np.sin(theta + idx)

    # Inclinazione alternata originale
    if idx % 2 == 0:
        y_proj = y * 0.5 + x * 0.2
    else:
        y_proj = y * 0.5 - x * 0.2

    is_new = (new_spiral_detected and idx >= len(st.session_state.sheet_data) - spiral_count_change and 
              current_time - st.session_state.new_spiral_time < 10)

    spirali.append({
        "x": x.tolist(), "y": y_proj.tolist(), "color": color,
        "intensity": float(intensity), "freq": float(freq), "id": idx,
        "is_new": is_new, "base_color": base_color
    })

# Calcolo offset originale
if spirali:
    all_y = np.concatenate([np.array(s["y"]) for s in spirali])
    y_min, y_max = all_y.min(), all_y.max()
    y_range = y_max - y_min
    OFFSET = -0.06 * y_range  # Offset originale
    for s in spirali: 
        s["y"] = (np.array(s["y"]) + OFFSET).tolist()

st.session_state.current_spirals = spirali
data_json = json.dumps({"spirali": spirali})

# URL corretto per l'immagine
FRAME_IMAGE_URL = "https://raw.githubusercontent.com/riccardoboscariol/luccione-v2/main/frame.png"

# 📊 HTML + JS - ESTETICA ORIGINALE
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
#graph-container {{
    position: relative;
    width: 100%;
    height: 80vh;
    background: black;
    border-radius: 15px;
    overflow: hidden;
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
    background: rgba(255,255,255,0.2);
    color: white;
    border: none;
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 24px;
}}
#fullscreen-btn:hover {{
    background: rgba(255,255,255,0.3);
}}
#status {{
    position: absolute;
    top: 15px;
    left: 15px;
    z-index: 10000;
    background: rgba(0,0,0,0.7);
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
}}
#logo {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    z-index: 10000;
    width: 60px;
    height: 60px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.3);
    box-shadow: 0 0 15px rgba(0,0,0,0.5);
    transition: all 0.3s ease;
    opacity: 0.8;
    object-fit: cover;
}}
#logo:hover {{
    transform: scale(1.1);
    opacity: 1;
}}
:fullscreen #logo {{
    width: 80px;
    height: 80px;
}}
/* Animazione originale per nuove spirale */
@keyframes pulse {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
    100% {{ opacity: 1; }}
}}
</style>
</head>
<body>
<div id="graph-container">
    <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
    <div id="status">Spirali: {len(df)} | Ultimo agg: {time.strftime('%H:%M:%S')}</div>
    <img id="logo" src="{FRAME_IMAGE_URL}" alt="Luccione Project">
    <div id="graph"></div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();

function toggleFullscreen() {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen().catch(() => {{}});
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}}

function buildTraces(time){{
    const traces = [];
    const currentTime = Date.now();
    
    DATA.spirali.forEach(s => {{
        const step = 4;  // Step originale
        const flicker = 0.5 + 0.5 * Math.sin(2 * Math.PI * s.freq * time);  // Formula originale
        
        let glowEffect = 0;
        let glowColor = s.color;
        
        // EFFETTO ORIGINALE per nuove spirale
        if (s.is_new) {{
            const explosionProgress = Math.min(1, (currentTime - t0) / 15000);
            glowEffect = 3;  // Effetto più sottile
            glowColor = s.base_color;  // Mantieni il colore originale
            
            // Aggiungi glow solo per le nuove
            if (explosionProgress < 0.5) {{
                glowEffect = 5 * (1 - explosionProgress/0.5);
            }}
        }}
        
        for(let j=1; j < s.x.length; j += step){{
            const segmentProgress = j / s.x.length;
            const alpha = (0.2 + 0.7 * segmentProgress) * flicker;  // Formula originale
            
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{
                    color: glowColor, 
                    width: 1.5 + s.intensity * 3 + glowEffect,  // Formula originale
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
t0 = Date.now();
render();

// Gestione fullscreen
document.addEventListener('fullscreenchange', () => {{
    const logo = document.getElementById('logo');
    if (document.fullscreenElement) {{
        logo.style.width = '80px';
        logo.style.height = '80px';
    }} else {{
        logo.style.width = '60px';
        logo.style.height = '60px';
    }}
}});

// Aggiorna l'orario ogni minuto
setInterval(() => {{
    document.getElementById('status').textContent = 
        `Spirali: {len(df)} | Ultimo agg: ${{new Date().toLocaleTimeString()}}`;
}}, 60000);
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# LEGENDA ORIGINALE
st.markdown("---")
st.markdown("## 🎨 LEGENDA DELL'OPERA")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🎯 Dimensioni Empathic**")
    st.markdown("- **🔴 Perspective Taking** - Mettersi nei panni altrui")
    st.markdown("- **🟠 Fantasy** - Identificazione con personaggi")  
    st.markdown("- **🔵 Empathic Concern** - Compassione e preoccupazione")
    st.markdown("- **🟣 Personal Distress** - Disagio emotivo")

with col2:
    st.markdown("**✨ Caratteristiche Visive**")
    st.markdown("- **Dimensione**: Maggiore empatia → Spirale più grande")
    st.markdown("- **Colore**: Dominanza di una dimensione empatica")
    st.markdown("- **Saturazione**: Colori puri = risposte coerenti")
    st.markdown("- **Pulsazione**: Più veloce = maggiore intensità emotiva")

st.markdown("---")
st.markdown(f"**⏰ Ultimo aggiornamento**: {time.strftime('%H:%M:%S')}")
st.markdown(f"**📊 Spirali totali**: {len(df)}")

if spiral_count_change > 0:
    st.markdown(f"**✨ Nuove aggiunte**: {spiral_count_change} spirale(e)")

st.info("""
**🔄 Istruzioni aggiornamento:**
1. Compila il questionario in un'altra finestra
2. Torna qui e clicca **"Aggiorna Manualmente"**
3. Le nuove spirale appariranno con effetto glow
4. Il contatore si aggiornerà immediatamente
""")






