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
    iframe {
        height: 70vh !important;
        width: 100% !important;
        border: none;
        border-radius: 15px;
    }
    /* Nascondi elementi non necessari */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Legenda style */
    .legend-container {
        background: rgba(0,0,0,0.9) !important;
        padding: 25px;
        border-radius: 15px;
        border: 2px solid #333;
        margin: 20px 0;
        color: white;
    }
    .legend-title {
        color: #ffeb3b;
        font-size: 28px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: bold;
    }
    .legend-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin-bottom: 25px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        padding: 12px;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        border-left: 4px solid;
    }
    .color-dot {
        width: 25px;
        height: 25px;
        border-radius: 50%;
        margin-right: 15px;
        display: inline-block;
        flex-shrink: 0;
    }
    .legend-text {
        font-size: 16px;
        line-height: 1.4;
    }
    
    /* Fullscreen button */
    .fullscreen-btn {
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
        backdrop-filter: blur(5px);
    }
    .fullscreen-btn:hover {
        background: rgba(255,255,255,0.5);
    }
    
    /* Animation for explosion */
    @keyframes lightExplosion {
        0% { 
            transform: scale(0.5);
            opacity: 0;
            filter: brightness(20) blur(20px);
        }
        20% { 
            transform: scale(1.5);
            opacity: 1;
            filter: brightness(10) blur(10px);
        }
        50% { 
            transform: scale(2);
            opacity: 0.8;
            filter: brightness(5) blur(5px);
        }
        100% { 
            transform: scale(1);
            opacity: 1;
            filter: brightness(1) blur(0px);
        }
    }
    
    .exploding {
        animation: lightExplosion 2s ease-out;
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
        st.toast("✨ Nuova spirale aggiunta all'opera!", icon="🎨")
    
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
        "base_color": base_color,
        "media": float(media)
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

# 📊 HTML + JS con effetto esplosione di luce MIGLIORATO
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
#graph-container {{
    position: relative;
    width: 100%;
    height: 70vh;
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
    backdrop-filter: blur(5px);
}}
#fullscreen-btn:hover {{
    background: rgba(255,255,255,0.5);
}}
.explosion-particle {{
    position: absolute;
    background: radial-gradient(circle, #ffeb3b 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    z-index: 9999;
}}
</style>
</head>
<body>
<div id="graph-container">
    <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
    <div id="graph"></div>
</div>

<script>
const DATA = {data_json};
let t0 = Date.now();
let explosionParticles = [];

function toggleFullscreen() {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen().catch(err => {{
            console.log('Fullscreen error:', err);
        }});
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}}

