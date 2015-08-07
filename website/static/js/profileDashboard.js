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
var searchDashboard = require('js/search_dashboard/searchDashboard');

var profileDashboard = {};

var ctx = window.contextVars;
/**
 * Setups elastic aggregations to get contributers.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributorsAgg = function(){
    var agg = {'contributors': utils.termsFilter('field', 'contributors.url', 0, ctx.userId)};
    agg.contributors.aggregations = {'fullname': utils.termsFilter('field','contributors.fullname',1)};
    return agg;
};

/**
 * Setups elastic aggregations to get type of node.
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
    agg.projectsByTimes.aggregations = {'projectsOverTime': utils.dateHistogramFilter('date_created',dateRegistered,undefined,'day')};
    return agg;
};

profileDashboard.contributorsParser = function(rawData, levelNames, vm, widget){ //TODO to avoid all this dam hassle, user url and name should be concatenated as a searchable field in collaboarators...
    var urls = [];
    rawData.aggregations[levelNames[0]].buckets.forEach( //first find urls returned
        function (bucket) {
            urls.push(bucket.key);
        }
    );
    var guidToNamesMap = widgetUtils.getGuidsToNamesMap(urls, widget, vm);
    if (!guidToNamesMap) {return; }

    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    var hexColors = charts.generateColors(rawData.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    rawData.aggregations[levelNames[0]].buckets.forEach(
        function (bucket) {
            if (bucket.doc_count) {
                chartData.columns.push([vm.tempData.guidsToNames[bucket.key], bucket.doc_count]);
                chartData.colors[vm.tempData.guidsToNames[bucket.key]] = hexColors[i];
                i = i + 1;
            }
        }
    );
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
    var contributors = {
        title: 'Contributers of '+ ctx.name + '\'s projects',
        size: ['.col-md-6', 300],
        row: 1,
        levelNames: ['contributors','contributorsName'],
        display: {
            dataReady : m.prop(true),
            displayWidget: charts.donutChart,
            title: 'Projects contributed to:',
            parser: profileDashboard.contributorsParser,
            callback: { onclick : function (key) {
                var name = key;
                if (key.name) {name = key.name; }
                utils.updateFilter(
                    this.vm,
                    'match:contributors.url:' + widgetUtils.getKeyFromValue(this.vm.tempData.guidsToNames, name),
                    true
                );
                widgetUtils.signalWidgetsToUpdate(this.vm, this.widget.thisWidgetUpdates);
            }}
        },
        aggregation: profileDashboard.contributorsAgg(),
        thisWidgetUpdates: ['contributors', 'projectsByTimes', 'results'] //TODO give simple 'all' option
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

    var projectsByTimes = {
        title: ctx.name + '\'s projects over time',
        size: ['.col-md-6', 300],
        row: 1,
        levelNames: ['projectsByTimes', 'projectsOverTime'],
        display: {
            dataReady : m.prop(true),
            displayWidget: charts.timeseriesChart,
            parser: charts.twoLevelAggParser,
            yLabel: 'Number of Projects',
            xLabel: 'Time',
            type: 'area',
            customColors: [], //by setting custom colors to an empty string, we get the default c3 colors
            callback: {onbrush : function(zoomWin){
                var vm = this.vm;
                var widget = this.widget;
                clearTimeout(vm.tempData.projectByTimeTimeout); //stop constant redraws
                vm.tempData.projectByTimeTimeout = setTimeout( //update chart with new dates after some delay (1s) to stop repeated requests
                    function(){
                        utils.removeFilter(vm,vm.tempData.projectByTimeFilter);
                        vm.tempData.projectByTimeFilter = 'range:providerUpdatedDateTime:' + zoomWin[0].getTime()+':'+zoomWin[1].getTime()
                        utils.updateFilter(vm,vm.tempData.projectByTimeFilter,true);
                        widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
                    },1000);
            }}
        },
        aggregation: profileDashboard.projectsByTimesAgg(),
        thisWidgetUpdates: ['contributors', 'results']
    };

    var results = {
        title: ctx.name + '\'s public projects and components',
        size: ['.col-md-12'],
        row: 2,
        levelNames: ['results'],
        display: {
            dataReady : m.prop(true),
            displayWidget: ResultsWidget.display
        },
        aggregation: null, //this displays no stats, so needs no aggregations
        thisWidgetUpdates: ['contributors', 'projectsByTimes', 'results']
    };

    this.searchSetup = {
        elasticURL: '/api/v1/search/',
        user: ctx.userId,
        tempData: {guidsToNames : {}}, //collaborators require a second level of query to get URL to names mappings
        widgets : [contributors, projectsByTimes, results],
        rows:2,
        requiredFilters: ['match:contributors.url:' + ctx.userId], //forces us to only find  projects TODO this might not find components...
        optionalFilters: ['match:_type:project', 'match:_type:component']
    };
};

module.exports = profileDashboard;
