import os
import shutil
import uuid
import pandas as pd
import geopandas as gpd
from shapely import wkt
from .app import Gwlm as app
from .model import (Region,
                    Aquifer,
                    Well,
                    Measurement,
                    Variable)
import simplejson
import json
from tethys_sdk.gizmos import (TextInput,
                               SelectInput)
from pandarallel import pandarallel
from sqlalchemy.sql import func
import time
from datetime import datetime
import calendar
from thredds_crawler.crawl import Crawl
import xarray as xr
import plotly.graph_objects as go


def user_permission_test(user):
    return user.is_superuser or user.is_staff


def get_session_obj():
    app_session = app.get_persistent_store_database('gwdb', as_sessionmaker=True)
    session = app_session()
    return session


def get_region_select():
    region_list = get_regions()
    region_select = SelectInput(display_text='Select a Region',
                                name='region-select',
                                options=region_list,)

    return region_select


def get_regions():
    session = get_session_obj()
    regions = session.query(Region).all()
    region_list = []

    for region in regions:
        region_list.append(("%s" % region.region_name, region.id))

    session.close()
    return region_list


def get_aquifer_select(region_id, aquifer_id=False):
    aquifer_list = []
    if region_id is not None:
        session = get_session_obj()
        aquifers = session.query(Aquifer).filter(Aquifer.region_id == region_id)

        for aquifer in aquifers:
            if aquifer_id:
                aquifer_list.append(("%s" % aquifer.aquifer_name, aquifer.id))
            else:
                aquifer_list.append(("%s" % aquifer.aquifer_name, aquifer.aquifer_id))
        session.close()

    aquifer_select = SelectInput(display_text='Select an Aquifer',
                                 name='aquifer-select',
                                 options=aquifer_list,)

    return aquifer_select


def get_variable_list():
    session = get_session_obj()
    variables = session.query(Variable).all()

    variable_list = []
    for variable in variables:
        variable_list.append((f'{variable.name}, {variable.units}', variable.id))

    session.close()
    return variable_list


def get_variable_select():
    variable_list = get_variable_list()

    variable_select = SelectInput(display_text='Select Variable',
                                  name='variable-select',
                                  options=variable_list,)
    return variable_select


def get_region_variables_list(region_id):
    variable_list = []
    if region_id is not None:
        session = get_session_obj()
        variables = (session.query(Variable)
                     .join(Measurement, Measurement.variable_id == Variable.id)
                     .join(Well, Measurement.well_id == Well.id)
                     .join(Aquifer, Well.aquifer_id == Aquifer.id)
                     .filter(Aquifer.region_id == int(region_id))
                     # .join(Aquifer, Region.id == Aquifer.region_id)
                     # .join(Measurement, Well.id == Measurement.well_id)
                     # .filter(Aquifer.region_id == int(region_id))
                     .distinct()
                     )

        for variable in variables:
            variable_list.append((f'{variable.name}, {variable.units}', variable.id))

        session.close()

    return variable_list


def get_metrics():
    session = get_session_obj()
    metrics_query = (session.query(Region.region_name, Variable.name.label('variable_name'),
                                   func.count(Measurement.id).label('num_of_measurements'))
                     .join(Measurement, Measurement.variable_id == Variable.id)
                     .join(Well, Measurement.well_id == Well.id)
                     .join(Aquifer, Well.aquifer_id == Aquifer.id)
                     .join(Region, Region.id == Aquifer.region_id)
                     .group_by(Region.region_name, Variable.name)
                     )
    metrics_df = pd.read_sql(metrics_query.statement, session.bind)
    session.close()

    fig = go.Figure(data=[go.Table(
        header=dict(values=['Region Name', 'Variable Name', 'Number of Measurements'],
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[metrics_df.region_name, metrics_df.variable_name, metrics_df.num_of_measurements],
                   fill_color='lavender',
                   align='left'))
    ])

    return fig


def get_region_aquifers_list(region_id):
    session = get_session_obj()
    aquifers = session.query(Aquifer).filter(Aquifer.region_id == region_id)
    aquifers_list = [[aquifer.aquifer_name, aquifer.id] for aquifer in aquifers]
    session.close()
    return aquifers_list


