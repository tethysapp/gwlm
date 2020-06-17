from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.exc import IntegrityError
import math
import json
from .utils import (create_outlier,
                    get_session_obj,
                    user_permission_test,
                    process_region_shapefile,
                    process_aquifer_shapefile,
                    get_shapefile_attributes,
                    get_timeseries,
                    get_well_obs,
                    get_well_info,
                    get_wms_datasets,
                    get_region_aquifers_list,
                    get_region_variables_list,
                    process_wells_file,
                    process_measurements_file)
from tethys_sdk.workspaces import app_workspace
from .model import (Region,
                    Aquifer,
                    Variable,
                    Well)
from .interpolation_utils import process_interpolation



@user_passes_test(user_permission_test)
@app_workspace
def region_add(request, app_workspace):
    response = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        region_name = info.get('region')

        shapefile = request.FILES.getlist('shapefile')

        response = process_region_shapefile(shapefile, region_name, app_workspace)

        return JsonResponse(response)


@user_passes_test(user_permission_test)
def region_tabulator(request):
    json_obj = {}

    info = request.GET

    page = int(request.GET.get('page'))
    page = page - 1
    size = int(request.GET.get('size'))
    session = get_session_obj()
    # RESULTS_PER_PAGE = 10
    num_regions = session.query(Region).count()
    last_page = math.ceil(int(num_regions) / int(size))
    data_dict = []

    regions = (session.query(Region).order_by(Region.id)
    [(page * size):((page + 1) * size)])

    for region in regions:
        json_dict = {"id": region.id,
                     "region_name": region.region_name}
        data_dict.append(json_dict)

    session.close()

    response = {"data": data_dict, "last_page": last_page}

    return JsonResponse(response)


@user_passes_test(user_permission_test)
def region_update(request):
    response = {}

    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        region_id = info.get('region_id')
        region_name = info.get('region_name')
        try:
            int(region_id)
        except ValueError:
            return JsonResponse({'error': 'Region id is faulty.'})

        region = session.query(Region).get(region_id)

        try:
            region.region_name = region_name

            session.commit()
            session.close()
            return JsonResponse({'success': "Region successfully updated!"})
        except Exception as e:
            session.close()
            return JsonResponse({'error': "There is a problem with your request. " + str(e)})


@user_passes_test(user_permission_test)
def region_delete(request):
    """
    Controller for deleting a point.
    """
    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        post_info = request.POST

        region_id = post_info.get('region_id')

        try:
            # delete point
            try:
                region = session.query(Region).get(region_id)
            except ObjectDeletedError:
                session.close()
                return JsonResponse({'error': "The region to delete does not exist."})

            session.delete(region)
            session.commit()
            session.close()
            return JsonResponse({'success': "Region successfully deleted!"})
        except IntegrityError:
            session.close()
            return JsonResponse({'error': "There is a problem with your request."})


@user_passes_test(user_permission_test)
@app_workspace
def aquifer_add(request, app_workspace):
    response = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        region_id = info.get('region_id')
        name_attr = info.get('name_attribute')
        id_attr = info.get('id_attribute')

        shapefile = request.FILES.getlist('shapefile')

        response = process_aquifer_shapefile(shapefile,
                                             region_id,
                                             name_attr,
                                             id_attr,
                                             app_workspace)

        return JsonResponse(response)


@user_passes_test(user_permission_test)
def aquifer_tabulator(request):
    json_obj = {}

    info = request.GET

    page = int(request.GET.get('page'))
    page = page - 1
    size = int(request.GET.get('size'))
    session = get_session_obj()
    # RESULTS_PER_PAGE = 10
    num_aquifers = session.query(Aquifer).count()
    last_page = math.ceil(int(num_aquifers) / int(size))
    data_dict = []

    aquifers = (session.query(Aquifer).order_by(Aquifer.id)
    [(page * size):((page + 1) * size)])

    for aquifer in aquifers:
        json_dict = {"id": aquifer.id,
                     "aquifer_id": aquifer.aquifer_id,
                     "aquifer_name": aquifer.aquifer_name}
        data_dict.append(json_dict)

    session.close()

    response = {"data": data_dict, "last_page": last_page}

    return JsonResponse(response)


@user_passes_test(user_permission_test)
def aquifer_update(request):
    response = {}

    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        aquifer_id = info.get('aquifer_id')
        aquifer_name = info.get('aquifer_name')
        aquifer_name_id = info.get('aquifer_name_id')
        try:
            int(aquifer_id)
        except ValueError:
            return JsonResponse({'error': 'Region id is faulty.'})

        aquifer = session.query(Aquifer).get(aquifer_id)

        try:
            aquifer.aquifer_name = aquifer_name
            aquifer.aquifer_id = aquifer_name_id

            session.commit()
            session.close()
            return JsonResponse({'success': "Aquifer successfully updated!"})
        except Exception as e:
            session.close()
            return JsonResponse({'error': "There is a problem with your request. " + str(e)})


