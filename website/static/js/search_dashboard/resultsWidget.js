'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
var Results = {};
var ResultsWidget = {};


/**
* View function for the results widget (displays each of the results of the search)
*
* @param {Object} controller object automatically passed in by mithril
* @return {m.component object}  initialised resultsWidget component
*/
Results.view = function(ctrl) {
    var res = [];
    var len = 0;
    if (ctrl.vm.results){
        res = $.map(ctrl.vm.results, ctrl.renderResult);
        len = ctrl.vm.results.length;
    }
    return m('', [
        m('.row', m('.col-md-12', (!utils.arrayEqual(res, [])) ? res : (!ctrl.vm.resultsLoading() && (ctrl.vm.results !== null)) ? m('span', {style: {margin: 'auto'}}, 'No results') : [])),
        m('.row', m('.col-md-12', ctrl.vm.resultsLoading() ? utils.loadingIcon : [])),
        m('.row', m('.col-md-12', m('div', {style: {display: 'block', margin: 'auto', 'text-align': 'center'}},
            len > 0 && len < ctrl.vm.count ?
            m('a.btn.btn-md.btn-default', {
                onclick: function(){
                    utils.loadMore(ctrl.vm)
                        .then(function(data) {
                            utils.updateVM(ctrl.vm, data);
                        });
                }
            }, 'More') : [])
         ))
    ]);
};

Results.controller = function(params) {
    var self = this;
    self.vm = params.vm;
    self.vm.resultsLoading = m.prop(false);

    self.renderTitleBar = function(result) {
        return [m(
            'a[href=' + result.uris.canonicalUri + ']', ((result.title || '').length > 0) ? m.trust(result.title) : 'No title provided'),
            m('br'),
            self.renderDescription(result)];
    };

    self.renderDescription = function(result) {
        if ((result.description || '').length > 350) {
            return m('p.readable.pointer',
                {onclick:function(){result.showAll = result.showAll ? false : true;}},
                m.trust(result.showAll ? result.description : $.trim(result.description.substring(0, 350)) + '...')
            );
        }
        return m('p.readable', m.trust(result.description));

    };

    self.renderPerson = function(person, index) {
        return m('span', [
            m('span', index !== 0 ? ' · ' : ''),
            m('a', {
                onclick: function() {
                    utils.updateFilter(self.vm, 'match:contributors.familyName:' + person.familyName, true);
                    utils.updateFilter(self.vm, 'match:contributors.givenName:' + person.givenName, true);
                    widgetUtils.signalWidgetsToUpdate(self.vm, params.widget.thisWidgetUpdates);
                }
            }, person.name)
        ]);
    };

    self.renderContributors = function(result) {
        var renderPeople = function(people) {
            return $.map(people, self.renderPerson);
        };

        return m('span.pull-left', {style: {'text-align': 'left'}},
            result.showAllContrib || result.contributors.length < 8 ?
                renderPeople(result.contributors) :
                m('span', [
                    renderPeople(result.contributors.slice(0, 7)),
                    m('br'),
                    m('a', {onclick: function(){result.showAllContrib = result.showAllContrib ? false : true;}}, 'See All')
                ])
        );
    };

    self.renderSubjects = function(result) {
        var rendersubject = function(subject) {
            return [
                m('.badge.pointer', {onclick: function(){
                    utils.updateFilter(self.vm, 'match:subjects:"' + subject + '"', true);
                    widgetUtils.signalWidgetsToUpdate(self.vm, params.widget.thisWidgetUpdates);
                }}, subject.length < 50 ? subject : subject.substring(0, 47) + '...'),
                ' '
            ];
        };

        if (result.showAllsubjects || (result.subjects || []).length < 5) {
            return $.map((result.subjects || []), rendersubject);
        }
        return m('span', [
            $.map((result.subjects || []).slice(0, 5), rendersubject),
            m('br'),
            m('div', m('a', {onclick: function() {result.showAllsubjects = result.showAllsubjects ? false : true;}},'See All'))
        ]);
    };

    self.renderResultFooter = function(result) {
        return m('div', [
                    m('span',
                        'Released on ' + new $osf.FormattableDate(result.providerUpdatedDateTime).local,
                        self.vm.rawNormedLoaded() ?  m('span', [
                            m('span', {style: {'margin-right': '5px', 'margin-left': '5px'}}, ' | '),
                            m('a', {
                                onclick: function() {
                                    result.showRawNormed = result.showRawNormed ? false : true;
                                    if (!result.raw) {
                                        utils.loadRawNormalized(result);
                                    }
                                }
                            }, 'Data')
                        ]) : []
                    ),
                    m('span.pull-right', [
                        m('img', {src: self.vm.ProviderMap[result.shareProperties.source].favicon, style: {width: '16px', height: '16px'}}),
                        ' ',
                        m('a', {onclick: function() {
                            utils.updateFilter(self.vm, 'shareProperties.source:' + result.shareProperties.source);
                            widgetUtils.signalWidgetsToUpdate(self.vm, params.widget.thisWidgetUpdates);
                        }}, self.vm.ProviderMap[result.shareProperties.source].long_name),
                        m('br')
                    ])
                ]);
    };

    self.renderRawNormalizedData = function(result) {
        return m('.row', [
                    m('.col-md-12',
                        result.showRawNormed && result.raw ? m('div', [
                            m('ul', {class: 'nav nav-tabs'}, [
                                m('li', m('a', {href: '#raw', 'data-toggle': 'tab'}, 'Raw')),
                                m('li', m('a', {href: '#normalized', 'data-toggle': 'tab'}, 'Normalized'))
                            ]),
                            m('div', {class: 'tab-content'},
                                m('div',
                                    {class: 'tab-pane active', id:'raw'},
                                    m('pre',
                                        (function(){
                                            if (result.rawfiletype === 'xml') {
                                                return pd.xml(result.raw);
                                            }
                                            else {
                                                var rawjson = JSON.parse(result.raw);
                                                return JSON.stringify(rawjson, undefined, 2);
                                            }
                                        }())
                                    )
                                ),
                                m('div',
                                    {class: 'tab-pane', id:'normalized'},
                                    m('pre',
                                        result.normalized
                                    )
                                )
                            )
                        ]) : m('span')
                    )
                ]);
    };

    self.renderResult = function(result, index) {
        return m( '.animated.fadeInUp', [
            m('div', [
                m('h4', [
                    self.renderTitleBar(result)
                ]),
                m('.row', [
                    m('.col-md-7',
                      m('span.pull-left',
                        self.renderContributors(result)
                      )
                    ),
                    m('.col-md-5',
                        m('.pull-right',
                          {style: {'text-align': 'right'}},
                          self.renderSubjects(result)
                        )
                    )
                ]),
                m('br'),
                //m('div', self.renderResultFooter(result)),
                self.renderRawNormalizedData(result)
            ]),
            m('hr')
        ]);
    };

    // Uncomment for infinite scrolling!
    // $(window).scroll(function() {
    //     if  ($(window).scrollTop() === $(document).height() - $(window).height()){
    //         utils.loadMore(self.vm);
    //     }
    // });
};

ResultsWidget.display = function(data, vm, widget){
    //results will always update regardless of callback location (no mapping)
    //if (!utils.updateTriggered(widget.levelNames[0], vm)) {return null; }
    return m.component(Results,{data: data, vm: vm, widget: widget});
};

module.exports = ResultsWidget;
