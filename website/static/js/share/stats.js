var c3 = require('c3');
var m = require('mithril');
var $osf = require('osfHelpers');
var utils = require('./utils.js');

var Stats = {};

function get_source_length(elastic_data) {

    sources = elastic_data.raw_aggregations.sources.buckets;
    source_names = [];
    for (i = 0; i < sources.length; i++) {
        source_names.push(sources[i]);
    }

    return source_names.length;
}

function donutGraph (data) {
    return c3.generate({
        bindto: '#shareDonutGraph',
        size: {
            height: 200
        },
        data: data.charts.shareDonutGraph,
        donut: {
            title: get_source_length(data) + ' Providers'
        },
        legend: {
            show: false
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

    });
}

Stats.view = function(ctrl) {
    return [
        m('.row', {style: {color: 'darkgrey'}}, [
            m('.col-md-4', m('p.text-center', ctrl.vm.latestDate ? utils.formatNumber(ctrl.vm.totalCount) + ' events as of ' + new Date().toDateString() : '')),
            m('.col-md-4', m('p.text-center', ctrl.vm.query().length > 0 ? 'Found ' + utils.formatNumber(ctrl.vm.count) + ' events in ' + ctrl.vm.time + ' seconds' : '')),
            m('.col-md-4', m('p.text-center', ctrl.vm.providers + ' content providers'))
        ]),
        m('.row', ctrl.vm.showStats ? [
            m('.col-md-12', [
                m('.row', m('.col-md-12', [
                    !ctrl.vm.statsLoaded() ? m('img[src=/static/img/loading.gif]') : [
                        m('.row', [
                            m('.col-sm-3', ctrl.drawGraph('shareDonutGraph', donutGraph)),
                            m('.col-sm-9', ctrl.drawGraph('shareTimeGraph', timeGraph))
                        ])
                    ]
                ]))
            ]),
        ] : []),
        m('.row', [
            m('col-md-12', m('a.stats-expand', {
                onclick: function() {ctrl.vm.showStats = !ctrl.vm.showStats;}
            },
                ctrl.vm.showStats ? m('i.icon-angle-up') : m('i.icon-angle-down')
            ))
        ])
    ];
};




Stats.controller = function(vm) {
    var self = this;

    self.vm = vm;
    self.vm.providers = 26;

    self.graphs = {};

    self.vm.totalCount = 0;
    self.vm.showStats = true;
    self.vm.latestDate = undefined;
    self.vm.statsLoaded = m.prop(false);

    self.drawGraph = function(divId, graphFunction) {
        return m('div', {id: divId, config: function(e, i) {
            if (i) return;
            self.graphs[divId] = graphFunction(self.vm.statsData);
        }});
    };

    self.loadStats = function() {
        self.vm.statsLoaded(false);

        m.request({
            method: 'GET',
            url: '/api/v1/share/stats/?' + $.param({q: self.vm.query()}),
            background: true
        }).then(function(data) {
            self.vm.statsData = data;
            Object.keys(self.graphs).map(function(type) {
                self.vm.statsData.charts[type].unload = true;
                if(type === 'shareDonutGraph') {
                    var count = data.charts.shareDonutGraph.columns.filter(function(val){return val[1] > 0;}).length;
                    $('.c3-chart-arcs-title').text(count + ' Provider' + (count !== 1 ? 's' : ''));
                }
                self.graphs[type].load(self.vm.statsData.charts[type]);
            });
            self.vm.statsLoaded(true);
        }).then(m.redraw);
    };

    utils.onSearch(self.loadStats);

    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/share/?size=1',
    }).then(function(data) {
        self.vm.totalCount = data.count;
        self.vm.latestDate = new $osf.FormattableDate(data.results[0].dateUpdated).local;
    }).then(m.redraw);

    self.loadStats();
};

module.exports = Stats;
