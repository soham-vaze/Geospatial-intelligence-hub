import streamlit as st
import pandas as pd
import folium
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
/* Make the Folium iframe fill the viewport */
[data-testid="stIFrame"] > iframe {
    height: 100vh !important;
    min-height: 100vh !important;
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

# -------- MAP GENERATION --------
m = folium.Map(location=[13.7367, 100.5231], zoom_start=6)
m.add_child(ResetViewControl(13.7367, 100.5231, 6))

for idx, (_, row) in enumerate(filtered_df.iterrows()):
    uid = f"site_{idx}"
    status = str(row.get('Status', 'Unknown'))
    status_bg = "#27ae60" if status.lower() == "active" else "#e74c3c" if status.lower() == "inactive" else "#95a5a6"
    

    # -------- BUILD DETAIL PANEL SECTIONS --------
    layer_label  = layer_meta.get(str(row.get('Layer','')), ('','',''))[2]
    bays         = int(row.get('Bays', 0))
    bay_bar_pct  = min(int((bays / 20) * 100), 100)
    source_sys   = row.get('Source System', row.get('SourceSystem', 'N/A'))
    last_upd     = row.get('Last Updated', row.get('LastUpdated', 'N/A'))
    category     = row.get('Category', 'N/A')
    sub_cat      = row.get('Sub-Category', row.get('SubCategory', 'N/A'))
    site_name    = str(row.get('Name', ''))

    # --- Deterministic derived insights (stable per site) ---
    seed          = sum(ord(c) for c in site_name) + idx
    rating        = (seed % 5) + 1                         # 1–5 stars
    health_score  = 55 + (seed * 7 % 44)                   # 55–99%
    monthly_vis   = 120 + (seed * 31 % 880)                # 120–999 monthly visitors
    rev_tiers     = ["Emerging", "Growing", "Established", "High Value", "Strategic"]
    rev_tier      = rev_tiers[seed % len(rev_tiers)]
    coverage_km   = round(2.5 + (seed % 18) * 0.5, 1)     # 2.5–11.0 km
    compliance    = 70 + (seed * 11 % 29)                  # 70–99%
    stars_html    = "".join(
        ["⭐" if i < rating else "☆" for i in range(5)]
    )
    health_color  = "#22c55e" if health_score >= 80 else "#f97316" if health_score >= 60 else "#ef4444"
    comp_color    = "#22c55e" if compliance  >= 90 else "#f97316" if compliance  >= 75 else "#ef4444"

    # --- Tier-matched review pools (reviews match the star rating) ---
    reviews_low = [   # 1–2 stars: critical / disappointed
        ("Arjun S.",  "Very disappointing experience. Long wait times and poor communication."),
        ("Priya M.",  "Staff was unhelpful and the facility looked poorly maintained."),
        ("Rahul K.",  "Wouldn't recommend. Service took twice the promised time."),
        ("Neeraj D.", "Frequent billing errors and no follow-up from the team."),
        ("Pooja T.",  "Extremely unresponsive to complaints. Will not return."),
    ]
    reviews_mid = [   # 3 stars: decent but room for improvement
        ("Sneha T.",  "Decent service overall, but wait times can be long during peak hours."),
        ("Vijay N.",  "Average experience. Facilities are adequate, nothing exceptional."),
        ("Deepak L.", "OK visit. Staff was polite but the process felt disorganised."),
        ("Meena R.",  "Service was acceptable. Would be better with online appointment booking."),
        ("Suresh K.", "Gets the job done, but the customer lounge needs improvement."),
    ]
    reviews_high = [  # 4–5 stars: positive / glowing
        ("Anita R.",  "Excellent technical expertise. Highly recommended – will visit again!"),
        ("Kavya P.",  "Very responsive team. Resolved our query the same day. Outstanding!"),
        ("Rohan M.",  "Clean, organized, and efficient. Best service center in the region."),
        ("Divya S.",  "Impressed by the professionalism. The team went above and beyond."),
        ("Amit B.",   "Fast turnaround and transparent pricing. Couldn't ask for more."),
    ]

    if rating <= 2:
        pool = reviews_low
    elif rating == 3:
        pool = reviews_mid
    else:
        pool = reviews_high

    r1 = pool[seed % len(pool)]
    r2 = pool[(seed + 2) % len(pool)]


    # --- Business Hours ---
    hours_pool = [
        ("Mon–Sat", "08:00 – 18:00"),
        ("Mon–Sat", "09:00 – 19:00"),
        ("Mon–Sun", "09:00 – 17:00"),
        ("Mon–Fri", "08:30 – 17:30"),
        ("Mon–Sun", "08:00 – 20:00"),
    ]
    biz_days, biz_time = hours_pool[seed % len(hours_pool)]
    lunch_break = "13:00–14:00" if seed % 3 == 0 else "None"

    # --- Vehicle Specialization ---
    spec_all = ["Passenger Cars", "SUVs & MUVs", "Commercial Vehicles",
                "Electric Vehicles", "Trucks", "Fleet Maintenance"]
    n_specs = 2 + (seed % 3)
    specializations = [spec_all[(seed + i * 2) % len(spec_all)] for i in range(n_specs)]

    # --- Infrastructure ---
    parking_spots  = 10 + (seed % 60)
    ev_bays        = seed % 6
    showroom_sqft  = 800 + (seed * 7 % 4200)
    has_lounge     = seed % 4 != 0
    has_test_drive = seed % 3 == 0

    # --- Market Intelligence ---
    competitors    = seed % 8
    mkt_share_pct  = 15 + (seed * 3 % 55)
    mkt_color      = "#22c55e" if mkt_share_pct >= 45 else "#f97316" if mkt_share_pct >= 25 else "#ef4444"
    opp_score      = 40 + (seed * 13 % 59)
    opp_color      = "#22c55e" if opp_score >= 75 else "#f97316" if opp_score >= 55 else "#3b82f6"
    trends         = ["Growing demand", "Stable market", "High competition", "Untapped potential", "Seasonal peaks"]
    trend_tag      = trends[seed % len(trends)]

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
          <button onclick="
            document.getElementById('detail_{uid}').style.display='none';
            document.getElementById('summary_{uid}').style.display='block';
            this.closest('.leaflet-popup-content-wrapper').parentElement._popup.update();
          " style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.4); color:white; padding:3px 10px; border-radius:4px; cursor:pointer; font-size:10px; font-weight:600;">&larr; BACK</button>
        </div>

        <!-- Scrollable body -->
        <div style="border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:#f8fafc; max-height:300px; overflow-y:auto; padding:10px 12px;">

          <!-- QUICK METRICS STRIP -->
          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-bottom:12px;">
            <div style="background:white; border:1px solid #e2e8f0; border-radius:6px; padding:7px 8px; text-align:center;">
              <div style="font-size:14px; font-weight:800; color:#2563eb;">{monthly_vis}</div>
              <div style="font-size:9px; color:#94a3b8; font-weight:600; text-transform:uppercase; margin-top:1px;">Monthly Visitors</div>
            </div>
            <div style="background:white; border:1px solid #e2e8f0; border-radius:6px; padding:7px 8px; text-align:center;">
              <div style="font-size:14px; font-weight:800; color:#7c3aed;">{coverage_km} km</div>
              <div style="font-size:9px; color:#94a3b8; font-weight:600; text-transform:uppercase; margin-top:1px;">Coverage Radius</div>
            </div>
            <div style="background:white; border:1px solid #e2e8f0; border-radius:6px; padding:7px 8px; text-align:center;">
              <div style="font-size:11px; font-weight:800; color:#0891b2; line-height:1.2; padding-top:2px;">{rev_tier}</div>
              <div style="font-size:9px; color:#94a3b8; font-weight:600; text-transform:uppercase; margin-top:1px;">Revenue Tier</div>
            </div>
          </div>

          <!-- IDENTITY -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">📌 Identity</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">SITE NAME</span>
              <span style="font-size:11px; font-weight:700; color:#1e293b; max-width:180px; text-align:right;">{row.get('Name','N/A')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">ADDRESS</span>
              <span style="font-size:10px; color:#374151; max-width:190px; text-align:right; line-height:1.3;">{row.get('Address','N/A')}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">COORDINATES</span>
              <span style="font-size:10px; color:#3b82f6; font-weight:700;">{round(float(row.get('Lat',0)),5)}, {round(float(row.get('Long',0)),5)}</span>
            </div>
          </div>

          <!-- CLASSIFICATION -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🏷️ Classification</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
              <span style="background:#dbeafe; color:#1d4ed8; font-size:10px; font-weight:700; padding:2px 8px; border-radius:20px;">{row.get('Layer','N/A')}</span>
              <span style="background:#f3e8ff; color:#7e22ce; font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px;">{category}</span>
              <span style="background:#ecfdf5; color:#166534; font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px;">{sub_cat}</span>
            </div>
            <div style="font-size:10px; color:#64748b; padding-top:4px; border-top:1px solid #f1f5f9;">{layer_label}</div>
          </div>

          <!-- CONTACT & OPERATIONS -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">👤 Contact &amp; Operations</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">MANAGER</span>
              <span style="font-size:10px; color:#1e293b; font-weight:600;">{row.get('Owner / Manager', row.get('Owner','N/A'))}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">PHONE</span>
              <span style="font-size:10px; color:#1e293b;">{row.get('Phone','N/A')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">EMAIL</span>
              <span style="font-size:10px; color:#3b82f6;">{row.get('Email','N/A')}</span>
            </div>
            <div style="border-top:1px solid #f1f5f9; padding-top:8px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">SERVICE BAYS</span>
                <span style="font-size:11px; font-weight:800; color:#1e293b;">{bays}</span>
              </div>
              <div style="background:#e2e8f0; border-radius:4px; height:5px;">
                <div style="background:linear-gradient(90deg,#3b82f6,#2563eb); width:{bay_bar_pct}%; height:5px; border-radius:4px;"></div>
              </div>
            </div>
          </div>

          <!-- PERFORMANCE & INSIGHTS -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">📊 Performance &amp; Insights</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">SITE RATING</span>
              <span style="font-size:13px; letter-spacing:1px;">{stars_html}</span>
            </div>
            <div style="margin-bottom:6px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">SITE HEALTH</span>
                <span style="font-size:10px; font-weight:700; color:{health_color};">{health_score}%</span>
              </div>
              <div style="background:#e2e8f0; border-radius:4px; height:5px;">
                <div style="background:{health_color}; width:{health_score}%; height:5px; border-radius:4px; transition:width 0.5s;"></div>
              </div>
            </div>
            <div>
              <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">COMPLIANCE SCORE</span>
                <span style="font-size:10px; font-weight:700; color:{comp_color};">{compliance}%</span>
              </div>
              <div style="background:#e2e8f0; border-radius:4px; height:5px;">
                <div style="background:{comp_color}; width:{compliance}%; height:5px; border-radius:4px;"></div>
              </div>
            </div>
          </div>

          <!-- CUSTOMER REVIEWS -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">💬 Customer Reviews</div>
          <div style="margin-bottom:10px;">
            <div style="background:white; border:1px solid #e2e8f0; border-radius:6px; padding:9px 10px; margin-bottom:6px;">
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                <div style="width:26px; height:26px; border-radius:50%; background:linear-gradient(135deg,#3b82f6,#8b5cf6); color:white; font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0;">{r1[0][0]}</div>
                <div>
                  <div style="font-size:11px; font-weight:700; color:#1e293b;">{r1[0]}</div>
                  <div style="font-size:11px; color:#f59e0b; letter-spacing:1px;">{'⭐' * rating}{'☆' * (5-rating)}</div>
                </div>
              </div>
              <div style="font-size:10px; color:#475569; font-style:italic; line-height:1.4;">&ldquo;{r1[1]}&rdquo;</div>
            </div>
            <div style="background:white; border:1px solid #e2e8f0; border-radius:6px; padding:9px 10px;">
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                <div style="width:26px; height:26px; border-radius:50%; background:linear-gradient(135deg,#22c55e,#0891b2); color:white; font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0;">{r2[0][0]}</div>
                <div>
                  <div style="font-size:11px; font-weight:700; color:#1e293b;">{r2[0]}</div>
                  <div style="font-size:11px; color:#f59e0b; letter-spacing:1px;">{'⭐' * max(rating-1,1)}{'☆' * (5-max(rating-1,1))}</div>
                </div>
              </div>
              <div style="font-size:10px; color:#475569; font-style:italic; line-height:1.4;">&ldquo;{r2[1]}&rdquo;</div>
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

          <!-- BUSINESS HOURS & FACILITIES -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🕐 Business Hours &amp; Facilities</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">OPERATING DAYS</span>
              <span style="font-size:10px; font-weight:700; color:#1e293b;">{biz_days}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">HOURS</span>
              <span style="font-size:10px; font-weight:700; color:#2563eb;">{biz_time}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">LUNCH BREAK</span>
              <span style="font-size:10px; color:#64748b;">{lunch_break}</span>
            </div>
            <div style="border-top:1px solid #f1f5f9; padding-top:7px; display:flex; gap:6px; flex-wrap:wrap;">
              <span style="background:{'#dcfce7' if has_lounge else '#fee2e2'}; color:{'#166534' if has_lounge else '#991b1b'}; font-size:9px; font-weight:700; padding:2px 7px; border-radius:20px;">{'✓ Customer Lounge' if has_lounge else '✗ No Lounge'}</span>
              <span style="background:{'#dbeafe' if has_test_drive else '#f1f5f9'}; color:{'#1d4ed8' if has_test_drive else '#64748b'}; font-size:9px; font-weight:700; padding:2px 7px; border-radius:20px;">{'🚗 Test Drive' if has_test_drive else 'No Test Drive'}</span>
            </div>
          </div>

          <!-- VEHICLE SPECIALIZATION -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🚘 Vehicle Specialization</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; gap:5px; flex-wrap:wrap; margin-bottom:8px;">
              {''.join(f'<span style="background:#eff6ff; color:#1d4ed8; font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px; border:1px solid #bfdbfe;">{s}</span>' for s in specializations)}
            </div>
            <div style="border-top:1px solid #f1f5f9; padding-top:7px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">SHOWROOM AREA</span>
                <span style="font-size:10px; font-weight:700; color:#1e293b;">{showroom_sqft:,} sq ft</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">PARKING SPOTS</span>
                <span style="font-size:10px; font-weight:700; color:#1e293b;">{parking_spots}</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">EV CHARGING BAYS</span>
                <span style="font-size:10px; font-weight:700; color:{'#22c55e' if ev_bays > 0 else '#94a3b8'};">{ev_bays if ev_bays > 0 else 'None'}</span>
              </div>
            </div>
          </div>

          <!-- MARKET INTELLIGENCE -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">📈 Market Intelligence</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">NEARBY COMPETITORS</span>
              <span style="font-size:10px; font-weight:700; color:#1e293b;">{competitors} sites</span>
            </div>
            <div style="margin-bottom:6px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="color:#94a3b8; font-size:10px; font-weight:600;">EST. MARKET SHARE</span>
                <span style="font-size:10px; font-weight:700; color:{mkt_color};">{mkt_share_pct}%</span>
              </div>
              <div style="background:#e2e8f0; border-radius:4px; height:5px;">
                <div style="background:{mkt_color}; width:{mkt_share_pct}%; height:5px; border-radius:4px;"></div>
              </div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="color:#94a3b8; font-size:10px; font-weight:600;">MARKET TREND</span>
              <span style="background:#f1f5f9; color:#334155; font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px;">{trend_tag}</span>
            </div>
          </div>

          <!-- OPPORTUNITY SCORE -->
          <div style="font-size:9px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">🎯 Opportunity Score</div>
          <div style="background:white; border-radius:6px; border:1px solid #e2e8f0; padding:10px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
              <div>
                <div style="font-size:22px; font-weight:900; color:{opp_color}; line-height:1;">{opp_score}<span style="font-size:12px; font-weight:600; color:#94a3b8;">/100</span></div>
                <div style="font-size:9px; color:#94a3b8; font-weight:600; margin-top:2px;">EXPANSION POTENTIAL</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:11px; font-weight:700; color:{opp_color};">
                  {'🔥 High Priority' if opp_score >= 75 else '⚡ Medium Priority' if opp_score >= 55 else '🔵 Monitor'}
                </div>
                <div style="font-size:9px; color:#94a3b8; margin-top:2px;">Rev Tier: {rev_tier}</div>
              </div>
            </div>
            <div style="background:#e2e8f0; border-radius:6px; height:8px;">
              <div style="background:linear-gradient(90deg,{opp_color},{opp_color}aa); width:{opp_score}%; height:8px; border-radius:6px;"></div>
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
st_folium(m, width="100%", height=900, key=f"map_{st.session_state.map_key}")