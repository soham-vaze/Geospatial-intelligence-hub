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
    df = pd.read_excel("dummy_data.xlsx")
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

# -------- SIDEBAR STYLING --------
st.markdown("""
<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg", width=80)
st.sidebar.markdown("### Thailand Hub\n**Geospatial Intelligence POC**")
st.sidebar.divider()

# -------- FILTERS --------
selected_layers = []
for layer, (_, hex_color, label) in layer_meta.items():
    if st.sidebar.checkbox(f"{layer} - {label}", value=(layer in ['L1', 'L5']), key=f"chk_{layer}"):
        selected_layers.append(layer)

min_bays = st.sidebar.slider("Min. Service Bays", 0, int(df["Bays"].max()), 0)
filtered_df = df[(df["Layer"].isin(selected_layers)) & (df["Bays"] >= min_bays)]

# -------- RESET VIEW BUTTON CLASS --------
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
                            map.flyTo([{{ this.lat }}, {{ this.lng }}], {{ this.zoom }}, {animate: true, duration: 1.5});
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
m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="cartodbpositron")
m.add_child(ResetViewControl(13.7367, 100.5231, 6))

for idx, (_, row) in enumerate(filtered_df.iterrows()):
    uid = f"site_{idx}"
    status = str(row.get('Status', 'Unknown'))
    status_bg = "#27ae60" if status.lower() == "active" else "#e74c3c" if status.lower() == "inactive" else "#95a5a6"
    
    # Building the dynamic Detail Table for "View More"
    detail_rows = "".join([f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 5px; font-weight: bold; color: #555; font-size: 11px;">{col}</td>
            <td style="padding: 5px; color: #222; font-size: 11px;">{row[col]}</td>
        </tr>
    """ for col in row.index])

    popup_html = f"""
    <div style="width:340px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
      <div id="summary_{uid}">
        <div style="background:#1a1a2e; color:white; padding:12px; border-radius:8px 8px 0 0;">
          <div style="font-size:16px; font-weight:bold; margin-bottom:2px;">{row.get('Name','N/A')}</div>
          <div style="font-size:11px; opacity:0.8;">{row.get('Layer')} | {row.get('Sub-Category')}</div>
        </div>
        
        <div style="padding:15px; border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:white;">
          <div style="margin-bottom:8px;">
            <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">📍 Address & Geocode</span><br>
            <span style="font-size:12px;">{row.get('Address','N/A')}</span><br>
            <span style="font-size:10px; color:#3b82f6; font-weight:bold;">{row.get('Lat')}, {row.get('Long')}</span>
          </div>
          
          <div style="margin-bottom:8px;">
            <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">📞 Contact Details</span><br>
            <span style="font-size:12px;"><b>Mgr:</b> {row.get('Owner / Manager','N/A')}</span><br>
            <span style="font-size:12px;"><b>Phone:</b> {row.get('Phone','N/A')} | <b>Email:</b> {row.get('Email','N/A')}</span>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
             <div>
                <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">Status</span><br>
                <span style="background:{status_bg}; color:white; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:bold;">{status.upper()}</span>
             </div>
             <div style="text-align:right;">
                <span style="font-size:11px; color:#888; text-transform:uppercase; font-weight:bold;">Last Updated</span><br>
                <span style="font-size:11px;">{row.get('Source System')} ({row.get('Last Updated')})</span>
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

      <div id="detail_{uid}" style="display:none;">
        <div style="background:#2563eb; color:white; padding:10px; border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:bold; font-size:13px;">Full System Profile</span>
          <button onclick="
            document.getElementById('detail_{uid}').style.display='none';
            document.getElementById('summary_{uid}').style.display='block';
            this.closest('.leaflet-popup-content-wrapper').parentElement._popup.update();
          " style="background:rgba(255,255,255,0.2); border:1px solid white; color:white; padding:2px 8px; border-radius:4px; cursor:pointer; font-size:10px;">&larr; BACK</button>
        </div>
        <div style="padding:0; border:1px solid #ddd; background:#fcfcfc; max-height:300px; overflow-y:auto; border-radius:0 0 8px 8px;">
          <table style="width:100%; border-collapse: collapse;">
            {detail_rows}
          </table>
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
st_folium(m, width="100%", height=650, key=f"map_{st.session_state.map_key}")

c1, c2, c3 = st.columns(3)
c1.metric("Active Sites", len(filtered_df))
c2.metric("Total Bays", int(filtered_df["Bays"].sum()))
c3.metric("L5 Priority Targets", len(filtered_df[filtered_df['Layer'] == 'L5']))