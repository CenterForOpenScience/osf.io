var c3 = require('c3');
var m = require('mithril');
var $osf = require('osfHelpers');
var utils = require('./utils.js');

var Stats = {};

function getSourcesOneCol(raw_data) {
    var source_data = raw_data['sources']['buckets'];
    var chart_list = [];

    for (i = 0; i < source_data.length; i++){
        var new_item = [];
        new_item.push(source_data[i]['key']);
        new_item.push(source_data[i]['doc_count']);
        chart_list.push(new_item);
    }

    return chart_list;
}

function doughnutGraph (data) {
    var chart2 = c3.generate({
        bindto: '#shareDoughnutGraph',
        data: {
            columns: getSourcesOneCol(data),
            type : 'donut',
        },
        donut: {
            title: 'SHARE Providers'
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
            m('col-md-12', [
                m('.row', m('.col-md-12', [
                    m('h1.about-share-header', {
                        class: 'animated fadeInUp'
                    },'What is SHARE?'),
                    !ctrl.vm.statsLoaded() ? utils.loadingIcon : [
                        ctrl.drawGraph('shareDoughnutGraph', doughnutGraph)
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
            url: '/api/v1/share/stats/',
            background: true
        }).then(function(data) {
            self.vm.statsData = data;
            self.vm.statsLoaded(true);
        }).then(m.redraw);
    };

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
