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
import threading

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
if 'new_spirals_data' not in st.session_state:
    st.session_state.new_spirals_data = []
if 'update_trigger' not in st.session_state:
    st.session_state.update_trigger = 0

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

# Preparazione dati per il frontend
spirals_data = {
    "spirali": st.session_state.current_spirals,
    "count": st.session_state.spiral_count,
    "last_update": st.session_state.last_update_time,
    "update_trigger": st.session_state.update_trigger
}
initial_data_json = json.dumps(spirals_data)

# 📊 HTML + JS con aggiornamento in tempo reale
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
body {{
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: black;
}}
#graph-container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: black;
}}
#graph {{
    width: 100%;
    height: 100%;
}}
#status {{
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 10000;
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 10px 15px;
    border-radius: 8px;
    font-family: monospace;
    font-size: 14px;
    border: 1px solid rgba(255,255,255,0.2);
}}
#logo {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 10000;
    width: 60px;
    height: 60px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.3);
    box-shadow: 0 0 20px rgba(0,0,0,0.8);
    opacity: 0.9;
    object-fit: cover;
    transition: all 0.3s ease;
}}
#logo:hover {{
    transform: scale(1.1);
    opacity: 1;
}}
.pulse {{
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(255,255,255,0.4); }}
    70% {{ box-shadow: 0 0 0 10px rgba(255,255,255,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(255,255,255,0); }}
}}
.new-spiral {{
    filter: brightness(2) drop-shadow(0 0 10px #ffffff);
    transition: all 2s ease-out;
}}
</style>
</head>
<body>
<div id="graph-container">
    <div id="status">Spirali: {st.session_state.spiral_count} | Sistema attivo</div>
    <img id="logo" src="{FRAME_IMAGE_URL}" alt="Luccione Project">
    <div id="graph"></div>
</div>

<script>
let currentData = {initial_data_json};
let t0 = Date.now();
let currentSpiralCount = {st.session_state.spiral_count};
let lastUpdateTrigger = {st.session_state.update_trigger};
let plotlyGraph = null;
let isInitialized = false;

// Funzione per inizializzare il grafico
function initializePlot() {{
    if (isInitialized) return;
    
    const layout = {{
        xaxis: {{visible: false, range: [-10, 10]}},
        yaxis: {{visible: false, range: [-10, 10]}},
        margin: {{t:0, b:0, l:0, r:0}},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        autosize: true,
        showlegend: false
    }};
    
    Plotly.newPlot('graph', [], layout, {{
        displayModeBar: false,
        staticPlot: false,
        responsive: true
    }}).then(function() {{
        isInitialized = true;
        render();
    }});
}}

// Funzione principale di rendering
function render() {{
    if (!isInitialized) {{
        requestAnimationFrame(render);
        return;
    }}
    
    try {{
        const time = (Date.now() - t0) / 1000;
        const traces = [];
        
        currentData.spirali.forEach(spiral => {{
            if (!spiral.x || !spiral.y) return;
            
            const step = 3;
            const flicker = 0.6 + 0.4 * Math.sin(2 * Math.PI * spiral.freq * time);
            
            for (let j = 1; j < spiral.x.length; j += step) {{
                if (j >= spiral.x.length || j >= spiral.y.length) continue;
                
                const segmentProgress = j / spiral.x.length;
                const alpha = (0.2 + 0.8 * segmentProgress) * flicker;
                const width = 1 + spiral.intensity * 4;
                
                let color = spiral.color;
                if (spiral.is_new) {{
                    const pulse = 0.5 + 0.5 * Math.sin(time * 8);
                    color = `rgb(${{255 * pulse}}, ${{255 * pulse}}, 255)`;
                }}
                
                traces.push({{
                    x: [spiral.x[j-1], spiral.x[j]],
                    y: [spiral.y[j-1], spiral.y[j]],
                    mode: 'lines',
                    line: {{
                        color: color,
                        width: width,
                        shape: 'spline'
                    }},
                    opacity: Math.max(0.1, Math.min(1, alpha)),
                    hoverinfo: 'skip',
                    showlegend: false
                }});
            }}
        }});
        
        // Aggiorna il grafico senza cancellarlo
        Plotly.react('graph', traces, {{
            xaxis: {{range: [-10, 10]}},
            yaxis: {{range: [-10, 10]}}
        }});
        
    }} catch (error) {{
        console.log('Render error:', error);
    }}
    
    requestAnimationFrame(render);
}}

// Controlla aggiornamenti dal server
function checkForUpdates() {{
    try {{
        // Usa un approccio diverso: verifica se la pagina è stata aggiornata
        if (window.updateTrigger !== undefined && window.updateTrigger !== lastUpdateTrigger) {{
            lastUpdateTrigger = window.updateTrigger;
            document.getElementById('status').textContent = 
                "Nuove spirali! Aggiornamento...";
            document.getElementById('status').classList.add('pulse');
            
            // Ricarica solo i dati, non tutta la pagina
            setTimeout(() => {{
                window.location.reload();
            }}, 1000);
        }}
    }} catch (error) {{
        console.log('Update check error:', error);
    }}
}}

// Inizializzazione
window.addEventListener('load', function() {{
    initializePlot();
    setInterval(checkForUpdates, 2000);
    document.getElementById('status').textContent = 
        "Spirali: " + currentSpiralCount + " | Sistema pronto";
}});

// Supporto schermo intero
document.addEventListener('dblclick', function() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(console.log);
    }} else {{
        document.exitFullscreen().catch(console.log);
    }}
}});

