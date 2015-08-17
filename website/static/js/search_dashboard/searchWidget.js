'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

require('../../css/search_widget.css');

function loadingIcon(){
    return m('.spinner-loading-wrapper', [
            m('.logo-spin.text-center', [
                m('img[src=/static/img/logo_spin.png][alt=loader]')
            ]),
            m('p.m-t-sm.fg-load-message', ' Loading... ')
        ]);
}

var SearchWidget = {
    /**
     * View function for a search widget. Returns display widget if data ready, otherwise loading spinner
     *
     * @param {Object} ctrl: controller object automatically passed in by mithril
     * @return {Object} m.component type object (initialised searchWidget component)
     */
    view: function (ctrl, params) {
        var dataReady = params.widget.display.reqRequests.every(function(req){
            return params.vm.requests[req].complete();
        });//TODO fix so that display is a mithril component not a function
        return m('div',{}, dataReady ? params.widget.display.displayComponent(params.vm, params.widget) : loadingIcon());
    }
};

var searchWidgetPanel = {
    /**
     * View function for a search widget panel. Returns search widget nicely wrapped in panel with minimize actions.
     *
     * @param {Object} ctrl: controller object automatically passed in by mithril
     * @param {Object} params: params containing vm
     * @return {m.component object}  initialised searchWidgetPanel component
     */
    view : function (ctrl, params, children) {
        return m(params.widget.size[0], {},
            m('.panel.panel-default', {}, [
                m('.panel-heading clearfix', {},[
                    m('h3.panel-title',params.widget.title),
                    m('.pull-right', {},
                        m('a.widget-expand', {onclick: function () {
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

    /**
     * controller function for a search widget pannel. Initialises component.
     *
     * @return {m.component.controller}  returns itself
     */
    controller : function(params) {
        this.hidden = m.prop(false);
    }
};

module.exports = searchWidgetPanel;
