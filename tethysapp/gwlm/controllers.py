from django.shortcuts import render, reverse, redirect
from django.contrib import messages
from tethys_sdk.permissions import login_required
from tethys_sdk.gizmos import Button, TextInput, SelectInput
from django.http.response import HttpResponseRedirect
from django.contrib.auth.decorators import user_passes_test
from .utils import user_permission_test
from .app import Gwlm as app
from .model import Region, Aquifer, Variable
from tethys_sdk.compute import get_scheduler
from tethys_sdk.gizmos import JobsTable
from tethys_compute.models.dask.dask_job_exception import DaskJobException
from .utils import (geoserver_text_gizmo,
                    get_region_select,
                    get_region_variable_select,
                    get_aquifer_select,
                    get_variable_select,
                    thredds_text_gizmo,
                    get_session_obj)
import sys
# get job manager for the app
job_manager = app.get_job_manager()


def home(request):
    """
    Controller for the app home page.
    """
    region_select = get_region_select()

    context = {
        'region_select': region_select
    }

    return render(request, 'gwlm/home.html', context)


def region_map(request):
    """
    Controller for the Region Map home page.
    """
    info = request.GET

    region_id = info.get('region-select')
    aquifer_select = get_aquifer_select(region_id, aquifer_id=True)
    geoserver_text_input = geoserver_text_gizmo()
    thredds_text_input = thredds_text_gizmo()
    variable_select = get_region_variable_select(region_id=region_id)
    # variable_select = get_variable_select()

    context = {
        'aquifer_select': aquifer_select,
        'variable_select': variable_select,
        'geoserver_text_input': geoserver_text_input,
        'thredds_text_input': thredds_text_input
    }

    return render(request, 'gwlm/region_map.html', context)


