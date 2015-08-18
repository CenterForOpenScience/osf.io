'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var searchUtils = require('js/search_dashboard/searchUtils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
var charts = require('js/search_dashboard/charts');
var SearchDashboard = require('js/search_dashboard/searchDashboard');

var ResultsWidget = require('./resultsWidget');
var FilterWidget = require('./FilterWidget');


var profileDashboard = {};

var ctx = window.contextVars;
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

profileDashboard.contributorsParser = function(rawData, levelNames, vm){
    var guidsToNames = vm.requests.nameRequest.formattedData;

    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    var numProjects = 0;
    var hexColors = charts.generateColors(rawData.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    rawData.aggregations[levelNames[0]].buckets.forEach(
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
        if (numProjects > 1){
            chartData.title = numProjects.toString() + ' projects & components';
        } else {
            chartData.title = numProjects.toString() + ' project or component';
        }
    } else {
        chartData.title = 'No Results';
    }
    $('.c3-chart-arcs-title').text(chartData.title); //dynamically update chart title //TODO update (remove) when c3 issue #1058 resolved (dynamic update of title)
    return chartData;

};

/**
* View function for the profile dashboard
*
* @param {Object} ctrl: controller Object automatically passed in by mithril
* @return {Object}  initialised searchDashboard component
*/
profileDashboard.view = function(ctrl) {
    return m.component(SearchDashboard, ctrl.searchSetup);
};

/**
 * controller function for the ProfileDashboard. Basically a constructor that sets up a SearchDashboard.
 * Contains settings for all widgets. Contains Elastic Data.
 *
 * @return {m.component.controller} returns itself
 */
profileDashboard.controller = function(params) {
    var contributorLevelNames = ['contributors','contributorsName'];
    var contributors = {
        id: contributorLevelNames[0],
        title: ctx.name + '\'s top 10 contributors',
        size: ['.col-md-6', 300],
        levelNames: contributorLevelNames,
        aggregations: {mainRequest: profileDashboard.contributorsAgg()},
        display: {
            reqRequests: ['mainRequest', 'nameRequest'], //these are the requests that need to have completed before we can update this widget
            displayComponent: charts.donutChart,
            labelFormat: function(value, ratio){return value; },
            parser: profileDashboard.contributorsParser, //this function is run by the display widget to format data for display
            callbacks: { onclick : function (key) {
                //bound information (this) from chart contains vm and widget
                var vm = this.vm;
                var widget = this.widget;
                var request = vm.requests.mainRequest;
                var guidsToNames = vm.requests.nameRequest.formattedData;
                var name = key;
                if (key.name) {name = key.name; }
                //utils.removeFilter(vm, widget.filters.contributorsFilter, true); //uncomment to overwrite last filter
                widget.filters.contributorsFilter = 'match:contributors.url:' + widgetUtils.getKeyFromValue(guidsToNames, name);
                widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                searchUtils.updateFilter(vm, [request], widget.filters.contributorsFilter, true);
            }},
            callbacksUpdate: ['all']
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
            displayComponent: charts.timeseriesChart,
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
            displayComponent: FilterWidget.display,
            callbacks: null, //callbacks included in displayWidget
            callbacksUpdate: ['all']
        }
    };

    var results = {
        id: 'results',
        title: ctx.name + '\'s public projects and components',
        size: ['.col-md-12'],
        display: {
            reqRequests : ['mainRequest'],
            displayComponent: ResultsWidget.display,
            callbacks: null, //callbacks included in displayWidget
            callbacksUpdate: ['all']
        }
    };

    var mainRequest = {
            elasticURL: '/api/v1/search/',
            size: 5,
            page: 0,
            requiredFilters: ['match:contributors.url:' + ctx.userId + '=lock'],
            optionalFilters: ['match:_type:project=lock', 'match:_type:component=lock'],
            sort: 'Date',
            sortMap: {
                Date: 'date_created',
                Relevance: null
            }
    };

    var nameRequest = {
        elasticURL: '/api/v1/search/',
        requiredFilters: ['match:category:user=lock'],
        preRequest: [function (requestIn, data) { //functions to modify filters and query before request
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
            request.optionalFilters = guidFilters;
            request.size = missingGuids.length;
            return request;
        }],
        postRequest: [function (requestIn, data) {
            var request = $.extend({}, requestIn);
            var newGuidMaps = {};
            data.results.forEach(function (user) {
                newGuidMaps[user.id] = user.user;
            });
            request.formattedData = $.extend(request.formattedData, newGuidMaps);
            return request;
        }]
    };

    this.searchSetup = {
        user: ctx.userId,
        requests : {
            mainRequest: mainRequest,
            nameRequest: nameRequest
        },
        requestOrder: [
            ['mainRequest', 'nameRequest'], //run these two in serial
            //[] //this would be run in parallel with the two above
        ],
        widgets : {
            contributors: contributors,
            projectsByTimes: projectsByTimes,
            results: results,
            activeFilters: activeFilters
        },
        rowMap: [
            ['contributors', 'projectsByTimes'],
            ['activeFilters'],
            ['results'],
        ],
    };
};

module.exports = profileDashboard;
