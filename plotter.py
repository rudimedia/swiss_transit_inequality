import geopandas as gpd
from ckdtree import ckdTree2
from pyrosm import OSM
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def group_travel_time_matrix(travel_time_matrix):
    travel_time_matrix = travel_time_matrix.groupby("from_id").agg(
        spread = ("spread", "max"),
        travel_time_p5 = ("travel_time_p5", "min"),
        travel_time_p50 = ("travel_time_p50", "median"),
        travel_time_p95 = ("travel_time_p95", "max"),
        travel_time = ("travel_time", "median"),
    ).reset_index()

    return travel_time_matrix

def plot_list(city_file, boundary, origins, buildings, which_plots, metric_crs=2056):
    
    to_plot = []
    
    # load all requested travel matrices for plotting (if available, otherwise quit)
    if "travel_time_matrix_center" in gpd.list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:
        travel_time_matrix = gpd.read_file(f"data/gpkg/{city_file}_data.gpkg", layer="travel_time_matrix_center")
        
        if "day" in which_plots or which_plots == []:
            travel_time_matrix_day = travel_time_matrix[travel_time_matrix["departure_time"].dt.hour.between(6,20)].copy()
            travel_time_matrix_day = group_travel_time_matrix(travel_time_matrix_day)

            travel_time_matrix_day["plot_type"] = "day" 
            to_plot.append(travel_time_matrix_day)
        
        if "night" in which_plots or which_plots == []:
            travel_time_matrix_night = travel_time_matrix[travel_time_matrix["departure_time"].dt.hour.between(22, 24) | travel_time_matrix["departure_time"].dt.hour.between(0, 2)].copy()
            travel_time_matrix_night = group_travel_time_matrix(travel_time_matrix_night)

            travel_time_matrix_night["plot_type"] = "night"
            to_plot.append(travel_time_matrix_night)
    
    if "travel_time_matrix_school" in gpd.list_layers(f"data/gpkg/{city_file}_data.gpkg")["name"].values:
        if "school" in which_plots or which_plots == []:
            travel_time_matrix_school = gpd.read_file(f"data/gpkg/{city_file}_data.gpkg", layer="travel_time_matrix_school").copy()
            travel_time_matrix_school["plot_type"] = "school"
            to_plot.append(travel_time_matrix_school)
    
    all_points_imputed_list = []

    # impute values for unsampled points, approximate nearest neighbor. Weight by inverse distance
    for i, matrix in enumerate(to_plot):
        plot_type = matrix["plot_type"].iloc[0]
        all_points_imputed = ckdTree2(city_file, matrix, origins, buildings, metric_crs)
        all_points_imputed["plot_type"] = plot_type

        # precompute geojson for interactive visualisation
        all_points_imputed["geometry_plot"] = None
        for j, row in all_points_imputed.iterrows():
            all_points_imputed.at[j, "geometry_plot"] = row["geometry_poly"].representative_point().__geo_interface__

        to_plot[i] = all_points_imputed
        all_points_imputed_list.append(all_points_imputed)  

        to_plot[i] = all_points_imputed

    # save plottable dataframes as single geodataframe
    gpd.pd.concat(all_points_imputed_list, ignore_index=True).to_pickle(f"data/pickle/{city_file}_to_plot.pkl")    

    # get shapes of public transport routes for city to be plotted
    osm = OSM(f"data/osm/{city_file}.osm.pbf")
    transit_lines = osm.get_data_by_custom_criteria(custom_filter={"route": ["bus", "tram", "subway", "train", "rail", "ferry"]})
    transit_lines = gpd.clip(transit_lines, boundary)

    return to_plot, transit_lines



# plotter()
# -----------------------
# Input:
# - str: city_file
# - gdf: to_plot
# - gdf: transit_lines
# -----------------------
# Output:
# - None, creates pdf files

def plotter(city_file, to_plot, transit_lines):

    # separate plot sizes per city
    if city_file == "Bern":
        figsize = (20, 10)
    elif city_file == "Zürich":
        figsize = (20,20)
    else:
        figsize = (15,15)
    
    # create color range from custom colors
    cmap = LinearSegmentedColormap.from_list("green_blue_purple_red", ["#0B4D03", "#1BA308", "#0B81E3", "#085DA3", "#9608A3", "#A30808", "#850505"])
    
    print("Plotting...")

    for matrix in to_plot:

        print("...", matrix["plot_type"].dropna().iloc[0])

        for col in ["ratio_p5", "ratio_p50", "ratio_p95", "spread"]:

            # scale limits for ratio but not spread
            if col != "spread":
                lower_bound_plotting = 0.5
                upper_bound_plotting = 4.0
            else:
                lower_bound_plotting = min(matrix[col])
                upper_bound_plotting = max(matrix[col])

            # Clip plotted variable to bounds
            clipped_col_name = col + "_clipped"
            matrix[clipped_col_name] = matrix[col].clip(lower=lower_bound_plotting, upper=upper_bound_plotting)

            # initialise plot
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_facecolor("black")
            fig.patch.set_facecolor("black")
            
            # plot building polygons, colored by value of current column / dependent variable
            matrix.plot(column=clipped_col_name, cmap=cmap, legend=True, ax=ax,
                vmin=lower_bound_plotting, vmax=upper_bound_plotting,
                missing_kwds={"color": "grey", "label": "No PT route"},
                legend_kwds={"shrink": 0.4})
            
            # plot transit lines
            transit_lines.plot(ax=ax, color="lightgrey", linewidth=0.02, alpha=0.2)

            # styling
            ax.set_axis_off()
            color_legend = ax.get_figure().axes[-1]
            color_legend.set_ylabel(f"{str(lower_bound_plotting)}−        {str(upper_bound_plotting)}+", color="white")   
            color_legend.yaxis.set_tick_params(color="white")
            plt.setp(color_legend.yaxis.get_ticklabels(), color="white")
            color_legend.set_facecolor("black")   

            plt.savefig(f"plots/{city_file}/{city_file}_{matrix["plot_type"].dropna().iloc[0]}_{col}.pdf", bbox_inches="tight", dpi=300)

    return f"\nDone! Plots can be found under '~/plots/{city_file}/'.\n"           
                  