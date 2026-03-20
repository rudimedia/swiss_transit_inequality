from scipy.spatial import KDTree
import pandas as pd
import geopandas as gpd
import numpy as np

def KDTree_imputer(city_file, travel_time_matrix, origins, buildings, metric_crs=25832):
    # Merge travel time matrix with origin geometries; unmatched origins are kept (right join)
    ttm = pd.DataFrame(travel_time_matrix).merge(
        origins[["id", "geometry"]],
        left_on="from_id", right_on="id", how="right"
    )
    ttm = gpd.GeoDataFrame(ttm, geometry="geometry", crs=origins.crs)
    ttm = ttm.to_crs(epsg=metric_crs)

    # Extract coordinates and flag rows that have travel time data
    ttm["x"] = ttm.geometry.x
    ttm["y"] = ttm.geometry.y
    ttm["is_sampled"] = ttm["from_id"].notna()

    # IDW imputation: fill unsampled origins from 5 nearest sampled neighbors
    sampled = ttm[ttm["is_sampled"]]
    unsampled = ttm["is_sampled"] == False

    if unsampled.any():
        tree = KDTree(sampled[["x", "y"]].values)
        distances, point_ids = tree.query(ttm.loc[unsampled, ["x", "y"]].values, k=5)

        for col in ["travel_time_p50", "spread", "travel_time", "travel_time_p5", "travel_time_p95"]:
            if col not in ttm.columns:
                continue

            ttm[col] = pd.to_numeric(ttm[col]).astype(float)

            imputed = []
            for distance, point_id in zip(distances, point_ids):
                neighbor_values = sampled[col].values[point_id]

                # Keep only neighbors with valid (non-NaN) travel times
                valid_pairs = [(d, v) for d, v in zip(distance, neighbor_values) if not np.isnan(v)]

                if not valid_pairs:
                    imputed.append(np.nan)
                else:
                    valid_dists = [d for d, v in valid_pairs]
                    valid_vals  = [v for d, v in valid_pairs]
                    weights = [1 / max(d, 1e-10) for d in valid_dists]  # guard against zero distance
                    imputed.append(sum(w * v for w, v in zip(weights, valid_vals)) / sum(weights))

            ttm.loc[unsampled, col] = np.array(imputed, dtype=float)

    # Flag origins with no public transport access
    ttm["no_pt"] = ttm["travel_time_p5"].isna()
    ttm["no_pt"] = ttm["travel_time_p50"].isna()
    ttm["no_pt"] = ttm["travel_time_p95"].isna()

    # Ratio of PT median travel time to baseline (car/walk) travel time
    ttm["ratio_p5"] = ttm["travel_time_p5"] / ttm["travel_time"]
    ttm["ratio_p50"] = ttm["travel_time_p50"] / ttm["travel_time"]
    ttm["ratio_p95"] = ttm["travel_time_p95"] / ttm["travel_time"]
    ttm.loc[ttm["travel_time"] == 0, ["ratio_p5", "ratio_p50", "ratio_p95"]] = np.nan

    # Attach building polygons to each origin point
    all_points_imputed = ttm.merge(buildings[["id", "geometry"]], on="id", suffixes=("_point", "_poly"))
    all_points_imputed = all_points_imputed.drop(columns=["geometry_point"])
    all_points_imputed = gpd.GeoDataFrame(all_points_imputed, geometry="geometry_poly", crs=buildings.crs)
    gpd.GeoDataFrame(all_points_imputed).to_file(f"data/gpkg/{city_file}_data.gpkg", layer="all_points_imputed", driver="GPKG")

    return all_points_imputed