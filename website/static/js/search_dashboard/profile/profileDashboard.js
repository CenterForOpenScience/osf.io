'use strict';
//Defines a template for a basic search widget
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

//TODO pack into lib
var searchUtils = require('js/search_dashboard/searchUtils'); //This file includes useful function to help with elasticsearch
var widgetUtils = require('js/search_dashboard/widgetUtils'); //This file has widget helpers
var charts = require('js/search_dashboard/charts'); //This file contains components and helper functions for charting (c3 stuff)
var FilterWidget = require('js/search_dashboard/FilterWidget'); //This file has the component to display filters
var SearchDashboard = require('js/search_dashboard/searchDashboard'); //This is the main file that setup the dashboard and widgets + processes requests

//Custom widgets...
var ResultsWidget = require('./resultsWidget');  //This is a non-standard file with a mithril component to display widget //TODO make generic


var profileDashboard = {};

var ctx = window.contextVars; //contains user information
/**
 * Setups elastic aggregations to get contributers.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributorsAgg = function(){
    var agg = {'contributors': searchUtils.termsFilter('field', 'contributors.url', undefined, undefined, 11)}; //11 because one contributor is the user
    return agg;
};

/**
 * Setups elastic aggregations to get type of node. //NOT USED CURRENTLY
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.nodeTypeAgg = function(){
    var agg = {'nodeType': searchUtils.termsFilter('field','_type', 0, 'user')};
    return agg;
};

/**
 * Setups elastic aggregations to get projects by time data.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.projectsByTimesAgg = function() {
    var dateRegistered = new Date(ctx.date_registered); //get current time
    var agg = {'projectsByTimes': searchUtils.termsFilter('field','_type', 1, 'user')};
    agg.projectsByTimes.aggregations = {'projectsOverTime': searchUtils.dateHistogramFilter('date_created',dateRegistered.getTime(),undefined,'day')};
    return agg;
};

/**
 * Parses the returned contributors information, it gets the conversion between guids and names if not present already
 *
 * @return {object} Parsed data for c3 objects
 */

profileDashboard.contributorsParser = function(rawData, levelNames, vm){ //a custom parser, because we need guidsToNames mapping...
    var guidsToNames = vm.requests.nameRequest.formattedData;

    var chartData = {};
    chartData.name = levelNames[0]; //name if the chart influences its c3 divId
    chartData.columns = []; //Column wise data for c3
    chartData.colors = {}; //colours of column data
    var numProjects = 0; //numb of projects to change title
    var hexColors = charts.generateColors(rawData.aggregations[levelNames[0]].buckets.length); //get colors for columns
    var i = 0;
    rawData.aggregations[levelNames[0]].buckets.forEach( //step into returned agg data
        function (bucket) {
            if (bucket.key === ctx.userId){
                numProjects = bucket.doc_count;
                return;
            }
            if (bucket.doc_count) {
                chartData.columns.push([guidsToNames[bucket.key], bucket.doc_count]);
                chartData.colors[guidsToNames[bucket.key]] = hexColors[i];
                i = i + 1;
            }
        }
    );
    if (numProjects > 0) {
        if (numProjects > 1) {
            chartData.title = numProjects.toString() + ' projects & components';
        } else {
            chartData.title = numProjects.toString() + ' project or component';
        }
        if (chartData.columns.length === 0){
            chartData.title = chartData.title + ' with no collaborators';
        }
    } else {
        chartData.title = 'No Results';
    }
    $('.c3-chart-arcs-title').text(chartData.title); //dynamically update chart title //TODO update (remove) when c3 issue #1058 resolved (dynamic update of title)
    return chartData;

};

/**
 * Mount function of the profile dashboard, it constructs and mounts a SearchDashboard.
 * Contains settings for all widgets and requests.
 */
