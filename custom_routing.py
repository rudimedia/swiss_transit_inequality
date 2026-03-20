import osmnx as ox
import streamlit as st
from router import route_custom
from integrated import make_city_file
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import signal

st.subheader("Check out public transit quality and quantity from your favorite flat contenders.")

# I looked up how to do this, I just couldn't get JAVA and Docker to react to normal streamlit quit commands, so defaulted to killing the session.
with st.sidebar:
    if st.button("End App"):
        os.kill(os.getpid(), signal.SIGKILL)
    st.write("Warning: This kills the process without regard to anything. You mayyy need to restart your kernel.")

# initialise origins, destinations, travel_time_matrix dataframes if not already present
if "origins" not in st.session_state:
    st.session_state.origins = gpd.GeoDataFrame(columns=["id", "address", "geometry"], geometry="geometry", crs=4326)

if "destinations" not in st.session_state:
    st.session_state.destinations = gpd.GeoDataFrame(columns=["id", "address", "geometry"], geometry="geometry", crs=4326)

if "travel_time_matrix" not in st.session_state:
    st.session_state.travel_time_matrix = None

# Let user select city, create filename-suitable version
city = st.selectbox("City", ["Zürich", "Bern", "Solothurn"])

##### FIX !!! ######
if city is None:
    city = "Zürich"

city_file = make_city_file(city)

# Let user specify date
date = st.date_input(label="Enter date", value="2025-03-13", min_value="2024-12-15", max_value="2025-12-13")

# initialise travel_time_matrix
travel_time_matrix = None

st.text(f"Note: You may specify origins and destinations within the city boundary of {city}.")

# Two columns for style
col1, col2 = st.columns([2, 4])

with col2:

    # Add origins, soft error if location cannot be found by Nominatim within city
    address = st.text_input("Enter origin address", placeholder=f"Street 23, {city}")

    if st.button("Add origin"):
        if address:
            try:
                
                # get coordinates from nominatim
                lat, lon = ox.geocode(f"{address}, {city}")

                # assign unique ID
                if len(st.session_state.origins) == 0:
                    id = 0
                else:
                    st.session_state.origins["id"].max() + 1

                # dataframe
                curr_address = gpd.GeoDataFrame({"id": id, "address": [address]}, geometry=[Point(lon, lat)], crs=4326)
                st.session_state.origins = pd.concat([st.session_state.origins, curr_address], ignore_index=True)
            except Exception:
                st.error("Could not find location")


    # Add destinations, soft error if location cannot be found by Nominatim within city
    address_dest = st.text_input("Enter destination address", placeholder=f"Street 23, {city}")

    if st.button("Add destination"):
        if address_dest:
            try:
                # get coordinates from nominatim
                lat, lon = ox.geocode(address_dest)

                # assign unique ID
                if len(st.session_state.destinations) == 0:
                    id = 0
                else:
                    st.session_state.destinations["id"].max() + 1

                # dataframe
                curr_address = gpd.GeoDataFrame({"id": [len(st.session_state.destinations)], "address": [address_dest]}, geometry=[Point(lon, lat)], crs=4326)
                st.session_state.destinations = pd.concat([st.session_state.destinations, curr_address], ignore_index=True)

            except Exception:

                st.error("Could not find location")


    # Compute travel times for custom destinations / origins
    if st.button("Compute travel times"):

        if len(st.session_state.origins) == 0:
            st.warning("Please specify at least one (valid) origin!")

        elif len(st.session_state.destinations) == 0:
            st.warning("Please specify at least one (valid) destination!")

        else:

            st.session_state.travel_time_matrix = None  # reset on each attempt

            try:

                origins = st.session_state.origins.drop_duplicates(subset="address").reset_index(drop=True)
                origins["id"] = origins.index
                result = route_custom(city_file, date.strftime("%Y-%m-%d"), origins, st.session_state.destinations)

                id_to_origin = origins.set_index("id")["address"]
                id_to_dest = st.session_state.destinations.set_index("id")["address"]
                result["from_id"] = result["from_id"].map(id_to_origin)
                result["to_id"] = result["to_id"].map(id_to_dest)
                st.session_state.travel_time_matrix = result.rename(columns={"from_id": "Origin", "to_id": "Destination", "travel_time_p5": "Transit: best", "travel_time_p50": "Transit: median", "travel_time_p95": "Transit: worst", "spread": "Transit: spread", "departure_time": "Departure Time", "travel_time": "Car / walking time"})

            except Exception as e:

                st.error(f"Routing failed: {e}")


with col1:
    with st.container():
        st.markdown("**From:**")
    for i, row in st.session_state.origins.iterrows():
        str_column, button_column = st.columns([4, 1])
        str_column.markdown(row["address"])
        if button_column.button("X", key=f"del_origin_{i}"):
            st.session_state.origins = st.session_state.origins.drop(index=i).reset_index(drop=True)
            st.rerun()
    st.divider()        

    with st.container():
        st.markdown("**To:**")
    for j, row in st.session_state.destinations.iterrows():
        str_column, button_column = st.columns([4, 1])
        str_column.markdown(row["address"])
        if button_column.button("X", key=f"del_dest_{j}"):
            st.session_state.destinations = st.session_state.destinations.drop(index=j).reset_index(drop=True)
            st.rerun()
    st.divider()        

# show toggle if travel_time_matrix exists
if st.session_state.travel_time_matrix is not None:
    show_ratios = st.toggle("Show ratios")
    st.text("Ratios represent (transit travel time / car travel time)")

    # toggle between raw times / ratios
    if show_ratios:
        ratio_df = st.session_state.travel_time_matrix.copy()
        ratio_df["Transit: best (ratio)"] = ratio_df["Transit: best"] / ratio_df["Car / walking time"]
        ratio_df["Transit: median (ratio)"] = ratio_df["Transit: median"] / ratio_df["Car / walking time"]
        ratio_df["Transit: worst (ratio)"] = ratio_df["Transit: worst"] / ratio_df["Car / walking time"]
        st.dataframe(ratio_df.sort_values(["Origin", "Destination"])[["Origin", "Destination", "Departure Time", "Transit: best (ratio)", "Transit: median (ratio)", "Transit: worst (ratio)"]])
    else:
        st.dataframe(st.session_state.travel_time_matrix.sort_values(["Origin", "Destination"])[["Origin", "Destination", "Departure Time", "Transit: best", "Transit: median", "Transit: worst", "Car / walking time"]])