@user_passes_test(user_permission_test)
def interpolation(request):

    region_select = get_region_select()
    aquifer_select = get_aquifer_select(None)
    variable_select = get_variable_select()
    select_porosity = TextInput(display_text='Enter the storage coefficient for the aquifer:',
                                name='select-porosity',
                                initial='0.1',
                                )
    select_interpolation = SelectInput(display_text='Spatial Interpolation Method',
                                       name='select-spatial-interpolation',
                                       multiple=False,
                                       options=[("IDW (Shepard's Method)", 'IDW'), ('Kriging', 'Kriging'),
                                                ('Kriging with External Drift', 'Kriging with External Drift')],
                                       initial="IDW (Shepard's Method)",
                                       )
    temporal_interpolation = SelectInput(display_text='Temporal Interpolation Method',
                                         name='select-temporal-interpolation',
                                         multiple=False,
                                         options=[("Pchip Interpolation", 'pchip'), ('Multi-Linear Regression', 'MLR')],
                                         initial="Pchip Interpolation",
                                         )
    well_sample_options = [(i, i) for i in range(101)]
    well_sample_options.append(("No Maximum", 999))
    rads = [(float(i)/10.0, float(i)/10.0) for i in range(1, 50)]
    for i in range(5, 10, 1):
        rads.append((i, i))
    dates = [(i, i) for i in range(1850, 2019)]
    tolerances = [(f'{i} Year', i) for i in range(1, 26)]
    tolerances.append(("50 Years", 50))
    tolerances.append(("No Limit", 999))
    ratios = [(f'{i}%', float(i)/100) for i in range(5, 105, 5)]
    ratios.append(("No Minimum", 0))

    select_search_radius = SelectInput(display_text='Specify search radius in degrees',
                                       name='select-search-radius',
                                       multiple=False,
                                       options=rads
                                       )

    select_ndmin = SelectInput(display_text='Minimum Wells to use for estimating a block',
                               name='select-ndmin',
                               options=well_sample_options,
                               initial=5,
                               multiple=False)
    select_ndmax = SelectInput(display_text='Maximum Wells to use for estimating a block',
                               name='select-ndmax',
                               options=well_sample_options,
                               initial=15,
                               multiple=False)
    start_date = SelectInput(display_text='Interpolation Start Date',
                             name='start-date',
                             multiple=False,
                             options=dates,
                             initial=1950
                             )
    resolution = SelectInput(display_text='Raster Resolution',
                             name='resolution',
                             multiple=False,
                             options=[(".001 degree", .001), (".0025 degree", .0025), (".005 degree", .005),
                                      (".01 degree", .01), (".025 degree", .025), (".05 degree", .05), (".1 degree", .10)],
                             initial=".05 degree"
                             )
    end_date = SelectInput(display_text='Interpolation End Date',
                           name='end-date',
                           multiple=False,
                           options=dates,
                           initial=2018
                           )
    min_ratio = SelectInput(display_text='Percent of Time Frame Well Timeseries Must Span',
                            name='min-ratio',
                            options=ratios,
                            initial="75%"
                            )
    time_tolerance = SelectInput(display_text='Temporal Extrapolation Limit',
                                 name='time-tolerance',
                                 multiple=False,
                                 options=tolerances,
                                 initial="5 Years"
                                 )
    frequency = SelectInput(display_text='Time Increment',
                            name='frequency',
                            multiple=False,
                            options=[("3 months", .25), ("6 months", .5), ("1 year", 1), ("2 years", 2),
                                     ("5 years", 5), ("10 years", 10), ("25 years", 25)],
                            initial="5 years"
                            )
    default = SelectInput(display_text='Set Interpolation as Default for the Aquifer',
                          name='default',
                          multiple=False,
                          options=[("Yes", 1), ("No", 0)],
                          initial="No"
                          )
    min_samples = SelectInput(display_text='Minimum Water Level Samples per Well',
                              name='min-samples',
                              options=[("1 Sample", 1), ("2 Samples", 2), ("5 Samples", 5), ("10 Samples", 10),
                                       ("15 Samples", 15), ("20 Samples", 20), ("25 Samples", 25), ("50 Samples", 50)],
                              initial="5 Samples"
                              )
    seasonal = SelectInput(display_text='Annual Sampling Time',
                           name='seasonal',
                           multiple=False,
                           options=[("Winter (Nov-Jan)", 0),
                                    ("Spring (Feb-Apr)", 1),
                                    ("Summer (May-July)", 2),
                                    ("Fall (Aug-Oct)", 3),
                                    ("Use All Data", 999)],
                           initial="Use All Data"
                           )
    add_button = Button(display_text='Submit',
                        icon='glyphicon glyphicon-plus',
                        style='primary',
                        name='submit',
                        attributes={'id': 'submit'},
                        href=reverse('gwlm:run-dask', kwargs={'job_type': 'delayed'}),
                        classes="add")

    context = {
        'region_select': region_select,
        'aquifer_select': aquifer_select,
        'variable_select': variable_select,
        'select_porosity': select_porosity,
        'select_interpolation': select_interpolation,
        'temporal_interpolation': temporal_interpolation,
        'select_ndmin': select_ndmin,
        'select_ndmax': select_ndmax,
        'select_search_radius': select_search_radius,
        'start_date': start_date,
        'end_date': end_date,
        'frequency': frequency,
        'default': default,
        'resolution': resolution,
        'min_ratio': min_ratio,
        'time_tolerance': time_tolerance,
        'min_samples': min_samples,
        'seasonal': seasonal,
        'add_button': add_button
    }
    return render(request, 'gwlm/interpolation.html', context)


@user_passes_test(user_permission_test)
def add_region(request):
    """
    Controller for add region
    """

    region_text_input = TextInput(display_text='Region Name',
                                  name='region-text-input',
                                  placeholder='e.g.: West Africa',
                                  attributes={'id': 'region-text-input'},
                                  )

    add_button = Button(display_text='Add Region',
                        icon='glyphicon glyphicon-plus',
                        style='primary',
                        name='submit-add-region',
                        attributes={'id': 'submit-add-region'},
                        classes="add")

    context = {
        'region_text_input': region_text_input,
        'add_button': add_button
    }

    return render(request, 'gwlm/add_region.html', context)


@user_passes_test(user_permission_test)
def update_region(request):

    id_input = TextInput(display_text='Region ID',
                         name='id-input',
                         placeholder='',
                         attributes={'id': 'id-input', 'readonly': 'true'})

    region_text_input = TextInput(display_text='Region Name',
                                  name='region-text-input',
                                  placeholder='e.g.: West Africa',
                                  attributes={'id': 'region-text-input'},
                                  )

    geoserver_text_input = geoserver_text_gizmo()

    context = {
        'id_input': id_input,
        'region_text_input': region_text_input,
        'geoserver_text_input': geoserver_text_input
    }
    return render(request, 'gwlm/update_region.html', context)


