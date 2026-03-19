import re

import streamlit as st
import pydeck as pdk

import geopandas as gpd
import pandas as pd

from matplotlib.colors import LinearSegmentedColormap, Normalize
import matplotlib.pyplot as plt



st.subheader("Public transport travel times, relative to car.")
st.text("")

col1, col2, col3 = st.columns([1, 4, 1])

with col1:

    city = st.selectbox("City", ["Zürich", "Bern", "Solothurn"])
    city_file = re.sub(r'[^\w\-.]', '_', city).strip().replace(' ', '_')

    # create dict with options and internal variable names
    dvs = {"Median": "p50", "Worst": "p95", "Best": "p5", "Spread": "sp"}
    # use values as options and keys as label
    dependent_variable = st.selectbox("Dependent variable", options=dvs.values(), format_func = lambda x: {value: key for key, value in dvs.items()}[x])

    if dependent_variable == "p50":
        dv = "ratio_p50"
    elif dependent_variable == "p5":
        dv = "ratio_p5"
    elif dependent_variable == "p95":
        dv = "ratio_p95"
    elif dependent_variable == "sp":
        dv = "spread"

    # create dict with options and internal variable names
    filters = ["Day", "Night"]

    # only allow selection of "School" if city is not Solothurn
    if city != "Solothurn":
        filters.append("School")

    # use values as options and keys as label
    filter_state = st.selectbox("Day Center / Night Center / Schools (7am)", options=filters)

# read data 
@st.cache_data
def load_data(city_file):
    data = pd.read_pickle(f"data/pickle/{city_file}_to_plot.pkl").to_crs(4326)
    keep_cols = ["ratio_p5", "ratio_p50", "ratio_p95", "spread", "geometry_plot", "plot_type"]
    data = data[keep_cols].rename(columns={"geometry_plot": "geometry"})
    bbox = gpd.read_file(f"data/gpkg/{city_file}_data.gpkg", layer="boundary")
    return data, bbox

data_full, bbox = load_data(city_file)

# filter data dependent on user selection
data = data_full[data_full["plot_type"] == filter_state.lower()]

# color mapping
cmap = LinearSegmentedColormap.from_list(
    "green_blue_red",
    ["#0B4D03", "#1BA308", "#0B81E3", "#085DA3", "#9608A3", "#A30808", "#850505"]
)
norm = Normalize(vmin=0.5, vmax=4.0)

rgba = cmap(norm(data[dv].clip(0.5, 4.0)))

data = data.copy()
data.loc[:, "color"] = (rgba * 255).astype(int).tolist()

# color bar
fig, ax = plt.subplots(figsize=(0.1,1.5))
plt.colorbar(plt.cm.ScalarMappable(norm, cmap), cax=ax)

with col2:

    # pydeck
    view_state = pdk.ViewState(latitude=bbox["lat"].iloc[0], longitude=bbox["lon"].iloc[0], zoom=14)
    layer = pdk.Layer("GeoJsonLayer", data=data, get_fill_color="color", opacity=1, get_radius=5, radius_min_pixels=3)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_style="light",))

with col3:

    # color legend
    st.pyplot(fig)
    st.text("4 = Public transport takes 4+ times as long as traveling by car, 0.5 = Public transport takes half (or less than half) as long as by car.")
