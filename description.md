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

## import_zipfile.py

xxx

## sampler.py

This script consists of a single function, `grid_sampler()` which starts off by creating a grid of cells with width=height (as specified by the user through the `--cell int` option) from the bounding box of the area of analysis. It then takes the midpoint (I used 'representative point' which ensure the point lies within cell to be safe, but the 'centroid' would have been fine as squares are not unusual geometries) of each cell. I then (1) match origins to cells using geopandas `sjoin()` and compute distances from each origin to their respective cell midpoint. I then use the inverse of the distance to the cell midpoint as a weight when sampling one point from each cell. This is done so that points close the middle are preferred. It would be even simpler to just use the midpoint of the cell as the sample point, but it is important to me that only "real" buildings (the irony is not lost on me that in edge cases, a hut made for cows may be viewed as a building) are used for routing later on. This is especially important at the edge of the sampling area as there, a grid may span well outside the area boundary and only intersect a small part. The difference in sampling can be seen from the figures below in examples for Bern and Zürich. The function returns the sample of origins without any additional columns added from the input.

## router.py

This script handles everything regarding transit routing and high-level tasks for driving and walk routing and defines the three functions `route_center()`, `route_schools()` and `route_custom()` to perform similar tasks with slightly different requirements. Here, to be fair, they may could have been written as one function is more if else statements, but I felt like this provided better readability.

First things first, `route_center()` takes in multiple origins and one destination from the previous steps and computes transit, driving, and walking times for a variety of timepoints across a day (between 6:00am and 02:00am (next day)). Transit routes are computed for every origin whereas whether driving or walking routes are computed depends on distance of an origin to the destination. Transit routing is performed by r5py's `TravelTimeMatrix()` function, which uses an adaptation of the [RAPTOR algorithm](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf) to RAPidly (is that where it got its name?) compute transit routes between origins and destinations. Because of this, r5py is very efficient at computing transit routes, but is not at all efficient at computing driving and walking routes. I am not sure why that is, but I have thus decided to use OSRM to accomplish this task as not to make performance abysmal. Calling OSRM is outsourced to the file `osrm_routing.py` and is covered below. OSRM computes walking routes for every origin within 500m distance to the destination and driving routes for all others. This is due to the way I present results in the visualisation part: As a ratio between transit travel time and driving / walking travel time. This, when using driving travel times for every origin, results in very "badly covered by public transit" areas close to the destination because a wait time of one minute is suddenly horrific compared to half a minute driving. I make the assumption that no one who would be considering public transit (e.g. not moving into a new flat) would use their car for a trip of 500m or less and that walking time would be a more fair comparison. In addition to this, I administer a 10min penalty on top of driving times to account for traffic, parking and similar mild inconveniences associated with commuting in a metal box. Because r5py uses walk routing for transit time calculation as well (to get to a stop, between stops, or from last stop to destination), both r5py and OSRM use a walking speed of 5km/h. The function returns a combined travel time matrix with both transit and driving / walking (one column, mode dependent on distance to destination) travel times for each origin.

The second function, `route_schools()` essentially mirrors `route_center()` but handles origin-school pairs (so neither all origins -> one same destination nor all origins -> all destinations) by comuting a travel time matrix per school for all of its assigned origins and row-binding afterwards. 

Finally, `route_custom()` is identical in setup for the transit routing as `route_center()`, because r5py supports all origins to all destinations, but differs in how it calls the OSRM routing so that it can handle all origins to all destinations which is possible as the user can specify a (theoretically) unlimited number of origins and destinations. It is not possible to restrict routing to specific origins for destinations like in `route_school()`. 

- Transit: Median, Worst, Best, what is a day? what is a night? which date is used?

## plotter.py

xxx

## imputer.py

xxx

## osrm

OSRM is a routing engine written in C++ which I have decided to run in Docker. This is due to several reasons, to name a few: [1] Building OSRM from source alone takes longer than the allowed 10min setup, [2] OSRM runs natively on Linux, not very much so in Windows without using WSL, and [3] using Docker makes it very easy to use as it just runs as a local server and can be called via an API. This makes prompting it from Python very easy. A reason for a native install would be to increase performance (even more) but given it finishes processing of 160.000 origins to one destination in under a second using docker, I do not feel the need. 

# Innovation
<!-- Detail what are the new components of your project that have not
been covered in class. Give details on what you learned in terms of algorithms, packages, resources, etc. The level of learning in this new skill development will be graded. What is not graded is the novelty of the project as if it was a research project, it is OK to rebuild something that already exists. You must show clearly what you have developed yourself and what you use from the work of others. -->

To start off: Most things I have newly learned are packages or tools I use. Most of the code I use with them is derived from the documentation of said tools, e.g. example usage and or guides from [geopandas](https://geopandas.org/en/stable/docs.html), [osmnx](https://osmnx.readthedocs.io/en/stable/), [pydeck](https://deckgl.readthedocs.io/en/latest/), [r5py](https://r5py.readthedocs.io/stable/), [OSRM (Docker-Version)](https://hub.docker.com/r/osrm/osrm-backend/) and the [Docker SDK](https://docker-py.readthedocs.io/en/stable/) itself.

One exception is the process used for imputing, which I have written more or less from scratch, although the grunt work is done by [scipy.spatial's KDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html#scipy.spatial.KDTree) function.


# Results

xxx




# Outlook

xxx








