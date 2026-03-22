import zipfile
import pandas as pd
import geopandas as gpd

# fix_gtfs()
# -----------------------
# xxx
# -----------------------
# Input:
# - box: bbox_box
# - str: city
# - str: gtfs_path
# - int: COORD_CRS
# -----------------------
# Returns:
# - path to fixed zipfile


def fix_gtfs(bbox_box, city, gtfs_path, coord_crs):

    # read gtfs-feed csv's as separate dataframes
    with zipfile.ZipFile(f"{gtfs_path}") as z:

        agency = pd.read_csv(z.open("agency.txt"))
        stops = pd.read_csv(z.open("stops.txt"))
        stop_times = pd.read_csv(z.open("stop_times.txt"))
        trips = pd.read_csv(z.open("trips.txt"))
        routes = pd.read_csv(z.open("routes.txt"))
        calendar = pd.read_csv(z.open("calendar.txt"))       
        calendar_dates = pd.read_csv(z.open("calendar_dates.txt")) 
        feed_info = pd.read_csv(z.open("feed_info.txt"))      
        transfers = pd.read_csv(z.open("transfers.txt"))

    # Fix stops
    stops["location_type"] = (pd.to_numeric(stops["location_type"], errors="coerce").fillna(0).astype(int))

    # Drop trips with any stop time >= 48:00:00 (r5py limit)
    bad_trip_ids = set(stop_times[stop_times["arrival_time"].str.split(":").str[0].astype(int) >= 48]["trip_id"])
    if bad_trip_ids:

        print(f"Dropping {len(bad_trip_ids)} trip(s) with arrival hour >= 48")

        stop_times = stop_times[~stop_times["trip_id"].isin(bad_trip_ids)].copy()
        trips = trips[~trips["trip_id"].isin(bad_trip_ids)].copy()

    # Fix missing pickup type and drop off type and force integer 
    stop_times["pickup_type"]   = stop_times["pickup_type"].fillna(0).astype(int)
    stop_times["drop_off_type"] = stop_times["drop_off_type"].fillna(0).astype(int)

    # Fix route type mapping, r5 expects types between 0-7
    routes["route_type"] = routes["route_type"].replace({101:2, 102:2, 103:2, 105:2, 106:2, 107:2, 109:2, 116:2, #rail
                       202:3, 700:3, 702:3, 705:3, 710:3, 715:3, # bus
                       401:1, 900:0, 1000:4, 1400:7, 1700:0}) # 1700 is gondola, mapped to tram

    # Geographic filter for GTFS file to make computation more performant
    stops_gdf = gpd.GeoDataFrame(stops.copy(), geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]), crs=coord_crs)
    stops_keep = stops_gdf[stops_gdf.intersects(bbox_box)].copy()

    # Keep stations -1 from last station within boundary if data available from feed
    if "parent_station" in stops.columns:

        parent_ids = set(stops_keep["parent_station"].dropna().astype(str))

        if parent_ids:

            parent_rows = stops_gdf[stops_gdf["stop_id"].astype(str).isin(parent_ids)].copy()

            if parent_rows.empty == False: 

                stops_keep = pd.concat([stops_keep, parent_rows], ignore_index=True).drop_duplicates(subset=["stop_id"])
                stops_keep = gpd.GeoDataFrame(stops_keep, crs="EPSG:4326")

    # keep stops, trips, stop times, transfers within used by stops within boundary 
    keep_stop_ids = set(stops_keep["stop_id"])
    keep_trip_ids = set(stop_times[stop_times["stop_id"].isin(keep_stop_ids)]["trip_id"])
    trips_keep = trips[trips["trip_id"].isin(keep_trip_ids)].copy()
    trips_keep = trips_keep.drop(columns=["block_id"], errors="ignore")
    stop_times_keep = stop_times[stop_times["trip_id"].isin(set(trips_keep["trip_id"]))].copy()
    transfers_keep = transfers[transfers["from_stop_id"].isin(keep_stop_ids) & transfers["to_stop_id"].isin(keep_stop_ids)].copy()

    # Re-include stops from boundary-crossing trips
    missing_stop_ids = set(stop_times_keep["stop_id"]) - keep_stop_ids
    if missing_stop_ids:

        extra_stops = stops_gdf[stops_gdf["stop_id"].isin(missing_stop_ids)]
        stops_keep  = pd.concat([stops_keep, extra_stops], ignore_index=True).drop_duplicates(subset=["stop_id"])

    # keep routes, services, agencies, calendar values, calendar dates within boundary or boundary-crossing trips 
    keep_route_ids = set(trips_keep["route_id"])
    routes_keep = routes[routes["route_id"].isin(keep_route_ids)].copy()
    keep_service_ids = set(trips_keep["service_id"])
    agency_keep = agency[agency["agency_id"].isin(set(routes_keep["agency_id"].dropna()))].copy()
    calendar = calendar[calendar["service_id"].isin(keep_service_ids)].copy()
    calendar_dates = calendar_dates[calendar_dates["service_id"].isin(keep_service_ids)].copy()

    # Write fixed GTFS-feed as .zip
    with zipfile.ZipFile(f"data/gtfs/gtfs-{city}.zip", "w", compression=zipfile.ZIP_DEFLATED) as z:
        
        agency_keep.to_csv(z.open("agency.txt", "w"), index=False)
        stops_keep.drop(columns=["geometry"], errors="ignore").to_csv(z.open("stops.txt", "w"), index=False)
        stop_times_keep.to_csv(z.open("stop_times.txt", "w"), index=False)
        trips_keep.to_csv(z.open("trips.txt", "w"), index=False)
        routes_keep.to_csv(z.open("routes.txt", "w"), index=False)
        calendar.to_csv(z.open("calendar.txt", "w"), index=False)
        calendar_dates.to_csv(z.open("calendar_dates.txt", "w"), index=False)
        feed_info.to_csv(z.open("feed_info.txt", "w"), index=False)
        transfers_keep.to_csv(z.open("transfers.txt", "w"), index=False)

    path = f"data/gtfs/gtfs-{city}.zip"
    
    return path