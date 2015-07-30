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
                    id: params.widget.levelNames[0],
                    //style: ctrl.hidden() ? 'display:none' : 'display:',
                    config: params.vm.dataLoaded() ? [ctrl.drawChart(params.widget, params.vm, params.vm.data)] : []//[$osf.loadingSpinner('large')]//TODO loading spinner + error
                });
    },

    controller : function (params) {
        this.hidden = params.hidden || m.prop(false);
        this.drawChart = function (widget, vm, data) {
            if (data.aggregations[widget.levelNames[0]] !== undefined) {
                return widget.chart(widget.parser(data, widget.levelNames), vm, widget.levelNames[0], widget.callback);
            }
        };
    }
};

var searchWidgetPanel = {
    view : function (ctrl, params, children) {
        return m('.col-sm-6', {},
            m('.panel.panel-default', {}, [
                m('.panel-heading clearfix', {},[
                    m('h3.panel-title',params.widget.title),
                    m('.pull-right', {},
                        m('a.stats-expand', {onclick: function () {
                                ctrl.hidden(!ctrl.hidden());
                                m.redraw(true);
                                //params.hidden = m.prop(ctrl.hidden());
                            }},
                            ctrl.hidden() ? m('i.fa.fa-angle-up') : m('i.fa.fa-angle-down')
                        )
                    )
                ]),
                ctrl.hidden() ? [] : [m('.panel-body', {}, m.component(SearchWidget, params))]
            ])
        );
    },
    controller : function(params) {
        this.hidden = m.prop(false);
    }
}

module.exports = searchWidgetPanel;