function createExplosionParticles(x, y, color, intensity) {{
    const container = document.getElementById('graph-container');
    const particleCount = 30 + intensity * 50;
    
    for (let i = 0; i < particleCount; i++) {{
        const particle = document.createElement('div');
        particle.className = 'explosion-particle';
        
        const size = 5 + Math.random() * 15 * intensity;
        const angle = Math.random() * Math.PI * 2;
        const distance = 50 + Math.random() * 150 * intensity;
        const duration = 800 + Math.random() * 1200;
        
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = (x - size/2) + 'px';
        particle.style.top = (y - size/2) + 'px';
        particle.style.background = `radial-gradient(circle, ${{color}} 0%, transparent 70%)`;
        particle.style.opacity = '0.9';
        particle.style.transform = 'scale(0)';
        
        container.appendChild(particle);
        
        // Animazione particella
        particle.animate([
            {{
                transform: 'scale(0) translate(0, 0)',
                opacity: 0.9,
                filter: 'blur(0px) brightness(3)'
            }},
            {{
                transform: `scale(3) translate(${{Math.cos(angle) * distance}}px, ${{Math.sin(angle) * distance}}px)`,
                opacity: 0,
                filter: 'blur(10px) brightness(1)'
            }}
        ], {{
            duration: duration,
            easing: 'cubic-bezier(0.2, 0, 0.8, 1)'
        }});
        
        // Rimuovi particella dopo l'animazione
        setTimeout(() => {{
            if (particle.parentNode) {{
                particle.parentNode.removeChild(particle);
            }}
        }}, duration);
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
        let lineWidth = 2 + s.intensity * 4;
        
        if (s.is_new) {{
            const explosionProgress = Math.min(1, (currentTime - t0) / 2000);
            
            // Effetto esplosione MIGLIORATO
            if (explosionProgress < 0.2) {{
                // Fase 1: Luce bianca accecante
                glowColor = '#ffffff';
                explosionEffect = 20 * (1 - explosionProgress/0.2);
                lineWidth += explosionEffect;
                
                // Crea particelle al centro della spirale
                if (explosionProgress < 0.05) {{
                    const centerX = (Math.max(...s.x) + Math.min(...s.x)) / 2;
                    const centerY = (Math.max(...s.y) + Math.min(...s.y)) / 2;
                    createExplosionParticles(centerX, centerY, '#ffeb3b', s.intensity);
                }}
                
            }} else if (explosionProgress < 0.5) {{
                // Fase 2: Transizione all'oro
                const goldProgress = (explosionProgress - 0.2) / 0.3;
                glowColor = goldProgress < 0.5 ? '#ffffff' : '#ffeb3b';
                explosionEffect = 10 * (1 - goldProgress);
                lineWidth += explosionEffect;
                
            }} else if (explosionProgress < 0.8) {{
                // Fase 3: Transizione al colore originale
                const colorProgress = (explosionProgress - 0.5) / 0.3;
                const r = Math.floor(255 * colorProgress + 255 * (1-colorProgress));
                const g = Math.floor(235 * colorProgress + 255 * (1-colorProgress));
                const b = Math.floor(59 * colorProgress + 255 * (1-colorProgress));
                glowColor = `rgb(${{r}}, ${{g}}, ${{b}})`;
                explosionEffect = 5 * (1 - colorProgress);
                lineWidth += explosionEffect;
                
            }} else {{
                // Fase 4: Ritorno alla normalità
                glowColor = s.color;
                explosionEffect = 2 * (1 - (explosionProgress-0.8)/0.2);
                lineWidth += explosionEffect;
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
                opacity: Math.max(0.1, alpha),
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

// Fullscreen con doppio click
document.addEventListener('dblclick', function() {{
    toggleFullscreen();
}});

// Ascolta cambiamenti fullscreen
document.addEventListener('fullscreenchange', function() {{
    const btn = document.getElementById('fullscreen-btn');
    if (document.fullscreenElement) {{
        btn.textContent = '⛶';
    }} else {{
        btn.textContent = '⛶';
    }}
}});
</script>
</body>
</html>
"""

# LEGENDA ESTERNA all'opera
st.markdown("""
<div class="legend-container">
    <div class="legend-title">🎨 LEGENDA DELL'OPERA "SPECCHIO EMPATICO"</div>
    
    <div class="legend-grid">
        <div class="legend-item" style="border-left-color: #e84393;">
            <span class="color-dot" style="background: #e84393"></span>
            <div class="legend-text">
                <strong>Perspective Taking</strong><br>
                Capacità di mettersi nei panni altrui
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: #e67e22;">
            <span class="color-dot" style="background: #e67e22"></span>
            <div class="legend-text">
                <strong>Fantasy</strong><br>
                Identificazione con personaggi e storie
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: #3498db;">
            <span class="color-dot" style="background: #3498db"></span>
            <div class="legend-text">
                <strong>Empathic Concern</strong><br>
                Compassione e preoccupazione per gli altri
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: #9b59b6;">
            <span class="color-dot" style="background: #9b59b6"></span>
            <div class="legend-text">
                <strong>Personal Distress</strong><br>
                Disagio emotivo di fronte alla sofferenza
            </div>
        </div>
    </div>
    
    <div class="legend-grid">
        <div class="legend-item" style="border-left-color: white;">
            <span class="color-dot" style="background: white"></span>
            <div class="legend-text">
                <strong>Dimensione della Spirale</strong><br>
                Maggiore è l'empatia, più grande è la spirale
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: gold;">
            <span class="color-dot" style="background: gold; animation: lightExplosion 2s infinite"></span>
            <div class="legend-text">
                <strong>Nuova Spirale</strong><br>
                Esplosione di luce dorata per ogni nuovo contributo
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: #ff6666;">
            <span class="color-dot" style="background: linear-gradient(to right, #e84393, #cccccc)"></span>
            <div class="legend-text">
                <strong>Coerenza</strong><br>
                Colori puri = risposte coerenti tra le dimensioni
            </div>
        </div>
        
        <div class="legend-item" style="border-left-color: #66ff66;">
            <span class="color-dot" style="background: white; animation: pulse 1s infinite"></span>
            <div class="legend-text">
                <strong>Pulsazione</strong><br>
                Più veloce = maggiore intensità emotiva
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Mostra la visualizzazione
st.components.v1.html(html_code, height=700, scrolling=False)

# Informazioni aggiuntive
st.markdown("""
<div style='color: white; text-align: center; padding: 20px; background: rgba(0,0,0,0.8); border-radius: 15px; margin: 20px 0;'>
    <h3 style='color: #ffeb3b;'>✨ COME FUNZIONA L'OPERA</h3>
    <p>Ogni partecipante che compila il questionario aggiunge una nuova spirale</p>
    <p>Le nuove spirale appaiono con una spettacolare <strong>esplosione di luce dorata</strong></p>
    <p>Click sul pulsante ⛶ o doppio click sull'opera per schermo intero</p>
</div>
""", unsafe_allow_html=True)





