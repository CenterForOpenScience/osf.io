'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('./utils');

var Stats = {};

function get_source_length(elastic_data) {

    var sources = elastic_data.raw_aggregations.sources.buckets;
    var source_names = [];
    for (var i=0; i<sources.length; i++) {
        source_names.push(sources[i]);
    }

    return source_names.length;
}

function donutGraph (data, vm) {
    data.charts.shareDonutGraph.onclick = function (d, element) {
        utils.updateFilter(vm, 'source:' + d.name, true);
    };
    return c3.generate({
        bindto: '#shareDonutGraph',
        size: {
            height: 200
        },
        data: data.charts.shareDonutGraph,
        donut: {
            title: get_source_length(data) + ' Providers',
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
                    if (name === 'pubmed') {
                        name = 'pubmed central';
                    }
                    return name; 
                }
            }
        }
    });
}

function timeGraph (data) {
    return c3.generate({
        bindto: '#shareTimeGraph',
        size: {
            height: 200
        },
        data: data.charts.shareTimeGraph,
        axis: {
            x: {
                type: 'category',
                label: {
                   text: 'Last Three Months',
                   position: 'outer-center',
                }
            },
            y: {
                label: {
                   text: 'Number of Events',
                   position: 'outer-middle'
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
                        m('.col-sm-3', ctrl.drawGraph('shareDonutGraph', donutGraph)),
                        m('.col-sm-9', ctrl.drawGraph('shareTimeGraph', timeGraph))
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

    self.vm.graphs = {};

    self.vm.totalCount = 0;
    self.vm.showStats = true;
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

    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/share/search/?size=1&v=1',
    }).then(function(data) {
        self.vm.totalCount = data.count;
        self.vm.latestDate = new $osf.FormattableDate(data.results[0].dateUpdated).local;
    }).then(m.redraw);

    self.loadStats();
};

module.exports = Stats;