def get_aquifers_list():
    session = get_session_obj()
    aquifers = session.query(Aquifer).all()
    aquifers_list = [[aquifer.aquifer_name, aquifer.id] for aquifer in aquifers]
    session.close()
    return aquifers_list


def get_num_wells():
    session = get_session_obj()
    wells = session.query(Well.id).distinct().count()
    session.close()
    return wells


def get_num_measurements():
    session = get_session_obj()
    measurements = session.query(Measurement.id).distinct().count()
    session.close()
    return measurements


def get_region_variable_select(region_id):
    variable_list = get_region_variables_list(region_id)
    variable_select = SelectInput(display_text='Select Variable',
                                  name='variable-select',
                                  options=variable_list,
                                  attributes={'id': 'variable-select'},
                                  classes='variable-select')

    return variable_select


def process_region_shapefile(shapefile, region_name, app_workspace):

    session = get_session_obj()
    temp_dir = None
    try:
        gdf, temp_dir = get_shapefile_gdf(shapefile, app_workspace)
        gdf['region_name'] = region_name
        gdf = gdf.dissolve(by='region_name')
        region = Region(region_name=region_name, geometry=gdf.geometry.values[0])
        session.add(region)
        session.commit()
        session.close()

        return {"success": "success"}

    except Exception as e:
        session.close()
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return {"error": str(e)}
    finally:
        # Delete the temporary directory once the shapefile is processed
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def process_aquifer_shapefile(shapefile,
                              region_id,
                              name_attr,
                              id_attr,
                              app_workspace):

    session = get_session_obj()
    temp_dir = None

    def add_aquifer_apply(row):
        aquifer = Aquifer(region_id=int(region_id),
                          aquifer_name=row.aquifer_name,
                          aquifer_id=row.aquifer_id,
                          geometry=row.geometry)
        return aquifer
    try:
        start_time = time.time()
        pandarallel.initialize()
        gdf, temp_dir = get_shapefile_gdf(shapefile, app_workspace)
        gdf = gdf.dissolve(by=name_attr, as_index=False)
        # gdf.to_csv('texas_aquifers.csv')
        rename_cols = {name_attr: 'aquifer_name',
                       id_attr: 'aquifer_id'}
        gdf.rename(columns=rename_cols, inplace=True)
        gdf = gdf[['aquifer_name', 'aquifer_id', 'geometry']]
        aquifer_list = gdf.parallel_apply(add_aquifer_apply, axis=1)

        session.add_all(aquifer_list)
        session.commit()
        session.close()
        end_time = time.time()
        total_time = (end_time - start_time)

        return {"success": "success"}

    except Exception as e:
        session.close()
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return {"error": str(e)}
    finally:
        # Delete the temporary directory once the shapefile is processed
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def get_shapefile_gdf(shapefile, app_workspace, polygons=True):
    temp_id = uuid.uuid4()
    temp_dir = os.path.join(app_workspace.path, str(temp_id))
    os.makedirs(temp_dir)
    gbyos_pol_shp = None
    upload_csv = None
    gdf = None

    for f in shapefile:
        f_name = f.name
        f_path = os.path.join(temp_dir, f_name)

        with open(f_path, 'wb') as f_local:
            f_local.write(f.read())

    for file in os.listdir(temp_dir):
        # Reading the shapefile only
        if file.endswith(".shp") or file.endswith(".geojson") or file.endswith(".json"):
            f_path = os.path.join(temp_dir, file)
            gbyos_pol_shp = f_path

        if file.endswith(".csv"):
            f_path = os.path.join(temp_dir, file)
            upload_csv = f_path

    if gbyos_pol_shp is not None:
        gdf = gpd.read_file(gbyos_pol_shp)

    if upload_csv is not None:
        df = pd.read_csv(upload_csv, engine='python')
        if polygons:
            gdf = gpd.GeoDataFrame(df, crs={'init': 'epsg:4326'}, geometry=df['geometry'].apply(wkt.loads))
        else:
            gdf = df

    return gdf, temp_dir


