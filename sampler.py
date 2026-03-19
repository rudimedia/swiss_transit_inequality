from shapely import box
import geopandas as gpd
import numpy as np

def grid_sampler(origins, boundary, cell_size=100, metric_crs=2056, coord_crs=4326):

    # get metric bounds for grid creation
    boundary = boundary.to_crs(metric_crs)
    xmin, ymin, xmax, ymax = boundary.total_bounds
    boundary = boundary.to_crs(coord_crs)

    # create grid from city boundary
    grid = []
    for x in np.arange(xmin, xmax, cell_size):
        for y in np.arange(ymin, ymax, cell_size):
            grid.append(box(x, y, x+cell_size, y+cell_size))
    grid = gpd.GeoDataFrame(geometry=grid, crs=metric_crs).to_crs(coord_crs)

    ### matching origins to their grid cell, then taking 2 samples (or 1 if no more available) from each grid cell
    # getting middle point of each grid cell, matching origins to their cell
    grid["middle_point"] = grid.representative_point()
    origins_with_grid = gpd.sjoin(origins, grid, predicate="within")
    
    # convert geometries to metric crs
    origins_with_grid = origins_with_grid.to_crs(metric_crs)
    origins_with_grid["middle_point"] = origins_with_grid["middle_point"].to_crs(metric_crs)
    
    # compute distances to cell midpoint for each origin
    origins_with_grid["dist_to_cell"] = origins_with_grid.geometry.distance(origins_with_grid["middle_point"])
    
    # convert back to coordinate crs
    origins_with_grid = origins_with_grid.to_crs(coord_crs)
    origins_with_grid["middle_point"] = origins_with_grid["middle_point"].to_crs(coord_crs)
    
    # weight sampling probability by inverse distance
    origins_with_grid["cell_weight"] = 1 / (origins_with_grid["dist_to_cell"] + 0.000000000000000000000000000001)

    # weighting sampling probability by the inverse of distance to middle point (origins closer to middle are favored)
    origins_sample = (origins_with_grid.groupby("index_right", group_keys=False).sample(n=1, weights=origins_with_grid["cell_weight"], random_state=42))

    return origins_sample.drop(columns=["index_right"])