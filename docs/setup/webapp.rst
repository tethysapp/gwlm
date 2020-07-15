********************************************
Setup: Web Application
********************************************

*Groundwater Data Mapper*

Prerequisites
--------------

-  Tethys Platform 3.0 with GeoServer, Postgis, and Thredds Docker containers: See:
   http://docs.tethysplatform.org

Installation
--------------
The installation is process is different for local development vs deployment. This section will walk you through both the methods.

Installation for App Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Install Tethys Platform**

Run these commands sequentially on the command line interface. Note: These instructions are for most linux systems. Most of the concepts are the same for mac/centos, except the docker installation.
You will have to install docker through the Docker documentation. Then use the tethys docker init commands to initialize the docker containers.

::

    mkdir thredds
    wget https://raw.githubusercontent.com/tethysplatform/tethys/release/scripts/install_tethys.sh
    bash install_tethys.sh --install-docker --docker-options '"-d -c thredds postgis geoserver"'


- Postgis Options
    * Enter the default options. *postgres* is the super user.

- GeoServer Options
    * Enter the options as you see fit. *admin* is the username, *geoserver* is the password for the geoserver portal.

- Thredds Options
    * Enter the options as you see fit. Be sure to link the thredds public directory to the thredds directory that was just created.

**Optional Tools to help with development**

*  pgAdmin4 - Application to view/manage postgresql database.
*  portainer - Open Source UI to manage Docker. View/manage docker images and containers.

**Install Groundwater Data Mapper App into the Portal**

Activate Tethys environment. If you followed developer installation simply type *t* and press enter. That will activate the Tethys environment.
If you installed Tethys as a conda-package activate the conda environment with the Tethys package.

You can use the following command to set alias via bashrc or you can use the command to activate the tethys-dev environment
::

    alias t='source /home/dev/miniconda/etc/profile.d/conda.sh; conda activate tethys-dev'

Clone the app repository into a directory of choice and install it
::

    git clone https://github.com/BYU-Hydroinformatics/gwlm.git
    cd gwlm
    tethys install -d

**Web Admin Setup**
