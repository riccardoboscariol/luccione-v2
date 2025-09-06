import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time
import colorsys
from streamlit_autorefresh import st_autorefresh

# 🔄 Auto-refresh ogni 15 secondi (più frequente)
st_autorefresh(interval=15000, key="data_refresh")

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
    
    /* Loading indicator */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        color: white;
        font-size: 24px;
    }
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
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'record_count' not in st.session_state:
    st.session_state.record_count = 0
if 'new_spiral_id' not in st.session_state:
    st.session_state.new_spiral_id = -1
if 'spiral_highlight_time' not in st.session_state:
    st.session_state.spiral_highlight_time = 0
if 'last_data_hash' not in st.session_state:
    st.session_state.last_data_hash = ""
if 'current_spirals' not in st.session_state:
    st.session_state.current_spirals = []
if 'is_initialized' not in st.session_state:
    st.session_state.is_initialized = False

def get_sheet_data():
    """Recupera i dati dal foglio Google con gestione degli errori"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["credentials"])
        if isinstance(creds_dict, str):
            creds_dict = json.loads(creds_dict)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key("16amhP4JqU5GsGg253F2WJn9rZQIpx1XsP3BHIwXq1EA").sheet1
        records = sheet.get_all_records()
        
        return pd.DataFrame(records), len(records)
    
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {str(e)}")
        return pd.DataFrame(), 0

# Mostra loading indicator durante l'aggiornamento
if not st.session_state.is_initialized:
    st.markdown("""
    <div class="loading-overlay">
        <div>🔄 Caricamento opera...</div>
    </div>
    """, unsafe_allow_html=True)

# 📥 Aggiorna dati in background
current_time = time.time()
if current_time - st.session_state.last_update > 10:  # 10 secondi tra gli aggiornamenti
    df, record_count = get_sheet_data()
    
    # Calcola hash per verificare cambiamenti
    current_data_hash = str(hash(str(df.values.tobytes()))) if not df.empty else "empty"
    
    if current_data_hash != st.session_state.last_data_hash:
        new_spiral_detected = False
        
        if st.session_state.sheet_data is not None and len(df) > len(st.session_state.sheet_data):
            st.session_state.new_spiral_id = len(st.session_state.sheet_data)
            st.session_state.spiral_highlight_time = current_time
            new_spiral_detected = True
        
        st.session_state.sheet_data = df
        st.session_state.record_count = len(df)
        st.session_state.last_data_hash = current_data_hash
        st.session_state.last_update = current_time
        
        # Rigenera le spirali solo se i dati sono cambiati
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
                      current_time - st.session_state.spiral_highlight_time < 15)

            spirali.append({
                "x": x.tolist(), "y": y_proj.tolist(), "color": color,
                "intensity": float(intensity), "freq": float(freq), "id": idx,
                "is_new": is_new, "base_color": base_color, "media": float(media)
            })

        # Calcolo offset verticale
        if spirali:
            all_y = np.concatenate([np.array(s["y"]) for s in spirali])
            y_min, y_max = all_y.min(), all_y.max()
            y_range = y_max - y_min
            OFFSET = -0.05 * y_range
            for s in spirali: 
                s["y"] = (np.array(s["y"]) + OFFSET).tolist()

        st.session_state.current_spirals = spirali
        st.session_state.is_initialized = True

# Usa le spirali dalla session state
spirali = st.session_state.current_spirals
data_json = json.dumps({"spirali": spirali})

# 📊 HTML + JS con aggiornamento senza ricaricare
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
    margin-bottom: 20px;
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
let currentTraces = [];
let explosionActive = false;

function toggleFullscreen() {{
    const container = document.getElementById('graph-container');
    if (!document.fullscreenElement) {{
        container.requestFullscreen().catch(err => {{}});
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}}

function createExplosionParticles(x, y, intensity) {{
    if (explosionActive) return;
    explosionActive = true;
    
    const container = document.getElementById('graph-container');
    const particleCount = 80 + intensity * 120;
    
    for (let i = 0; i < particleCount; i++) {{
        const particle = document.createElement('div');
        particle.className = 'explosion-particle';
        
        const size = 10 + Math.random() * 25 * intensity;
        const angle = Math.random() * Math.PI * 2;
        const distance = 100 + Math.random() * 250 * intensity;
        const duration = 1200 + Math.random() * 1800;
        const delay = Math.random() * 300;
        
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = (x - size/2) + 'px';
        particle.style.top = (y - size/2) + 'px';
        particle.style.opacity = '1';
        particle.style.transform = 'scale(0)';
        particle.style.background = 'radial-gradient(circle, #ffffff 0%, #ffeb3b 30%, transparent 70%)';
        
        container.appendChild(particle);
        
        // Animazione con delay casuale per effetto più naturale
        setTimeout(() => {{
            particle.animate([
                {{
                    transform: 'scale(0) translate(0, 0)',
                    opacity: 1,
                    filter: 'blur(0px) brightness(8)'
                }},
                {{
                    transform: 'scale(6) translate(0, 0)',
                    opacity: 0.9,
                    filter: 'blur(8px) brightness(12)'
                }},
                {{
                    transform: `scale(1) translate(${{Math.cos(angle) * distance}}px, ${{Math.sin(angle) * distance}}px)`,
                    opacity: 0,
                    filter: 'blur(20px) brightness(1)'
                }}
            ], {{
                duration: duration,
                easing: 'cubic-bezier(0.1, 0.8, 0.2, 1)'
            }});
            
            setTimeout(() => {{
                if (particle.parentNode) {{
                    particle.parentNode.removeChild(particle);
                }}
                if (i === particleCount - 1) {{
                    explosionActive = false;
                }}
            }}, duration);
        }}, delay);
    }}
}}

function buildTraces(time){{
    const traces = [];
    const currentTime = Date.now();
    let hasNewSpiral = false;
    let newSpiralData = null;
    
    DATA.spirali.forEach(s => {{
        const step = 3;
        const flicker = 0.6 + 0.4 * Math.sin(2 * Math.PI * s.freq * time);
        
        let explosionEffect = 0;
        let glowColor = s.color;
        let lineWidth = 2 + s.intensity * 4;
        
        if (s.is_new) {{
            hasNewSpiral = true;
            newSpiralData = s;
            const explosionProgress = Math.min(1, (currentTime - t0) / 2500);
            
            if (explosionProgress < 0.3) {{
                glowColor = '#ffffff';
                explosionEffect = 30 * (1 - explosionProgress/0.3);
                lineWidth += explosionEffect;
                
                if (explosionProgress < 0.1) {{
                    const centerX = (Math.max(...s.x) + Math.min(...s.x)) / 2;
                    const centerY = (Math.max(...s.y) + Math.min(...s.y)) / 2;
                    createExplosionParticles(centerX, centerY, s.intensity);
                }}
                
            }} else if (explosionProgress < 0.6) {{
                const goldProgress = (explosionProgress - 0.3) / 0.3;
                glowColor = goldProgress < 0.5 ? '#ffffff' : '#ffeb3b';
                explosionEffect = 20 * (1 - goldProgress);
                lineWidth += explosionEffect;
                
            }} else if (explosionProgress < 0.9) {{
                const colorProgress = (explosionProgress - 0.6) / 0.3;
                const r = Math.floor(255 * colorProgress + 255 * (1-colorProgress));
                const g = Math.floor(235 * colorProgress + 255 * (1-colorProgress));
                const b = Math.floor(59 * colorProgress + 255 * (1-colorProgress));
                glowColor = `rgb(${{r}}, ${{g}}, ${{b}})`;
                explosionEffect = 12 * (1 - colorProgress);
                lineWidth += explosionEffect;
                
            }} else {{
                glowColor = s.color;
                explosionEffect = 4 * (1 - (explosionProgress-0.9)/0.1);
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
    
    // Aggiorna solo se ci sono cambiamenti
    if (JSON.stringify(traces) !== JSON.stringify(currentTraces)) {{
        currentTraces = traces;
        
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
    }}
    
    requestAnimationFrame(render);
}}

// Inizia il rendering
t0 = Date.now();
render();

// Fullscreen con doppio click
document.addEventListener('dblclick', function() {{
    toggleFullscreen();
}});

// Previeni il ricaricamento della pagina
window.addEventListener('beforeunload', function(e) {{
    if (document.fullscreenElement) {{
        e.preventDefault();
        e.returnValue = '';
    }}
}});
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=700, scrolling=False)

# LEGENDA
st.markdown("---")
st.markdown("## 🎨 LEGENDA DELL'OPERA 'SPECCHIO EMPATICO'")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### **🎯 Dimensioni Empathic**")
    st.markdown("- **🔴 Perspective Taking**: Capacità di mettersi nei panni altrui")
    st.markdown("- **🟠 Fantasy**: Identificazione con personaggi e storie")  
    st.markdown("- **🔵 Empathic Concern**: Compassione e preoccupazione per gli altri")
    st.markdown("- **🟣 Personal Distress**: Disagio emotivo di fronte alla sofferenza")

with col2:
    st.markdown("### **✨ Caratteristiche Visive**")
    st.markdown("- **Dimensione**: Maggiore empatia → Spirale più grande")
    st.markdown("- **Colore**: Dominanza di una dimensione empatica")
    st.markdown("- **Saturazione**: Colori puri = risposte coerenti")
    st.markdown("- **Scintillio**: Nuove spirale con esplosione di luce")

st.markdown("---")
st.markdown(f"**⚡ LIVE** - Ultimo aggiornamento: {time.strftime('%H:%M:%S')} - Spirali: {len(st.session_state.sheet_data)}")







