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

function doughnutGraph (elastic_data) {
    var donutgraph = c3.generate({
        bindto: '#shareDoughnutGraph',
        size: {
            height: 240
        },
        data: {
            columns: elastic_data.for_charts.donut_chart,
            type : 'donut',
        },
        donut: {
            title: get_source_length(elastic_data) + ' Providers'
        },
        legend: {
            show: false
        }
    });
}

function timeGraph (elastic_data) {
    var timegraph = c3.generate({
        bindto: '#shareTimeGraph',
        size: {
            height: 240
        },
        data: {
            x: 'x',
            columns: elastic_data['for_charts']['date_totals']['date_numbers'],
            type: 'area-spline',
            groups: [elastic_data['for_charts']['date_totals']['group_names']]
        },
        axis: {
            x: {
                type: 'category'
            }
        },
        legend: {
            show: false
        }
    });
}

Stats.view = function(ctrl) {
    return [
        m('.row', {style: {color: 'darkgrey'}}, [
            m('.col-md-4', m('p.text-center', ctrl.vm.latestDate ? ctrl.vm.totalCount + ' events as of ' + ctrl.vm.latestDate : '')),
            m('.col-md-4', m('p.text-center', ctrl.vm.query().length > 0 ? 'Found ' + ctrl.vm.count + ' events in ' + ctrl.vm.time + ' seconds' : '')),
            m('.col-md-4', m('p.text-center', ctrl.vm.providers + ' content providers'))
        ]),
        m('.row', ctrl.vm.showStats ? [
            m('.col-md-12', [
                m('.row', m('.col-md-12', [
                    m('h1.about-share-header', {
                        class: 'animated fadeInUp'
                    },'What is SHARE?'),
                    !ctrl.vm.statsLoaded ? m('img[src=/static/img/loading.gif]') : [
                        m('.row', [
                            m('.col-md-3', ctrl.drawGraph('shareDoughnutGraph', doughnutGraph)),
                            m('.col-md-9', ctrl.drawGraph('shareTimeGraph', timeGraph))
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

    self.vm.totalCount = 0;
    self.vm.showStats = true;
    self.vm.latestDate = undefined;
    self.vm.statsLoaded = m.prop(false);

    self.drawGraph = function(divId, graphFunction) {
        return m('div', {id: divId, config: function(e, i) {
            if (i) return;
            graphFunction(self.vm.statsData);
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
