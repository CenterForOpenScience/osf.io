'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('./utils');

var Stats = {};

function donutGraph(data, vm) {
    data.charts.shareDonutGraph.onclick = function (d) {
        utils.updateFilter(vm, 'match:shareProperties.source:' + d.name);
    };
    return c3.generate({
        bindto: '#shareDonutGraph',
        size: {
            height: 200
        },
        data: data.charts.shareDonutGraph,
        donut: {
            title: data.charts.shareDonutGraph.title,
            label: {
                format: function (value, ratio, id) {
                    return Math.round(ratio * 100) + '%';
                }
            }
        },
        legend: {
            show: false
        },
        tooltip: {
            format: {
                value: function (value, ratio, id) {
                    return Math.round(ratio * 100) + '%';
                }
            }
        }
    });
}

/**
 * Creates a c3 time graph from the parsed elasticsearch data
 *
 * @param {Object} data The formatted elasticsearch results
 * @param {Object} vm The state of the view model
 */
function timeGraph(data, vm) {
    return c3.generate({
        bindto: '#shareTimeGraph',
        size: {
            height: 250
        },
        data: data.charts.shareTimeGraph,
        //subchart: { //TODO @bdyetton fix the aggregation that the subchart pulls from so it always has the global range results
        //    show: true,
        //    size: {
        //        height: 30
        //    },
        //    onbrush: function(zoomWin){
        //        clearTimeout(data.charts.shareTimeGraph.dateChangeCallbackId); //stop constant redraws
        //        data.charts.shareTimeGraph.dateChangeCallbackId = setTimeout( //update chart with new dates after some delay (1s) to stop repeated requests
        //            function(){
        //                utils.removeFilter(vm,vm.statsQueries.shareTimeGraph.filter);
        //                vm.statsQueries.shareTimeGraph.filter = 'range:providerUpdatedDateTime:'+zoomWin[0].getTime()+':'+zoomWin[1].getTime();
        //                utils.updateFilter(vm,vm.statsQueries.shareTimeGraph.filter, true);
        //            }
        //            ,1000);
        //    }
        //},
        axis: {
            x: {
                type: 'timeseries',
                label: {
                    text: 'Date',
                    position: 'outer-center'
                },
                tick: {
                    format: function (d) {return Stats.timeSinceEpochInMsToMMDDYY(d); }
                }
            },
            y: {
                label: {
                    text: 'Number of Events',
                    position: 'outer-middle'
                },
                tick: {
                    count: 8,
                    format: function (d) {return parseInt(d).toFixed(0); }
                }
            }
        },
        padding: {
          right: 15
        },
        legend: {
            show: false
        },
        tooltip: {
            grouped: false
        }
    });
}

/* Creates an Elasticsearch aggregation by source */
Stats.sourcesAgg = {
    query: {match_all: {} },
    aggregations: {
        sources: utils.termsFilter('field', '_type')
    }
};

/* Creates an Elasticsearch aggregation that breaks down sources by date (and number of things published on those dates) */
Stats.sourcesByDatesAgg = function () {
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    var dateHistogramAgg = {
        sourcesByTimes: utils.termsFilter('field', '_type')
    };
    dateHistogramAgg.sourcesByTimes.aggregations = {
        articlesOverTime : {
            filter: utils.rangeFilter('providerUpdatedDateTime', threeMonthsAgo),
            aggregations: {
                articlesOverTime: utils.dateHistogramFilter('providerUpdatedDateTime', threeMonthsAgo)
            }
        }
    };
    return {aggregations: dateHistogramAgg};
};

/* Helper function for dealing with epoch times returned by elasticsearch */
Stats.timeSinceEpochInMsToMMDDYY = function (timeSinceEpochInMs) {
    var d = new Date(timeSinceEpochInMs);
    return (d.getMonth()+1).toString() + '/' + d.getDate().toString() + '/' + d.getFullYear().toString().substring(2);
};

/* Parses elasticsearch data so that it can be fed into a c3 donut graph */
Stats.shareDonutGraphParser = function (data) {
    var chartData = {};
    chartData.name = 'shareDonutGraph';
    chartData.columns = [];
    chartData.colors = {};
    chartData.type = 'donut';

    var providerCount = 0;
    var hexColors = utils.generateColors(data.aggregations.sources.buckets.length);
    var i = 0;
    data.aggregations.sources.buckets.forEach(
        function (bucket) {
            chartData.columns.push([bucket.key, bucket.doc_count]);
            providerCount = providerCount + (bucket.doc_count ? 1 : 0);
            chartData.colors[bucket.key] = hexColors[i];
            i = i + 1;
        }
    );
    chartData.title = providerCount.toString() + ' Provider' + (providerCount !== 1 ? 's' : '');
    $('.c3-chart-arcs-title').text(chartData.title); //dynamically update chart title
    return chartData;
};

