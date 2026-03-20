# Motivation

xxx

# Design

<!-- outline your approach to developing the project, breaking it down into
subtasks, their relationships, and describing the overall structure of your
software. Here, a diagram or a figure explaining the design is usually helpful. -->

**Files (and their uses):**
- integrated.py, calls:
    - pre_function.py, calls:
        - import_zipfile.py
    - sampler.py
    - router.py, calls:
        - osrm_routing
    - plotter.py, calls:
        - imputer

- custom_routing.py, calls:
    - router.py, calls:
        - osrm_routing 
        - integrated.py 

- app.py, calls:
    - integrated.py 

**Dependencies between scripts:**
- output of integrated.py is required for usage of app.py and custom_routing.py

## integrated.py

This script has three primary functions: [1] **File management**: Copies user-provided files (e.g. Open Street Map (OSM) data and GTFS-feed) into the correct subdirectories and verifies copying worked. It then checks whether all optional files which should have been provided by cloning the git repository are in their correct locations and alerts the user otherwise. I have decided to (a) not provide these files from the github repository as they are too large and (b) to not rely on any function I write to properly handle interrupted downloads. Especially the OSM data file is quite large (~500MB) so I deemed it best for the user to decide how (and when) to properly download it. [2] **User input**: Take user-specified parameters and call only necessary (and allowed) functions from other files given these inputs. As part of that, it handles loading previously computed data if parts of the pipeline are skipped by the user. In that case, it also handles cases where the user skips parts he should not skip and exits the program gracefully, complimenting the user on their great input specification on the way out.  [3] **Global constants**: Defines global constants it then passes to each function that requires them instead of re-assigning constants across multiple scripts. This then makes changing specific parameters globally easier, like which cities are available, which dates are covered by the GTFS-feed or which path OSM files are to be found under. It also defines the function which converts a city input like "Zürich" into a filename-worthy string like "zuerich". This is then used throughout other scripts where the processed string cannot be passed directly as input (e.g. in app.py and custom_routing.py). 

Once this script has run through, all necessary data for running `app.py` and `custom_routing.py` is available. 

## pre_function.py

This script consists of a two functions of which the mosre important one is `pre_processing()` which is called by `integrated.py`. It retrieves all necessary data via [OSMNX](https://osmnx.readthedocs.io/en/stable/) (which itself calls the [Nominatim API](https://nominatim.org/), an open-source geocoding API which works with OpenStreetMap Data) and from local storage. While OSMNX is able to provide all data (except for the GTFS feed) itself, I choose to instead rely on the local copy of OSM data wherever possible and merely "abuse" osmnx for its simple Nominatim integration which allows me to easily geocode places. In this case, I only use it to extract the approximate boundary for the specified city, which is easier and more flexible than accounting for all possible cases in the administrative boundaries of the local OSM data. It also, most often, provides the "wanted" result even if the specification of the city is not very well formulated. Additionally, it allows for quite flexible switching between administrative levels: While specifying "Zürich" yields boundaries for the city Zürich, specifying "Kanton Zürich" or "county='Zürich', country='Switzerland'" would yield the boundary for the Kanton Zürich, all done through natural language without requiring to specify administrative levels manually. 

I have not found a good (installable) way to process OSM data from within python, which is why I use the external tool Osmium Tool. I call it through subprocess (which I looked up how to do that, in general) and the result is stored as a .osm.pbf file which than can be used by the following functions. I figured out how to extract a boundary from bounding box coordinates from its documentation and basically construct the terminals tring in Python. I then extract buildings and places from the local OSM data using pyrosm, which allows filtering by tags. They are also converted to point geometries using a "representative" point within their polygon which is not quite the centroid but rather something guaranteed to obey its boundaries. I don't quite know how that works, but geopandas handles it gracefully. Separate geodataframes are kept with either the polygon (buildings) *or* the point (origins) as their geometry because for some subsequent operations, geopandas does not allow for multiple geometry columns. I define buildings as *any and all* buildings cartographed, including huts in the woods and military bases. Public transport should not discriminate. These are then filtered and processed so they do not cause errors later on and made "reachable" so a point cannot lie in the middle of a sea without an island underneath it.  This usually doesn't do anything and acts as a safety net. This "reachability" processing can only be done after having computed a transport network using r5py. This is only possible if there is a valid GTFS-feed available, so before doing this, 'pre_processing()' calls 'fix_gtfs' from 'import_zipfile'. More on how that works later. 

The function returns the boundary, buildings, origins and the the center point for the city as geodataframes to `integrated.py`.

The second function, `origins_to_schools` maps origins to the closest school within their school district. I use official data from the cities of Bern and Zürich for the locations of schools, but only Bern consistently specifies the type of a school, thus I do not filter by this information. This then makes the results a bit less interesting because yes, sure, it is easy to get to *any* school from most location, just not maybe the one you are interested in. The function obeys mappings of origins to school districts (for which the data is also provided by the cities' open data platforms). I use geopandas' `sjoin()` function to merge origins to schools, which is very fast. The function returns the origins with an identifier for their nearest school added, as well as the locations of the schools where the former then can be used as origins and the latter as destinations for routing in later steps.

## router.py

This script handles everything regarding transit routing and high-level tasks for car and walk routing. It specifies 



# Innovation
<!-- Detail what are the new components of your project that have not
been covered in class. Give details on what you learned in terms of algorithms,
packages, resources, etc. The level of learning in this new skill development will
be graded. What is not graded is the novelty of the project as if it was a research
project, it is OK to rebuild something that already exists. You must show clearly
what you have developed yourself and what you use from the work of others. -->

To start off: Most things I have newly learned are packages or tools I use. Most of the code I use with them is derived from the documentation of said tools, e.g. example usage and or guides from [geopandas](https://geopandas.org/en/stable/docs.html), [osmnx](https://osmnx.readthedocs.io/en/stable/), [pydeck](https://deckgl.readthedocs.io/en/latest/), [r5py](https://r5py.readthedocs.io/stable/), [OSRM (Docker-Version)](https://hub.docker.com/r/osrm/osrm-backend/) and the [Docker SDK](https://docker-py.readthedocs.io/en/stable/) itself.

One exception is the process used for imputing, which I have written more or less from scratch, although the grunt work is done by [scipy.spatial's KDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html#scipy.spatial.KDTree) function.


# Results

xxx




# Outlook

xxx








