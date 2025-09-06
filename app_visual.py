import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time

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
    </style>
""", unsafe_allow_html=True)

# Gestione della cache in session_state
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'record_count' not in st.session_state:
    st.session_state.record_count = 0

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
        # In caso di errore, mantieni i dati precedenti
        if st.session_state.sheet_data is not None:
            return st.session_state.sheet_data, st.session_state.record_count
        # Dati di esempio per la prima volta
        sample_data = pd.DataFrame({
            "PT": [3, 4, 2, 5, 4, 3],
            "Fantasy": [4, 3, 5, 2, 4, 3],
            "Empathic Concern": [3, 5, 2, 4, 3, 4],
            "Personal Distress": [2, 3, 4, 5, 2, 3]
        })
        return sample_data, len(sample_data)

# 📥 Controlla se è necessario aggiornare i dati (solo ogni 10 minuti)
current_time = time.time()
if current_time - st.session_state.last_update > 600:  # 600 secondi = 10 minuti
    df, record_count = get_sheet_data()
    st.session_state.sheet_data = df
    st.session_state.record_count = record_count
    st.session_state.last_update = current_time
    st.session_state.data_updated = True
else:
    df = st.session_state.sheet_data
    record_count = st.session_state.record_count
    st.session_state.data_updated = False

# 🎨 Genera dati spirali
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6", "#2ecc71", "#f1c40f"]
theta = np.linspace(0, 12 * np.pi, 1200)
spirali = []

for idx, row in df.iterrows():
    # Calcola la media dei punteggi
    scores = [row.get("PT", 3), row.get("Fantasy", 3), 
              row.get("Empathic Concern", 3), row.get("Personal Distress", 3)]
    media = np.mean(scores)
    intensity = np.clip(media / 5, 0.2, 1.0)

    # Frequenza sfarfallio (0.5 - 3 Hz)
    freq = 0.5 + (media / 5) * (3.0 - 0.5)

    r = 0.3 + idx * 0.08
    radius = r * (theta / max(theta)) * intensity * 4.5
    color = palette[idx % len(palette)]

    x = radius * np.cos(theta + idx)
    y = radius * np.sin(theta + idx)

    # Inclinazione alternata
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
        "id": idx
    })

# 📏 Calcolo offset verticale per centratura perfetta
if spirali:
    all_y = np.concatenate([np.array(s["y"]) for s in spirali])
    y_min, y_max = all_y.min(), all_y.max()
    y_range = y_max - y_min
    OFFSET = -0.06 * y_range
    for s in spirali:
        s["y"] = (np.array(s["y"]) + OFFSET).tolist()

data_json = json.dumps({"spirali": spirali})

# 📊 HTML + JS con effetto sfarfallio
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
</style>
</head>
<body>
<div id="graph"></div>
<script>
const DATA = {data_json};
let t0 = Date.now();

function buildTraces(time){{
    const traces = [];
    DATA.spirali.forEach(s => {{
        const step = 4;
        // Calcolo opacità variabile in base alla frequenza
        const flicker = 0.5 + 0.5 * Math.sin(2 * Math.PI * s.freq * time);
        
        for(let j=1; j < s.x.length; j += step){{
            const alpha = (0.2 + 0.7 * (j / s.x.length)) * flicker;
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{color: s.color, width: 1.5 + s.intensity * 3}},
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
render();

// Fullscreen con doppio click
document.addEventListener('dblclick', function() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
    }} else {{
        if (document.exitFullscreen) {{
            document.exitFullscreen();
        }}
    }}
}});
</script>
</body>
</html>
"""

# Mostra la visualizzazione a schermo intero
st.components.v1.html(html_code, height=800, scrolling=False)

# Informazioni nascoste (visibili solo se si scorre)
st.markdown("---")
st.markdown("""
<div style='color: white; text-align: center; padding: 10px;'>
    <p>Opera d'arte generativa "Specchio Empatico"</p>
    <p>Scansiona il QR code per contribuire con la tua empatia</p>
</div>
""", unsafe_allow_html=True)