profileDashboard.mount = function(divID) {
    var contributorLevelNames = ['contributors','contributorsName']; //names of the levels of aggregation, used for parsing results to c3
    var contributors = {
        id: contributorLevelNames[0], //{string} id of the widget, required.
        title: ctx.name + '\'s top 10 contributors', // {string} title of the widget, displayed in widget panel
        size: ['.col-md-6', 300], //{string/int} size of the widget, the width is controlled via bootstrap, the height is controlled by the display widget (c3 in this case)
        levelNames: contributorLevelNames, //{array of strings} Levels names for parsing to c3
        aggregations: {mainRequest: profileDashboard.contributorsAgg()}, //{object} an object containing aggregations and what request (object key) they should be applied too
        display: { //display object contains all the params for the display component that sits in the widgets outer pannel
            reqRequests: ['mainRequest', 'nameRequest'], //these are the requests that need to have completed before we can update this widget, order is irrelevant
            component: charts.donut, //{mithril component} display component which must contain a view function that returns mithril m()'s
            labelFormat: function(value, ratio){return value; }, //function to run to format chart labels
            parser: profileDashboard.contributorsParser, //this function is run by the display widget to format data for display
            callbacks: { onclick : function (key) { //callbacks that run when interacting with c3 chart, this one runs on click of donut slice
                //bound information (this) from chart contains vm and widget
                var vm = this.vm; //the search widget vm
                var widget = this.widget; //the search widget (i.e. contributers)
                var request = vm.requests.mainRequest;
                var guidsToNames = vm.requests.nameRequest.formattedData;
                var name = key;
                if (key.name) {name = key.name; } //force click of legend or donut slice to have same name
                //utils.removeFilter(vm, widget.filters.contributorsFilter, true); //uncomment to overwrite last filter
                widget.filters.contributorsFilter = 'match:contributors.url:' + widgetUtils.getKeyFromValue(guidsToNames, name); //create and save a match filter
                widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate); //Signal all the other widgets to update with next run of requests
                searchUtils.updateFilter(vm, [request], widget.filters.contributorsFilter, true); //add filters and run requests
            }},
            callbacksUpdate: ['all'] //signal that interaction with this widget should update all other widgets...
        }
    };

    var projectLevelNames = ['projectsByTimes', 'projectsOverTime'];
    var projectsByTimes = {
        id: projectLevelNames[0],
        title: ctx.name + '\'s projects and components over time',
        size: ['.col-md-6', 300],
        levelNames: projectLevelNames,
        display: {
            reqRequests : ['mainRequest'], //the first req requests data will be the 'rawData' input to any parser, other request data should be pulled from vm.requests
            component: charts.timeSeries,
            parser: charts.twoLevelAggParser,
            yLabel: 'Number of Projects',
            xLabel: 'Time',
            type: 'area',
            customColors: [], //by setting custom colors to an empty string, we get the default c3 colors
            callbacks: {
                onbrushOfSubgraph : function(zoomWin){
                    var vm = this.vm;
                    var widget = this.widget;
                    var request = vm.requests.mainRequest;
                    var bounds = this.bounds;
                    clearTimeout(widget.projectByTimeTimeout); //stop constant redraws
                    widget.projectByTimeTimeout = setTimeout( //update chart with new dates after some delay (1s) to stop repeated requests
                        function(){
                            if ((zoomWin[0] <= bounds[0]) && (zoomWin[1] >= bounds[1])) {
                                widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                                searchUtils.removeFilter(vm, [request],widget.filters.rangeFilter, false);
                                return;
                            }
                            searchUtils.removeFilter(vm, [request],widget.filters.rangeFilter, true);
                            widget.filters.rangeFilter = 'range:date_created:' + zoomWin[0].getTime() + ':' + zoomWin[1].getTime();
                            widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                            searchUtils.updateFilter(vm, [request], widget.filters.rangeFilter,true);
                        },1000);
                },
                onclickOfLegend : function(item){
                    var vm = this.vm;
                    var widget = this.widget;
                    var request = vm.requests.mainRequest;
                    searchUtils.removeFilter(vm, [request], widget.filters.typeFilter, true);
                    widget.filters.typeFilter = 'match:_type:' + item;
                    widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                    searchUtils.updateFilter(vm, [request], widget.filters.typeFilter ,true);
                }
            },
            callbacksUpdate: ['all']
        },
        aggregations: { //aggregations can be attached to any request, just specify name.
            mainRequest: profileDashboard.projectsByTimesAgg()
        }
    };

    var activeFilters = {
        id: 'activeFilters',
        title: 'Active Filters',
        size: ['.col-md-12'],
        display: {
            reqRequests : ['mainRequest'],
            component: FilterWidget, //this widget does not require any callbacks, parsers, title etc
            callbacks: null, //callbacks included in displayWidget
            callbacksUpdate: ['all'],
            filterParsers: { //tells the filter object how to display filters as string tags
                range: function(field, value){ //if we have a range filter do this
                    if (field[0] === 'date_created') {
                        var valueOut = widgetUtils.timeSinceEpochInMsToMMYY(parseInt(value[0])) +
                            ' to ' + widgetUtils.timeSinceEpochInMsToMMYY(parseInt(value[1]));
                        return 'Data created is ' + valueOut;
                    }
                    return value + ' ' + field;
                },
                match: function(field, value, vm){ //if we have a match filter, do this
                    var fieldMappings = {
                        '_type' : 'Type is ',
                        'contributors': ' is a Contributor',
                        'tags': 'Tags contain '
                    };
                    if (field[0] === 'contributors' && field[1] === 'url') {
                        var url = value[0].replace(/\//g, '');
                        var urlToNameMapper = vm.requests.nameRequest.formattedData;
                        var valueOut = urlToNameMapper[url];
                        return valueOut + fieldMappings[field[0]];
                    }
                    return fieldMappings[field[0]] + value;
                }
            }
        }
    };

    var results = {
        id: 'results',
        title: ctx.name + '\'s public projects and components',
        size: ['.col-md-12'],
        display: {
            reqRequests : ['mainRequest'],
            component: ResultsWidget, //This widget is custom made for the profile page, so not many display settings required
            callbacks: null, //callbacks included in displayWidget
            callbacksUpdate: ['all']
        }
    };

    //Requests are the things that get data from elastic-search which can then populate widgets.
    // Requests run in the order specified by 'requestOrder' and run on load, filter and history change. Can also be called manually with utils.runRequests(vm)
    var mainRequest = { //This is the main request which the majority of aggregations are applied too (see widgets)
            id: 'mainRequest', //id of request, required
            elasticURL: '/api/v1/search/', //elasticsearch DB to hit
            size: 5, //The number of results we want to return
            page: 0, //page to begin with. without setting page to zero, pagination is not possible
            ANDFilters: ['match:contributors.url:' + ctx.userId], //and filters that are always applied to this request (as opposed to user added)
            ORFilters: ['match:_type:project', 'match:_type:component'], //or filters that are always applied to this request
            sort: 'Date', //start by sorting by 'Date' entry of sort map
            sortMap: { //tells what elastic feilds to sort based on 'sort' value above
                Date: 'date_created',
                Relevance: null
            }
    };

    var nameRequest = {
        id: 'nameRequest',
        elasticURL: '/api/v1/search/',
        ANDFilters: ['match:category:user'],
        //any missing variables will be populated with defaults by search widgets (ORFilters = [])
        preRequest: [function (requestIn, data) { //{array of functions} functions to modify filters and query before request, the last requests data is inputed
            var request = $.extend({}, requestIn);
            var urls = [];
            data.aggregations.contributors.buckets.forEach( //first find urls returned
                function (bucket) {
                    urls.push(bucket.key);
                });
            var missingGuids = widgetUtils.keysNotInObject(urls, request.formattedData);
            if (missingGuids.length === 0){
                return false; //by returning false we do not run request.
            }
            var guidFilters = [];
            $.map(missingGuids, function (guid) {
                guidFilters.push('match:id:' + guid);
            });
            request.userDefinedORFilters = guidFilters;
            request.size = missingGuids.length;
            return request;
        }],
        postRequest: [function (requestIn, data) { //{array of functions} functions to modify filters and query before request, result data from request is inputted
            var request = $.extend({}, requestIn);
            var newGuidMaps = {};
            data.results.forEach(function (user) {
                newGuidMaps[user.id] = user.user;
            });
            request.formattedData = $.extend(request.formattedData, newGuidMaps);
            return request;
        }]
    };

    var searchSetup = {
        url: document.location.search, //url from page, this means we can resume filter state from any url
        loadingIcon: function() { //loading icon that we want to display when request data not ready
            return m('.spinner-loading-wrapper', [m('.logo-spin.text-center',
                m('img[src=/static/img/logo_spin.png][alt=loader]')),
                m('p.m-t-sm.fg-load-message', ' Loading... ')]);
        },
        errorHandlers: { //handlers to run when we have an error
            invalidQuery: function(vm){$osf.growl('Error', 'invalid query');}
        },
        requests : {
            mainRequest: mainRequest, //request objects to run
            nameRequest: nameRequest
        },
        requestOrder: [ //this is the order to run requests, string names here must match ids of each request.
            ['mainRequest', 'nameRequest'], //run these two in serial
            //[] //this would be run in parallel with the two above
        ],
        widgets : { //widgets to add
            contributors: contributors,
            projectsByTimes: projectsByTimes,
            activeFilters: activeFilters,
            results: results
        },
        rowMap: [ //the row layout of the widgets
            ['contributors', 'projectsByTimes'], //row 1
            ['activeFilters'], //row 2
            ['results'], //row 3
        ],
    };
    
    SearchDashboard.mount(divID, searchSetup); //call to setup dashboard and attach to a div on page
};

module.exports = profileDashboard;
