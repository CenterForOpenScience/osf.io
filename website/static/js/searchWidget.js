'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var searchWidget = {};

//renders the c3 graph widget
searchWidget.view = function (ctrl, params, children) {
    return [
        m('.row', ctrl.hidden ? [] : [
            m('div', {
                    id: params.divId,
                    config : params.dataLoaded ? [ctrl.drawChart(params)] : [$osf.loadingSpinner('large')]//TODO loading spinner + error
                }
            )
        ]),
        m('.row', [
            m('a.stats-expand',
                {onclick: function () {ctrl.hidden = !ctrl.hidden; }},
                ctrl.hidden ? m('i.fa.fa-angle-down') : m('i.fa.fa-angle-up')
            )
        ])
    ];
};

//search widget state is in a vm
searchWidget.controller = function (params) {
    this.error = params.error || m.prop(''); //TODO error handeling
    this.hidden = this.hidden || m.prop(false);
    this.drawChart = function (data) {
        return data.chart(data.parser(data.data,data.name,data.callbacks));
    };
};


//Lets not worry about you for now
var Panel = {
    view: function(ctrl, params, children) {
        return m('div.osf-panel', {}, children);
    }
};

var MyCoolWidget = {
    view: function(ctrl, params, children) {
        return m.component(Panel, {}, ctrl.message);
    },
    controller: function(params) {
        this.message = params.message;
    }
};

var Dashboard = {
    view: function(ctrl, params, children) {
        var nodes = getNodes();
        return m('row-12', {}, [
            m.component(MyCoolWidget, {message: 'Widget message'})
        ])
    }
};

module.exports = searchWidget;
