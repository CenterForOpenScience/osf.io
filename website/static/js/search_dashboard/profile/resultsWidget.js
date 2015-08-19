'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var icon = require('js/iconmap');
var searchUtils = require('js/search_dashboard/searchUtils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');

var ResultsWidget = {
    /**
     * view function for results component. Over-arching component to display all results
     * Loads more results on click of 'more results' button
     *
     * @param {Object} ctrl: empty controller pasted in by mithril
     * @param {Object} params: contains widget and vm information
     * @return {Object}  initialised results component
     */
    view: function(ctrl, params) {
        var vm = params.vm;
        var results = params.vm.requests.mainRequest.data.results;
        var totalResults = params.vm.requests.mainRequest.data.counts.total;
        var widget = params.widget;
        var resultViews = $.map(results || [], function(result, i) {
            return m.component(Result, {result: result, vm: vm, widget: widget });
        });

        var maybeResults = function(results) {
            if (results.length > 0) {
                return results;
            } else if (results.length === 0) {
                return m('p', {class: 'text-muted'}, 'No results for this query');
            }
        };

        return m('', [
            m('.row', m('.col-md-12', maybeResults(resultViews))),
            m('.row', m('.col-md-12', m('div', {style: {display: 'block', margin: 'auto', 'text-align': 'center'}},
                results.length > 0  && results.length < totalResults ?
                m('a.btn.btn-md.btn-default', {
                    onclick: function(){
                        searchUtils.paginateRequests(vm, []);
                    }
                }, 'More') : [])
            ))
        ]);

    }
};

var Result = {
    /**
     * view function for result component. Component displays one result
     *
     * @param {Object} ctrl: empty controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised result component
     */
    view: function(ctrl, params) {
        return m( '.animated.fadeInUp', [
            m('div', [
                m('h4', [
                    m.component(TitleBar, params)
                ]),
                m('.row', [
                    m('.col-md-7',
                      m('span.pull-left',
                        m.component(Contributors, params)
                      )
                    )
                ]),
                m.component(Footer, params),
                m('br')
            ]),
            m('hr')
        ]);

    }
};

var TitleBar = {
    /**
     * view function for TitleBar component. TitleBar contains description also
     *
     * @param {Object} ctrl: empty controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised result component
     */
    view: function(ctrl, params) {
        var result = params.result;
        var vm = params.vm;
        var widget = params.widget;
        var nodeType = result.is_component ?
            (result.is_registered ? 'registeredComponent' : 'component') :
            (result.is_registered ? 'registration' : 'project');

        return m('span', {}, [
            m('div.m-xs', {
                'class': icon.projectIcons[nodeType],
                style: 'cursor:pointer',
                title: nodeType,
                onclick: function() {
                    widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                    searchUtils.updateFilter(vm, [], 'match:_type:' + nodeType, true);
                }}
            ),
            m('a[href=' + result.url + ']', ((result.title || 'No title provided'))),
            m('br'),
            m.component(Description, params)
        ]);
    }
};

/* Render the description of a single result. Will highlight the matched text */
var Description = {
    /**
     * controller function for Description component. Initialises show state.
     *
     */
    controller: function() {
        var self = this;
        self.showAll = false;
    },
    /**
     * view function for Description component.
     *
     * @param {Object} ctrl: controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised result component
     */
    view: function(ctrl, params) {
        var result = params.result;
        if ((result.description || '').length > 350) {
            return m('p.readable.pointer', {
                onclick: function() {
                    ctrl.showAll = !ctrl.showAll;
                    }
                },
                ctrl.showAll ? result.description : $.truncate(result.description, {length: 350})
            );
        } else {
            return m('p.readable', result.description);
        }
    }
};

var Contributors = {
    /**
     * controller function for contributors component. Initialises show state.
     */
    controller: function() {
        var self = this;
        self.showAll = false;
    },
    /**
     * view function for Contributors component. This displays all individual contributor components
     *
     * @param {Object} ctrl: controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised result component
     */
    view: function(ctrl, params) {
        var result = params.result;
        var contributorViews = $.map(result.contributors, function(contributor, i) {
                return m.component(Contributor, $.extend({contributor: contributor, index: i}, params));
            });

        return m('span.pull-left', {style: {'text-align': 'left'}},
            ctrl.showAll || result.contributors.length < 8 ?
                contributorViews :
                m('span', [
                    contributorViews.slice(0, 7),
                    m('br'),
                    m('a', {onclick: function(){ctrl.showAll = !ctrl.showAll;}}, 'See All')
                ])
        );

    }
};

var Contributor = {
    /**
     * view function for an individual Contributors component.
     *
     * @param {Object} ctrl: controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised contributor component
     */
    view: function(ctrl, params) {
        var contributor = params.contributor;
        var index = params.index;
        var vm = params.vm;
        var widget = params.widget;
        return m('span', [
            m('span', index !== 0 ? ' · ' : ''),
            m('a', {
                onclick: function() {
                    widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                    searchUtils.updateFilter(vm, [], 'match:contributors.url:' + contributor.url, true);
                }
            }, contributor.fullname)
        ]);
    }
};

var Tags = {
    /**
     * controller function for tags component. Initialises show state.
     */
    controller: function(vm) {
        var self = this;
        self.showAll = false;
    },
    /**
     * view function for tags component.
     *
     * @param {Object} ctrl: controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised tags component
     */
    view: function(ctrl, params){
        var result = params.result;
        var tagViews = $.map(result.tags || [], function(tag, i) {
            return m.component(Tag, $.extend({tag: tag}, params));
        });
        if (ctrl.showAll || (result.tags || []).length <= 5) {
            return m('span', tagViews);
        }
        return m('span', [
            tagViews.slice(0, 5),
            m('br'),
            m('div', m('a', {onclick: function() {ctrl.showAll = !ctrl.showAll;}},'See All'))
        ]);

    }
};

var Tag = {
    /**
     * view function for an individual tag component.
     *
     * @param {Object} ctrl: controller pasted in by mithril
     * @param {Object} params: contains result, widget and vm information
     * @return {Object}  initialised tag component
     */
    view: function(ctrl, params) {
        var tag = params.tag;
        var vm = params.vm;
        var widget = params.widget;
        return m('span', m('.badge.pointer.m-t-xs', {onclick: function(){
                widgetUtils.signalWidgetsToUpdate(vm, widget.display.callbacksUpdate);
                searchUtils.updateFilter(vm, [], 'match:tags:' + tag, true);
            }}, $.truncate(tag, {length: 50}), ' '
        ));
    }
};

var Footer = {
    view: function(ctrl, params) {
        var result = params.result;
        var vm = params.vm;
        return m('span', {}, [
            m('row',{},[
                m('span.pull-left','Date created: ' + result.date_created.substring(0,10)),
                m('.pull-right',
                  {style: {'text-align': 'right'}},
                  m.component(Tags, params)
                )
            ]),
        ]);
    }
};

module.exports = ResultsWidget;