@user_passes_test(user_permission_test)
def add_aquifer(request):
    """
    Controller for add aquifer
    """
    region_select = get_region_select()
    aquifer_text_input = TextInput(display_text='Aquifer Name',
                                   name='aquifer-text-input',
                                   placeholder='e.g.: Niger',
                                   attributes={'id': 'aquifer-text-input'},
                                   )

    add_button = Button(display_text='Add Aquifer',
                        icon='glyphicon glyphicon-plus',
                        style='primary',
                        name='submit-add-aquifer',
                        attributes={'id': 'submit-add-aquifer'},
                        classes="add hidden")

    attributes_button = Button(display_text='Get Attributes',
                               icon='glyphicon glyphicon-plus',
                               style='primary',
                               name='submit-get-attributes',
                               attributes={'id': 'submit-get-attributes'}, )

    context = {
        'aquifer_text_input': aquifer_text_input,
        'region_select': region_select,
        'attributes_button': attributes_button,
        'add_button': add_button
    }

    return render(request, 'gwlm/add_aquifer.html', context)


@user_passes_test(user_permission_test)
def update_aquifer(request):

    id_input = TextInput(display_text='Aquifer ID',
                         name='id-input',
                         placeholder='',
                         attributes={'id': 'id-input', 'readonly': 'true'})

    aquifer_text_input = TextInput(display_text='Aquifer Name',
                                   name='aquifer-text-input',
                                   placeholder='e.g.: Abod',
                                   attributes={'id': 'aquifer-text-input'},
                                   )

    aquifer_id_input = TextInput(display_text='Aquifer ID',
                                 name='aquifer-id-input',
                                 placeholder='e.g.: 23',
                                 attributes={'id': 'aquifer-id-input'},
                                 )

    geoserver_text_input = geoserver_text_gizmo()

    context = {
        'id_input': id_input,
        'geoserver_text_input': geoserver_text_input,
        'aquifer_text_input': aquifer_text_input,
        'aquifer_id_input': aquifer_id_input
    }
    return render(request, 'gwlm/update_aquifer.html', context)


@user_passes_test(user_permission_test)
def add_wells(request):
    """
    Controller for add wells
    """

    region_select = get_region_select()

    aquifer_select = get_aquifer_select(None)

    attributes_button = Button(display_text='Get Attributes',
                               icon='glyphicon glyphicon-plus',
                               style='primary',
                               name='submit-get-attributes',
                               attributes={'id': 'submit-get-attributes'}, )

    context = {
        'aquifer_select': aquifer_select,
        'region_select': region_select,
        'attributes_button': attributes_button
    }

    return render(request, 'gwlm/add_wells.html', context)


@user_passes_test(user_permission_test)
def edit_wells(request):

    geoserver_text_input = geoserver_text_gizmo()

    context = {
        'geoserver_text_input': geoserver_text_input
    }
    return render(request, 'gwlm/edit_wells.html', context)


@user_passes_test(user_permission_test)
def add_measurements(request):

    region_select = get_region_select()

    variable_select = get_variable_select()

    aquifer_select = get_aquifer_select(None)

    attributes_button = Button(display_text='Get Attributes',
                               icon='glyphicon glyphicon-plus',
                               style='primary',
                               name='submit-get-attributes',
                               attributes={'id': 'submit-get-attributes'}, )
    format_text_input = TextInput(display_text='Date Format',
                                  name='format-text-input',
                                  placeholder='e.g.: mm-dd-yyyy',
                                  attributes={'id': 'format-text-input'},
                                  )

    context = {
        'region_select': region_select,
        'aquifer_select': aquifer_select,
        'variable_select': variable_select,
        'attributes_button': attributes_button,
        'format_text_input': format_text_input
    }
    return render(request, 'gwlm/add_measurements.html', context)


