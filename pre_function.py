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

# pre_processing()
# -----------------------
# Processes raw Open Street Map data and GTFS-feed to be 
# useable for sampling, routing and plotting
# -----------------------
# Input:
# - str: city
# - str: city_file
# - str: country
# - str: destination_name (always equals city for the purposes of these examples)
# - str: osm_path
# - str: gtfs_path
# - bool: osmium_avail
# - int: coord_crs
# -----------------------
# Returns:
# - gdf: boundary
# - gdf: buildings
# - gdf: origins
# - gdf: center_dest

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

    buildings = buildings[~buildings.geometry.is_empty & buildings.geometry.notna()].copy()
    boundary = boundary[~boundary.geometry.is_empty & boundary.geometry.notna()].copy()

    buildings = gpd.clip(buildings, boundary).copy()

    # get OSM-defined center points, assign the first one with point geometry and matching name (city) as center
    # this will be used as destination for "Center" travel time calculations
    centers = osm.get_data_by_custom_criteria(custom_filter={"place": ["city", "town", "village", "hamlet"]}, filter_type="keep", extra_attributes=["name"])
    center = centers[centers["name"] == destination_name].copy()
    center = center[center.geometry.geom_type == "Point"]

    # Fixing GTFS-feed
    print(f"\nFixing GTFS-feed for {city}.\n")
    path_to_new_gtfs = fix_gtfs(bbox_box, city_file, gtfs_path, coord_crs)

    # Create r5py transport network
    transport_network = r5py.TransportNetwork(f"data/osm/{city_file}.osm.pbf", [path_to_new_gtfs])

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

# origins_to_schools()
# -----------------------
# Maps sampled origins to their closest school,
# respects allocation of origins to school districts.
# -----------------------
# Input:
# - city
# - METRIC_CRS
# - COORD_CRS
# - origins_sample
# -----------------------
# Returns:
# - origins_sample_with_nearest_school

def origins_to_schools(city, origins_sample, metric_crs=2056, coord_crs=4326):

    print(f"Matching origins to schools conditional on school district...")

    # load appropriate school / school district datasets depending on city
    if city == "Bern":
        # schools
        schools_geo = gpd.read_parquet("data/parquet/oevschul_soe.parquet").to_crs(coord_crs)
        schools_geo.rename(columns={"soename": "einheit"}, inplace=True)

        # school districts
        district_url = "https://map.bern.ch/arcgis/rest/services/Geoportal/Schulkreise/MapServer/0/query?where=1=1&outFields=*&f=geojson"
        schools_dist = gpd.read_file(district_url).to_crs(coord_crs)
        schools_dist.rename(columns={"Nummer": "objid"}, inplace=True)
        schools_dist.rename(columns={"Name": "name"}, inplace=True)
    elif city == "Zürich":
        # schools
        schools_geo = gpd.read_file(f"data/gpkg/schulen_zuerich.gpkg", layer="stzh.poi_volksschule_view")

        # school districts
        schools_dist = gpd.read_file(f"data/gpkg/schulkreise_zuerich.gpkg", layer="stzh.adm_schulkreise_a")

    # clean indices
    schools_dist = schools_dist.to_crs(metric_crs).reset_index(drop=True)
    schools_geo = schools_geo.to_crs(metric_crs).reset_index(drop=True)
    origins_sample = origins_sample.to_crs(metric_crs).reset_index(drop=True)

    # join both origins and schools to their district
    origins_to_dists = gpd.sjoin(origins_sample, schools_dist[["objid", "geometry"]], how="left", predicate="within").drop(columns=["index_right"])
    schools_to_dists = gpd.sjoin(schools_geo, schools_dist[["objid", "geometry"]], how="left", predicate="within").drop(columns=["index_right"])

    ### for each district, join origins to their closest school within that district
    origins_sample_with_nearest_school_list = []

    for district_id, orig_group in origins_to_dists.groupby("objid"):
        schools_group = schools_to_dists[schools_to_dists["objid"] == district_id]
        district_origins_with_school = gpd.sjoin_nearest(orig_group, schools_group[["objectid", "einheit", "geometry"]], how="left", distance_col="distance_to_dest_meters")
        origins_sample_with_nearest_school_list.append(district_origins_with_school)

    # rowbind mapped data for all districts
    origins_sample_with_nearest_school = gpd.GeoDataFrame(pd.concat(origins_sample_with_nearest_school_list, ignore_index=True), crs=metric_crs)
    origins_sample_with_nearest_school = origins_sample_with_nearest_school.rename(columns={"objectid": "school_id"}).to_crs(coord_crs)
    
    return origins_sample_with_nearest_school, schools_geo
