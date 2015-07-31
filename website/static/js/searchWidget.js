'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

function loadingIcon(container){
    return m('.spinner-loading-wrapper', [
            m('.logo-spin.text-center', [
                m('img[src=/static/img/logo_spin.png][alt=loader]')
            ]),
            m('p.m-t-sm.fg-load-message', ' Loading... ')
        ]);
}

var SearchWidget = {
//renders the c3 graph widget
    view: function (ctrl, params) { //this should always be a component, and c3 should be wrapped!
        //m('.pull-left', params.vm.dataLoaded() ? [] : m('.logo-spin.logo-sm', m('img[src=/static/img/logo_spin.png][alt=loader]'))),
        return m('div',{}, params.vm.dataLoaded() ? ctrl.drawChart(params.widget, params.vm, params.vm.data) : loadingIcon());
    },

    controller : function (params) {
        this.drawChart = function (widget, vm, data) {
            if ((data.aggregations[widget.levelNames[0]] !== undefined) || (data[widget.levelNames[0]] !== undefined)) {
                return widget.display(data, vm, widget);
            }
        };
    }
};

var searchWidgetPanel = {
    view : function (ctrl, params, children) {
        return m(params.widget.size[0], {},
            m('.panel.panel-default', {}, [
                m('.panel-heading clearfix', {},[
                    m('h3.panel-title',params.widget.title),
                    m('.pull-right', {},
                        m('a.stats-expand', {onclick: function () {
                                ctrl.hidden(!ctrl.hidden());
                                m.redraw(true);
                            }},
                            ctrl.hidden() ? m('i.fa.fa-angle-up') : m('i.fa.fa-angle-down')
                        )
                    )
                ]),
                m('.panel-body', {style: ctrl.hidden() ? 'display:none' : ''}, m.component(SearchWidget, params))
            ])
        );
    },
    controller : function(params) {
        this.hidden = m.prop(false);
    }
};

module.exports = searchWidgetPanel;