/* Parses elasticsearch data so that it can be fed into a c3 time graph */
Stats.shareTimeGraphParser = function (data) {
    var chartData = {};
    chartData.name = 'shareTimeGraph';
    chartData.columns = [];
    chartData.colors = {};
    chartData.type = 'area-spline';
    chartData.x = 'x';
    chartData.groups = [];
    var grouping = [];
    grouping.push('x');
    var hexColors = utils.generateColors(data.aggregations.sourcesByTimes.buckets.length);
    var datesCol = [];
    data.aggregations.sourcesByTimes.buckets.forEach( //TODO @bdyetton what would be nice is a helper function to do this for any agg returned by elastic
        function (source, i) {
            var total = 0;
            chartData.colors[source.key] = hexColors[i];
            var column = [source.key];
            grouping.push(source.key);
            source.articlesOverTime.articlesOverTime.buckets.forEach(function(date){
                total = total + date.doc_count;
                column.push(total);
                if (i === 0) {
                    datesCol.push(date.key);
                }
            });
            chartData.columns.push(column);
        }
    );
    chartData.groups.push(grouping);
    datesCol.unshift('x');
    chartData.columns.unshift(datesCol);
    return chartData;
};


Stats.view = function (ctrl) {
    return [
        m('.row.search-helper', {style: {color: 'darkgrey'}},
            m('.col-xs-12.col-lg-8.col-lg-offset-2', [
                m('.col-md-4', m('p.text-center', ctrl.vm.latestDate ? utils.formatNumber(ctrl.vm.totalCount) + ' events as of ' + new Date().toDateString() : '')),
                m('.col-md-4', m('p.text-center.font-thick', (ctrl.vm.query() && ctrl.vm.query().length > 0) ? 'Found ' + utils.formatNumber(ctrl.vm.count) + ' events in ' + ctrl.vm.time + ' seconds' : '')),
                m('.col-md-4', m('p.text-center', ctrl.vm.providers + ' content providers'))
            ])
        ),
        m('.row', ctrl.vm.showStats ? [
            m('.col-md-12', [
                m('.row', m('.col-md-12', [
                    m('.row', (ctrl.vm.statsData) ? [
                        m('.col-sm-3', (ctrl.vm.statsData.charts.shareDonutGraph) ? [ctrl.drawGraph('shareDonutGraph', donutGraph)] : []),
                        m('.col-sm-9', (ctrl.vm.statsData.charts.shareTimeGraph) ? [ctrl.drawGraph('shareTimeGraph', timeGraph)] : [])
                    ] : [])
                ]))
            ]),
        ] : [])
    ];
};

Stats.controller = function (vm) {
    var self = this;

    self.vm = vm;
    self.vm.graphs = {}; //holds actual c3 chart objects
    self.vm.statsData = {'charts': {}}; //holds data for charts
    self.vm.loadStats = true; //we want to turn stats on
    //request these querys/aggregations for charts
    self.vm.statsQueries = {
        'shareTimeGraph' : Stats.sourcesByDatesAgg(),
        'shareDonutGraph' : Stats.sourcesAgg
    };

    //set each aggregation as the data source for each chart parser, and hence chart
    self.vm.statsParsers = {
        'sources' : Stats.shareDonutGraphParser,
        'sourcesByTimes' : Stats.shareTimeGraphParser
    };

    self.vm.totalCount = 0;
    self.vm.latestDate = undefined;
    self.vm.statsLoaded = m.prop(false);

    self.drawGraph = function (divId, graphFunction) {
        return m('div', {id: divId, config: function (e, i) {
            if (i) {
                return;
            }
            self.vm.graphs[divId] = graphFunction(self.vm.statsData, self.vm);
        }});
    };

    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/share/search/?size=1&sort=providerUpdatedDateTime'
    }).then(function (data) {
        self.vm.totalCount = data.count;
        self.vm.latestDate = new $osf.FormattableDate(data.results[0].providerUpdatedDateTime).local;
    }).then(m.redraw);
};

module.exports = Stats;
