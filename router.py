from datetime import datetime, timedelta
import time as pytime
import os

import pandas as pd
import geopandas as gpd

from r5py import TransportNetwork, TravelTimeMatrix, TransportMode
from osrm_routing import osrm_process, osrm_process_schools

import streamlit as st

# suppressing JAVA warning which are triggered by r5py internals
os.environ["_JAVA_OPTIONS"] = "--enable-native-access=ALL-UNNAMED"

# route_center()
# -----------------------
# Computes travel times between each origin and the destination (1) for
# departures between 6:00am and 02:00am (next day), simulating a departure for every minute for half-hour 
# intervals two / three hours spaced and (2) time-independent for car and pedestrian routing. It is assumed that when distance to
# a school is <500m, walking is used instead of driving. Returns a travel time matrix where each row represents data for a separate origin.
# Columns include worst-case (5% quantile), best-case (95% quantile), and median case (50% quantile) transit travel times and
# travel time by car (or if distance <500m) by foot.
# -----------------------
# Input:
# - str: city
# - str: city_file
# - int: METRIC_CRS
# - int: COORD_CRS
# - int: cell_size (meters)
# - gdf: origins_sample_with_nearest_school
# - gdf: boundary
# - r5py: transport_network
# -----------------------
# Returns:
# - df: travel_time_matrix_school

