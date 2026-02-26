import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from branca.element import MacroElement
from jinja2 import Template

st.set_page_config(layout="wide", page_title="Ford Geospatial Hub")

# -------- SESSION STATE INIT --------
if "map_center" not in st.session_state:
    st.session_state.map_center = [13.7367, 100.5231]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 6
if "selected_site" not in st.session_state:
    st.session_state.selected_site = None
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False
if "map_key" not in st.session_state:
    st.session_state.map_key = 0

# -------- LOAD DATA --------
@st.cache_data
def load_data():
    df = pd.read_excel("POC Ford Dummy Data.xlsx")
    df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    df["Bays"] = pd.to_numeric(df["Bays"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Lat", "Long"])
    return df

df = load_data()

# -------- LAYER COLORS --------
layer_colors = {
    "L1": "blue",
    "L2": "green",
    "L3": "orange",
    "L4": "cadetblue",
    "L5": "red",
    "L6": "purple",
}

# -------- SIDEBAR STYLING --------
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stSlider > label,
[data-testid="stSidebar"] .stMultiSelect > label {
    color: #94a3b8 !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
    margin-top: 4px;
}
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
    font-weight: 600;
    padding: 10px;
    transition: opacity 0.2s;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    opacity: 0.85;
}
</style>
""", unsafe_allow_html=True)

# -------- SIDEBAR HEADER --------
layer_meta = {
    "L1": ("blue",   "#3b82f6", "Tier 1 — Primary Sites"),
    "L2": ("green",  "#22c55e", "Tier 2 — Secondary Sites"),
    "L3": ("orange", "#f97316", "Tier 3 — Regional Hubs"),
    "L4": ("cadetblue", "#06b6d4", "Tier 4 — Service Centers"),
    "L5": ("red",    "#ef4444", "Tier 5 — Opportunities"),
    "L6": ("purple", "#a855f7", "Tier 6 — Expansion Zones"),
}
layer_colors = {k: v[0] for k, v in layer_meta.items()}

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg", width=80)
st.sidebar.markdown("""
<div style="padding: 4px 4px 8px 4px;">
  <div style="font-size:16px; font-weight:700; color:#f1f5f9;">Thailand Hub</div>
  <div style="font-size:11px; color:#64748b;">Ford Geospatial Intelligence</div>
</div>
<hr style="border:none; border-top:1px solid #1e3a5f; margin:4px 0 12px 0;">
""", unsafe_allow_html=True)

# -------- LEGEND --------
st.sidebar.markdown("""
<div style="font-size:10px; font-weight:700; color:#64748b;
            text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px;">
  Map Legend
</div>
""", unsafe_allow_html=True)

for layer, (_, hex_color, label) in layer_meta.items():
    st.sidebar.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px;
                background:rgba(255,255,255,0.04); border-radius:8px;
                padding:7px 10px; margin-bottom:5px;
                border:1px solid rgba(255,255,255,0.07);">
      <div style="width:12px; height:12px; border-radius:50%;
                  background:{hex_color}; flex-shrink:0;
                  box-shadow: 0 0 6px {hex_color}88;"></div>
      <div>
        <span style="font-weight:700; font-size:12px; color:#f1f5f9;">{layer}</span>
        <span style="color:#64748b; font-size:11px; margin-left:6px;">{label}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# -------- FILTERS --------
st.sidebar.markdown("""
<div style="font-size:10px; font-weight:700; color:#64748b;
            text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px;">
  Filters
</div>
""", unsafe_allow_html=True)

# -------- LAYER TOGGLES --------
# CSS for styled checkbox rows
st.markdown("""
<style>
[data-testid="stSidebar"] [data-testid="stCheckbox"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 4px 10px;
    margin-bottom: 5px;
    transition: background 0.15s;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"]:hover {
    background: rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #f1f5f9 !important;
    gap: 8px;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stCheckboxWidget"] span {
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)

selected_layers = []
for layer, (_, hex_color, label) in layer_meta.items():
    col_dot, col_cb = st.sidebar.columns([0.12, 0.88])
    with col_dot:
        st.markdown(
            f'<div style="width:10px;height:10px;border-radius:50%;'
            f'background:{hex_color};margin-top:14px;'
            f'box-shadow:0 0 6px {hex_color}99;"></div>',
            unsafe_allow_html=True
        )
    with col_cb:
        if st.checkbox(f"**{layer}** — {label}", value=True, key=f"layer_chk_{layer}"):
            selected_layers.append(layer)


min_bays = st.sidebar.slider(
    "Min. Service Bays",
    0,
    int(df["Bays"].max()),
    0
)

st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# -------- FILTER STATS --------
filtered_df = df[
    (df["Layer"].isin(selected_layers)) &
    (df["Bays"] >= min_bays)
]

st.sidebar.markdown(f"""
<div style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.25);
            border-radius:10px; padding:12px 14px; margin:8px 0 16px 0;">
  <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
    <span style="color:#94a3b8; font-size:11px;">Active Sites</span>
    <span style="color:#60a5fa; font-weight:700; font-size:14px;">{len(filtered_df)}</span>
  </div>
  <div style="display:flex; justify-content:space-between;">
    <span style="color:#94a3b8; font-size:11px;">Total Bay Capacity</span>
    <span style="color:#60a5fa; font-weight:700; font-size:14px;">{int(filtered_df["Bays"].sum())}</span>
  </div>
</div>
""", unsafe_allow_html=True)


# -------- DETAIL MODAL --------
@st.dialog("📍 Site Details")
def show_site_modal(site):
    st.markdown(f"### {site.get('Name', 'N/A')}")
    st.divider()

    col1, col2 = st.columns(2)
    fields = list(site.index)
    mid = len(fields) // 2

    with col1:
        for field in fields[:mid]:
            st.markdown(f"**{field}:** {site[field]}")

    with col2:
        for field in fields[mid:]:
            st.markdown(f"**{field}:** {site[field]}")

# -------- FLY TO ANIMATION --------
class FlyToOnClick(MacroElement):
    """Attaches a Leaflet flyTo() click handler to a marker.
    After the animation ends (moveend), the popup is automatically opened."""
    def __init__(self, marker, lat, lng, zoom=15, duration=1.5):
        super().__init__()
        self._name = "FlyToOnClick"
        self._template = Template("""
            {% macro script(this, kwargs) %}
            {{ this.marker_name }}.on('click', function(e) {
                // Store the clicked marker so moveend can open its popup
                window._flyToTarget = {{ this.marker_name }};
                {{ this.map_name }}.flyTo(
                    [{{ this.lat }}, {{ this.lng }}],
                    {{ this.zoom }},
                    {animate: true, duration: {{ this.duration }}}
                );
            });

            // One-time global moveend handler: open popup after animation ends
            if (!window._flyToMoveEndAdded_{{ this.map_name }}) {
                window._flyToMoveEndAdded_{{ this.map_name }} = true;
                {{ this.map_name }}.on('moveend', function() {
                    if (window._flyToTarget) {
                        var target = window._flyToTarget;
                        window._flyToTarget = null;
                        setTimeout(function() { target.openPopup(); }, 100);
                    }
                });
            }
            {% endmacro %}
        """)
        self.lat = lat
        self.lng = lng
        self.zoom = zoom
        self.duration = duration
        self.marker_name = marker.get_name()
        self.map_name = None  # set after adding to map

    def render(self, **kwargs):
        figure = self.get_root()
        self.map_name = list(figure._children.keys())[0] if figure else "map"
        super().render(**kwargs)


# -------- RESET VIEW CONTROL --------
class ResetViewControl(MacroElement):
    """Injects a custom Leaflet control button on the map to reset to default view."""
    def __init__(self, default_lat, default_lng, default_zoom=6, duration=1.5):
        super().__init__()
        self._name = "ResetViewControl"
        self._template = Template("""
            {% macro script(this, kwargs) %}
            (function() {
                var ResetControl = L.Control.extend({
                    options: { position: 'topright' },
                    onAdd: function(map) {
                        var btn = L.DomUtil.create('button', '');
                        btn.innerHTML = '&#x21BA;&nbsp; Reset View';
                        btn.title = 'Reset map to Thailand overview';
                        btn.style.cssText = [
                            'background: linear-gradient(135deg,#1e293b,#0f172a)',
                            'color: #60a5fa',
                            'border: 1px solid #334155',
                            'border-radius: 8px',
                            'padding: 7px 14px',
                            'font-size: 12px',
                            'font-weight: 600',
                            'font-family: Segoe UI, Arial, sans-serif',
                            'cursor: pointer',
                            'box-shadow: 0 2px 8px rgba(0,0,0,0.35)',
                            'transition: all 0.2s',
                            'margin: 10px 10px 0 0',
                            'letter-spacing: 0.3px'
                        ].join(';');
                        btn.onmouseover = function() {
                            btn.style.background = 'linear-gradient(135deg,#1e3a5f,#1e293b)';
                            btn.style.color = '#93c5fd';
                        };
                        btn.onmouseout = function() {
                            btn.style.background = 'linear-gradient(135deg,#1e293b,#0f172a)';
                            btn.style.color = '#60a5fa';
                        };
                        L.DomEvent.on(btn, 'click', function(e) {
                            L.DomEvent.stopPropagation(e);
                            window._flyToTarget = null;
                            {{ this.map_name }}.flyTo(
                                [{{ this.lat }}, {{ this.lng }}],
                                {{ this.zoom }},
                                {animate: true, duration: {{ this.duration }}}
                            );
                        });
                        return btn;
                    }
                });
                new ResetControl().addTo({{ this.map_name }});
            })();
            {% endmacro %}
        """)
        self.lat = default_lat
        self.lng = default_lng
        self.zoom = default_zoom
        self.duration = duration
        self.map_name = None

    def render(self, **kwargs):
        figure = self.get_root()
        self.map_name = list(figure._children.keys())[0] if figure else "map"
        super().render(**kwargs)

# -------- MAP --------
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom
)

