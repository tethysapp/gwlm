/*****************************************************************************
 * FILE:    View Region Map
 * DATE:    3 MARCH 2020
 * AUTHOR: Brigham Young University
 * LICENSE: BSD 2-Clause
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/

var LIBRARY_OBJECT = (function() {
    // Wrap the library in a package function
    "use strict"; // And enable strict mode for this library

    /************************************************************************
     *                      MODULE LEVEL / GLOBAL VARIABLES
     *************************************************************************/
    var aquiferGroup,
        $geoserverUrl,
        map,
        markers,
        $modalChart,
        public_interface,				// Object returned by the module
        $threddsUrl,
        wellsGroup;

    /************************************************************************
     *                    PRIVATE FUNCTION DECLARATIONS
     *************************************************************************/

    var get_ts,
        generate_chart,
        init_all,
        init_events,
        init_jquery_vars,
        init_dropdown,
        init_map,
        reset_alert,
        reset_form,
        set_outlier,
        view_aquifer,
        view_wells;


    /************************************************************************
     *                    PRIVATE FUNCTION IMPLEMENTATIONS
     *************************************************************************/
    //Reset the form when the request is made successfully
    reset_form = function(result){
        if("success" in result){
            addSuccessMessage('');
        }
    };

    init_jquery_vars = function(){
        $geoserverUrl = $("#geoserver-text-input").val();
        $modalChart = $("#chart-modal");
        $threddsUrl = $("#thredds-text-input").val();
    };

    init_map = function(){
        map = L.map('map',{
            zoom: 3,
            center: [0, 0],
            // crs: L.CRS.EPSG3857
        });

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            // maxZoom: 10,
            attribution:
                '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);

        // var timeDimension = new L.TimeDimension();
        // map.timeDimension = timeDimension;
        //
        // var player        = new L.TimeDimension.Player({
        //     loop: true,
        //     startOver:true
        // }, timeDimension);
        //
        // var timeDimensionControlOptions = {
        //     player:        player,
        //     timeDimension: timeDimension,
        //     position:      'bottomleft',
        //     autoPlay:      false,
        //     minSpeed:      1,
        //     speedStep:     0.5,
        //     maxSpeed:      20,
        //     timeSliderDragUpdate: true,a
        //     loopButton:true,
        //     limitSliders:true
        // };

        // var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
        // map.addControl(timeDimensionControl);
        //
        // var wmsUrl = "http://127.0.0.1:8383/thredds/wms/testAll/groundwater/clipped_well.nc";
        //
        // var wmsLayer = L.tileLayer.wms(wmsUrl, {
        //     layers: 'tsvalue',
        //     format: 'image/png',
        //     transparent: true,
        //     styles: 'boxfill/rainbow',
        //     colorscalerange: [-700, 900],
        //     version:'1.3.0'
        // });
        //
        //
        // var tdWmsLayer = L.timeDimension.layer.wms(wmsLayer,{
        //     updateTimeDimension:true,
        //     setDefaultTime:true,
        //     cache:48
        // });
        // tdWmsLayer.addTo(map);
        //
        aquiferGroup = L.featureGroup().addTo(map);
        markers = L.markerClusterGroup(    {iconCreateFunction: function (cluster) {
                // get the number of items in the cluster
                var count = cluster.getChildCount();

                // figure out how many digits long the number is
                var digits = (count + '').length;

                // Return a new L.DivIcon with our classes so we can
                // style them with CSS. Take a look at the CSS in
                // the <head> to see these styles. You have to set
                // iconSize to null if you want to use CSS to set the
                // width and height.
                return L.divIcon({
                    html: count,
                    className: 'cluster digits-' + digits,
                    iconSize: null
                });
            }}).addTo(map);
    };


    $('#update-well').on('hide.bs.modal', function () {
        reset_form({"reset": "reset"});
    });

    view_aquifer = function(aquifer_id){
        var defaultParameters = {
            service : 'WFS',
            version : '2.0.0',
            request : 'GetFeature',
            typeName : 'gwlm:aquifer',
            outputFormat : 'text/javascript',
            format_options : 'callback:getJson',
            SrsName : 'EPSG:4326',
            featureID: 'aquifer.'+aquifer_id
        };

        var parameters = L.Util.extend(defaultParameters);
        var URL = $geoserverUrl + L.Util.getParamString(parameters);

        aquiferGroup.clearLayers();

        var ajax = $.ajax({
            url : URL,
            dataType : 'jsonp',
            jsonpCallback : 'getJson',
            success : function (response) {
                var myStyle = {
                    "color": "#2d84c8",
                    "weight": 4,
                    "opacity": 1,
                    "fillOpacity": 0
                };
                var feature = L.geoJSON(response, {style: myStyle}).addTo(aquiferGroup);
                map.fitBounds(feature.getBounds());
            }
        });
    };

    view_wells = function(aquifer_id){
        var defaultParameters = {
            service : 'WFS',
            version : '2.0.0',
            request : 'GetFeature',
            typeName : 'gwlm:well',
            outputFormat : 'text/javascript',
            format_options : 'callback:getJson',
            SrsName : 'EPSG:4326',
            cql_filter: 'aquifer_id='+aquifer_id
        };

        var parameters = L.Util.extend(defaultParameters);
        var URL = $geoserverUrl + L.Util.getParamString(parameters);

        // aquiferGroup.clearLayers();
        markers.clearLayers();
        var ajax = $.ajax({
            url : URL,
            dataType : 'jsonp',
            jsonpCallback : 'getJson',
            success : function (response) {
                var WFSLayer = null;
                WFSLayer = L.geoJson(response, {
                    style: function (feature) {
                        return {
                            stroke: false,
                            fillColor: 'FFFFFF',
                            fillOpacity: 0
                        };
                    },
                    onEachFeature: function (feature, layer) {
                        var popupOptions = {maxWidth: 200};
                        if (feature.properties) {
                            var popupString = '<div class="popup">';
                            popupString += '<span class="well_id" well-id="'+feature.id+'">'+feature.id+'</span><br/>';
                            for (var k in feature.properties) {
                                var v = feature.properties[k];
                                popupString += k + ': ' + v + '<br />';
                            }
                            popupString += '</div>';
                            layer.bindPopup(popupString);
                            layer.on('click', get_ts);
                        }

                    }
                }).addTo(markers);

            }
        });
    };

    get_ts = function(e){
        var popup = e.target.getPopup();
        var content = popup.getContent();
        var well_id = popup._source.feature.id;
        var aquifer_id = $("#aquifer-select option:selected").val();
        var variable_id = $("#variable-select option:selected").val();
        var data = new FormData();
        data.append("aquifer_id", aquifer_id);
        data.append("variable_id", variable_id);
        data.append("well_id", well_id);
        $("#well-info").attr("well-id", well_id);
        var xhr = ajax_update_database_with_file("get-timeseries", data);
        xhr.done(function(return_data){
            if("success" in return_data){
                $modalChart.modal('show');
                // reset_form(return_data)
                generate_chart(return_data);
                // addSuccessMessage("Aquifer Update Successful!");
            }else if("error" in return_data){
                // addErrorMessage(return_data["error"]);
                console.log('err');
            }
        });
    };

    set_outlier = function(){
        var aquifer_id = $("#aquifer-select option:selected").val();
        var variable_id = $("#variable-select option:selected").val();
        var well_id = $("#well-info").attr("well-id");

        var data = new FormData();
        data.append("aquifer_id", aquifer_id);
        data.append("variable_id", variable_id);
        data.append("well_id", well_id);
        var xhr = ajax_update_database_with_file("set-outlier", data);
        xhr.done(function(return_data){
            if("success" in return_data){
                console.log(return_data);
                // addSuccessMessage("Aquifer Update Successful!");
            }else if("error" in return_data){
                // addErrorMessage(return_data["error"]);
                console.log('err');
            }
        });
    };

    $("#set-outlier").click(set_outlier);

    generate_chart = function(result){
        var variable_name = $("#variable-select option:selected").text();
        Highcharts.stockChart('plotter',{

            // chart: {
            //     type:'spline',
            //     zoomType: 'x'
            // },
            // tooltip: {
            //     backgroundColor: '#FCFFC5',
            //     borderColor: 'black',
            //     borderRadius: 10,
            //     borderWidth: 3
            // },
            title: {
                text: result['well_info']["well_name"]+ variable_name + " values",
                style: {
                    fontSize: '14px'
                }
            },
            xAxis: {
                title: {
                    text: result['well_info']['attr_dict']
                }
            },
            yAxis: {
                title: {
                    text: variable_name
                }

            },
            exporting: {
                enabled: true
            },
            series: [{
                data:result['timeseries'],
                name: variable_name
            }]

        });
    };

    init_dropdown = function () {
    };

    init_all = function(){
        init_jquery_vars();
        init_map();
        init_dropdown();
    };

    /************************************************************************
     *                        DEFINE PUBLIC INTERFACE
     *************************************************************************/
    /*
     * Library object that contains public facing functions of the package.
     * This is the object that is returned by the library wrapper function.
     * See below.
     * NOTE: The functions in the public interface have access to the private
     * functions of the library because of JavaScript function scope.
     */
    public_interface = {

    };

    /************************************************************************
     *                  INITIALIZATION / CONSTRUCTOR
     *************************************************************************/

    // Initialization: jQuery function that gets called when
    // the DOM tree finishes loading
    $(function() {
        init_all();
        $("#aquifer-select").change(function(){
            var aquifer_id = $("#aquifer-select option:selected").val();
            view_aquifer(aquifer_id);
            view_wells(aquifer_id);
        }).change();
    });

    return public_interface;

}()); // End of package wrapper
// NOTE: that the call operator (open-closed parenthesis) is used to invoke the library wrapper
// function immediately after being parsed.