def get_shapefile_attributes(shapefile, app_workspace, polygons=True):
    temp_dir = None
    try:

        gdf, temp_dir = get_shapefile_gdf(shapefile, app_workspace, polygons)

        attributes = gdf.columns.values.tolist()

        return attributes

    except Exception as e:
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return {"error": str(e)}
    finally:
        # Delete the temporary directory once the shapefile is processed
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def geoserver_text_gizmo():
    geoserver_wfs_endpoint = app.get_spatial_dataset_service('primary_geoserver', as_wfs=True)

    geoserver_text_input = TextInput(display_text='Geoserver',
                                     name='geoserver-text-input',
                                     placeholder=geoserver_wfs_endpoint,
                                     attributes={'value': geoserver_wfs_endpoint},
                                     classes="hidden")

    return geoserver_text_input


def thredds_text_gizmo():
    thredds_endpoint = app.get_spatial_dataset_service('primary_thredds', as_endpoint=True)
    thredds_text_input = TextInput(display_text='Thredds',
                                   name='thredds-text-input',
                                   placeholder=thredds_endpoint,
                                   attributes={'value': thredds_endpoint},
                                   classes="hidden")

    return thredds_text_input


def process_wells_file(lat,
                       lon,
                       well_id,
                       name,
                       gse,
                       attrs,
                       file,
                       aquifer_id,
                       aquifer_col,
                       app_workspace,
                       region_id):
    temp_dir = None
    session = get_session_obj()
    try:
        gdf, temp_dir = get_shapefile_gdf(file, app_workspace, polygons=False)
        rename_cols = {lat: 'latitude',
                       lon: 'longitude',
                       well_id: 'well_id',
                       name: 'well_name',
                       gse: 'gse'}
        if len(aquifer_id) > 0:
            gdf['aquifer_id'] = aquifer_id
            gdf = gdf.rename(columns=rename_cols)

        if len(aquifer_col) > 0:
            rename_cols[aquifer_col] = 'aquifer_id'
            gdf.rename(columns=rename_cols, inplace=True)
            aquifer_ids = list(gdf['aquifer_id'].unique().astype(str))
            aquifer = (session.query(Aquifer).filter(Aquifer.region_id == region_id,
                                                     Aquifer.aquifer_id.in_(aquifer_ids)).all())
            aq_dict = {aq.aquifer_id: aq.id for aq in aquifer}
            gdf['aquifer_id'] = gdf['aquifer_id'].astype(str)
            gdf['aquifer_id'] = gdf['aquifer_id'].map(aq_dict)

        attributes = None
        if attrs:
            attributes = attrs.split(',')

        for row in gdf.itertuples():
            attr_dict = {}
            if attributes:
                attr_dict = {attr: getattr(row, attr) for attr in attributes}

            attr_dict = simplejson.dumps(attr_dict, ignore_nan=True)
            attr_dict = json.loads(attr_dict)
            well = Well(aquifer_id=int(row.aquifer_id),
                        latitude=float(row.latitude),
                        longitude=float(row.longitude),
                        well_id=row.well_id,
                        well_name=str(row.well_name),
                        gse=float(row.gse),
                        attr_dict=attr_dict,
                        outlier=False)
            session.add(well)
        session.commit()
        session.close()

        response = {'success': 'success'}

    except Exception as e:
        session.close()
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return {"error": str(e)}
    finally:
        # Delete the temporary directory once the shapefile is processed
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    return response


