'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('./utils');

//var mouseDown = 0;
//document.body.onmousedown = function() {
//  ++mouseDown;
//};
//document.body.onmouseup = function() {
//  --mouseDown;
//};

var Stats = {};

function donutGraph (data, vm) {
    data.charts.shareDonutGraph.onclick = function (d, element) {
        utils.updateFilter(vm, 'shareProperties.source:' + d.name, true); //TODO change this to subscription based filter?
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
                    return Math.round(ratio*100) + '%';
                }
            }
        },
        legend: {
            show: false
        },
        tooltip: {
            format: {
                name: function (name, ratio, id, index) {
                    if (name === 'pubmed') { //TODO @fabianvf, can we get rid of this now? looks like pubmedcentral is already the name of one of the sources
                        name = 'pubmed central';
                    }
                    return name; 
                }
            }
        }
    });
}

function timeGraph (data,vm) {
    return c3.generate({
        bindto: '#shareTimeGraph',
        size: {
            height: 250
        },
        data: data.charts.shareTimeGraph,
        subchart: {
            show: true,
            size: {
                height: 20
            },
            onbrush: function(zoomWin){
                console.log(zoomWin)
                var rawX = data.charts.shareTimeGraph.rawX;
                var xTick = (rawX.slice(-1)[0]-rawX[0])/rawX.length;
                var xMin = rawX[0]+xTick*zoomWin[0];
                var xMax = rawX[0]+xTick*zoomWin[1];
                //Stats.mapFilter(vm, utils.fieldRange('dateUpdated',xMin,xMax), 'shareTimeGraph');
                //range restriction should influence donut, and donut should influence time graph. both should influence main query
                //should come up with some form of filter subscription, where it is easy to subscribe to filters from graphs
            }
        },
        axis: {
            x: {
                type: 'category',
                label: {
                    text: 'Last Three Months',
                    position: 'outer-center'
                },
                tick: {
                    format: function(d) {return Stats.timeSinceEpochInMsToMMYY(d)}
                }
            },
            y: {
                label: {
                    text: 'Number of Events',
                    position: 'outer-middle'
                },
                tick: {
                    count: 8,
                    format: function (d) {return parseInt(d).toFixed(0);}
                }
            }
        },
        legend: {
            show: false
        },
        tooltip: {
            grouped: false,
            format: {
              name: function (name, ratio, id, index) {
                  if (name === 'pubmed') {
                      name = 'pubmed central';
                  }
                  return name; 
              }
            }
        }
    });
}

Stats.sourcesAgg = function(){
    var sourcesQuery = {'match_all':{}};
    var sourcesAgg = {'sources': utils.termsFilter('field','_type')};
    return {'query' : sourcesQuery, 'aggregations': sourcesAgg ,'filters' : []}
};

Stats.sourcesByDatesAgg = function(){
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    
    var dateHistogramQuery = {'match_all':{}};
    var dateHistogramFilter = utils.fieldRange('dateUpdated',threeMonthsAgo);
    var dateHistogramAgg = {'sourcesByTimes': utils.termsFilter('field','_type')};
    dateHistogramAgg.sourcesByTimes['aggregations'] = {'articlesOverTime' : utils.dateHistogramFilter('dateUpdated',threeMonthsAgo)};

    return {'query' : dateHistogramQuery, 'aggregations': dateHistogramAgg ,'filters' : []};//[dateHistogramFilter]}
};

Stats.timeSinceEpochInMsToMMYY = function(timeSinceEpochInMs)
{
    var d = new Date(0);
    d.setUTCSeconds(timeSinceEpochInMs/1000);
    return d.getMonth().toString() + '/' + d.getFullYear().toString().substring(2);

};

Stats.shareDonutGraphParser = function(data)
{
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
    return chartData
};

Stats.mapFilter = function(vm,filter,sourceOfFilter) //TODO
{
    vm.statsQuerys.shareDonutGraph.filters.push(filter);
    utils.search(vm)//hack to force update
    //TODO work out some way to add filters based on some mapping
    //MUST BE ADDED to Querys somehow!
    //add everything to main query for now...
    //if ('main' in vm.filterCallbackMap[sourceOfFilter] ||  ~vm.filterCallbackMap[sourceOfFilter]){
    //    utils.updateFilter(vm, filter, true)}
};

Stats.shareTimeGraphParser = function(data)
{
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
    var i = 0;
    var datesCol = [];
    data.aggregations.sourcesByTimes.buckets.forEach( //TODO what would be nice is a helper function to do this for any agg returned by elastic
        function (source) {
            chartData.colors[source.key] = hexColors[i];
            var column = [source.key];
            grouping.push(source.key);
            source.articlesOverTime.buckets.forEach(function(date){
                column.push(date.doc_count);
                if(i===0){
                    //convert date to reable format
                    datesCol.push(date.key);
                }
            });
            chartData.columns.push(column);
            i = i + 1;
        }
    );
    chartData.rawX = datesCol;
    chartData.groups.push(grouping);
    chartData.columns.unshift('x'.concat(datesCol));

    return chartData;
};


Stats.view = function(ctrl) {
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
                    m('.row', (ctrl.vm.statsData && ctrl.vm.count > 0) ? [
                        m('.col-sm-3', (ctrl.vm.statsData.charts.shareDonutGraph) ? [ctrl.drawGraph('shareDonutGraph', donutGraph)] : []),
                        m('.col-sm-9', (ctrl.vm.statsData.charts.shareTimeGraph) ? [ctrl.drawGraph('shareTimeGraph', timeGraph)] : [])
                    ] : [])
                ]))
            ]),
        ] : []),
        m('.row', [
            m('col-md-12', m('a.stats-expand', {
                onclick: function() {ctrl.vm.showStats = !ctrl.vm.showStats;}
            },
                ctrl.vm.showStats ? m('i.fa.fa-angle-up') : m('i.fa.fa-angle-down')
            ))
        ])
    ];
};

Stats.controller = function(vm) {
    var self = this;

    self.vm = vm;
    self.vm.graphs = {}; //holds actual c3 chart objects
    self.vm.statsData = {'charts': {}}; //holds data for charts

    //request these querys/aggregations for charts
    self.vm.statsQuerys = {
        'shareTimeGraph' : Stats.sourcesByDatesAgg(),
        'shareDonutGraph' : Stats.sourcesAgg()
    };

    //set each aggregation as the data source for each chart
    self.vm.statsParsers = {
        'sources' : Stats.shareDonutGraphParser,
        'sourcesByTimes' : Stats.shareTimeGraphParser
    };

    self.vm.filterCallbackMap = { //Location : Query/Agg THESE ARE ONLY THE ONES NOT APPLIED TO ALL!
        'shareTimeGraph' : ['main','shareDonutGraph'],
    };

    self.vm.totalCount = 0;
    self.vm.latestDate = undefined;
    self.vm.statsLoaded = m.prop(false);

    self.drawGraph = function(divId, graphFunction) {
        return m('div', {id: divId, config: function(e, i) {
            if (i) {
                return;
            }
            self.vm.graphs[divId] = graphFunction(self.vm.statsData, self.vm);
        }});
    };
    self.loadStats = function(){
        return utils.loadStats(self.vm);
    };

    utils.onSearch(self.loadStats);

    //Get all our initial agg values
    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/share/search/?size=1&v=1'
    }).then(function(data) {
        self.vm.totalCount = data.count;
        self.vm.latestDate = new $osf.FormattableDate(data.results[0].dateUpdated).local;
    }).then(m.redraw);

    self.loadStats();

};

module.exports = Stats;