@user_passes_test(user_permission_test)
def aquifer_delete(request):
    """
    Controller for deleting a point.
    """
    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        post_info = request.POST

        aquifer_id = post_info.get('aquifer_id')

        try:
            # delete point
            try:
                aquifer = session.query(Aquifer).get(aquifer_id)
            except ObjectDeletedError:
                session.close()
                return JsonResponse({'error': "The aquifer to delete does not exist."})

            session.delete(aquifer)
            session.commit()
            session.close()
            return JsonResponse({'success': "Aquifer successfully deleted!"})
        except IntegrityError:
            session.close()
            return JsonResponse({'error': "There is a problem with your request."})


@user_passes_test(user_permission_test)
@app_workspace
def get_shp_attributes(request, app_workspace):

    response = {}

    if request.is_ajax() and request.method == 'POST':

        try:

            shapefile = request.FILES.getlist('shapefile')

            attributes = get_shapefile_attributes(shapefile, app_workspace, True)

            response = {"success": "success",
                        "attributes": attributes}

            return JsonResponse(response)

        except Exception as e:
            json_obj = {'error': json.dumps(e)}

            return JsonResponse(json_obj)


@user_passes_test(user_permission_test)
@app_workspace
def get_well_attributes(request, app_workspace):

    response = {}

    if request.is_ajax() and request.method == 'POST':

        try:

            shapefile = request.FILES.getlist('shapefile')

            attributes = get_shapefile_attributes(shapefile, app_workspace, False)
            print(attributes)

            response = {"success": "success",
                        "attributes": attributes}

            return JsonResponse(response)

        except Exception as e:
            json_obj = {'error': json.dumps(e)}

            return JsonResponse(json_obj)


@user_passes_test(user_permission_test)
@app_workspace
def get_measurements_attributes(request, app_workspace):

    response = {}

    if request.is_ajax() and request.method == 'POST':

        try:

            shapefile = request.FILES.getlist('shapefile')

            attributes = get_shapefile_attributes(shapefile, app_workspace, False)

            response = {"success": "success",
                        "attributes": attributes}

            return JsonResponse(response)

        except Exception as e:
            json_obj = {'error': json.dumps(e)}

            return JsonResponse(json_obj)


