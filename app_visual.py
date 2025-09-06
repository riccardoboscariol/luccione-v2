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

# Carica i dati
df = get_sheet_data()
current_data_hash = str(hash(str(df.values.tobytes()))) if not df.empty else "empty"

# Verifica se ci sono nuove spirale
new_spiral_detected = False
if current_data_hash != st.session_state.last_data_hash:
    if len(df) > len(st.session_state.sheet_data):
        st.session_state.new_spiral_time = time.time()
        new_spiral_detected = True
        st.success("✨ Nuova spirale rilevata! (Aggiornamento senza refresh)")
    
    st.session_state.sheet_data = df
    st.session_state.last_data_hash = current_data_hash

# Genera le spirali
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
theta = np.linspace(0, 10 * np.pi, 800)
spirali = []

for idx, row in df.iterrows():
    scores = [row.get("PT", 3), row.get("Fantasy", 3), 
              row.get("Empathic Concern", 3), row.get("Personal Distress", 3)]
    media = np.mean(scores)
    
    size_factor = 0.3 + (media / 5) * 0.7
    intensity = np.clip(size_factor, 0.4, 1.0)
    freq = 0.8 + size_factor * (2.5 - 0.8)

    std_dev = np.std(scores) if len(scores) > 1 else 0
    coherence = 1 - min(std_dev / 1.5, 1)
    
    dominant_dim = np.argmax(scores) if len(scores) > 0 else 0
    base_color = palette[dominant_dim % len(palette)]
    
    if coherence > 0.6: 
        color = base_color
    else:
        color = fade_color(base_color, (0.6 - coherence) * 1.2)

    r = 0.4 + size_factor * 0.4
    radius = r * (theta / max(theta)) * 4.0

    x = radius * np.cos(theta + idx * 0.7)
    y = radius * np.sin(theta + idx * 0.7)

    if len(scores) >= 4:
        pattern_score = (scores[0] - scores[2]) + (scores[1] - scores[3])
        if pattern_score > 0.8: 
            y_proj = y * 0.5 + x * 0.25
        elif pattern_score < -0.8: 
            y_proj = y * 0.5 - x * 0.25
        else: 
            y_proj = y * 0.6
    else: 
        y_proj = y * 0.6

    is_new = (new_spiral_detected and idx >= len(st.session_state.sheet_data) - (len(df) - len(st.session_state.sheet_data)) and 
              time.time() - st.session_state.new_spiral_time < 10)

    spirali.append({
        "x": x.tolist(), "y": y_proj.tolist(), "color": color,
        "intensity": float(intensity), "freq": float(freq), "id": idx,
        "is_new": is_new, "base_color": base_color
    })

# Calcolo offset
if spirali:
    all_y = np.concatenate([np.array(s["y"]) for s in spirali])
    y_min, y_max = all_y.min(), all_y.max()
    y_range = y_max - y_min
    OFFSET = -0.05 * y_range
    for s in spirali: 
        s["y"] = (np.array(s["y"]) + OFFSET).tolist()

st.session_state.current_spirals = spirali
data_json = json.dumps({"spirali": spirali})

# URL corretto per l'immagine da GitHub
FRAME_IMAGE_URL = "https://raw.githubusercontent.com/riccardoboscariol/luccione-v2/main/frame.png"

# 📊 HTML + JS con immagine in basso a destra
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
    background: rgba(255,255,255,0.3);
    color: white;
    border: none;
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 24px;
}}
#fullscreen-btn:hover {{
    background: rgba(255,255,255,0.5);
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
    width: 80px;
    height: 80px;
    border-radius: 12px;
    border: 2px solid rgba(255,255,255,0.4);
    box-shadow: 0 0 25px rgba(0,0,0,0.6);
    transition: all 0.3s ease;
    opacity: 0.85;
    object-fit: cover;
    background: rgba(0,0,0,0.3);
    backdrop-filter: blur(5px);
}}
#logo:hover {{
    transform: scale(1.15);
    opacity: 1;
    box-shadow: 0 0 35px rgba(255,255,255,0.3);
    border-color: rgba(255,255,255,0.6);
}}
/* Responsive per schermi piccoli */
@media (max-width: 768px) {{
    #logo {{
        width: 60px;
        height: 60px;
        bottom: 15px;
        right: 15px;
    }}
}}
/* Stile per fullscreen */
:fullscreen #logo {{
    width: 100px;
    height: 100px;
    bottom: 25px;
    right: 25px;
    border-width: 3px;
}}
/* Loading state per immagine */
.logo-loading {{
    background: linear-gradient(45deg, #333, #666, #333);
    animation: loadingShine 1.5s infinite;
}}
@keyframes loadingShine {{
    0% {{ background-position: -200px 0; }}
    100% {{ background-position: 200px 0; }}
}}
</style>
</head>
<body>
<div id="graph-container">
    <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
    <div id="status">Spirali: {len(df)} | Ultimo agg: {time.strftime('%H:%M:%S')}</div>
    <img id="logo" src="{FRAME_IMAGE_URL}" 
         alt="Luccione Project" 
         title="Luccione Project - Specchio Empatico"
         onload="this.classList.remove('logo-loading')"
         onerror="this.style.display='none'">
    <div id="graph"></div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();
let isFullscreen = false;

// Aggiungi classe loading iniziale
document.getElementById('logo').classList.add('logo-loading');

// Memorizza lo stato del fullscreen
if (localStorage.getItem('wasFullscreen') === 'true') {{
    setTimeout(() => {{
        if (!document.fullscreenElement) {{
            document.getElementById('graph-container').requestFullscreen().catch(() => {{}});
        }}
    }}, 1000);
}}

function toggleFullscreen() {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen()
            .then(() => {{
                isFullscreen = true;
                localStorage.setItem('wasFullscreen', 'true');
                updateLogoSize();
            }})
            .catch(err => {{}});
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
            isFullscreen = false;
            localStorage.setItem('wasFullscreen', 'false');
            updateLogoSize();
        }}
    }}
}}