def route_center(city_file, date, origins_sample, destinations, metric_crs=2056):

    transport_network = TransportNetwork(f"data/osm/{city_file}.osm.pbf", [f"data/gtfs/gtfs-{city_file}.zip"])

    # compute distance to destiny point for each origin
    origins_sample["distance_to_dest_meters"] = origins_sample.to_crs(metric_crs).geometry.distance(
        destinations.to_crs(metric_crs).geometry.iloc[0]).sort_values(ascending=True)
    
    print("Routing daytime trips...")
    
    # parse date + 1 from input date
    next_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    # specify time points for which routing is done
    times = ([datetime.strptime(f"{date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(6, 19, 3)] +
        [datetime.strptime(f"{date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(18, 24, 2)] +
        [datetime.strptime(f"{next_date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(0, 3, 2)])


    t1a = pytime.time()

    # Compute transit travel time matrix for each origin x timepoint. 
    transit_matrices = []
    for time in times:
        
        t1 = pytime.time()

        transit_matrix = TravelTimeMatrix(
            transport_network=transport_network,
            origins=origins_sample,
            destinations=destinations,
            transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
            speed_walking=5.0,    # match osrm      
            max_time_walking=timedelta(minutes=40),  
            departure=time,
            departure_time_window=timedelta(minutes=30),
            percentiles=[5, 50, 95])

        # calculate "spread" variable and add time identifier
        transit_matrix["spread"] = transit_matrix["travel_time_p95"] - transit_matrix["travel_time_p5"]
        transit_matrix["departure_time"] = time
        transit_matrices.append(pd.DataFrame(transit_matrix))

        t2 = pytime.time()
        t_diff = t2 - t1

        print(f"Computed transit routes for {time}. Took {round(t_diff, 3)}s.")

    # rowbind all time-specific transit travel time matrices
    transit_matrices = pd.concat(transit_matrices, ignore_index=True)

    # save for access
    gpd.GeoDataFrame(transit_matrices).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="transit_matrix_center", driver="GPKG")

    t2a = pytime.time()

    print(f"\nDone! Took {round((t2a - t1a), 3)}s.\n")

    ##########################################################################

    # use OSRM to do the car / walking calculations, is incredibly fast. Does munich (3000 points) in 2 seconds
    combined = osrm_process(city_file, origins_sample, destinations)

    # Merge car / walking travel times to transit travel times
    travel_time_matrix_center = pd.DataFrame(transit_matrices).merge(combined, on="from_id")

    # save travel time matrix
    gpd.GeoDataFrame(travel_time_matrix_center).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="travel_time_matrix_center", driver="GPKG")
    print("Done!")

    return travel_time_matrix_center


# route_schools()
# -----------------------
# Computes travel times between each origin and their respective school (1) for
# departures between 7:00 to 7:30am, simulating a departure for every minute and
# (2) time-independent for car and pedestrian routing. It is assumed that when distance to
# a school is <500m, walking is used instead of driving. Returns a travel time matrix where each row is an origin / school combination.
# Columns include worst-case (5% quantile), best-case (95% quantile), and median case (50% quantile) transit travel times and
# travel time by car (or if distance <500m) by foot.
# -----------------------
# Input:
# - str: city
# - str: city_file
# - int: METRIC_CRS
# - int: COORD_CRS
# - int: cell_size (meters)
# - gdf: origins_sample_with_nearest_school
# - gdf: boundary
# - r5py: transport_network
# -----------------------
# Returns:
# - df: travel_time_matrix_school

def route_schools(city_file, date, origins_sample_with_nearest_school, schools_geo, coord_crs=4326):

    transport_network = TransportNetwork(f"data/osm/{city_file}.osm.pbf", [f"data/gtfs/gtfs-{city_file}.zip"])

    # representative day, 7:30am usual time for school start in Switzerland, 30min travel time + buffer reasonable
    time = datetime.strptime(f"{date} 07:00:00", "%Y-%m-%d %H:%M:%S")

    transit_matrices_school = []
    for school_id, group in origins_sample_with_nearest_school.groupby("school_id"):
        destination = schools_geo[schools_geo["objectid"] == school_id]
        destination = destination.rename(columns={"objectid": "id"})

        origins_group = group[["id", "geometry"]].copy().reset_index(drop=True)

        print(f"Computing matrix for {destination["einheit"].iloc[0]}")
        transit_matrix = TravelTimeMatrix(
            transport_network=transport_network,
            origins=origins_group,
            destinations=destination,
            transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
            speed_walking=5.0,
            max_time_walking=timedelta(minutes=20),
            departure=time,
            departure_time_window=timedelta(minutes=30),
            percentiles=[5, 50, 95])
        
        # calculate spread -> worst case - best case travel time
        transit_matrix["spread"] = transit_matrix["travel_time_p95"] - transit_matrix["travel_time_p5"]

        transit_matrices_school.append(pd.DataFrame(transit_matrix))

    transit_matrix_school = pd.concat(transit_matrices_school, ignore_index=True)
    gpd.GeoDataFrame(transit_matrix_school).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="transit_matrix_school", driver="GPKG")

    # osrm routing
    osrm_matrix_school = osrm_process_schools(city_file, origins_sample_with_nearest_school, schools_geo)

    gpd.GeoDataFrame(osrm_matrix_school).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="osrm_matrix_school", driver="GPKG")

    # travel time matrix
    travel_time_matrix_school = pd.DataFrame(transit_matrix_school).merge(osrm_matrix_school, on="from_id")

    # save travel time matrices
    gpd.GeoDataFrame(travel_time_matrix_school).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="travel_time_matrix_school", driver="GPKG")
    print("Done!")

    return travel_time_matrix_school




def route_custom(city_file, date, origins, destinations, coord_crs=4326, metric_crs=2056):
        
        # transit routing
        @st.cache_resource
        def load_network(city_file):
            return TransportNetwork(f"data/osm/{city_file}.osm.pbf",[f"data/gtfs/gtfs-{city_file}.zip"])
        
        transport_network = load_network(city_file)

        next_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        times = ([datetime.strptime(f"{date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(6, 19, 3)] +
        [datetime.strptime(f"{date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(19, 24, 2)] +
        [datetime.strptime(f"{next_date} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S") for h in range(0, 3, 2)])

        transit_matrices = []

        for time in times:

            transit_matrix = TravelTimeMatrix(
            transport_network=transport_network,
            origins=origins,
            destinations=destinations,
            transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
            speed_walking=5.0,    # match osrm      
            max_time_walking=timedelta(minutes=40),  
            departure=time,
            departure_time_window=timedelta(minutes=30),
            percentiles=[5, 50, 95])

            transit_matrix["spread"] = transit_matrix["travel_time_p95"] - transit_matrix["travel_time_p5"]
            transit_matrix["departure_time"] = time
            transit_matrices.append(pd.DataFrame(transit_matrix))

        transit_matrices = pd.concat(transit_matrices, ignore_index=True)

        # osrm routing
        osrm_matrices = []
        for dest_id, _ in destinations.iterrows():

            destination_gdf = destinations.loc[[dest_id]]

            origins_with_dist = origins.copy()
            origins_with_dist["distance_to_dest_meters"] = origins_with_dist.geometry.to_crs(metric_crs).distance(destination_gdf.geometry.to_crs(metric_crs).iloc[0])

            osrm_matrix = osrm_process(city_file, origins_with_dist, destination_gdf, skip=True)
            if osrm_matrix is not None:
                osrm_matrices.append(osrm_matrix)

        if osrm_matrices is not None:
            combined = pd.concat(osrm_matrices, ignore_index=True)
        else:
            print("No destinations and origins within scope. Exiting.")
            exit()

        # merge transit times and osrm times
        travel_time_matrix = pd.DataFrame(transit_matrices).merge(combined, on=["from_id", "to_id"])

        return travel_time_matrix