@user_passes_test(user_permission_test)
def get_aquifers(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        region_id = info.get('id')
        aquifers_list = get_region_aquifers_list(region_id)
        variables_list = get_region_variables_list(region_id)

        response = {'success': 'success',
                    'variables_list': variables_list,
                    'aquifers_list': aquifers_list}

        return JsonResponse(response)


@user_passes_test(user_permission_test)
def get_wells(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        aquifer_id = info.get('id')
        session = get_session_obj()
        wells = session.query(Well).filter(Well.aquifer_id == aquifer_id)
        wells_list = [[well.well_name, well.id] for well in wells]
        session.close()

        response = {'success': 'success',
                    'wells_list': wells_list}

        return JsonResponse(response)


@user_passes_test(user_permission_test)
@app_workspace
def wells_add(request, app_workspace):
    response = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        lat = info.get('lat')
        lon = info.get('lon')
        well_id = info.get('id')
        name = info.get('name')
        gse = info.get('gse')
        attributes = info.get('attributes')
        file = request.FILES.getlist('shapefile')
        aquifer_id = info.get('aquifer_id')
        aquifer_col = info.get('aquifer_col')
        region_id = info.get('region_id')
        response = process_wells_file(lat, lon, well_id, name,
                                      gse, attributes, file,
                                      aquifer_id, aquifer_col,
                                      app_workspace, region_id)


        return JsonResponse(response)


@user_passes_test(user_permission_test)
def wells_tabulator(request):
    page = int(request.GET.get('page'))
    page = page - 1
    size = int(request.GET.get('size'))
    session = get_session_obj()
    # RESULTS_PER_PAGE = 10
    num_wells = session.query(Well).count()
    last_page = math.ceil(int(num_wells) / int(size))
    data_dict = []

    wells = (session.query(Well).order_by(Well.id)
    [(page * size):((page + 1) * size)])

    for well in wells:
        json_dict = {"id": well.id,
                     "well_name": well.well_name,
                     "gse": well.gse,
                     "attr_dict": json.dumps(well.attr_dict)
                     }
        data_dict.append(json_dict)

    session.close()

    response = {"data": data_dict, "last_page": last_page}

    return JsonResponse(response)


@user_passes_test(user_permission_test)
def well_delete(request):
    """
    Controller for deleting a point.
    """
    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        post_info = request.POST

        well_id = post_info.get('well_id')

        try:
            # delete point
            try:
                well = session.query(Well).get(well_id)
            except ObjectDeletedError:
                session.close()
                return JsonResponse({'error': "The well to delete does not exist."})

            session.delete(well)
            session.commit()
            session.close()
            return JsonResponse({'success': "Well successfully deleted!"})
        except IntegrityError:
            session.close()
            return JsonResponse({'error': "There is a problem with your request."})


@user_passes_test(user_permission_test)
@app_workspace
def measurements_add(request, app_workspace):
    response = {}

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        file = request.FILES.getlist('shapefile')
        time = info.get("time")
        value = info.get("value")
        well_id = info.get("id")
        variable_id = info.get("variable_id")
        time_format = info.get("date_format")
        region_id = info.get("region_id")
        aquifer_id = info.get('aquifer_id')
        aquifer_col = info.get('aquifer_col')
        response = process_measurements_file(region_id, well_id, time, value,
                                             time_format, variable_id, file,
                                             aquifer_id, aquifer_col,
                                             app_workspace)


        return JsonResponse(response)


def region_timeseries(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        info = request.POST
        aquifer_id = info.get('aquifer_id')
        well_id = info.get('well_id')
        variable_id = info.get('variable_id')
        timeseries = get_timeseries(well_id, variable_id)
        response['success'] = 'success'
        response['timeseries'] = timeseries
        response['well_info'] = get_well_info(well_id)

        return JsonResponse(response)


def region_well_obs(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        info = request.POST
        aquifer_id = info.get('aquifer_id')
        variable_id = info.get('variable_id')
        well_obs = get_well_obs(aquifer_id, variable_id)
        response['obs_dict'] = well_obs
        if len(well_obs) > 0:
            response['min_obs'] = min(well_obs.values())
            response['max_obs'] = max(well_obs.values())
        response['success'] = 'success'

    return JsonResponse(response)


def set_outlier(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        info = request.POST
        well_id = info.get('well_id')
        outlier = create_outlier(well_id)
        response['success'] = 'success'
        response['outlier'] = outlier

    return JsonResponse(response)


@user_passes_test(user_permission_test)
def variable_tabulator(request):
    page = int(request.GET.get('page'))
    page = page - 1
    size = int(request.GET.get('size'))
    session = get_session_obj()
    # RESULTS_PER_PAGE = 10
    num_vars = session.query(Variable).count()
    last_page = math.ceil(int(num_vars) / int(size))
    data_dict = []

    vars = (session.query(Variable).order_by(Variable.id)
    [(page * size):((page + 1) * size)])

    for var in vars:
        json_dict = {"id": var.id,
                     "variable_name": var.name,
                     "variable_units": var.units,
                     "variable_description": var.description,
                     }
        data_dict.append(json_dict)

    session.close()

    response = {"data": data_dict, "last_page": last_page}

    return JsonResponse(response)


@user_passes_test(user_permission_test)
def variable_update(request):
    response = {}

    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        info = request.POST

        variable_id = info.get('variable_id')
        variable_name = info.get('variable_name')
        variable_units = info.get('variable_units')
        variable_description = info.get('variable_description')

        try:
            int(variable_id)
        except ValueError:
            return JsonResponse({'error': 'Variable id is faulty.'})

        variable = session.query(Variable).get(variable_id)

        try:
            variable.name = variable_name
            variable.units = variable_units
            variable.description = variable_description

            session.commit()
            session.close()
            return JsonResponse({'success': "Variable successfully updated!"})
        except Exception as e:
            session.close()
            return JsonResponse({'error': "There is a problem with your request. " + str(e)})


@user_passes_test(user_permission_test)
def variable_delete(request):
    """
    Controller for deleting a variable.
    """
    session = get_session_obj()

    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        post_info = request.POST

        variable_id = post_info.get('variable_id')

        try:
            # delete point
            try:
                variable = session.query(Variable).get(variable_id)
            except ObjectDeletedError:
                session.close()
                return JsonResponse({'error': "The variable to delete does not exist."})

            session.delete(variable)
            session.commit()
            session.close()
            return JsonResponse({'success': "Variable successfully deleted!"})
        except IntegrityError:
            session.close()
            return JsonResponse({'error': "There is a problem with your request."})


INFO_DICT = {'region': '3',
             'aquifer': '24',
             'variable': '1',
             'porosity': '0.1',
             'spatial_interpolation': 'IDW',
             'temporal_interpolation': 'MLR',
             'search_radius': '0.1',
             'ndmin': '5',
             'ndmax': '15',
             'start_date': '1970',
             'end_date': '1980',
             'resolution': '0.05',
             'min_ratio': '0.25',
             'time_tolerance': '20',
             'frequency': '5',
             'default': '0',
             'min_samples': '10',
             'seasonal': '999',
             'from_wizard': 'true',
             'gap_size': '365 days',
             'pad': '90',
             'spacing': '1MS'}


@user_passes_test(user_permission_test)
def interpolate(request):
    response = {}
    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        try:
            post_info = request.POST
            info_dict = post_info.dict()
            result = process_interpolation(info_dict)
            response['success'] = 'success'
            response['result'] = result
        except Exception as e:
            response['error'] = str(e)

        return JsonResponse(response)


def region_wms_datasets(request):

    response = {}
    if request.is_ajax() and request.method == 'POST':
        # get/check information from AJAX request
        post_info = request.POST
        aquifer_name = post_info.get('aquifer_name')
        print(aquifer_name)
        well_files = get_wms_datasets(aquifer_name)
        response['success'] = 'success'

    return JsonResponse(response)
