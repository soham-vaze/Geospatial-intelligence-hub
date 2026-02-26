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

# -------- LAYER CONFIG --------
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
m = folium.Map(location=[13.7367, 100.5231], zoom_start=6)

for _, row in filtered_df.iterrows():
    folium.Marker(
        location=[row["Lat"], row["Long"]],
        popup=f"""
        <b>{row['Name']}</b><br>
        Layer: {row['Layer']}<br>
        Bays: {row['Bays']}<br>
        Status: {row.get('Status','N/A')}<br>
        Address: {row.get('Address','N/A')}
        """,
        icon=folium.Icon(
            color=layer_colors.get(row["Layer"], "blue"),
            icon="info-sign"
        )
    ).add_to(m)

st_folium(m, width="stretch", height=600)

# -------- METRICS --------
col1, col2, col3 = st.columns(3)
col1.metric("Active Sites", len(filtered_df))
col2.metric("Total Bay Capacity", int(filtered_df["Bays"].sum()))
col3.metric("L5 Opportunities",
            len(filtered_df[filtered_df["Layer"] == "L5"]))