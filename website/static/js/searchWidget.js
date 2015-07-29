'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var SearchWidget = {
//renders the c3 graph widget
    view: function (ctrl, params) {
        return m('div', {
                    id: params.data.levelNames[0], //TODO find out why data is not bound to this object correctly
                    //style: params.hidden ? 'display:none' : 'display:',
                    config: params.data.dataLoaded() ? [ctrl.drawChart(params.data, params.data.levelNames[0])] : [$osf.loadingSpinner('large')]//TODO loading spinner + error
                });
    },

    controller : function (params) {
        this.error = params.error || m.prop(''); //TODO error handeling
        this.drawChart = function (data) {
            if (!data.data) {
                data.data = {};
                data.data.aggregations = { //TODO remove post testing
                    "contributers": {
                        "buckets": [
                            {"key": "figshare", "doc_count": 1378},
                            {"key": "calhoun", "doc_count": 119},
                            {"key": "ucescholarship", "doc_count": 74},
                            {"key": "mit", "doc_count": 68},
                            {"key": "pubmedcentral", "doc_count": 52},
                            {"key": "datacite", "doc_count": 40},
                            {"key": "dash", "doc_count": 28},
                            {"key": "caltech", "doc_count": 24},
                            {"key": "bhl", "doc_count": 23},
                            {"key": "scholarworks_umass", "doc_count": 23},
                            {"key": "udel", "doc_count": 20},
                            {"key": "upennsylvania", "doc_count": 13},
                            {"key": "doepages", "doc_count": 12},
                            {"key": "smithsonian", "doc_count": 8},
                            {"key": "opensiuc", "doc_count": 4},
                            {"key": "scholarsbank", "doc_count": 4},
                            {"key": "trinity", "doc_count": 2},
                            {"key": "asu", "doc_count": 1}],
                        "sum_other_doc_count": 0,
                        "doc_count_error_upper_bound": 0
                    },
                    "contributersByTimes": {
                        "buckets": [
                            {
                                "contributers": {
                                    "buckets": [
                                        {"key": 1434326400000, "doc_count": 0},
                                        {"key": 1434931200000, "doc_count": 0},
                                        {"key": 1435536000000, "doc_count": 1378},
                                        {"key": 1436140800000, "doc_count": 0},
                                        {"key": 1436745600000, "doc_count": 0},
                                        {"key": 1437350400000, "doc_count": 0}
                                    ]
                                },
                                "key": "figshare",
                                "doc_count": 1378
                            },
                            {
                                "contributers": {
                                    "buckets": [
                                        {"key": 1434326400000, "doc_count": 0},
                                        {"key": 1434931200000, "doc_count": 0},
                                        {"key": 1435536000000, "doc_count": 73},
                                        {"key": 1436140800000, "doc_count": 0},
                                        {"key": 1436745600000, "doc_count": 0},
                                        {"key": 1437350400000, "doc_count": 0}
                                    ]
                                },
                                "key": "ucescholarship",
                                "doc_count": 73
                            }
                        ],
                        "sum_other_doc_count": 390,
                        "doc_count_error_upper_bound": 20
                    }
                };
            }
            if (data.data.aggregations[data.levelNames[0]] !== undefined) {
                return data.chart(data.parser(data.data, data.levelNames), data.levelNames[0], data.callbacks);
            }
        };
    }

};

var searchWidgetPanel = {
    view : function (ctrl, params, children) {
        return m('.col-sm-6', {},
            m('.panel.panel-default', {}, [
                m('.panel-heading clearfix', {},[
                    m('h3.panel-title',params.data.title),
                    m('.pull-right', {},
                        m('a.stats-expand', {onclick: function () {ctrl.hidden(!ctrl.hidden());}},
                            ctrl.hidden() ? m('i.fa.fa-angle-up') : m('i.fa.fa-angle-down')
                        )
                    )
                ]),
                [m('.panel-body', {}, m.component(SearchWidget, params))] //ctrl.hidden() ? [] :
            ])
        );
    },
    controller : function(params) {
        this.hidden = this.hidden || m.prop(true);
    }
}

module.exports = searchWidgetPanel;
