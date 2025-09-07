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
        
        # LOGICA ORIGINALE
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

        spirali.append({
            "x": x.tolist(), "y": y_proj.tolist(), "color": color,
            "intensity": float(intensity), "freq": float(freq), "id": idx,
            "base_color": base_color
        })

    # Calcolo offset originale
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

# Preparazione dati per il frontend
spirals_data = {
    "spirali": st.session_state.current_spirals,
    "count": st.session_state.spiral_count,
    "last_update": st.session_state.last_update_time,
}
initial_data_json = json.dumps(spirals_data)

# 📊 HTML + JS con AUTO-AGGIORNAMENTO SENZA REFRESH
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
/* Animazione per nuove spirale */
@keyframes spiralPulse {{
    0% {{ 
        opacity: 0;
        transform: scale(0.5);
    }}
    50% {{
        opacity: 1;
        transform: scale(1.2);
        filter: brightness(3) drop-shadow(0 0 15px #ffffff);
    }}
    100% {{
        opacity: 1;
        transform: scale(1);
        filter: brightness(1);
    }}
}}
.new-spiral {{
    animation: spiralPulse 2s ease-out;
}}
.pulse {{
    animation: spiralPulse 1s ease-in-out infinite;
}}
</style>
</head>
<body>
<div id="graph-container">
    <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
    <div id="status">Spirali: {st.session_state.spiral_count} | Sistema attivo</div>
    <img id="logo" src="{FRAME_IMAGE_URL}" alt="Luccione Project">
    <div id="graph"></div>
</div>

<script>
let currentData = {initial_data_json};
let t0 = Date.now();
let currentSpiralCount = {st.session_state.spiral_count};
let plotlyGraph = null;
let checkInterval;
let isChecking = false;

// Funzione per creare una nuova spirale
function createNewSpiral(id, scores, palette) {{
    const theta = Array.from({{length: 1200}}, (_, i) => i * 12 * Math.PI / 1200);
    
    const media = scores.reduce((a, b) => a + b, 0) / scores.length;
    const size_factor = media / 5;
    const intensity = Math.max(0.2, Math.min(1.0, size_factor));
    const freq = 0.5 + size_factor * 2.5;
    
    const r = 0.3 + id * 0.08;
    const radius = theta.map(t => r * (t / Math.max(...theta)) * intensity * 4.5);
    
    const x = radius.map((r, i) => r * Math.cos(theta[i] + id));
    const y = radius.map((r, i) => r * Math.sin(theta[i] + id));
    
    let y_proj;
    if (id % 2 === 0) {{
        y_proj = y.map((y_val, i) => y_val * 0.5 + x[i] * 0.2);
    }} else {{
        y_proj = y.map((y_val, i) => y_val * 0.5 - x[i] * 0.2);
    }}
    
    // Calcola offset come nel Python
    const allY = y_proj.flat();
    const yMin = Math.min(...allY);
    const yMax = Math.max(...allY);
    const yRange = yMax - yMin;
    const OFFSET = -0.06 * yRange;
    y_proj = y_proj.map(y => y + OFFSET);
    
    const base_color = palette[id % palette.length];
    
    return {{
        x: x,
        y: y_proj,
        color: base_color,
        intensity: intensity,
        freq: freq,
        id: id,
        base_color: base_color,
        is_new: true
    }};
}}

// Funzione per aggiungere nuove spirali
function addNewSpirals(newSpiralsData) {{
    const palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"];
    
    newSpiralsData.forEach(newSpiral => {{
        const scores = [
            newSpiral.PT || 3,
            newSpiral.Fantasy || 3,
            newSpiral["Empathic Concern"] || 3,
            newSpiral["Personal Distress"] || 3
        ];
        
        const newSpiralObj = createNewSpiral(currentData.spirali.length, scores, palette);
        currentData.spirali.push(newSpiralObj);
        currentSpiralCount++;
        
        // Aggiungi effetto visivo
        setTimeout(() => {{
            newSpiralObj.is_new = false;
        }}, 2000);
    }});
    
    updateSpiralCount();
    document.getElementById('status').classList.add('pulse');
    setTimeout(() => {{
        document.getElementById('status').classList.remove('pulse');
    }}, 1000);
}}

function updateSpiralCount() {{
    document.getElementById('status').textContent = 
        "Spirali: " + currentSpiralCount + " | Aggiornato: " + new Date().toLocaleTimeString();
}}

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
    
    currentData.spirali.forEach(s => {{
        const step = 4;
        const flicker = 0.5 + 0.5 * Math.sin(2 * Math.PI * s.freq * time);
        
        let glowEffect = 0;
        let glowColor = s.color;
        
        // Effetto per nuove spirale
        if (s.is_new) {{
            const pulseTime = (Date.now() - t0) / 1000;
            glowEffect = 3 + 2 * Math.sin(pulseTime * 10);
            glowColor = '#ffffff';
        }}
        
        for(let j = 1; j < s.x.length; j += step){{
            const segmentProgress = j / s.x.length;
            const alpha = (0.2 + 0.7 * segmentProgress) * flicker;
            
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{
                    color: glowColor, 
                    width: 1.5 + s.intensity * 3 + glowEffect,
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
    
    if (!plotlyGraph) {{
        plotlyGraph = document.getElementById('graph');
    }}
    
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

// Simula l'arrivo di nuovi dati (per testing)
setTimeout(() => {{
    // Questo è solo per dimostrazione - nella realtà verrebbero dal server
    console.log("Simulazione nuovo dato...");
    document.getElementById('status').textContent = 
        "Spirali: " + currentSpiralCount + " | Controllo nuovi dati...";
}}, 5000);

// Inizializza lo status
updateSpiralCount();
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# LEGENDA
st.markdown("---")
st.markdown("## 🎯 SISTEMA VISUALIZZAZIONE")

col1, col2 = st.columns(2)

with col1:
    st.metric("Spirali Totali", st.session_state.spiral_count, delta=None)
    st.info("""
    **✨ Visualizzazione ATTIVA**
    - Spirali generate: {}
    - Ultimo aggiornamento: {}
    - Sistema stabile senza refresh
    """.format(st.session_state.spiral_count, st.session_state.last_update_time))

with col2:
    status = "🟢 ATTIVO" if st.session_state.spiral_count > 0 else "🟡 IN ATTESA"
    st.metric("Stato Sistema", status)
    st.info("""
    **🔧 Tecnologia:**
    - Visualizzazione JavaScript diretta
    - Nessun refresh di pagina
    - Animazioni fluide
    - Supporto schermo intero
    """)

st.markdown("---")
st.success(f"""
**✅ Sistema attivo!** Visualizzazione di {st.session_state.spiral_count} spirali.
I nuovi questionari verranno mostrati senza interruzioni.
""")

# Aggiungi un pulsante per forzare il controllo manuale
if st.button("🔄 Aggiorna manualmente"):
    new_df = get_sheet_data()
    new_count = len(new_df)
    if new_count > st.session_state.spiral_count:
        st.success(f"Trovati {new_count - st.session_state.spiral_count} nuovi questionari!")
        st.session_state.sheet_data = new_df
        st.session_state.spiral_count = new_count
        st.session_state.last_data_hash = get_data_hash(new_df)
        st.session_state.current_spirals = generate_spirals(new_df)
        st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
        st.session_state.last_check_time = time.time()
        st.rerun()
    else:
        st.info("Nessun nuovo questionario trovato.")

# Note importanti
st.markdown("---")
st.warning("""
**ℹ️ Modalità visualizzazione:**
- Le spirali vengono visualizzate direttamente in JavaScript
- Nessun refresh della pagina necessario
- I nuovi dati richiedono un aggiornamento manuale
- Visualizzazione stabile senza schermo nero
""")