def process_measurements_file(region_id,
                              well_id,
                              m_time,
                              value,
                              time_format,
                              variable_id,
                              file,
                              aquifer_id,
                              aquifer_col,
                              app_workspace):

    temp_dir = None
    session = get_session_obj()
    try:
        gdf, temp_dir = get_shapefile_gdf(file, app_workspace, polygons=False)
        rename_cols = {well_id: 'well_id',
                       m_time: 'time',
                       value: 'value'}
        gdf = gdf.rename(columns=rename_cols)
        gdf['variable_id'] = variable_id

        if len(aquifer_id) > 0:
            gdf['aquifer_id'] = aquifer_id
            gdf = gdf.rename(columns=rename_cols)

        if len(aquifer_col) > 0:
            rename_cols[aquifer_col] = 'aquifer_id'
            gdf.rename(columns=rename_cols, inplace=True)
            aquifer_ids = list(gdf['aquifer_id'].unique().astype(str))
            aquifers = (session.query(Aquifer).filter(Aquifer.region_id == region_id,
                                                      Aquifer.aquifer_id.in_(aquifer_ids)).all())
            aq_dict = {aq.aquifer_id: aq.id for aq in aquifers}
            gdf['aquifer_id'] = gdf['aquifer_id'].astype(str)
            gdf['aquifer_id'] = gdf['aquifer_id'].map(aq_dict)

        aquifer_ids = list(gdf['aquifer_id'].unique().astype(str))
        well_ids = list(gdf['well_id'].unique().astype(str))
        wells = (session.query(Well).filter(Well.well_id.in_(well_ids),
                                            Well.aquifer_id.in_(aquifer_ids)).all())

        well_dict = {well.well_id: well.id for well in wells}
        gdf['well_id'] = gdf['well_id'].astype(str)
        gdf['well_id'] = gdf['well_id'].map(well_dict)
        gdf.dropna(subset=['time', 'value'], inplace=True)
        for row in gdf.itertuples():
            measurement = Measurement(well_id=int(row.well_id),
                                      variable_id=int(row.variable_id),
                                      ts_time=row.time,
                                      ts_value=float(row.value),
                                      ts_format=time_format
                                      )
            session.add(measurement)
        session.commit()
        session.close()
        response = {'success': 'success'}

    except Exception as e:
        session.close()
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return {"error": str(e)}

    finally:
        # Delete the temporary directory once the shapefile is processed
        if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    return response


def get_timeseries(well_id, variable_id):
    session = get_session_obj()
    well_id = well_id.split('.')[1]
    ts_obj = session.query(Measurement).filter(Measurement.well_id == well_id,
                                               Measurement.variable_id == variable_id).all()
    timeseries = [[calendar.timegm(datetime.strptime(obj.ts_time, obj.ts_format).utctimetuple())*1000, obj.ts_value]
                  for obj in ts_obj]
    timeseries = sorted(timeseries)
    session.close()
    return timeseries


def get_well_obs(aquifer_id, variable_id):
    session = get_session_obj()
    wells_list = [r.id for r in session.query(Well.id).filter(Well.aquifer_id == aquifer_id).distinct()]
    m_query = (session.query(Measurement.well_id,
                             func.count(Measurement.ts_value).label('obs'))
               .group_by(Measurement.well_id)
               .filter(Measurement.well_id.in_(wells_list),
                       Measurement.variable_id == variable_id))
    obs_dict = {w.well_id: w.obs for w in m_query}
    zero_obs_wells = set(wells_list) - set(obs_dict.keys())
    for well in zero_obs_wells:
        obs_dict[well] = 0
    return obs_dict


def get_well_info(well_id):
    session = get_session_obj()
    well_id = well_id.split('.')[1]
    well = session.query(Well).filter(Well.id == well_id).first()
    json_dict = {"id": well.id,
                 "well_name": well.well_name,
                 "gse": well.gse,
                 "attr_dict": json.dumps(well.attr_dict)
                 }

    session.close()
    return json_dict


def create_outlier(well_id):
    session = get_session_obj()
    well_id = well_id.split('.')[1]
    well_obj = session.query(Well).filter(Well.id == well_id).first()
    set_value = not well_obj.outlier
    well_obj.outlier = set_value
    session.commit()
    session.flush()
    session.close()
    return set_value


def get_wms_datasets(aquifer_name, variable_id, region_id):
    catalog = app.get_spatial_dataset_service('primary_thredds', as_engine=True)
    aquifer_name = aquifer_name.replace(" ", "_")
    c = Crawl(catalog.catalog_url)
    file_str = f'{region_id}/{aquifer_name}/{aquifer_name}_{variable_id}'
    urls = [[s.get("url"), d.name] for d in c.datasets for s in d.services
            if s.get("service").lower() == "wms" and file_str in s.get("url")]
    return urls


def get_wms_metadata(aquifer_name, file_name, region_id):
    thredds_directory = app.get_custom_setting('gw_thredds_directoy')
    # aquifer_dir = os.path.join(thredds_directory, str(region_id), str(aquifer_obj[1]))
    aquifer_name = aquifer_name.replace(" ", "_")
    file_path = os.path.join(thredds_directory, str(region_id), aquifer_name, file_name)
    ds = xr.open_dataset(file_path)
    range_min = int(ds.tsvalue.min().values)
    range_max = int(ds.tsvalue.max().values)
    return range_min, range_max
