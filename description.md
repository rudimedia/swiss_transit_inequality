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
        - ckdtree

- custom_routing.py, calls:
    - router.py, calls:
        - osrm_routing 
        - integrated.py 

- app.py, calls:
    - integrated.py 

**Dependencies between scripts:**
- output of integrated.py is required for usage of app.py and custom_routing.py

## integrated.py

This script has three primary functions: [1] **File management**: Copies user-provided files (e.g. Open Street Map data and GTFS-feed) into the correct subdirectories and verifies copying worked. It then checks whether all optional files which should have been provided by cloning the git repository are in their correct locations and alerts the user otherwise. I have decided to (a) not provide these files from the github repository as they are too large and (b) to not rely on any function I write to properly handle interrupted downloads. Especially the Open Street Map data file is quite large (~500MB) so I deemed it best for the user to decide how (and when) to properly download it. [2] **User input**: Take user-specified parameters and call only necessary (and allowed) functions from other files given these inputs. As part of that, it handles loading previously computed data if parts of the pipeline are skipped by the user. In that case, it also handles cases where the user skips parts he should not skip and exits the program gracefully, complimenting the user on their great input specification on the way out.  [3] **Global constants**: Defines global constants it then passes to each function that requires them instead of re-assigning constants across multiple scripts. This then makes changing specific parameters globally easier, like which cities are available, which dates are covered by the GTFS-feed or which path OSM files are to be found under. It also defines the function which converts a city input like "Zürich" into a filename-worthy string like "zuerich". This is then used throughout other scripts where the processed string cannot be passed directly as input (e.g. in app.py and custom_routing.py). 

Once this script has run through, all necessary data for running `app.py` and `custom_routing.py` is available. 

## pre_function.py

This script consists of a single function `pre_processing()` which is called by `integrated.py`. It retrieves all necessary data via [OSMNX](https://osmnx.readthedocs.io/en/stable/) (which itself calls the [Nominatim API](https://nominatim.org/), an open-source geocoding API which works with OpenStreetMap Data) and from local storage. While OSMNX is able to provide all data (except for the GTFS feed) itself, I choose to instead rely on the local copy of Open Street Map data wherever possible and merely "abuse" osmnx for its simple Nominatim integration which allows me to easily geocode places. In this case, it is used to geocode the destination "center", so, ideally, the historical city center, but I simply take the first result Nominatim recommends given the input. This works well for the cities used here and, mostly, well for medium-sized cities (>20.000 inhabitants) in Germany and Switzerland.  




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