# Add the reset button directly on the map
reset_ctrl = ResetViewControl(13.7367, 100.5231, default_zoom=6, duration=1.5)
reset_ctrl.map_name = m.get_name()
m.add_child(reset_ctrl)

for idx, (_, row) in enumerate(filtered_df.iterrows()):
    uid = f"site_{idx}"

    status = row.get('Status', 'Unknown')
    status_color = "#27ae60" if str(status).lower() in ["active", "open", "operational"] else "#e74c3c"

    popup_html = f"""
    <div style="width:340px; font-family: 'Segoe UI', Arial, sans-serif; font-size:13px; color:#222;">

      <!-- SUMMARY PANEL -->
      <div id="summary_{uid}">
        <div style="background:#1a1a2e; color:white; padding:10px 12px; border-radius:6px 6px 0 0;">
          <span style="font-size:15px; font-weight:bold;">📍 {row.get('Name','N/A')}</span><br>
          <span style="font-size:11px; opacity:0.8;">Layer: {row.get('Layer','N/A')} &nbsp;|&nbsp; {row.get('Category','N/A')}</span>
        </div>
        <div style="padding:10px 12px; border:1px solid #e0e0e0; border-top:none; border-radius:0 0 6px 6px; background:#fff;">
          <b>📌 Address:</b><br>
          {row.get('Address','N/A')}<br>
          <small style="color:#888;">🌐 {round(row.get('Lat',0),5)}, {round(row.get('Long',0),5)}</small><br><br>

          <b>📞 Phone:</b> {row.get('Phone','N/A')}<br>
          <b>👤 Owner:</b> {row.get('Owner','N/A')}<br><br>

          <b>🔧 Service Bays:</b> {int(row.get('Bays', 0))}<br>
          <b>🟢 Status:</b>
          <span style="background:{status_color}; color:white; padding:1px 8px; border-radius:20px; font-size:11px;">{status}</span>

          <hr style="margin:10px 0 8px 0;">
          <div style="text-align:center;">
            <button onclick="
              document.getElementById('summary_{uid}').style.display='none';
              document.getElementById('detail_{uid}').style.display='block';
            " style="
              background:#2563eb; color:white;
              border:none; padding:7px 18px;
              border-radius:6px; font-weight:bold;
              font-size:12px; cursor:pointer;
              width:100%;
            ">📋 View Full Details &rarr;</button>
          </div>
        </div>
      </div>

      <!-- DETAIL PANEL (hidden by default) -->
      <div id="detail_{uid}" style="display:none;">
        <div style="background:#2563eb; color:white; padding:10px 12px; border-radius:6px 6px 0 0; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:14px; font-weight:bold;">� Full Site Details</span>
          <button onclick="
            document.getElementById('detail_{uid}').style.display='none';
            document.getElementById('summary_{uid}').style.display='block';
          " style="background:transparent; border:1px solid rgba(255,255,255,0.6); color:white; padding:2px 8px; border-radius:4px; cursor:pointer; font-size:11px;">← Back</button>
        </div>
        <div style="padding:10px 12px; border:1px solid #e0e0e0; border-top:none; border-radius:0 0 6px 6px; background:#f9fafb; max-height:320px; overflow-y:auto;">

          <div style="background:white; border-radius:6px; padding:8px 10px; margin-bottom:8px; border-left:4px solid #1a1a2e;">
            <b style="color:#1a1a2e; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">� Location</b><br>
            <b>Name:</b> {row.get('Name','N/A')}<br>
            <b>Address:</b> {row.get('Address','N/A')}<br>
            <b>Geocode:</b> {round(row.get('Lat',0),6)}, {round(row.get('Long',0),6)}<br>
          </div>

          <div style="background:white; border-radius:6px; padding:8px 10px; margin-bottom:8px; border-left:4px solid #2563eb;">
            <b style="color:#2563eb; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">🏷️ Classification</b><br>
            <b>Layer:</b> {row.get('Layer','N/A')}<br>
            <b>Category:</b> {row.get('Category','N/A')}<br>
            <b>Sub-Category:</b> {row.get('SubCategory','N/A')}<br>
            <b>Source System:</b> {row.get('SourceSystem','N/A')}<br>
          </div>

          <div style="background:white; border-radius:6px; padding:8px 10px; margin-bottom:8px; border-left:4px solid #16a34a;">
            <b style="color:#16a34a; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">👤 Contact</b><br>
            <b>Owner:</b> {row.get('Owner','N/A')}<br>
            <b>Phone:</b> {row.get('Phone','N/A')}<br>
            <b>Email:</b> {row.get('Email','N/A')}<br>
          </div>

          <div style="background:white; border-radius:6px; padding:8px 10px; border-left:4px solid #dc2626;">
            <b style="color:#dc2626; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">⚙️ Operations</b><br>
            <b>Status:</b>
            <span style="background:{status_color}; color:white; padding:1px 8px; border-radius:20px; font-size:11px;">{status}</span><br>
            <b>Service Bays:</b> {int(row.get('Bays', 0))}<br>
            <b>Last Updated:</b> {row.get('LastUpdated','N/A')}<br>
          </div>

        </div>
      </div>

    </div>
    """

    marker = folium.Marker(
        location=[row["Lat"], row["Long"]],
        popup=folium.Popup(popup_html, max_width=380),
        tooltip=row.get("Name", ""),
        icon=folium.Icon(
            color=layer_colors.get(row["Layer"], "blue"),
            icon="info-sign"
        )
    )
    marker.add_to(m)

    # Attach smooth flyTo animation on marker click
    fly = FlyToOnClick(marker, lat=row["Lat"], lng=row["Long"], zoom=15, duration=1.5)
    fly.map_name = m.get_name()
    marker.add_child(fly)

# 🔥 IMPORTANT: key added here
map_data = st_folium(
    m,
    width="stretch",
    height=600,
    key=f"map_{st.session_state.map_key}"
)

col1, col2 = st.columns(2)
col1.metric("Active Sites", len(filtered_df))
col2.metric("Total Bay Capacity", int(filtered_df["Bays"].sum()))