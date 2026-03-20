import subprocess
import warnings
import os
import shutil
from pathlib import Path

import pandas as pd
import geopandas as gpd
from shapely import make_valid, box
import osmnx as ox
from pyrosm import OSM

import r5py

from import_zipfile import fix_gtfs


# Using pyrosm throws two chained assignment errors within pyrosm.py (line 109) and user_defined.py (line 58) 
# which are both calling functions from two separate .pyx files. Within these files, I could not find chained assignment.
# I choose to ignore and suppress these warnings as they are non-breaking
warnings.filterwarnings("ignore", category=pd.errors.ChainedAssignmentError)
# suppressing JAVA warning which are triggered by r5py internals
os.environ["_JAVA_OPTIONS"] = "--enable-native-access=ALL-UNNAMED"



def pre_processing(city, city_file, country, destination_name, osm_path, gtfs_path, osmium_avail="True", coord_crs=4326):

    place = f"{city}, {country}"

    print(f"\nPreprocessing maps and transit data for: {place}.\n")

    # get city boundary from osmnx / nominatim
    print(f"\nGetting administrative boundary from ox.\n")
    boundary = ox.geocode_to_gdf(place)
    boundary.to_file(f"data/gpkg/{city_file}_data.gpkg", layer="boundary", driver="GPKG")

    # create square boundary box from polygon boundary
    west, south, east, north = boundary.total_bounds
    bbox = f"{west},{south},{east},{north}"
    bbox_box = box(west, south, east, north)

    # clip OSM file, error if Osmium is not available
    if osmium_avail == "True":
        print("Clipping OSM data to administrative boundary...")
        osm_path = Path(f"data/osm/{city_file}.osm.pbf")
        osmium_path = shutil.which("osmium")

        if osmium_path is None:
            raise RuntimeError("Osmium not found. Please install osmium-tool and ensure it is on your PATH.\nmacOS:  brew install osmium-tool\nLinux:  sudo apt install osmium-tool\nconda:  conda install -c conda-forge osmium-tool." \
            "If you are on Windows, use the precompiled city-level osm.pbf files provided through the university cloud and use '--osmium False'.")

        subprocess.run([osmium_path, "extract", "-b", bbox, "-o", str(osm_path), "data/osm/switzerland-latest.osm.pbf", "--overwrite"], check=True)
    
    ##### get buildings
    # 1. load clipped OSM file
    # 2. extract buildings
    # 3. match crs, fix geometries, drop empty
    # 4. Keep buildings within boundary
    print(f"\nGetting building polygons from OSM.\n")

    osm = OSM(f"data/osm/{city_file}.osm.pbf")
    buildings = osm.get_buildings()
    buildings = buildings.to_crs(boundary.crs)
    buildings["geometry"] = buildings.geometry.apply(make_valid)
    boundary["geometry"] = boundary.geometry.apply(make_valid)
    # buildings = buildings[~buildings.geometry.is_empty & buildings.geometry.notna()].copy()
    # boundary = boundary[~boundary.geometry.is_empty & boundary.geometry.notna()].copy()
    buildings = gpd.clip(buildings, boundary).copy()

    # get OSM-defined center points, assign the first one with point geometry and matching name (city) as center
    # this will be used as destination for "Center" travel time calculations
    centers = osm.get_data_by_custom_criteria(custom_filter={"place": ["city", "town", "village", "hamlet"]}, filter_type="keep", extra_attributes=["name"])
    center = centers[centers["name"] == destination_name].copy()
    center = center[center.geometry.geom_type == "Point"]

    # Fixing GTFS-feed
    print(f"\nFixing GTFS-feed for {city}.\n")
    fix_gtfs(bbox_box, city_file, gtfs_path, coord_crs)

    # Create r5py transport network
    transport_network = r5py.TransportNetwork(f"data/osm/{city_file}.osm.pbf", [f"data/gtfs/gtfs-{city_file}.zip"])

    # Use representative point for routing (both irigins and center), snap to transport network (make reachable)
    # ...drop if cannot be snapped to network 
    origins = buildings.copy()
    origins["geometry"] = origins.geometry.representative_point()
    origins["geometry"] = transport_network.snap_to_network(origins["geometry"])

    center_dest = center.copy()
    center_dest["geometry"] = transport_network.snap_to_network(center_dest["geometry"])
    
    origins = origins[origins.geometry.is_empty == False].copy()
    center_dest = center_dest[center_dest.geometry.is_empty == False].copy()

    # save for later access 
    buildings.to_file(f"data/gpkg/{city_file}_data.gpkg", layer="buildings", driver="GPKG")
    origins.to_file(f"data/gpkg/{city_file}_data.gpkg", layer="origins", driver="GPKG")
    center_dest.to_file(f"data/gpkg/{city_file}_data.gpkg", layer="destinations", driver="GPKG")

    return boundary, buildings, origins, center_dest