function updateLogoSize() {{
    const logo = document.getElementById('logo');
    if (document.fullscreenElement) {{
        logo.style.width = '100px';
        logo.style.height = '100px';
    }} else {{
        logo.style.width = '80px';
        logo.style.height = '80px';
    }}
}}

function buildTraces(time){{
    const traces = [];
    const currentTime = Date.now();
    
    DATA.spirali.forEach(s => {{
        const step = 3;
        const flicker = 0.6 + 0.4 * Math.sin(2 * Math.PI * s.freq * time);
        
        let pulseEffect = 0;
        let glowColor = s.color;
        let lineWidth = 2 + s.intensity * 4;
        
        // EFFETTO NUOVA SPIRALE
        if (s.is_new) {{
            const pulseTime = (currentTime - t0) / 1000;
            const pulseSpeed = 15;
            
            pulseEffect = 10 * Math.sin(pulseTime * pulseSpeed * Math.PI * 2);
            lineWidth += Math.abs(pulseEffect) * 2;
            
            const pulsePhase = Math.sin(pulseTime * pulseSpeed * Math.PI);
            if (pulsePhase > 0.8) {{
                glowColor = '#FFFFFF';
                lineWidth += 15;
            }} else if (pulsePhase > 0.4) {{
                glowColor = '#FFD700';
                lineWidth += 10;
            }} else {{
                glowColor = s.color;
                lineWidth += 6;
            }}
        }}
        
        for(let j=1; j < s.x.length; j += step){{
            const segmentProgress = j / s.x.length;
            const alpha = (0.3 + 0.6 * segmentProgress) * flicker;
            
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{
                    color: glowColor, 
                    width: lineWidth,
                    shape: 'spline'
                }},
                opacity: Math.max(0.2, alpha),
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
    isFullscreen = !!document.fullscreenElement;
    localStorage.setItem('wasFullscreen', isFullscreen.toString());
    updateLogoSize();
}});

// Aggiorna stato ogni 5 secondi
setInterval(() => {{
    document.getElementById('status').textContent = 
        `Spirali: {len(df)} | Ultimo agg: ${{new Date().toLocaleTimeString()}}`;
}}, 5000);
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# LEGENDA
st.markdown("---")
st.markdown("## 🎨 LEGENDA DELL'OPERA")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🎯 Dimensioni Empathic**")
    st.markdown("- 🔴 Perspective Taking")
    st.markdown("- 🟠 Fantasy")  
    st.markdown("- 🔵 Empathic Concern")
    st.markdown("- 🟣 Personal Distress")

with col2:
    st.markdown("**✨ Nuove Spirale**")
    st.markdown("- 💥 Pulsazione ultra-rapida")
    st.markdown("- 🌟 Cambiamento colore (bianco/oro)")
    st.markdown("- 📏 Ingrandimento evidente")
    st.markdown("- ⏱️ Durata: 10 secondi")

st.markdown("---")
st.markdown("**🖼️ Logo Luccione Project**")
st.markdown("- **Posizione**: Fisso in basso a destra")
st.markdown("- **Dimensioni**: 80px (100px in fullscreen)")
st.markdown("- **Effetti**: Hover, ombra, bordo luminoso")
st.markdown("- **URL**: [frame.png](https://github.com/riccardoboscariol/luccione-v2/blob/main/frame.png)")

st.success("✅ Immagine frame.png caricata correttamente da GitHub!")







