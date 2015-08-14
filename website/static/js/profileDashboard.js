'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
var charts = require('js/search_dashboard/charts');
var ResultsWidget = require('js/search_dashboard/resultsWidget');
var filterAndSearchWidget = require('js/search_dashboard/filterAndSearchWidget');
var searchDashboard = require('js/search_dashboard/searchDashboard');

var profileDashboard = {};

var ctx = window.contextVars;
/**
 * Setups elastic aggregations to get contributers.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributorsAgg = function(){
    var agg = {'contributors': utils.termsFilter('field', 'contributors.url', undefined, undefined, 11)}; //11 because one contributor is the user
    return agg;
};

/**
 * Setups elastic aggregations to get type of node. //NOT USED CURRENTLY
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.nodeTypeAgg = function(){
    var agg = {'nodeType': utils.termsFilter('field','_type', 0, 'user')};
    return agg;
};

/**
 * Setups elastic aggregations to get projects by time data.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.projectsByTimesAgg = function() {
    var dateRegistered = new Date(ctx.date_registered); //get current time
    var agg = {'projectsByTimes': utils.termsFilter('field','_type', 1, 'user')};
    agg.projectsByTimes.aggregations = {'projectsOverTime': utils.dateHistogramFilter('date_created',dateRegistered.getTime(),undefined,'day')};
    return agg;
};

/**
 * Parses the returned contributors information, it gets the conversion between guids and names if not present already
 *
 * @return {object} Parsed data for c3 objects
 */

profileDashboard.contributorsParser = function(rawData, levelNames, vm, widget){ //TODO to avoid all this dam hassle, user url and name should be concatenated as a searchable field in collaboarators...
    var urls = [];
    rawData.aggregations[levelNames[0]].buckets.forEach( //first find urls returned
        function (bucket) {
            urls.push(bucket.key);
        }
    );
    var guidToNamesMap = widgetUtils.getGuidsToNamesMap(urls, widget, vm);
    if (!guidToNamesMap) {return; } //return ti mithril and wait for this information if we dont have it

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
                chartData.columns.push([vm.tempData.guidsToNames[bucket.key], bucket.doc_count]);
                chartData.colors[vm.tempData.guidsToNames[bucket.key]] = hexColors[i];
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
* @return {m.component object}  initialised searchDashboard component
*/
profileDashboard.view = function(ctrl) {
    return m.component(searchDashboard, ctrl.searchSetup);
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
        row: 1,
        levelNames: contributorLevelNames,
        aggregation: {mainRequest: profileDashboard.contributorsAgg()},
        display: {
            dataReady : m.prop(true),
            displayWidget: charts.donutChart,
            parser: profileDashboard.contributorsParser,
            callback: { onclick : function (key) {
                //bound information (this) from chart contains vm and widget
                var vm = this.vm;
                var widget = this.widget;
                var name = key;
                if (key.name) {name = key.name; }
                //utils.removeFilter(vm,vm.tempData.contributerFilter, true); //uncomment to overwrite last filter
                vm.tempData.contributerFilter = 'match:contributors.url:' + widgetUtils.getKeyFromValue(this.vm.tempData.guidsToNames, name);
                utils.updateFilter(
                    vm,
                    vm.tempData.contributerFilter,
                    true
                );
                widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
            }}
        },
        thisWidgetRequiresRequests: ['mainRequest', 'nameRequest'],
        thisWidgetUpdates: ['all'] //TODO give simple 'all' option
    };

    var projectLevelNames = ['projectsByTimes', 'projectsOverTime'];
    var projectsByTimes = {
        id: projectLevelNames[0],
        title: ctx.name + '\'s projects and components over time',
        size: ['.col-md-6', 300],
        row: 1,
        levelNames: projectLevelNames,
        display: {
            dataReady : m.prop(true),
            displayWidget: charts.timeseriesChart,
            parser: charts.twoLevelAggParser,
            yLabel: 'Number of Projects',
            xLabel: 'Time',
            type: 'area',
            customColors: [], //by setting custom colors to an empty string, we get the default c3 colors
            callback: {
                onbrushOfSubgraph : function(zoomWin){
                    var vm = this.vm;
                    var widget = this.widget;
                    clearTimeout(vm.tempData.projectByTimeTimeout); //stop constant redraws
                    vm.tempData.projectByTimeTimeout = setTimeout( //update chart with new dates after some delay (1s) to stop repeated requests
                        function(){
                            utils.removeFilter(vm,vm.tempData.projectByTimeTimeFilter, true);
                            vm.tempData.projectByTimeTimeFilter = 'range:date_created:' + zoomWin[0].getTime() + ':' + zoomWin[1].getTime();
                            widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
                            utils.updateFilter(vm,vm.tempData.projectByTimeTimeFilter,true);
                        },1000);
                },
                onclickOfLegend : function(item){
                    var vm = this.vm;
                    var widget = this.widget;
                    utils.removeFilter(vm,vm.tempData.projectByTimeProjectFilter, true);
                    vm.tempData.projectByTimeProjectFilter = 'match:_type:' + item;
                    widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
                    utils.updateFilter(vm,vm.tempData.projectByTimeProjectFilter,true);
                }
            }
        },
        aggregation: {mainRequest: profileDashboard.projectsByTimesAgg()},
        thisWidgetRequiresRequests: ['mainRequest'],
        thisWidgetUpdates: ['all']
    };

        //var nodeType = {
    //    title: 'Type',
    //    size: ['.col-md-6', 260],
    //    row: 1,
    //    levelNames: ['nodeType'],
    //    display: {
    //        dataReady : m.prop(true),
    //        displayWidget: charts.barChart,
    //        parser: charts.barParser,
    //        rotateAxis: true,
    //        customColors: [], //by setting custom colors to an empty string, we get the default c3 colors
    //    },
    //    aggregation: profileDashboard.nodeTypeAgg(),
    //    thisWidgetUpdates: ['Contributors', 'projectsByTimes', 'results']
    //};

    var activeFilters = {
        id: 'activeFilters',
        title: 'Active Filters',
        size: ['.col-md-12'],
        row: 2,
        display: {
            dataReady : m.prop(true),
            displayWidget: filterAndSearchWidget.display,
            callback: null //callbacks included in displayWidget
        },
        aggregation: null, //this displays no stats, so needs no aggregations
        thisWidgetRequiresRequests: ['mainRequest', 'nameRequest'],
        thisWidgetUpdates: ['all']
    };

    var results = {
        id: 'results',
        title: ctx.name + '\'s public projects and components',
        size: ['.col-md-12'],
        row: 3,
        display: {
            dataReady : m.prop(true),
            displayWidget: ResultsWidget.display,
            callback: null //callbacks included in displayWidget
        },
        aggregation: null, //this displays no stats, so needs no aggregations
        thisWidgetRequiresRequests: ['mainRequest'], //the names of elastic queries that this widget needs before data is ready
        thisWidgetUpdates: ['all']
    };

    var mainRequest = {
            elasticURL: '/api/v1/search/',
            requiredFilters: ['match:contributors.url:' + ctx.userId + '=lock'],
            optionalFilters: ['match:_type:project=lock', 'match:_type:component=lock'],
    };

    this.searchSetup = {
        requests: [mainRequest],
        user: ctx.userId,
        tempData: {guidsToNames : {}}, //collaborators require a second level of query to get URL to names mappings //TODO @bdyetton, this should no be exposed... remove from here
        widgets : [contributors, projectsByTimes, results, activeFilters],
        rows: 3 //total number of rows to draw
    };
};

module.exports = profileDashboard;
