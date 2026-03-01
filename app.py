import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from branca.element import MacroElement
from jinja2 import Template

st.set_page_config(layout="wide", page_title="Ford Geospatial Hub", page_icon="📍")

# -------- SESSION STATE INIT --------
if "map_center" not in st.session_state:
    st.session_state.map_center = [13.7367, 100.5231]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 6
if "map_key" not in st.session_state:
    st.session_state.map_key = 0

# -------- LOAD DATA --------
@st.cache_data
def load_data():
    # Note: Use pd.read_csv if your file is the csv provided, otherwise read_excel
    df = pd.read_excel("POC Ford Dummy Data.xlsx")
    df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    df["Bays"] = pd.to_numeric(df["Bays"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Lat", "Long"])
    return df

df = load_data()

# -------- LAYER METADATA --------
layer_meta = {
    "L1": ("blue",   "#3b82f6", "Primary Network"),
    "L2": ("green",  "#22c55e", "Partnered Customers"),
    "L3": ("orange", "#f97316", "Organized IRFs"),
    "L4": ("cadetblue", "#06b6d4", "Retail & Wholesale"),
    "L5": ("red",    "#ef4444", "Unorganized Sector"),
    "L6": ("purple", "#a855f7", "Specialized Outlets"),
}
layer_colors = {k: v[0] for k, v in layer_meta.items()}

# -------- GLOBAL LAYOUT CSS --------
st.markdown("""
<style>
/* Remove all default Streamlit padding so the map can go edge-to-edge */
[data-testid="stAppViewContainer"] > .main {
    padding: 0 !important;
    margin: 0 !important;
}
.main .block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}
/* Make the Folium iframe fill the viewport but account for the header */
[data-testid="stIFrame"] {
    height: calc(100vh - 3rem) !important;
    min-height: calc(100vh - 3rem) !important;
}
[data-testid="stIFrame"] > iframe {
    height: 100% !important;
    min-height: 100% !important;
}
/* Shrink the top header bar to reclaim space */
[data-testid="stHeader"] {
    height: 2.5rem !important;
}

/* ---- Force iframe below sidebar ---- */
[data-testid="stIFrame"],
[data-testid="stIFrame"] > iframe {
    z-index: 0 !important;
    position: relative !important;
}

/* ---- Sidebar always on top ---- */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    z-index: 99999 !important;
    position: relative !important;
}

/* ---- Sidebar close arrow: sticky at top, always visible ---- */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] button,
button[aria-label*="sidebar"],
button[aria-label*="Sidebar"] {
    z-index: 999999 !important;
    position: sticky !important;
    top: 0 !important;
    pointer-events: all !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] {
    padding: 2px 0;
}
[data-testid="stSidebar"] .stSlider > label {
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748b !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg", width=80)
st.sidebar.markdown("""
<div style="padding:4px 0 14px 0;">
  <div style="font-size:17px; font-weight:800; color:#f1f5f9; letter-spacing:0.3px;">Thailand Hub</div>
  <div style="font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:1px;">Geospatial Intelligence POC</div>
</div>
<hr style="border:none; border-top:1px solid #1e3a5f; margin:0 0 14px 0;">
<div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px;">Map Layers</div>
""", unsafe_allow_html=True)

# -------- LAYER TOGGLES — color-coded cards --------
# Folium color name → actual hex (matches leaflet marker palette)
FOLIUM_HEX = {
    "blue":      "#2563eb",
    "green":     "#16a34a",
    "orange":    "#ea580c",
    "cadetblue": "#0891b2",
    "red":       "#dc2626",
    "purple":    "#9333ea",
}

selected_layers = []
for layer, (folium_color, hex_color, label) in layer_meta.items():
    marker_hex = FOLIUM_HEX.get(folium_color, hex_color)
    col_dot, col_cb = st.sidebar.columns([0.10, 0.90])
    with col_dot:
        st.markdown(
            f'<div style="width:11px;height:11px;border-radius:50%;'
            f'background:{marker_hex};margin-top:11px;'
            f'box-shadow:0 0 7px {marker_hex}bb;"></div>',
            unsafe_allow_html=True
        )
    with col_cb:
        if st.checkbox(f"**{layer}** · {label}", value=True, key=f"chk_{layer}"):
            selected_layers.append(layer)


st.sidebar.markdown('<hr style="border:none; border-top:1px solid #1e3a5f; margin:10px 0 12px 0;">', unsafe_allow_html=True)
st.sidebar.markdown('<div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:8px;">Filters</div>', unsafe_allow_html=True)

min_bays = st.sidebar.slider("Min. Service Bays", 0, int(df["Bays"].max()), 0)
filtered_df = df[(df["Layer"].isin(selected_layers)) & (df["Bays"] >= min_bays)]

# Live stats card
st.sidebar.markdown(f"""
<div style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.25);
            border-radius:8px; padding:10px 14px; margin:10px 0 4px 0;">
  <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
    <span style="color:#94a3b8; font-size:10px; font-weight:600;">ACTIVE SITES</span>
    <span style="color:#60a5fa; font-weight:800; font-size:14px;">{len(filtered_df)}</span>
  </div>
  <div style="display:flex; justify-content:space-between;">
    <span style="color:#94a3b8; font-size:10px; font-weight:600;">TOTAL BAY CAPACITY</span>
    <span style="color:#60a5fa; font-weight:800; font-size:14px;">{int(filtered_df["Bays"].sum())}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# -------- RESET VIEW BUTTON CLASS (FIXED) --------
# class ResetViewControl(MacroElement):
#     def __init__(self, lat, lng, zoom=6):
#         super().__init__()
#         self._template = Template("""
#             {% macro script(this, kwargs) %}
#             (function() {
#                 var ResetControl = L.Control.extend({
#                     options: { position: 'topright' },
#                     onAdd: function(map) {
#                         var btn = L.DomUtil.create('button', '');
#                         btn.innerHTML = '↺ Reset Map';
#                         btn.style.cssText = 'background:#1e293b; color:#60a5fa; border:1px solid #334155; border-radius:6px; padding:6px 12px; cursor:pointer; font-weight:bold; font-size:12px; margin:10px;';
#                         L.DomEvent.on(btn, 'click', function(e) {
#                             L.DomEvent.stopPropagation(e);
#                             // FIX: Close any open popups before resetting view to prevent cut-off issues
#                             map.closePopup();
#                             map.flyTo([{{ this.lat }}, {{ this.lng }}], {{ this.zoom }}, {animate: true, duration: 1.5});
#                         });
#                         return btn;
#                     }
#                 });
#                 new ResetControl().addTo({{ this.map_name }});
#             })();
#             {% endmacro %}
#         """)
#         self.lat, self.lng, self.zoom = lat, lng, zoom
#         self.map_name = None

#     def render(self, **kwargs):
#         figure = self.get_root()
#         self.map_name = list(figure._children.keys())[0] if figure else "map"
#         super().render(**kwargs)

# -------- RESET VIEW BUTTON CLASS (DYNAMIC VISIBILITY FIX) --------
class ResetViewControl(MacroElement):
    def __init__(self, lat, lng, zoom=6):
        super().__init__()
        self._template = Template("""
            {% macro script(this, kwargs) %}
            (function() {
                var ResetControl = L.Control.extend({
                    options: { position: 'topright' },
                    onAdd: function(map) {
                        var btn = L.DomUtil.create('button', '');
                        btn.innerHTML = '↺ Reset Map';
                        btn.style.cssText = 'background:#1e293b; color:#60a5fa; border:1px solid #334155; border-radius:6px; padding:6px 12px; cursor:pointer; font-weight:bold; font-size:12px; margin:10px;';
                        
                        L.DomEvent.on(btn, 'click', function(e) {
                            L.DomEvent.stopPropagation(e);
                            
                            var targetLat = {{ this.lat }};
                            var targetLng = {{ this.lng }};
                            var openPopup = null;

                            // Find the currently open popup
                            map.eachLayer(function(layer) {
                                if (layer.getPopup && layer.getPopup() && layer.isPopupOpen()) {
                                    openPopup = layer;
                                }
                            });

                            if (openPopup) {
                                // If a popup is open, we offset the reset center 
                                // to move the map "up", ensuring the popup stays in view.
                                // 2.5 degrees is roughly the offset needed at Zoom 6
                                targetLat = openPopup.getLatLng().lat + 2.8; 
                                targetLng = openPopup.getLatLng().lng;
                            }

                            map.flyTo([targetLat, targetLng], {{ this.zoom }}, {
                                animate: true, 
                                duration: 1.5
                            });
                        });
                        return btn;
                    }
                });
                new ResetControl().addTo({{ this.map_name }});
            })();
            {% endmacro %}
        """)
        self.lat, self.lng, self.zoom = lat, lng, zoom
        self.map_name = None

    def render(self, **kwargs):
        figure = self.get_root()
        self.map_name = list(figure._children.keys())[0] if figure else "map"
        super().render(**kwargs)

# -------- FLY-TO LOGIC CLASS --------
class FlyToOnClick(MacroElement):
    def __init__(self, marker, lat, lng, zoom=15, duration=1.2):
        super().__init__()
        self._template = Template("""
            {% macro script(this, kwargs) %}
            {{ this.marker_name }}.on('click', function(e) {
                window._flyToTarget = {{ this.marker_name }};
                {{ this.map_name }}.flyTo([{{ this.lat + 0.007 }}, {{ this.lng }}], {{ this.zoom }}, {animate: true, duration: {{ this.duration }}});
            });
            if (!window._flyToMoveEndAdded_{{ this.map_name }}) {
                window._flyToMoveEndAdded_{{ this.map_name }} = true;
                {{ this.map_name }}.on('moveend', function() {
                    if (window._flyToTarget) {
                        var target = window._flyToTarget; window._flyToTarget = null;
                        setTimeout(function() { target.openPopup(); }, 100);
                    }
                });
            }
            {% endmacro %}
        """)
        self.lat, self.lng, self.zoom, self.duration = lat, lng, zoom, duration
        self.marker_name = marker.get_name()
        self.map_name = None

    def render(self, **kwargs):
        figure = self.get_root()
        self.map_name = list(figure._children.keys())[0] if figure else "map"
        super().render(**kwargs)

# -------- PDF GENERATION MACRO --------
class DownloadPDFMacro(MacroElement):
    def __init__(self):
        super().__init__()
        self._template = Template("""
            {% macro script(this, kwargs) %}
            
            // Helper to dynamically load JS libraries safely
            window._loadScript = function(src) {
                return new Promise((resolve, reject) => {
                    if (document.querySelector(`script[src="${src}"]`)) {
                        resolve(); return;
                    }
                    const script = document.createElement('script');
                    script.src = src;
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            };

            window.generatePDF = async function(btn) {
                const uid = btn.getAttribute('data-uid');
                const rawData = btn.getAttribute('data-pdf-info');
                const d = JSON.parse(rawData);
                
                const originalText = btn.innerHTML;
                btn.innerHTML = '⏳ Loading...';
                btn.style.opacity = '0.7';
                btn.style.pointerEvents = 'none';
                
                try {
                    // 1. Ensure jsPDF is loaded
                    await window._loadScript("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
                    if (!window.jspdf || !window.jspdf.jsPDF) throw new Error("jsPDF failed");
                    
                    btn.innerHTML = '⏳ Map Tile...';
                    
                    const { jsPDF } = window.jspdf;
                    const pdf = new jsPDF('p', 'mm', 'a4');
                    
                    // --- 1. Load Static High-Res Map (3x3 Tile Stitching) ---
                    // The website uses CartoDB Dark Matter or Voyager, let's use Voyager (light, high contrast streets)
                    const zoom = 15;
                    const tileUrlBase = 'https://a.basemaps.cartocdn.com/rastertiles/voyager';
                    
                    const lon_rad = d.lng * Math.PI / 180;
                    const lat_rad = d.lat * Math.PI / 180;
                    const n = Math.pow(2, zoom);
                    
                    const exactX = (d.lng + 180) / 360 * n;
                    const exactY = (1 - Math.log(Math.tan(lat_rad) + 1 / Math.cos(lat_rad)) / Math.PI) / 2 * n;
                    
                    const centerTileX = Math.floor(exactX);
                    const centerTileY = Math.floor(exactY);
                    
                    // Center pixel of the marker within the center tile
                    const markerPixelX = (exactX - centerTileX) * 256;
                    const markerPixelY = (exactY - centerTileY) * 256;

                    // We want a rectangular crop, e.g. 600px wide x 400px high, 
                    // perfectly centered on the marker.
                    const cropW = 600;
                    const cropH = 400;
                    
                    const getCenteredMapBase64 = async () => {
                        const canvas = document.createElement('canvas');
                        canvas.width = cropW;
                        canvas.height = cropH;
                        const ctx = canvas.getContext('2d');
                        
                        // Fill background just in case
                        ctx.fillStyle = '#e5e7eb';
                        ctx.fillRect(0, 0, cropW, cropH);
                        
                        // Load image helper
                        const loadImg = (url) => new Promise((res, rej) => {
                            const img = new Image();
                            img.crossOrigin = 'anonymous';
                            img.onload = () => res(img);
                            img.onerror = () => res(null); // Ignore missing tiles gracefully
                            img.src = url;
                        });

                        // Calculate offset to place marker exactly at center of canvas (300, 200)
                        // If center tile (tx,ty) is drawn at (offsetX, offsetY), 
                        // then marker is at (offsetX + markerPixelX, offsetY + markerPixelY).
                        // We want: offsetX + markerPixelX = cropW/2
                        const offsetX = (cropW / 2) - markerPixelX;
                        const offsetY = (cropH / 2) - markerPixelY;

                        // Fetch a 3x3 grid around the center tile to ensure we cover the 600x400 area
                        const promises = [];
                        for(let dy = -1; dy <= 1; dy++) {
                            for(let dx = -1; dx <= 1; dx++) {
                                const tx = centerTileX + dx;
                                const ty = centerTileY + dy;
                                const url = `${tileUrlBase}/${zoom}/${tx}/${ty}.png`;
                                promises.push(loadImg(url).then(img => ({img, dx, dy})));
                            }
                        }
                        
                        const tiles = await Promise.all(promises);
                        
                        // Draw tiles
                        tiles.forEach(t => {
                            if(t.img) {
                                const drawX = offsetX + (t.dx * 256);
                                const drawY = offsetY + (t.dy * 256);
                                ctx.drawImage(t.img, drawX, drawY);
                            }
                        });
                        
                        // Draw marker pin in exact center
                        ctx.beginPath();
                        ctx.arc(cropW/2, cropH/2, 10, 0, 2*Math.PI);
                        ctx.fillStyle = '#ef4444'; // Red
                        ctx.shadowColor = 'rgba(0,0,0,0.5)';
                        ctx.shadowBlur = 4;
                        ctx.shadowOffsetX = 0;
                        ctx.shadowOffsetY = 2;
                        ctx.fill();
                        
                        ctx.shadowColor = 'transparent';
                        ctx.lineWidth = 3;
                        ctx.strokeStyle = '#ffffff';
                        ctx.stroke();
                        
                        return canvas.toDataURL('image/jpeg', 0.9);
                    };

                    let mapImg = null;
                    try { mapImg = await getCenteredMapBase64(); } 
                    catch(e) { console.warn("Map grid failed to load:", e); }

                    // --- 2. HEADER BLOCK ---
                    // Dark edge-to-edge header
                    pdf.setFillColor(30, 41, 59); // #1e293b
                    pdf.rect(0, 0, 210, 45, 'F');
                    
                    pdf.setTextColor(255, 255, 255);
                    pdf.setFont("helvetica", "bold");
                    pdf.setFontSize(22);
                    let splitTitle = pdf.splitTextToSize(String(d.name), 180);
                    pdf.text(splitTitle, 15, 20);
                    
                    pdf.setFontSize(11);
                    pdf.setFont("helvetica", "normal");
                    pdf.setTextColor(148, 163, 184); // #94a3b8
                    pdf.text(`Geospatial Intelligence Report  •  ${d.layer}`, 15, 20 + (splitTitle.length * 8));
                    
                    // --- 3. MAP IMAGE (Right Side) ---
                    let startY = 55;
                    if (mapImg) {
                        pdf.setDrawColor(203, 213, 225);
                        pdf.setLineWidth(0.5);
                        // Draw at (X:115, Y:50) size 84w x 56h mm (3:2 ratio matching 600x400 canvas)
                        pdf.addImage(mapImg, 'JPEG', 111, 50, 84, 56);
                        pdf.rect(111, 50, 84, 56); 
                    }

                    // --- 4. DATA SECTIONS (Left Side & Below) ---
                    const drawSection = (title, yPos) => {
                        pdf.setFont("helvetica", "bold");
                        pdf.setFontSize(12);
                        pdf.setTextColor(30, 41, 59);
                        pdf.text(title, 15, yPos);
                        pdf.setDrawColor(226, 232, 240);
                        pdf.setLineWidth(0.5);
                        pdf.line(15, yPos+2, 100, yPos+2); // Line up to map
                        return yPos + 8;
                    };
                    const drawSectionFull = (title, yPos) => {
                        pdf.setFont("helvetica", "bold");
                        pdf.setFontSize(12);
                        pdf.setTextColor(30, 41, 59);
                        pdf.text(title, 15, yPos);
                        pdf.setDrawColor(226, 232, 240);
                        pdf.setLineWidth(0.5);
                        pdf.line(15, yPos+2, 195, yPos+2); // Full width line
                        return yPos + 8;
                    };
                    const drawItem = (label, val, xPos, yPos, maxW=45) => {
                        pdf.setFont("helvetica", "bold");
                        pdf.setFontSize(9);
                        pdf.setTextColor(100, 116, 139);
                        pdf.text(label, xPos, yPos);
                        pdf.setFont("helvetica", "normal");
                        pdf.setFontSize(10);
                        pdf.setTextColor(15, 23, 42);
                        let splitVal = pdf.splitTextToSize(String(val), maxW);
                        pdf.text(splitVal, xPos + 28, yPos);
                        return Math.max(7, splitVal.length * 5);
                    };

                    let curY = startY;
                    
                    // Box 1: Identity & Contact
                    curY = drawSection("SITE IDENTITY & STATUS", curY);
                    let h1 = drawItem("Address:", d.address, 15, curY, 65);
                    curY += h1 + 1;
                    h1 = drawItem("Coordinates:", `${d.lat.toFixed(5)}, ${d.lng.toFixed(5)}`, 15, curY, 65);
                    curY += h1;
                    h1 = drawItem("Status:", d.status, 15, curY, 65);
                    curY += h1;
                    h1 = drawItem("Manager:", d.manager, 15, curY, 65);
                    curY += h1 + 8;

                    // Push curY below the map image to expand to full width
                    curY = Math.max(curY, 118);

                    // Box 2: Classification
                    curY = drawSectionFull("SITE CLASSIFICATION", curY);
                    h1 = drawItem("Network Layer:", `${d.layer}`, 15, curY, 65);
                    let h2 = drawItem("Category:", d.category, 115, curY, 65);
                    curY += Math.max(h1, h2);
                    h1 = drawItem("Sub-Category:", d.sub_category, 15, curY, 65);
                    h2 = drawItem("Establishment:", d.estab_type, 115, curY, 65);
                    curY += Math.max(h1, h2) + 6;

                    // Box 3: Infrastructure & Service
                    curY = drawSectionFull("INFRASTRUCTURE PROFILE", curY);
                    h1 = drawItem("Service Bays:", d.bays, 15, curY, 65);
                    h2 = drawItem("Specialization:", d.specialization, 115, curY, 70);
                    curY += Math.max(h1, h2) + 6;
                    
                    // Box 4: Data Quality & Audit
                    curY = drawSectionFull("SYSTEM AUDIT", curY);
                    h1 = drawItem("Source System:", d.source_system, 15, curY, 65);
                    h2 = drawItem("Last Updated:", d.last_updated, 115, curY, 70);
                    curY += Math.max(h1, h2) + 10;
                    
                    // --- 5. FOOTER
                    pdf.setFont("helvetica", "italic");
                    pdf.setFontSize(8);
                    pdf.setTextColor(148, 163, 184);
                    const timestamp = new Date().toLocaleString();
                    pdf.text(`Ford Geospatial Intelligence Hub - Confidential Report Generated: ${timestamp}`, 15, 285);
                    
                    pdf.save((d.name || 'Site').replace(/[^a-z0-9]/gi, '_') + '_Report.pdf');
                } catch(e) {
                    console.error("PDF generation failed", e);
                    alert("Failed to generate PDF. Make sure plugins are loaded.");
                } finally {
                    btn.innerHTML = originalText;
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                }
            };
            {% endmacro %}
        """)

# -------- MAP GENERATION --------
m = folium.Map(location=[13.7367, 100.5231], zoom_start=6)
m.add_child(ResetViewControl(13.7367, 100.5231, 6))
m.add_child(DownloadPDFMacro())

for idx, (_, row) in enumerate(filtered_df.iterrows()):
    uid = f"site_{idx}"
    status = str(row.get('Status', 'Unknown'))
    status_bg = "#27ae60" if status.lower() == "active" else "#e74c3c" if status.lower() == "inactive" else "#95a5a6"
    

    # -------- BUILD DETAIL PANEL SECTIONS --------
    # --- Genuine detail extraction ---
    layer_label  = layer_meta.get(str(row.get('Layer','')), ('','',''))[2]
    bays         = int(row.get('Bays', 0))
    source_sys   = str(row.get('Source System', row.get('SourceSystem', 'N/A')))
    raw_date     = row.get('Last Updated', row.get('LastUpdated', 'N/A'))
    last_upd     = str(raw_date.date()) if hasattr(raw_date, 'date') else str(raw_date)
    category     = str(row.get('Category', 'N/A'))
    sub_cat      = str(row.get('Sub-Category', row.get('SubCategory', 'N/A')))
    site_name    = str(row.get('Name', ''))
    phone        = str(row.get('Phone', 'N/A'))
    email        = str(row.get('Email', 'N/A'))
    spec         = str(row.get('Specialization', 'N/A'))
    manager      = str(row.get('Owner / Manager', row.get('Owner', 'N/A')))
    estab_type   = str(row.get('Establishment Type', 'N/A'))
    address      = str(row.get('Address', 'N/A'))

    import math
    safe_lat = row.get('Lat', 0.0)
    safe_lng = row.get('Long', 0.0)
    if math.isnan(safe_lat): safe_lat = 0.0
    if math.isnan(safe_lng): safe_lng = 0.0
    
    pdf_data = {
        "uid": uid,
        "lat": safe_lat,
        "lng": safe_lng,
        "name": site_name,
        "address": address,
        "layer": layer_label,
        "category": category,
        "sub_category": sub_cat,
        "status": status.upper(),
        "manager": manager,
        "phone": phone,
        "email": email,
        "bays": bays,
        "specialization": spec,
        "estab_type": estab_type,
        "source_system": source_sys,
        "last_updated": last_upd
    }
    # Safely escape double quotes for the HTML attribute
    pdf_json_str = json.dumps(pdf_data).replace('"', '&quot;')

    popup_html = f"""
    <div style="width:340px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">

      <!-- ===== SUMMARY PANEL ===== -->
      <div id="summary_{uid}">
        <div style="background:#1a1a2e; color:white; padding:12px; border-radius:8px 8px 0 0;">
          <div style="font-size:16px; font-weight:bold; margin-bottom:2px;">{row.get('Name','N/A')}</div>
          <div style="font-size:11px; opacity:0.8;">{row.get('Layer')} | {row.get('Sub-Category', row.get('SubCategory',''))}</div>
        </div>
        <div style="padding:15px; border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:white;">
          <div style="margin-bottom:8px;">
            <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">📍 Address &amp; Geocode</span><br>
            <span style="font-size:12px;">{row.get('Address','N/A')}</span><br>
            <span style="font-size:10px; color:#3b82f6; font-weight:bold;">{row.get('Lat')}, {row.get('Long')}</span>
          </div>
          <div style="margin-bottom:8px;">
            <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">📞 Contact Details</span><br>
            <span style="font-size:12px;"><b>Mgr:</b> {row.get('Owner / Manager', row.get('Owner','N/A'))}</span><br>
            <span style="font-size:12px;"><b>Phone:</b> {row.get('Phone','N/A')} | <b>Email:</b> {row.get('Email','N/A')}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
             <div>
                <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">Status</span><br>
                <span style="background:{status_bg}; color:white; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:bold;">{status.upper()}</span>
             </div>
             <div style="text-align:right;">
                <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">Last Updated</span><br>
                <span style="font-size:11px;">{source_sys} ({last_upd})</span>
             </div>
          </div>
          <button onclick="
            document.getElementById('summary_{uid}').style.display='none';
            document.getElementById('detail_{uid}').style.display='block';
            this.closest('.leaflet-popup-content-wrapper').parentElement._popup.update();
          " style="background:#2563eb; color:white; border:none; padding:10px; width:100%; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px; transition:0.3s;">
            📋 VIEW FULL ATTRIBUTE LOG &rarr;
          </button>
        </div>
      </div>

      <!-- ===== DETAIL PANEL ===== -->
      <div id="detail_{uid}" style="display:none;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1a1a2e,#2563eb); color:white; padding:10px 12px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:13px; letter-spacing:0.3px;">📋 Full System Profile</div>
            <div style="font-size:10px; opacity:0.7; margin-top:1px;">{row.get('Name','N/A')}</div>
          </div>
          <div style="display:flex; gap:6px;">
            <button id="pdfBtn_{uid}" data-uid="{uid}" data-pdf-info="{pdf_json_str}" onclick="window.generatePDF(this)" style="background:#1e3a8a; border:1px solid rgba(255,255,255,0.2); color:#ffffff; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:10px; font-weight:700; display:flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.1); transition:all 0.2s;">
              📥 Report
            </button>
            <button onclick="
              document.getElementById('detail_{uid}').style.display='none';
              document.getElementById('summary_{uid}').style.display='block';
              this.closest('.leaflet-popup-content-wrapper').parentElement._popup.update();
            " style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.4); color:white; padding:3px 10px; border-radius:4px; cursor:pointer; font-size:10px; font-weight:600;">&larr; BACK</button>
          </div>
        </div>

        <!-- Scrollable body -->
        <div style="border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:#f8fafc; max-height:300px; overflow-y:auto; padding:10px 12px;">

          <!-- IDENTITY -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">📌 Identity</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">SITE NAME</span>
              <span style="font-size:11px; font-weight:700; color:#1e293b; max-width:180px; text-align:right;">{site_name}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">ADDRESS</span>
              <span style="font-size:10px; color:#374151; max-width:190px; text-align:right; line-height:1.3;">{address}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">COORDINATES</span>
              <span style="font-size:10px; color:#3b82f6; font-weight:700;">{round(safe_lat,5)}, {round(safe_lng,5)}</span>
            </div>
          </div>

          <!-- CLASSIFICATION -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🏷️ Classification</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
              <span style="background:#dbeafe; color:#1d4ed8; font-size:10px; font-weight:700; padding:2px 8px; border-radius:20px;">{row.get('Layer','N/A')} ({layer_label})</span>
              <span style="background:#f3e8ff; color:#7e22ce; font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px;">{category}</span>
              <span style="background:#ecfdf5; color:#166534; font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px;">{sub_cat}</span>
              <span style="background:#fef3c7; color:#92400e; font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px;">{estab_type}</span>
            </div>
          </div>

          <!-- CONTACT & OPERATIONS -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">👤 Contact &amp; Infrastructure</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">MANAGER</span>
              <span style="font-size:10px; color:#1e293b; font-weight:600;">{manager}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">PHONE</span>
              <span style="font-size:10px; color:#1e293b;">{phone}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">EMAIL</span>
              <span style="font-size:10px; color:#3b82f6;">{email}</span>
            </div>
            <div style="border-top:1px solid #f1f5f9; padding-top:8px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">SERVICE BAYS</span>
                <span style="font-size:11px; font-weight:800; color:#1e293b;">{bays}</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">SPECIALIZATION</span>
                <span style="font-size:10px; font-weight:600; color:#1e293b;">{spec}</span>
              </div>
            </div>
          </div>

          <!-- DATA QUALITY -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">⚙️ Data &amp; Audit</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">STATUS</span>
              <span style="background:{status_bg}; color:white; font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px;">{status.upper()}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">SOURCE SYSTEM</span>
              <span style="font-size:10px; color:#1e293b; font-weight:600;">{source_sys}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">LAST UPDATED</span>
              <span style="font-size:10px; color:#1e293b;">{last_upd}</span>
            </div>
          </div>

        </div>
      </div>
    </div>
    """


    marker = folium.Marker(
        location=[row["Lat"], row["Long"]],
        popup=folium.Popup(popup_html, max_width=400, auto_pan=True),
        icon=folium.Icon(color=layer_colors.get(row["Layer"], "blue"), icon="info-sign")
    )
    marker.add_to(m)
    
    fly = FlyToOnClick(marker, lat=row["Lat"], lng=row["Long"])
    fly.map_name = m.get_name()
    marker.add_child(fly)

# -------- RENDER --------
st_folium(m, width="100%", height=700, use_container_width=True, key=f"map_{st.session_state.map_key}")