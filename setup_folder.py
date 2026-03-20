import os


folders = ["data/gpkg", "data/osm", "data/pickle", "data/parquet", "data/gtfs", "data/osm/osrm_driving", "data/osm/osrm_foot", "plots/bern", "plots/zuerich", "plots/solothurn"]

# create folder structure (or leave as-is if already existent)
for directory in folders:
    os.makedirs(directory, exist_ok=True)

for folder in folders:
    if os.path.exists(folder) != True:
        print("\n[WARNING] Folder creation failed. Check permissions. Else, resort to readme.md\n")
        exit()

print("\nFolders created / already exist!\n")


        