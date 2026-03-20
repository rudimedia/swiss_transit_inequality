import argparse
import re
import os
import shutil

# Available countries / cities / plots / dates
COUNTRY = "Switzerland"
AVAIL_CITIES = ["Bern", "Zürich", "Solothurn"]
SCHOOLS_LIST = ["Bern", "Zürich"]
DATE_RANGE = ["2024-12-15", "2025-12-13"]
SKIP_LIST = ["pre", "routing", "plotting"]
PLOT_LIST = ["day", "night", "school"]

# CRS constants
COORD_CRS = 4326
METRIC_CRS = 2056

def make_city_file(city):
    city_file = re.sub(r'[^\w\-.]', '_', city).strip().replace(' ', '_').replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").lower()
    return city_file


def main():
    # Suppress JAVA warnings (triggered by r5py)
    os.environ["_JAVA_OPTIONS"] = "--enable-native-access=ALL-UNNAMED"

    # Import only if script is run as itself (slower import)
    print("Importing required libraries...")
    from pre_function import pre_processing
    from sampler import grid_sampler
    from router import origins_to_schools, route_schools, route_center
    from plotter import plot_list, plotter
    from geopandas import read_file, list_layers



    # give description for integrated.py, parse user arguments
    parser = argparse.ArgumentParser(description=("Transit accessibility analysis pipeline. "
            "Computes travel time matrices from residential buildings to city centers and schools "
            "using public transit as well as by car and foot. Returns computed travel time matrices "
            "as well as (optionally) visualisations in form of pdf plots."), 

            epilog=("Example usage:"
            "  python integrated.py --city Zürich --date 2025-03-13 --cell 100 --plot day night"
            "  python integrated.py --city Bern --schools True --skip plotting"), 

            formatter_class=argparse.RawDescriptionHelpFormatter)

    # Specify possible user inputs
    parser.add_argument("--city", help=f"Select any of {AVAIL_CITIES}.")
    parser.add_argument("--date", default="2025-03-13", help=f"Choose any date between {DATE_RANGE}.")
    parser.add_argument("--schools", default="False", help=f"School data available for {SCHOOLS_LIST}. Specify True or False.")
    parser.add_argument("--cell", default=100, help="Grid cell size in meters, only numeric allowed, no 'm' or 'meters' necessary.")
    parser.add_argument("--osmium", default="True", help="['True', 'False']: Is Osmium-Tool available on your device? If not, please use the precomputed .osm.pbf files for each city and copy them to the correct folder, see readme.md.")
    parser.add_argument("--skip", nargs="+", default=[], help=f"Skip any of {SKIP_LIST}. This is meant for debugging and can only be done if the steps that are being skipped have been run already")
    parser.add_argument("--plot", nargs="+", default=[], help=f"Plot any of {PLOT_LIST}. Default is all.")

    # Read user inputs
    arguments = parser.parse_args()

    city = arguments.city
    schools = arguments.schools
    date = arguments.date
    skip = arguments.skip
    which_plots = arguments.plot
    osmium_avail = arguments.osmium
    CELL_SIZE = float(arguments.cell)

    ### check if user inputs are valid, if any is not, exit
    if city not in AVAIL_CITIES or city == None:

        print(f"Please use a city from {AVAIL_CITIES} or use --help.")
        exit()

    # filename version
    city_file = make_city_file(city)

    for s in skip:

        if s not in SKIP_LIST:
            print(f"{s} cannot be skipped, use --help for more.")
            exit()


    for p in which_plots:

        if p not in PLOT_LIST:
            print(f"{p} is not a valid argument, use --help for more.")
            exit()

    # general (logical) check of whether school data is - in principle - available for a given city
    if schools != "False" and city not in SCHOOLS_LIST:

        print(f"No school data available for {city}. Please choose from {SCHOOLS_LIST}.")
        exit()

    # Set global paths for OSM data and GTFS file
    OSM_PATH = f"data/osm/{COUNTRY.lower()}-latest.osm.pbf"
    GTFS_PATH = "data/gtfs/gtfs_fp2025_2024-09-02.zip"

    folders = ["data/gpkg", "data/osm", "data/pickle", "data/parquet", "data/gtfs", "data/osm/osrm_driving", "data/osm/osrm_foot", "plots/bern", "plots/zuerich", "plots/solothurn"]

    # create folder structure (or leave as-is if already existent)
    for directory in folders:
        os.makedirs(directory, exist_ok=True)

    for folder in folders:
        if os.path.exists(folder) != True:
            print("\n[WARNING] Folder creation failed. Check permissions. Else, resort to readme.md\n")
            exit()

    print("\nFolders created / already exist!\n")

    # copy user files into correct subdirectories
    # verify copying was successfull 
    required_files = {f"{COUNTRY.lower()}-latest.osm.pbf": OSM_PATH, "gtfs_fp2025_2024-09-02.zip": GTFS_PATH}

    for file, out_file in required_files.items():

        if os.path.exists(file):

            shutil.copy(file, out_file)

            if os.path.exists(out_file) != True:

                print(f"\nCopying {file} into {out_file} failed. Check folder structure and permissions.\n")
                exit()

    # Check whether optional files are present
    optional_files = ["data/gpkg/schulen_zuerich.gpkg", "data/gpkg/schulkreise_zuerich.gpkg", "data/parquet/oevschul_soe.parquet"]

    for file in optional_files:

        if os.path.exists(file) != True:

            if file == optional_files[2]:

                print(f"Optional file '{file}' does not exist or is not in the correct location. \nIf you intend to never run the script for Bern including schools, this is fine.\n Otherwise, please resort to the readme.md\n")

            elif file in optional_files[0:1]:

                print(f"Optional file '{file}' does not exist or is not in the correct location. \nIf you intend to never run the script for Zürich including schools, this is fine.\n Otherwise, please resort to the readme.md\n")


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


    # either compute or load pre-processed data based on user input
    if "pre" not in skip:

        # compute pre-processed data
        print("Pre-processing...\n")
        boundary, buildings, origins, destinations = pre_processing(city, city_file, COUNTRY, destination_name=city, osmium_avail=osmium_avail, osm_path=OSM_PATH, gtfs_path=GTFS_PATH, coord_crs=COORD_CRS)

    else:

        # check whether pre-processed data exists. if not, quit.
        if os.path.exists(f"data/gpkg/{city_file}_data.gpkg"):
            if "buildings" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values or "origins" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values or "destinations" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values or "boundary" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:

                print("At least one of 'buildings', 'origins', 'destinations', 'boundary' missing from data.\nDo not use '--skip pre' before having computed preprocessed data at least once.\n")
                exit()
        else:
            print(f"No pre-processed data found for {city}. Run without '--skip pre'.\n")
            exit()

        # load pre-processed data
        print("Loading pre-processed data...\n")
        buildings = read_file(f"data/gpkg/{city_file}_data.gpkg", layer="buildings")
        origins = read_file(f"data/gpkg/{city_file}_data.gpkg", layer="origins")
        destinations = read_file(f"data/gpkg/{city_file}_data.gpkg", layer="destinations")
        boundary = read_file(f"data/gpkg/{city_file}_data.gpkg", layer="boundary")

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

    # only match origins to schools if school routing is requested
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


    # either compute or check whether routing data exists based on user input, exit if not available. Loading handled by plot_list()
    if "routing" not in skip:    

        # only route to schools if specified
        if schools == "True":

            travel_time_matrix_school = route_schools(city_file, date, origins_sample_with_nearest_school, schools_geo, COORD_CRS)

        # always route to center   
        travel_time_matrix = route_center(city_file, date, origins_sample, destinations, METRIC_CRS)

    else:

        # check whether routing data exists already
        if "travel_time_matrix" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:

            print(f"No routing data found for {city}. Please run the script without '--skip routing'. '--help' for more.\n")
            exit()

        if schools == "True" and "travel_time_matrix_school" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:

            print(f"No SCHOOL routing data found for {city}. Please run the script without '--skip routing' or with '--schools False'. '--help' for more.\n")
            exit()



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

        # Handle misspecification by the user
        if "travel_time_matrix_center" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values and "travel_time_matrix_school" not in list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:

            print(f"You skipped something you shouldn't have. No transit matrices have been computed yet for {city_file}.\nPlease rerun this script without skipping routing.\n")
            exit()

        to_plot, transit_lines = plot_list(city_file, boundary, origins, buildings, which_plots, metric_crs=2056)

    # plotter()
    # -----------------------
    # Input:
    # - str: city_file
    # - gdf: to_plot
    # - gdf: transit_lines
    # -----------------------
    # Output:
    # - None, creates pdf files

        done = plotter(city_file, to_plot, transit_lines)
        
        print(done)

    else:

        print("\nDone! No plots generated.\n")

if __name__ == "__main__":
    main()