from pathlib import Path
import pandas as pd
import docker
import requests
import numpy as np
import time
import shutil

client = docker.from_env()

def setup_osrm(city_file, mode, skip=False):
    # define volume to mount to and copy map data to subdirectories
    volumes = {str(Path("data").resolve()): {"bind": "/data", "mode": "rw"}}
    link_to_osrm = "ghcr.io/project-osrm/osrm-backend"
    shutil.copy2(f"data/osm/{city_file}.osm.pbf", f"data/osm/osrm_{mode}/{city_file}.osm.pbf")
    base = f"/data/osm/osrm_{mode}/{city_file}"

    # working around osrm api inconsistency, driving == car
    if mode == "driving":
        lua_profile = "car"
    else:
        lua_profile = "foot"

    # Doing pre-processing on the open street map data for routing, option to skip (used for custom routes)
    if skip == False:

        print("\nMaking OSM routable...")
        client.containers.run(link_to_osrm, f"osrm-extract -p /opt/{lua_profile}.lua {base}.osm.pbf", volumes=volumes, remove=True, platform="linux/amd64")
        client.containers.run(link_to_osrm, f"osrm-partition {base}.osrm", volumes=volumes, remove=True, platform="linux/amd64")
        client.containers.run(link_to_osrm, f"osrm-customize {base}.osrm", volumes=volumes, remove=True, platform="linux/amd64")

    # starting server 
    print("Starting server...")

    if mode == "driving":
        port = 5001
    else:
        port = 5002

    # start osrm in docker container
    container = client.containers.run(link_to_osrm, f"osrm-routed --algorithm mld --max-table-size 20000 {base}.osrm", volumes=volumes, ports={"5000/tcp": port}, detach=True, platform="linux/amd64")
    
    # wait so that osrm is up and running
    time.sleep(2)
    print(f"Server running on port {port}, container: {container.id[:12]}")

    return container

# function: stops an existing docker container
def stop_osrm(container):
    container.stop()
    container.remove()
    print("Stopped server")

# function: uses an existing docker container to compute routes from many points to one destination
def osrm_route(origins, destination, mode, coord_crs=4326):

    # working around osrm api inconsistency, driving == car
    if mode == "driving":
        lua_profile = "car"
    else:
        lua_profile = "foot"

    if mode == "driving":
        host = "http://localhost:5001"
    else:
        host = "http://localhost:5002"

    origins = origins.to_crs(coord_crs)
    destination = destination.to_crs(coord_crs)
    all_points = [(p.x, p.y) for p in origins.geometry]
    all_points.append((destination.geometry.x.iloc[0], destination.geometry.y.iloc[0]))
    coords_str = ";".join([f"{lon},{lat}" for lon, lat in all_points])

    response = requests.get(f"{host}/table/v1/{lua_profile}/{coords_str}", params={"destinations": str(len(all_points) - 1)})
    durations = np.array(response.json()["durations"]).flatten()[:-1] / 60

    return origins[["id"]].rename(columns={"id": "from_id"}).assign(travel_time=durations)

def osrm_process(city_file, origins_sample, destinations, skip=False):
    car_container = setup_osrm(city_file, mode="driving", skip=skip)
    walk_container = setup_osrm(city_file, mode="foot", skip=skip)
    
    car_matrix = None
    walking_matrix = None

    print("Computing car routes...")
    try:
        origins_driving = origins_sample[origins_sample["distance_to_dest_meters"] > 500]
        if len(origins_driving) > 0:
            car_matrix = osrm_route(origins=origins_driving, destination=destinations, mode="driving")
            car_matrix["travel_time"] += 10
    finally:
        stop_osrm(car_container)

    print("Computing pedestrian routes...")
    try:
        origins_walking = origins_sample[origins_sample["distance_to_dest_meters"] <= 500]
        if len(origins_walking) > 0:
            walking_matrix = osrm_route(origins=origins_walking, destination=destinations, mode="foot")
    finally:
        stop_osrm(walk_container)

    # Combine whichever matrices exist
    osrm_matrices = []
    if car_matrix is not None:
        osrm_matrices.append(car_matrix)
    if walking_matrix is not None:
        osrm_matrices.append(walking_matrix)

    if osrm_matrices is not None:
        combined = pd.concat(osrm_matrices, ignore_index=True)

    if combined is not None and "to_id" not in combined.columns:
        combined["to_id"] = destinations["id"].iloc[0]

    return combined

def osrm_process_schools(city_file, origins_sample, destinations):
    car_container = setup_osrm(city_file, mode="driving")
    walk_container = setup_osrm(city_file, mode="foot")

    osrm_matrices = []
    try:
        for school_id, group in origins_sample.groupby("school_id"):
            destination = destinations[destinations["objectid"] == school_id].rename(columns={"objectid": "id"})
            origins_group = group[["id", "geometry", "distance_to_dest_meters"]].copy().reset_index(drop=True)

            car_matrix = None
            walking_matrix = None

            origins_driving = origins_group[origins_group["distance_to_dest_meters"] > 500]
            if len(origins_driving) > 0:
                car_matrix = osrm_route(origins=origins_driving, destination=destination, mode="driving")
                car_matrix["travel_time"] += 10

            origins_walking = origins_group[origins_group["distance_to_dest_meters"] <= 500]
            if len(origins_walking) > 0:
                walking_matrix = osrm_route(origins=origins_walking, destination=destination, mode="foot")

            parts = [m for m in [car_matrix, walking_matrix] if m is not None]
            if parts:
                combined = pd.concat(parts, ignore_index=True)
                combined["to_id"] = destination["id"].iloc[0]
                osrm_matrices.append(combined)

    finally:
        stop_osrm(car_container)
        stop_osrm(walk_container)

    return pd.concat(osrm_matrices, ignore_index=True) if osrm_matrices else None