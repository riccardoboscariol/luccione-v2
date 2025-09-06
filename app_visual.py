import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
import time

# 🖥 Configurazione Streamlit
st.set_page_config(page_title="Specchio empatico", layout="wide")
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
    }
    iframe {
        height: 100vh !important;
        width: 100vw !important;
    }
    </style>
""", unsafe_allow_html=True)

# Gestione della cache in session_state
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'record_count' not in st.session_state:
    st.session_state.record_count = 0

# Carica i dati di esempio se l'API fallisce
sample_data = pd.DataFrame({
    "PT": [3, 4, 2, 5],
    "Fantasy": [4, 3, 5, 2],
    "Empathic Concern": [3, 5, 2, 4],
    "Personal Distress": [2, 3, 4, 5]
})

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
        st.error(f"Errore nel caricamento dati: {e}")
        st.info("Utilizzo dati di esempio per dimostrazione")
        return sample_data, len(sample_data)

# 📥 Controlla se è necessario aggiornare i dati (solo ogni 5 minuti)
current_time = time.time()
if current_time - st.session_state.last_update > 300:  # 300 secondi = 5 minuti
    with st.spinner("Aggiornamento dati in corso..."):
        df, record_count = get_sheet_data()
        if df is not None:
            st.session_state.sheet_data = df
            st.session_state.record_count = record_count
            st.session_state.last_update = current_time
            st.session_state.data_updated = True
        else:
            # Fallback ai dati precedenti se il fetch fallisce
            st.session_state.data_updated = False
else:
    st.session_state.data_updated = False

# Usa i dati dalla cache se disponibili
if st.session_state.sheet_data is not None:
    df = st.session_state.sheet_data
    record_count = st.session_state.record_count
else:
    # Prima esecuzione, carica i dati
    df, record_count = get_sheet_data()
    st.session_state.sheet_data = df
    st.session_state.record_count = record_count
    st.session_state.last_update = current_time

# 🆕 Identifica nuove risposte
new_responses = []
if st.session_state.data_updated:
    # Evidenzia solo l'ultima spirale come nuova
    if len(df) > 0:
        new_responses = [len(df) - 1]

# 🎨 Genera dati spirali
palette = ["#e84393", "#e67e22", "#3498db", "#9b59b6"]
theta = np.linspace(0, 12 * np.pi, 1200)
spirali = []

for idx, row in df.iterrows():
    media = np.mean([row["PT"], row["Fantasy"], row["Empathic Concern"], row["Personal Distress"]])
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

    # Determina se è una nuova risposta
    is_new = idx in new_responses

    spirali.append({
        "x": x.tolist(),
        "y": y_proj.tolist(),
        "color": color,
        "intensity": float(intensity),
        "freq": float(freq),
        "is_new": is_new,
        "id": idx
    })

# 📏 Calcolo offset verticale per centratura perfetta
all_y = np.concatenate([np.array(s["y"]) for s in spirali])
y_min, y_max = all_y.min(), all_y.max()
y_range = y_max - y_min
OFFSET = -0.06 * y_range
for s in spirali:
    s["y"] = (np.array(s["y"]) + OFFSET).tolist()

data_json = json.dumps({"spirali": spirali, "new_responses": new_responses})

# 📊 HTML + JS con effetto sfarfallio e evidenziazione nuove spirali
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
body {{ margin:0; background:black; overflow:hidden; }}
#graph {{ width:100vw; height:100vh; position:relative; }}
#fullscreen-btn {{
    position: absolute;
    top: 10px; right: 10px;
    z-index: 9999;
    background: rgba(255,255,255,0.2);
    color: white;
    border: none;
    padding: 6px 10px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 18px;
}}
#fullscreen-btn:hover {{
    background: rgba(255,255,255,0.4);
}}
:fullscreen {{
    cursor: none;
}}
@keyframes pulse {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
    100% {{ opacity: 1; }}
}}
.new-spiral {{
    animation: pulse 1s infinite;
    filter: drop-shadow(0 0 5px #ffffff);
}}
</style>
</head>
<body>
<button id="fullscreen-btn">⛶</button>
<div id="graph"></div>
<script>
const DATA = {data_json};
let t0 = Date.now();
let newSpirals = DATA.new_responses;

function buildTraces(time){{
    const traces = [];
    DATA.spirali.forEach(s => {{
        const step = 4;
        // Calcolo opacità variabile in base alla frequenza
        const flicker = 0.5 + 0.5 * Math.sin(2 * Math.PI * s.freq * time);
        
        // Evidenziazione per nuove spirali
        const isNew = newSpirals.includes(s.id);
        const extraWidth = isNew ? 3 : 0;
        const extraOpacity = isNew ? 0.3 : 0;
        
        for(let j=1; j < s.x.length; j += step){{
            const alpha = (0.2 + 0.7 * (j / s.x.length)) * flicker + extraOpacity;
            traces.push({{
                x: s.x.slice(j-1, j+1),
                y: s.y.slice(j-1, j+1),
                mode: "lines",
                line: {{color: s.color, width: 1.5 + s.intensity * 3 + extraWidth}},
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
    const time = (Date.now() - t0) / 1000; // in secondi
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
        responsive: true
    }});
    
    // Rimuovi l'evidenziazione dopo 15 secondi
    if (time > 15 && newSpirals.length > 0) {{
        newSpirals = [];
    }}
    
    requestAnimationFrame(render);
}}

render();

document.getElementById('fullscreen-btn').addEventListener('click', () => {{
    const graphDiv = document.getElementById('graph');
    if (graphDiv.requestFullscreen) graphDiv.requestFullscreen();
    else if (graphDiv.webkitRequestFullscreen) graphDiv.webkitRequestFullscreen();
    else if (graphDiv.msRequestFullscreen) graphDiv.msRequestFullscreen();
}});
</script>
</body>
</html>
"""

st.components.v1.html(html_code, height=800, scrolling=False)

# ℹ️ Informazioni sullo stato
last_update_time = time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))
next_update_time = time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update + 300))

st.caption(f"🎨 Ultimo aggiornamento: {last_update_time} | Prossimo aggiornamento: {next_update_time}")
st.caption("Premi ⛶ per il fullscreen totale. Le nuove spirali si evidenziano con un effetto pulsante.")

# Pulsante per aggiornamento manuale
if st.button("🔄 Aggiorna manualmente"):
    st.session_state.last_update = 0  # Forza l'aggiornamento al prossimo rerun
    st.rerun()

st.markdown("---")
st.markdown("""
### 🧭 *Empatia come consapevolezza dell'impatto*

> *"L'empatia non è solo sentire l'altro, ma riconoscere il proprio impatto sul mondo e sulla realtà condivisa. È un atto di presenza responsabile."*

**Breve descrizione:**  
Ogni spirale rappresenta un individuo.  
L'inclinazione alternata e lo sfarfallio personalizzato creano un'opera viva, pulsante e ritmica.  
**Le nuove risposte si evidenziano con un effetto pulsante.**

**Nota:** I dati si aggiornano automaticamente ogni 5 minuti per rispettare i limiti delle API Google.
""")










