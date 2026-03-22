from scipy.spatial import KDTree
import pandas as pd
import geopandas as gpd
import numpy as np

# KDTree_imputer()
# -----------------------
# Imputes travel times for every unsampled point from its 5 nearest sampled neighbors.
# Value imputed by taking inverse-distance-weighted mean.
# If all 5 sampled neighbors are NA, the unsampled point is also set as NA. 
# Also joins building polygons to origins dataset for plotting.
# -----------------------
# Input:
# - str: city_file
# - df: travel_time_matrix
# - gdf: origins
# - gdf: buildings
# - int: METRIC_CRS
# -----------------------
# Returns:
# - gdf: all_points_imputed


def KDTree_imputer(city_file, travel_time_matrix, origins, buildings, metric_crs=25832):

    # Merge travel time matrix with origin geometries; unmatched origins are kept (right join)
    ttm = pd.DataFrame(travel_time_matrix).merge(origins[["id", "geometry"]], left_on="from_id", right_on="id", how="right")
    ttm = gpd.GeoDataFrame(ttm, geometry="geometry", crs=origins.crs)
    ttm = ttm.to_crs(epsg=metric_crs)

    # Extract coordinates and flag rows that have travel time data (is_sampled == True, after the left join this is the case for all that have a value in from_id)
    ttm["x"] = ttm.geometry.x
    ttm["y"] = ttm.geometry.y
    ttm["is_sampled"] = ttm["from_id"].notna()

    # Create dataframe with only sampled, and boolean mask for unsampled
    sampled = ttm[ttm["is_sampled"]]
    unsampled = ttm["is_sampled"] == False

    # fill unsampled origins from 5 nearest sampled neighbors (only runs if there are unsampled points)
    if unsampled.any():

        # Build KDTree from only sampled points
        tree = KDTree(sampled[["x", "y"]].values)

        # find 5 nearest (sampled) neighbors for each unsampled point including distance
        unsampled_neighbors = tree.query(ttm.loc[unsampled, ["x", "y"]].values, k=5)

        # impute each available column
        for col in ["travel_time_p50", "spread", "travel_time", "travel_time_p5", "travel_time_p95"]:

            # skip unavailable columns
            if col not in ttm.columns:
                continue
            
              
            imputed = []

            # Iterate over unsampled points
            for distance, point_id in zip(unsampled_neighbors[0], unsampled_neighbors[1]):
                
                # column values of nearest neighbors
                neighbor_values = sampled[col].values[point_id]
                
                # Keep only neighbors with valid (not missing) travel times
                valid_pairs = []

                for d, v in zip(distance, neighbor_values):

                    if np.isnan(v) != True:

                        valid_pairs.append((d, v))

                # If there are no (sampled) neighbors with a value for the column, the unsampled point is likely to not be reachable by transit either, so set NA
                if not valid_pairs:

                    imputed.append(np.nan)

                # If at least one (sampled) neighbor has a valid value for the column take weighted mean from values of neighbors
                else:
                    
                    valid_dists = [d for d, _ in valid_pairs]
                    valid_vals  = [v for _, v in valid_pairs]
                    weights = [1 / max(d, 0.00000000001) for d in valid_dists]

                    imputed.append(sum(w * v for w, v in zip(weights, valid_vals)) / sum(weights))

            # Add imputed data to original dataframe
            ttm.loc[unsampled, col] = np.array(imputed, dtype=float)

    # Dummy for origins with no public transport access at worst case, covers NAs at median and best case
    ttm["no_pt"] = ttm["travel_time_p95"].isna()

    # Ratio of PT median travel time to baseline (car/walk) travel time
    ttm["ratio_p5"] = ttm["travel_time_p5"] / ttm["travel_time"]
    ttm["ratio_p50"] = ttm["travel_time_p50"] / ttm["travel_time"]
    ttm["ratio_p95"] = ttm["travel_time_p95"] / ttm["travel_time"]

    # If destination (essentially) == origin, set travel time ratios to NA
    ttm.loc[ttm["travel_time"] == 0, ["ratio_p5", "ratio_p50", "ratio_p95"]] = np.nan

    # Attach building polygons to each origin point
    all_points_imputed = ttm.merge(buildings[["id", "geometry"]], on="id", suffixes=("_point", "_poly"))
    all_points_imputed = all_points_imputed.drop(columns=["geometry_point"])
    all_points_imputed = gpd.GeoDataFrame(all_points_imputed, geometry="geometry_poly", crs=buildings.crs)

    # Save for later access
    gpd.GeoDataFrame(all_points_imputed).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="all_points_imputed", driver="GPKG")

    return all_points_imputed