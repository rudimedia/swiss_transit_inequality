# Prerequisits

## First of all

1. Clone this github repository or download its contents into a folder of your choice.
2. `cd` into your chosen folder with the contents in them
3. Proceed.

## Download conda / miniforge

You do not need to install both. Miniforge is sufficient for this project and should take less time to install / use space on your disk. Conda is more foolproof. Resort to conda if miniforge does not work for you.

Before doing so, check whether you happen to have it installed already:
```
conda --version
```

### Conda
1. To install conda, please resort to their [installation guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). You can choose from the full anaconda install and miniconda. Miniconda should be sufficient for this project, resort to the full conda install if that does not work for you.

### Miniforge
1. Pick the fitting release file for your device / OS [here](https://github.com/conda-forge/miniforge/releases), download, install and follow the instructions.
2. A more comprehensive guide on how to install can be found [on the official github page](https://github.com/conda-forge/miniforge). This is especially useful if you choose to install it on Windows in WLS.

## Download OSM and GTFS data

Please, first of all download two files: Open Street Map data for Switzerland (~500MB) and its GTFS feed. 

1. Download GTFS from [here](https://data.opentransportdata.swiss/en/dataset/timetable-2025-gtfs2020). Search for "GTFS_FP2025_2024-09-02.zip" and download. Alternatively, scroll to the very bottom, that should be the one. Do not change the filename.

2. Download Open Street Map data for Switzerland from [Geofabrik here](https://download.geofabrik.de/europe/switzerland.html) under "Commonly Used Formats", download "switzerland-latest.osm.pbf". Do not change the filename.
    > Note: If you are on Windows and not willing to run WLS (or need to be able to do this in 10min or less) please resort to using already clipped OSM files available [here](https://drive.google.com/drive/folders/1Mp1g-txBi5JBEO_vjZGFSqDMNmeigjJO?usp=sharing). They are only ~70MB in size. If you use these, please specify "--osmium False" every time you run `integrated.py´.

4. Create a new folder `data` within your directory as well as its subdirectories `data/osm/` and `data/gtfs`. 

5. Copy your 'switzerland-latest.osm.pbf' (or 'Bern.osm.pbf', 'Zürich.osm.pbf' and 'Solothurn.osm.pbf' respectively) into `data/osm/`

6. Copy your 'GTFS_FP2025_2024-09-02.zip' file into `data/gtfs/`

## Create environment

Once you have opened the folder with the script files, create a conda environment using the environment.yml which will install all necessary dependencies (within python) and activate it.

```
conda env create -f environment.yml
conda activate kaenTransport
```

Troubleshooting:
> If you refuse to do what the conda installer(s) told you to do, you may need to run `conda init` beforehand.
> You /may/ need to check whether conda works in bash instead of zsh? Worked for my brother using Linux...

## Out-of-Python requirements

The scripts have (2) external requirements. Firstly, a version of [Osmium Tool](https://osmcode.org/osmium-tool/) is necessary to do local processing of Open Street Map data. Secondly, Docker is necessary to perform OSRM routing.

> Osmium Tool is not available for Windows. If you wish to use it anyways, resort to using WLS (broadly described below). I would recommend just using the precomputed clipped OSM files found [here](https://drive.google.com/drive/folders/1Mp1g-txBi5JBEO_vjZGFSqDMNmeigjJO?usp=sharing) and copying them into the correct folder `data/osm`. Once done that, every time you run `integrated.py` include `--osmium False` in your calls to avoid errors. This will work fine. I vouch for the code clipping the OSM file to work, if need be by demonstrating in person. In any case, use Linux. Thank you for listening to my TedTalk. 

## Install Osmium Tool
### macOS

1. The easiest way to install Osmium Tool on macOS is by using [homebrew](https://brew.sh/). Homebrew can be installed by running this command in terminal:
    ```
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2. Osmium Tool can then be installed using brew.
    ```
    brew install osmium-tool
    ```

3. Verify the install was successfull:
    ```
    osmium --version
    ```

### Linux

The easiest way to install Osmium-Tool across all Linux distributions is using conda within the environment you just created:
```
conda install -c conda-forge osmium-tool
```

### Windows

Unfortunately, Osmium-Tool is not available for Windows. I only found that out when I had already written all the scripts. It is possible to use Osmium-Tool via WSL which I will describe below, but if you are not feeling like doing so, please use the precomputed clipped osm.pbf files for Bern, Zürich, and Solothurn which I have linked to [here](https://drive.google.com/drive/folders/1Mp1g-txBi5JBEO_vjZGFSqDMNmeigjJO?usp=sharing) (~70MB in total) and put them in the appropriate folder. From you working directory that should be "data/osm/". In that case, please run `python integrated.py` with `--osmium False` at all times. 

If you do wanna use WSL:
1. Install WSL (For more information see [this Microsoft helppage](https://learn.microsoft.com/de-de/windows/wsl/install))
    ```
    wsl --install
    ```
2. Now, open the python scripts within WSL. Redo the environment creation step for this new configuration.

3. Run:
    ```
    conda install -c conda-forge osmium-tool
    ```
4. Verify the install was successfull:
    ```
    osmium --version
    ```

## Install Docker
### macOS

1. Download Docker Desktop from [here](https://www.docker.com/products/docker-desktop)
2. Choose the correct version:
   - Apple Silicon: Docker Desktop for Mac (Apple Silicon)
   - Intel: Docker Desktop for Mac (Intel)
3. Open the `.dmg`, drag Docker to Applications, and launch it.
4. Verify the install:
   ```bash
   docker --version
   ```

> !! Docker Desktop must be **running** (menu bar icon) whenever you execute the script.

### Linux

Docker has a "convenience script" available for Linux which you may use to install it.

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Then allow your user to run Docker without `sudo`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verify:
```bash
docker --version
docker run hello-world
```

### Windows

The way you install Docker depends on whether you chose to use the WSL-route and compute osm extracts using Osmium Tool yourself. 

 >(1) If you use WSL, do the following:

1. Download and install Docker Desktop, enabling the WSL 2 backend when prompted.

2. In Docker Desktop settings, go to Resources → WSL Integration and enable integration for your WSL distro (e.g. Ubuntu).

4. Verify Docker is accessible from WSL:
   ```bash
   docker --version
   docker run hello-world
   ```

> (2) If you do not use WSL and instead use precomputed OSM extracts, do the following:

1. Download Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. During installation, select "Use WSL 2 instead of Hyper-V" if prompted — this is a Docker-internal setting and does not require you to use WSL yourself.
3. Open Docker Desktop after install and complete the setup wizard.
4. Verify in PowerShell or Command Prompt:
   ```powershell
   docker --version
   ```
5. Run your Python script normally from PowerShell, Command Prompt, or your IDE — no WSL terminal needed.

# Script Usage
There are three scripts you will be executing directly: `integrated.py`, `custom_routing.py` and `app.py`. The former one is used for calculating the routes and some plots for one of the available cities / cantons [Bern, Zürich, Solothurn]. The latter ones are streamlit applications used for visualising the previously computed data (`app.py`) and calculating routings for custom origins and destinations and viewing results in table format (`custom_routing.py`) respectively.

## `integrated.py`

> Running this script for the first time will be quite slow for the first time due to the plethora of imports that are being made. On my machine it takes anywhere from one to two minutes for the imports to be done. Patience is key.

Usage of this script is straightforward. You run this script from terminal directly and specify all relevant options in your script call. If in doubt, run `python integrated.py --help` which gives you an overview of the options you can specify when running the script.

```
usage: integrated.py [-h] [--city CITY] [--date DATE] [--schools SCHOOLS] [--cell CELL] [--osmium OSMIUM] [--skip SKIP [SKIP ...]] [--plot PLOT [PLOT ...]]

Transit accessibility analysis pipeline. Computes travel time matrices from residential buildings to city centers and schools using public transit as well as by car and foot. Returns computed travel time matrices as well as (optionally) visualisations in form of pdf plots.

options:
  -h, --help            show this help message and exit
  --city CITY           Select any of ['Bern', 'Zürich', 'Solothurn'].
  --date DATE           Choose any date between ['2024-12-15', '2025-12-13'].
  --schools SCHOOLS     School data available for ['Bern', 'Zürich']. Specify True or False.
  --cell CELL           Grid cell size in meters, only numeric allowed, no 'm' or 'meters' necessary.
  --osmium OSMIUM       ['True', 'False']: Is Osmium-Tool available on your device? If not, please use the precomputed .osm.pbf files for each city and copy them to the correct
                        folder, see readme.md.
  --skip SKIP [SKIP ...]
                        Skip any of ['pre', 'routing', 'plotting']. This is meant for debugging and can only be done if the steps that are being skipped have been run already
  --plot PLOT [PLOT ...]
                        Plot any of ['day', 'night', 'school']. Default is all.
```

Example usage (1):
```
python integrated.py --city Zürich --date 2025-03-15 --cell 200 --plot day night
````

==> This returns full travel time matrices for Zürich and plots for travel times at day and night. The cell size is adjusted to 200x200m and the date (only relevant for transit) is set to 2025-03-15 instead of the default 2025-03-13. 

Example usage (2):
```
python integrated.py --city Bern --schools True --skip plotting
```

==> This returns full travel time matrices for Bern and no plots. 

If you intend to run `app.py` afterwards, you should run the script three times in the following configuration:

```
python integrated.py --city Bern --schools True --cell 100 --skip plotting
python integrated.py --city Zürich --schools True --cell 100 --skip plotting
python integrated.py --city Solothurn --schools False --cell 100 --skip plotting
```

> [1] Only specify `--schools True` for those cities for which school data is available, e.g. ["Bern", "Zürich"]. The program will alert you otherwise, obeying this will just save you a second.

> [2] A cell size of 100x100m is very precise but also computationally demanding as the sample size is quite large for bigger areas (especially Solothurn). **Consider using --cell 1000 for demo purposes (or checking whether my code works, hello @David Garcia et al.**).

If you are interested in the plots generated by this script, run, consecutively (only after having run the script has specified above):

```
python integrated.py --city Bern --schools True --skip pre routing
python integrated.py --city Zürich --schools True --skip pre routing
python integrated.py --city Solothurn --skip pre routing
```

This will output the plots into ~/plots/(Bern | Zürich | Solothurn)/...

If you want to do both things in one go and be done before lunch:
```
python integrated.py --city Bern --schools True --cell 1000
python integrated.py --city Zürich --schools True --cell 1000
python integrated.py --city Solothurn --cell 1000
```

## `app.py`

This is a streamlit app which allows you to interactively explore the results computed by `integrated.py`. As such, it is necessary for you to have run that script as described above before using `app.py`.

Start the streamlit app like such:

```
streamlit run app.py
```

This will open a browser window where you can view the resulting interactive visualisation. Close the browser to end, and exit in the terminal using `cmd + C` or similar (depending on OS).

## `custom_routing.py`

This is a streamlit app as well, and is dependent on `integrated.py` having run through (even though it only uses the clipped .osm.pbf files. So if you (a) have those already in the correct folder or (b) ran `python integrated.py --city (all cities) --skip routing plotting` this will run fine). If you have followed all the steps above, there is nothing you need to do additionally.

To start the streamlit app, do:

```
streamlit run custom_routing.py
```

You can now play around with finding out how badly (or well) your new flat options in Bern, Zürich or Solothurn are connected to your favorite university, unaffordable pizza place, or bridge to sleep under if you miss a rent payment.

Exiting is a bit of a problem-ish. As I (and r5py for that matter) are using external tools like Java and Docker, streamlit cannot close properly. To combat that, I implemented a kill switch at the very top left of the window. Once you press that, your python session is being killed without regard to anything. This will not break your computer, but may result in long loading times the next time you start up streamlit. Just as a note. More on that in the report (@David Garcia et al.). 

