import streamlit as st
import pandas as pd
import pydeck as pdk

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Ford Geospatial Hub", page_icon="📍")

@st.cache_data
def load_data():
    # Loading the specific dataset from your folder
    df = pd.read_excel("dummy_data.xlsx")
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Long'] = pd.to_numeric(df['Long'], errors='coerce')
    df = df.dropna(subset=['Lat', 'Long'])
    df['Bays'] = pd.to_numeric(df['Bays'], errors='coerce').fillna(0)
    return df

df = load_data()

# --- DEFINE COLORS & LEGEND ---
layer_info = {
    "L1": {"label": "L1: Primary Network", "color": [0, 52, 120, 255], "desc": "Authorized Dealers"},
    "L2": {"label": "L2: Partnered Customers", "color": [40, 167, 69, 255], "desc": "PSN/Trade Club"},
    "L3": {"label": "L3: Organized IRFs", "color": [255, 150, 0, 255], "desc": "Multi-brand Chains"},
    "L4": {"label": "L4: Retail & Wholesale", "color": [23, 162, 184, 255], "desc": "Parts Retailers"},
    "L5": {"label": "L5: Unorganized Sector", "color": [220, 53, 69, 255], "desc": "Local Workshops"},
    "L6": {"label": "L6: Specialized Outlets", "color": [111, 66, 193, 255], "desc": "Battery/Oil Shops"}
}

# --- SIDEBAR: HEADER & LEGEND ---
st.sidebar.markdown("# 🇹🇭 Thailand\n### Geospatial Intelligence Hub")
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg", width=80)
st.sidebar.divider()

st.sidebar.subheader("Map Legend")
# 1. Visual Legend
for key, info in layer_info.items():
    c = info['color']
    st.sidebar.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <div style="width: 18px; height: 18px; background-color: rgba({c[0]},{c[1]},{c[2]},{c[3]/255}); border-radius: 3px; margin-right: 10px; border: 1px solid white;"></div>
            <span style="font-size: 13px;"><b>{key}</b>: {info['desc']}</span>
        </div>
        """, unsafe_allow_html=True)

st.sidebar.divider()

# 2. Layer Toggles
st.sidebar.subheader("Visibility Controls")
selected_layers = []
for key, info in layer_info.items():
    # Default to L1 and L5 for White-Space visibility
    if st.sidebar.checkbox(info['label'], value=(key in ['L1', 'L5'])):
        selected_layers.append(key)

# 3. Capacity Filter
min_bays = st.sidebar.slider("Minimum Service Bays", 0, int(df['Bays'].max()), 0)

# --- DATA PREPARATION ---
filtered_df = df[(df['Layer'].isin(selected_layers)) & (df['Bays'] >= min_bays)].copy()

# CRITICAL FIX FOR COLORS: 
# Extract RGB components into separate columns to ensure Pydeck interprets them correctly
filtered_df['r'] = filtered_df['Layer'].map(lambda x: layer_info[x]['color'][0])
filtered_df['g'] = filtered_df['Layer'].map(lambda x: layer_info[x]['color'][1])
filtered_df['b'] = filtered_df['Layer'].map(lambda x: layer_info[x]['color'][2])

# Define icon settings
ICON_URL = "https://img.icons8.com/ios-filled/100/ffffff/marker.png"
filtered_df['icon_data'] = [
    {"url": ICON_URL, "width": 100, "height": 100, "anchorY": 100} 
    for _ in range(len(filtered_df))
]

# --- MAIN MAP DISPLAY ---
# Use the main area only for the map and high-level stats
view_state = pdk.ViewState(latitude=13.7367, longitude=100.5231, zoom=6, pitch=0)

icon_layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position='[Long, Lat]',
    get_radius=5000,
    get_fill_color='[r, g, b, 200]',
    pickable=True,
)

st.pydeck_chart(pdk.Deck(
    map_style='light',
    initial_view_state=view_state,
    layers=[icon_layer],
    tooltip={
        "html": """
            <div style="font-family: sans-serif; padding: 5px;">
                <b style="font-size: 14px; color: #f0f2f6;">{Name}</b><br/>
                <b>Layer:</b> {Layer}<br/>
                <b>Bays:</b> {Bays}<br/>
                <b>Status:</b> {Status}<br/>
                <small>{Address}</small>
            </div>
        """,
        "style": {"color": "white", "backgroundColor": "#002b5e", "borderRadius": "5px"}
    }
))

# Dashboard Summary Footer
m1, m2, m3 = st.columns(3)
m1.metric("Active Sites", len(filtered_df))
m2.metric("Total Bay Capacity", int(filtered_df['Bays'].sum()))
m3.metric("Opportunity (L5)", len(filtered_df[filtered_df['Layer'] == 'L5']))