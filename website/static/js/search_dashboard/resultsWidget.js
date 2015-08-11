'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var icon = require('js/iconmap')
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');
var ResultsWidget = {};

var Results = {
    view: function(ctrl, params) {
        var vm = params.vm;
        var resultViews = $.map(vm.results || [], function(result, i) {
            return m.component(Result, {result: result, vm: vm, widget: params.widget });
        });

        var len = 0;
        if (vm.results){
            len = vm.results.length;
        }
        var maybeResults = function(results, loading) {
            if (results.length > 0) {
                return results;
            } else if (!loading && results.length === 0) {
                return m('p', {class: 'text-muted'}, 'No results for this query');
            } else {
                return m('', [m.component(utils.loadingIcon), 'loading...']);
            }
        };

        return m('', [
            m('.row', m('.col-md-12', maybeResults(resultViews, vm.resultsLoading()))),
            m('.row', m('.col-md-12', m('div', {style: {display: 'block', margin: 'auto', 'text-align': 'center'}},
                len > 0 && len < vm.count ?
                m('a.btn.btn-md.btn-default', {
                    onclick: function(){
                        utils.loadMore(vm)
                            .then(function(data) {
                                utils.updateVM(vm, data);
                            });
                    }
                }, 'More') : [])
            ))
        ]);

    }
};

var Result = {
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
                title: nodeType,
                onclick: function() {
                    utils.updateFilter(vm, 'match:_type:' + nodeType, true);
                    widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
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
    controller: function() {
        var self = this;
        self.showAll = false;
    },
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
    controller: function() {
        var self = this;
        self.showAll = false;
    },
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
    view: function(ctrl, params) {
        var contributor = params.contributor;
        var index = params.index;
        var vm = params.vm;
        var widget = params.widget;
        return m('span', [
            m('span', index !== 0 ? ' · ' : ''),
            m('a', {
                onclick: function() {
                    utils.updateFilter(vm, 'match:contributors.url:' + contributor.url, true);
                    widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
                }
            }, contributor.fullname)
        ]);
    }
};

var Tags = {
    controller: function(vm) {
        var self = this;
        self.showAll = false;
    },
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
    view: function(ctrl, params) {
        var tag = params.tag;
        var vm = params.vm;
        var widget = params.widget;
        return m('span', m('.badge.pointer.m-t-xs', {onclick: function(){
                utils.updateFilter(vm, 'match:tags:' + tag, true);
                widgetUtils.signalWidgetsToUpdate(vm, widget.thisWidgetUpdates);
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

ResultsWidget.display = function(data, vm, widget){
    //results will always update regardless of callback location (no mapping)
    return m.component(Results,{data: data, vm: vm, widget: widget});
};

module.exports = ResultsWidget;