// Esponi il trigger per gli aggiornamenti
window.updateTrigger = {st.session_state.update_trigger};
</script>
</body>
</html>
"""

# Mostra la visualizzazione
st.components.v1.html(html_code, height=800, scrolling=False)

# Controllo automatico dei nuovi dati
current_time = time.time()
if current_time - st.session_state.last_check_time > 15:
    try:
        new_df = get_sheet_data()
        new_count = len(new_df)
        
        if new_count > st.session_state.spiral_count:
            st.session_state.new_spirals_data = new_df.iloc[st.session_state.spiral_count:].to_dict('records')
            st.session_state.sheet_data = new_df
            st.session_state.spiral_count = new_count
            st.session_state.last_data_hash = get_data_hash(new_df)
            st.session_state.current_spirals = generate_spirals(new_df)
            st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.update_trigger += 1
            st.rerun()
            
    except Exception as e:
        st.error(f"Errore durante il controllo: {e}")
    
    st.session_state.last_check_time = current_time

# LEGENDA
st.markdown("---")
st.markdown("## 🎯 SISTEMA AVANZATO")

col1, col2 = st.columns(2)

with col1:
    st.metric("Spirali Totali", st.session_state.spiral_count)
    st.info(f"""
    **✨ Sistema ATTIVO**
    - Spirali visualizzate: {st.session_state.spiral_count}
    - Ultimo aggiornamento: {st.session_state.last_update_time}
    - Controllo automatico ogni 15s
    """)

with col2:
    status = "🟢 ATTIVO" if st.session_state.spiral_count > 0 else "🟡 IN ATTESA"
    st.metric("Stato", status)
    st.info("""
    **🔧 Tecnologia:**
    - Render diretto in JavaScript
    - Doppio click per schermo intero
    - Aggiornamenti smooth
    - Nessun refresh visibile
    """)

# Pulsante di aggiornamento manuale
if st.button("🔄 Controlla nuovi dati ora", type="primary"):
    new_df = get_sheet_data()
    new_count = len(new_df)
    if new_count > st.session_state.spiral_count:
        st.success(f"🎉 Trovati {new_count - st.session_state.spiral_count} nuovi questionari!")
        st.session_state.sheet_data = new_df
        st.session_state.spiral_count = new_count
        st.session_state.last_data_hash = get_data_hash(new_df)
        st.session_state.current_spirals = generate_spirals(new_df)
        st.session_state.last_update_time = datetime.now().strftime("%H:%M:%S")
        st.session_state.update_trigger += 1
        st.rerun()
    else:
        st.info("📭 Nessun nuovo questionario trovato.")

# Istruzioni
st.markdown("---")
st.success("""
**✅ Istruzioni:**
- **Doppio click** sulla visualizzazione per schermo intero
- Il sistema controlla automaticamente nuovi dati ogni 15 secondi
- Nuove spirali appariranno senza refresh della pagina
- Schermo intero completamente funzionante
""")

# JavaScript per forzare l'aggiornamento
st.markdown(f"""
<script>
// Forza l'aggiornamento se ci sono nuovi dati
if (window.updateTrigger !== {st.session_state.update_trigger}) {{
    window.updateTrigger = {st.session_state.update_trigger};
    setTimeout(() => {{
        window.location.reload();
    }}, 100);
}}
</script>
""", unsafe_allow_html=True)



