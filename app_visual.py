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
        s = max(0.4, s * (1 - fade_factor * 0.6))
        
        # Converti nuovamente a RGB
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        
        # Ritorna in HEX
        return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
    except:
        return hex_color

# Gestione della cache in session_state
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'record_count' not in st.session_state:
    st.session_state.record_count = 0
if 'new_spiral_id' not in st.session_state:
    st.session_state.new_spiral_id = -1
if 'spiral_highlight_time' not in st.session_state:
    st.session_state.spiral_highlight_time = 0

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
        if st.session_state.sheet_data is not None:
            return st.session_state.sheet_data, st.session_state.record_count
        sample_data = pd.DataFrame({
            "PT": [4, 3, 5, 4],
            "Fantasy": [3, 4, 3, 4],
            "Empathic Concern": [4, 3, 4, 3],
            "Personal Distress": [3, 4, 3, 4]
        })
        return sample_data, len(sample_data)

# 📥 Controlla se è necessario aggiornare i dati
current_time = time.time()
new_spiral_detected = False

if current_time - st.session_state.last_update > 300:
    df, record_count = get_sheet_data()
    
    if st.session_state.sheet_data is not None and len(df) > len(st.session_state.sheet_data):
        st.session_state.new_spiral_id = len(st.session_state.sheet_data)
        st.session_state.spiral_highlight_time = current_time
        new_spiral_detected = True
    
    st.session_state.sheet_data = df
    st.session_state.record_count = record_count
    st.session_state.last_update = current_time
else:
    df = st.session_state.sheet_data
    record_count = st.session_state.record_count

# 🎨 Genera dati spirali
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
theta = np.linspace(0, 10 * np.pi, 1000)
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

    is_new = (idx == st.session_state.new_spiral_id and 
              current_time - st.session_state.spiral_highlight_time < 10)

    spirali.append({
        "x": x.tolist(),
        "y": y_proj.tolist(),
        "color": color,
        "intensity": float(intensity),
        "freq": float(freq),
        "id": idx,
        "is_new": is_new,
        "base_color": base_color
    })

# 📏 Calcolo offset verticale
if spirali:
    all_y = np.concatenate([np.array(s["y"]) for s in spirali])
    y_min, y_max = all_y.min(), all_y.max()
    y_range = y_max - y_min
    OFFSET = -0.05 * y_range
    for s in spirali:
        s["y"] = (np.array(s["y"]) + OFFSET).tolist()

data_json = json.dumps({"spirali": spirali})

# 📊 HTML + JS con effetto esplosione di luce
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
#fullscreen-btn {{
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    background: rgba(255,255,255,0.3);
    color: white;
    border: none;
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 24px;
    backdrop-filter: blur(5px);
}}
#fullscreen-btn:hover {{
    background: rgba(255,255,255,0.5);
}}
.legend {{
    position: fixed;
    bottom: 20px;
    left: 20px;
    background: rgba(0,0,0,0.85);
    color: white;
    padding: 15px;
    border-radius: 12px;
    z-index: 1000;
    max-width: 320px;
    border: 1px solid #444;
}}
.legend h3 {{
    margin-top: 0;
    color: #fff;
    border-bottom: 2px solid #666;
    padding-bottom: 10px;
    margin-bottom: 12px;
}}
.legend-item {{
    margin: 10px 0;
    display: flex;
    align-items: center;
    font-size: 14px;
}}
.color-dot {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    margin-right: 12px;
    display: inline-block;
    flex-shrink: 0;
}}
@keyframes lightExplosion {{
    0% {{ 
        filter: brightness(1) drop-shadow(0 0 0px rgba(255,255,255,0));
        opacity: 1;
    }}
    50% {{ 
        filter: brightness(5) drop-shadow(0 0 30px gold) drop-shadow(0 0 60px white);
        opacity: 1;
    }}
    100% {{ 
        filter: brightness(1) drop-shadow(0 0 0px rgba(255,255,255,0));
        opacity: 1;
    }}
}}
.exploding {{
    animation: lightExplosion 2s ease-out;
}}
</style>
</head>
<body>
<button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
<div id="graph"></div>

<div class="legend">
    <h3>🎨 Legenda dell'Opera</h3>
    <div class="legend-item">
        <span class="color-dot" style="background: white"></span>
        <span><strong>Dimensione:</strong> Maggiore empatia → Spirale più grande</span>
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
        <span class="color-dot" style="background: gold; animation: lightExplosion 2s infinite"></span>
        <span><strong>Esplosione di luce:</strong> Nuova spirale appena aggiunta!</span>
    </div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();
let lastRenderTime = 0;
const explosionDuration = 2000; // 2 secondi

function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(err => {{
            console.log('Fullscreen error:', err);
        }});
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
        const step = 3;
        const flicker = 0.6 + 0.4 * Math.sin(2 * Math.PI * s.freq * time);
        
        let explosionEffect = 0;
        let glowColor = s.color;
        
        if (s.is_new) {{
            const explosionProgress = Math.min(1, (currentTime - t0) / explosionDuration);
            if (explosionProgress < 1) {{
                // Effetto esplosione di luce
                explosionEffect = 15 * (1 - Math.pow(explosionProgress - 1, 2));
                glowColor = '#ffffff'; // Bianco puro durante l'esplosione
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
                    width: 2 + s.intensity * 4 + explosionEffect,
                    shape: 'spline'
                }},
                opacity: Math.max(0.1, alpha),
                hoverinfo: "none",
                showlegend: false,
                type: "scatter"
            }});
            
            // Aggiungi particelle di luce durante l'esplosione
            if (s.is_new && explosionEffect > 0 && j % 20 === 0) {{
                const particleSize = 8 + Math.random() * 12;
                const particleX = s.x[j];
                const particleY = s.y[j];
                
                traces.push({{
                    x: [particleX],
                    y: [particleY],
                    mode: "markers",
                    marker: {{
                        color: '#ffffff',
                        size: particleSize,
                        opacity: 0.8 * (1 - explosionProgress),
                        line: {{
                            color: '#ffeb3b',
                            width: 2
                        }}
                    }},
                    hoverinfo: "none",
                    showlegend: false
                }});
            }}
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
    toggleFullscreen();
}});

// Ascolta cambiamenti fullscreen
document.addEventListener('fullscreenchange', function() {{
    if (document.fullscreenElement) {{
        document.getElementById('fullscreen-btn').textContent = '⛶';
    }} else {{
        document.getElementById('fullscreen-btn').textContent = '⛶';
    }}
}});
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# Informazioni
st.markdown("---")
st.markdown("""
<div style='color: white; text-align: center; padding: 15px; background: rgba(0,0,0,0.8); border-radius: 10px; margin: 10px;'>
    <h3>✨ Opera "Specchio Empatico"</h3>
    <p>Ogni nuova partecipazione crea un'esplosione di luce dorata</p>
    <p>Click sul pulsante ⛶ o doppio click per schermo intero</p>
</div>
""", unsafe_allow_html=True)






