import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Ford Geospatial Hub")

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

# -------- LAYER COLORS --------
layer_colors = {
    "L1": "blue",
    "L2": "green",
    "L3": "orange",
    "L4": "cadetblue",
    "L5": "red",
    "L6": "purple",
}

# -------- SIDEBAR --------
st.sidebar.title("Thailand Geospatial Hub")
st.sidebar.divider()

st.sidebar.subheader("Legend")
for layer, color in layer_colors.items():
    st.sidebar.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:6px;">
            <div style="width:15px;height:15px;background:{color};
                        margin-right:8px;border-radius:3px;"></div>
            <span>{layer}</span>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.divider()

selected_layers = st.sidebar.multiselect(
    "Select Layers",
    options=list(layer_colors.keys()),
    default=list(layer_colors.keys())
)

min_bays = st.sidebar.slider(
    "Minimum Service Bays",
    0,
    int(df["Bays"].max()),
    0
)

filtered_df = df[
    (df["Layer"].isin(selected_layers)) &
    (df["Bays"] >= min_bays)
]

# -------- MAP --------
m = folium.Map(
    location=[13.7367, 100.5231],
    zoom_start=6,
    tiles="CartoDB positron"
)

for _, row in filtered_df.iterrows():

    popup_html = f"""
    <div style="width:350px; font-family: Arial; font-size:13px;">
        <h4 style="margin-bottom:8px;">{row.get('Name','N/A')}</h4>
        
        <b>Full Address:</b><br>
        {row.get('Address','N/A')}<br>
        <b>Geocode:</b> {row.get('Lat','N/A')}, {row.get('Long','N/A')}<br><br>
        
        <b>Category:</b> {row.get('Category','N/A')}<br>
        <b>Sub-Category:</b> {row.get('SubCategory','N/A')}<br><br>
        
        <b>Contact Details:</b><br>
        📞 {row.get('Phone','N/A')}<br>
        📧 {row.get('Email','N/A')}<br>
        👤 {row.get('Owner','N/A')}<br><br>
        
        <b>Operating Status:</b> {row.get('Status','Unknown')}<br>
        <b>Source System:</b> {row.get('SourceSystem','N/A')}<br>
        <b>Last Updated:</b> {row.get('LastUpdated','N/A')}
        
        <hr style="margin-top:10px;">
        <i>Scroll below map for complete details</i>
    </div>
    """

    folium.Marker(
        location=[row["Lat"], row["Long"]],
        popup=folium.Popup(popup_html, max_width=400),
        icon=folium.Icon(
            color=layer_colors.get(row["Layer"], "blue"),
            icon="info-sign"
        )
    ).add_to(m)

map_data = st_folium(m, width="stretch", height=600)

# -------- CAPTURE CLICK --------
selected_location = None

if map_data and map_data.get("last_object_clicked"):
    clicked = map_data["last_object_clicked"]

    lat = clicked.get("lat")
    lng = clicked.get("lng")

    # Match clicked location to dataframe
    selected_location = filtered_df[
        (filtered_df["Lat"].round(5) == round(lat, 5)) &
        (filtered_df["Long"].round(5) == round(lng, 5))
    ]

# -------- VIEW MORE SECTION --------
if selected_location is not None and not selected_location.empty:
    loc = selected_location.iloc[0]

    st.divider()
    st.subheader(f"📍 {loc['Name']} - Detailed Information")

    with st.expander("View More Details", expanded=True):
        for col in df.columns:
            st.write(f"**{col}:** {loc[col]}")

# -------- METRICS --------
col1, col2 = st.columns(2)
col1.metric("Active Sites", len(filtered_df))
col2.metric("Total Bay Capacity", int(filtered_df["Bays"].sum()))
# col3.metric("L5 Opportunities",
#             len(filtered_df[filtered_df["Layer"] == "L5"]))