@user_passes_test(user_permission_test)
def add_variable(request):
    name_error = ''
    units_error = ''
    desc_error = ''

    if request.method == 'POST' and 'submit-add-variable' in request.POST:
        has_errors = False

        name = request.POST.get('name', None)
        units = request.POST.get('units', None)
        desc = request.POST.get('desc', None)

        if not name:
            has_errors = True
            name_error = 'Name is required.'
        if not units:
            has_errors = True
            units_error = 'Units are required'
        if not desc:
            has_errors = True
            desc_error = 'Description is required'

        if not has_errors:
            session = get_session_obj()
            var_obj = Variable(name=name, units=units, description=desc)
            session.add(var_obj)
            session.commit()
            session.close()
            return redirect(reverse('gwlm:home'))

        messages.error(request, "Please fix errors.")


    name_text_input = TextInput(display_text='Variable Name',
                                name='name',
                                placeholder='e.g.: Ground Water Depth',
                                attributes={'id': 'variable-text-input'},
                                error=name_error
                                )

    units_text_input = TextInput(display_text='Variable Units',
                                 name='units',
                                 placeholder='e.g.: m',
                                 attributes={'id': 'units-text-input'},
                                 error=units_error
                                 )

    desc_text_input = TextInput(display_text='Variable Description',
                                name='desc',
                                placeholder='e.g.: m',
                                attributes={'id': 'desc-text-input'},
                                error=desc_error
                                )

    add_button = Button(display_text='Add Variable',
                        icon='glyphicon glyphicon-plus',
                        style='primary',
                        name='submit-add-variable',
                        attributes={'form': 'add-variable-form'},
                        submit=True,
                        classes="add")

    context = {
        'name_text_input': name_text_input,
        'desc_text_input': desc_text_input,
        'units_text_input': units_text_input,
        'add_button': add_button
    }

    return render(request, 'gwlm/add_variable.html', context)


@user_passes_test(user_permission_test)
def update_variable(request):

    id_input = TextInput(display_text='Variable ID',
                         name='id-input',
                         placeholder='',
                         attributes={'id': 'id-input', 'readonly': 'true'})

    name_text_input = TextInput(display_text='Variable Name',
                                name='variable-text-input',
                                placeholder='e.g.: Ground Water Depth',
                                attributes={'id': 'variable-text-input'},
                                )

    units_text_input = TextInput(display_text='Variable Units',
                                 name='units-text-input',
                                 placeholder='e.g.: m',
                                 attributes={'id': 'units-text-input'},
                                 )

    desc_text_input = TextInput(display_text='Variable Description',
                                name='desc-text-input',
                                placeholder='e.g.: m',
                                attributes={'id': 'desc-text-input'},
                                )


    context = {
        'id_input': id_input,
        'name_text_input': name_text_input,
        'units_text_input': units_text_input,
        'desc_text_input': desc_text_input
    }
    return render(request, 'gwlm/update_variable.html', context)


def run_job(request, job_type):
    """
    Controller for the app home page.
    """
    # Get test_scheduler app. This scheduler needs to be in the database.
    scheduler = get_scheduler(name='dask_local')

    if job_type.lower() == 'delayed':
        from .job_functions import delayed_job

        # Create dask delayed object
        delayed = delayed_job()
        dask = job_manager.create_job(
            job_type='DASK',
            name='dask_delayed',
            user=request.user,
            scheduler=scheduler,
        )

        # Execute future
        dask.execute(delayed)

    return HttpResponseRedirect(reverse('gwlm:jobs-table'))


def jobs_table(request):
    # Use job manager to get all the jobs.
    jobs = job_manager.list_jobs(order_by='-id', filters=None)

    # Table View
    jobs_table_options = JobsTable(
        jobs=jobs,
        column_fields=('id', 'name', 'description', 'creation_time'),
        hover=True,
        striped=False,
        bordered=False,
        condensed=False,
        results_url='gwlm:result',
        refresh_interval=1000,
        delete_btn=True,
        show_detailed_status=True,
    )

    home_button = Button(
        display_text='Home',
        name='home_button',
        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Home'
        },
        href=reverse('gwlm:home')
    )

    context = {'jobs_table': jobs_table_options, 'home_button': home_button}

    return render(request, 'gwlm/jobs_table.html', context)


def result(request, job_id):
    # Use job manager to get the given job.
    job = job_manager.get_job(job_id=job_id)

    # Get result and name
    job_result = job.result
    name = job.name

    home_button = Button(
        display_text='Home',
        name='home_button',
        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Home'
        },
        href=reverse('gwlm:home')
    )

    jobs_button = Button(
        display_text='Show All Jobs',
        name='dask_button',
        attributes={
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Show All Jobs'
        },
        href=reverse('gwlm:jobs-table')
    )

    context = {'result': job_result, 'name': name, 'home_button': home_button, 'jobs_button': jobs_button}

    return render(request, 'gwlm/results.html', context)


def error_message(request):
    messages.add_message(request, messages.ERROR, 'Invalid Scheduler!')
    return redirect(reverse('gwlm:home'))

