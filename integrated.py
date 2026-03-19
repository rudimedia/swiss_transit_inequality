import argparse

# Available cities / plots / dates
AVAIL_CITIES = ["Bern", "Zürich", "Solothurn"]
SCHOOLS_LIST = ["Bern", "Zürich"]
DATE_RANGE = ["2024-12-15", "2025-12-13"]
SKIP_LIST = ["pre", "routing", "plotting"]
PLOT_LIST = ["day", "night", "school"]

# give description for integrated.py, parse user arguments
parser = argparse.ArgumentParser(
    description=(
        "Transit accessibility analysis pipeline. "
        "Computes travel time matrices from residential buildings to city centers and schools "
        "using public transit as well as by car and foot. Returns computed travel time matrices "
        "as well as (optionally) visualisations in form of pdf plots."), 
        epilog=(
        "Example usage:\n"
        "  python integrated.py --city Zürich --date 2025-03-13 --cell 100 --plot day night\n"
        "  python integrated.py --city Bern --schools True --skip plotting\n"), 
        formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument("--city", help=f"Select any of {AVAIL_CITIES}.")
parser.add_argument("--date", default="2025-03-13", help=f"Choose any date between {DATE_RANGE}.")
parser.add_argument("--schools", default="False", help=f"School data available for {SCHOOLS_LIST}. Specify True or False.")
parser.add_argument("--cell", default=100, help="Grid cell size in meters, only numeric allowed, no 'm' or 'meters' necessary.")
parser.add_argument("--osmium", default="True", help="['True', 'False']: Is Osmium-Tool available on your device? If not, please use the precomputed .osm.pbf files for each city and copy them to the correct folder, see readme.md.")
parser.add_argument("--skip", nargs="+", default=[], help=f"Skip any of {SKIP_LIST}. This is meant for debugging and can only be done if the steps that are being skipped have been run already")
parser.add_argument("--plot", nargs="+", default=[], help=f"Plot any of {PLOT_LIST}. Default is all.")
arguments = parser.parse_args()

# import all necessary functions
from pre_function import pre_processing, load_previous_pre
from sampler import grid_sampler
from router import origins_to_schools, route_schools, route_center
from plotter import plot_list, plotter

import re
import os

# suppressing JAVA warning which are triggered by r5py internals
os.environ["_JAVA_OPTIONS"] = "--enable-native-access=ALL-UNNAMED"

COORD_CRS = 4326
METRIC_CRS = 2056
CELL_SIZE = float(arguments.cell)

city = arguments.city
schools = arguments.schools
date = arguments.date
skip = arguments.skip
which_plots = arguments.plot
osmium_avail = arguments.osmium

# make city name suitable for filenames / terminal commands
city_file = re.sub(r'[^\w\-.]', '_', city).strip().replace(' ', '_')

# check if user inputs are valid, if any is not, exit
if city not in AVAIL_CITIES:
    print(f"Please use a city from {AVAIL_CITIES} or use --help.")
    exit()

for s in skip:
    if s not in SKIP_LIST:
        print(f"{s} cannot be skipped, use --help for more.")
        exit()

for p in which_plots:
    if p not in PLOT_LIST:
        print(f"{p} is not a valid argument, use --help for more.")
        exit()

if schools != "False" and city not in SCHOOLS_LIST:
    print(f"No school data available for {city}. Please choose from {SCHOOLS_LIST}.")
    exit()

# create folder structure (or leave as-is if already existent)
for directory in ["data/gpkg", "data/osm", "data/plots", "data/pickle", "data/parquet", "data/gtfs", "data/osm/osrm_driving", "data/osm/osrm_foot", f"plots/{city_file}"]:
    os.makedirs(directory, exist_ok=True)

#################################################################################
# pre_processing()
# -----------------------
# Input:
# - METRIC_CRS
# - city
# - destination name (optional)
# -----------------------
# Output:
# - buildings (polygons)
# - origins (points, snapped to network)
# - destinations (only one, snapped to network)

if "pre" not in skip:
    boundary, buildings, origins, destinations = pre_processing(city, city_file, destination_name=city, osmium_avail=osmium_avail, coord_crs=COORD_CRS)
else:
    boundary, buildings, origins, destinations = load_previous_pre(city_file)

#################################################################################

# grid_sample()
# -----------------------
# Input:
# - city
# - origins
# - boundary
# - cell_size
# - METRIC_CRS
# - COORD_CRS
# -----------------------
# Returns:
# - origins_sample

origins_sample = grid_sampler(origins, boundary, CELL_SIZE, METRIC_CRS, COORD_CRS)

#################################################################################

# origins_to_schools()
# -----------------------
# Input:
# - city
# - METRIC_CRS
# - COORD_CRS
# - origins_sample
# -----------------------
# Returns:
# - origins_sample_with_nearest_school
# - schools_geo

if schools != "False":
    origins_sample_with_nearest_school, schools_geo = origins_to_schools(city, origins_sample, METRIC_CRS, COORD_CRS)

# route_schools()
# -----------------------
# Input:
# - city
# - city_file
# - METRIC_CRS
# - COORD_CRS
# - cell_size
# - origins_sample_with_nearest_school
# - schools_geo
# - boundary
# -----------------------
# Returns:
# - travel_time_matrix_school

if "routing" not in skip:
    if schools == "True":
        travel_time_matrix_school = route_schools(city_file, date, origins_sample_with_nearest_school, schools_geo, COORD_CRS)
        
    

# route_center()
# -----------------------
# Input:
# - city
# - city_file
# - origins_sample
# - METRIC_CRS
# - COORD_CRS
# -----------------------
# Returns:
# - travel_time_matrix_day
# - travel_time_matrix_night


    travel_time_matrix = route_center(city_file, date, origins_sample, destinations, METRIC_CRS)


# plot_list()
# -----------------------
# Input:
# - city_file
# - dest_type
# - case
# -----------------------
# Output:
# - plot_list
# - transit_lines

if "plot" not in skip:
    to_plot, transit_lines = plot_list(city_file, boundary, origins, buildings, which_plots, metric_crs=2056)

# plotter()
# -----------------------
# Input:
# - str: city
# - str: city_file
# - gdf: to_plot
# - gdf: transit_lines
# -----------------------
# Output:
# - None, creates pdf files

    plotter(city_file, to_plot, transit_lines)