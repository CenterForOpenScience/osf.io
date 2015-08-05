'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var Results = {
    controller: function(vm) {
        var self = this;
        self.vm = vm;
        self.vm.resultsLoading = m.prop(false);
    },
    view: function(ctrl) {
        var resultViews = $.map(ctrl.vm.results || [], function(result, i) {
            return m.component(Result, {result: result, vm: ctrl.vm});
        });



        var len = 0;
        if (ctrl.vm.results){
            len = ctrl.vm.results.length;
        }
        return m('', [
            m('.row', m('.col-md-12', (!utils.arrayEqual(resultViews, [])) ? resultViews : (!ctrl.vm.resultsLoading() && (ctrl.vm.results !== null)) ? m('span', {style: {margin: 'auto'}}, 'No results for this query') : [])),
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

    }
};

var Result = {
    /**
     * Formats a single search result for display
     *
     * @param {Object} result A map containing a single search result
     * @param {Integer} index Just ignore this, it doesn't matter
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
                    ),
                    m('.col-md-5',
                        m('.pull-right',
                          {style: {'text-align': 'right'}},
                          m.component(Subjects, params)
                        )
                    )
                ]),
                m('br'),
                m.component(Footer, params)
            ]),
            m('hr')
        ]);

    }
};

var TitleBar = {
    view: function(ctrl, params) {
        var result = params.result;
        return m('span', {}, [
            m('a[href=]' + result.canonicalUri + ']', ((result.title || 'No title provided'))),
            m('br'),
            m.component(Description, params)
        ]);
    }
};

/* Render the description of a single result. Will highlight the matched text */
var Description = {
    view: function(ctrl, params) {
        var result = params.result;
        if ((result.description || '').length > 350) {
                return m('p.readable.pointer', {
                    onclick:function(){
                        result.showAll = result.showAll ? false : true;
                        }
                    },
                    result.showAll ? result.description : $.trim(result.description.substring(0, 350)) + '...'
                );
            }
            return m('p.readable', result.description);
    }
};

var Contributors = {
    view: function(ctrl, params) {
        var result = params.result;
        var contributorViews = $.map(result.contributors, function(contributor, i) {
                return m.component(Contributor, $.extend({contributor: contributor, index: i}, params));
            });

        return m('span.pull-left', {style: {'text-align': 'left'}},
            result.showAllContrib || result.contributors.length < 8 ?
                contributorViews :
                m('span', [
                    contributorViews.slice(0, 7),
                    m('br'),
                    m('a', {onclick: function(){result.showAllContrib = result.showAllContrib ? false : true;}}, 'See All')
                ])
        );

    }
};

var Contributor = {
    view: function(ctrl, params) {
        var contributor = params.contributor;
        var index = params.index;
        var vm = params.vm;
        return m('span', [
            m('span', index !== 0 ? ' · ' : ''),
            m('a', {
                onclick: function() {
                    utils.updateFilter(vm, 'match:contributors.familyName:' + contributor.familyName, true);
                    utils.updateFilter(vm, 'match:contributors.givenName:' + contributor.givenName, true);
                }
            }, contributor.name)
        ]);
    }
};

var Subjects = {
    view: function(ctrl, params){
        var result = params.result;
        var subjectViews = $.map(result.subjects || [], function(subject, i) {
            return m.component(Subject, $.extend({subject: subject}, params));
        });
        if (result.showAllsubjects || (result.subjects || []).length <= 5) {
            return m('span', subjectViews);
        }
        return m('span', [
            subjectViews.slice(0, 5),
            m('br'),
            m('div', m('a', {onclick: function() {result.showAllsubjects = result.showAllsubjects ? false : true;}},'See All'))
        ]);

    }
};

var Subject = {
    view: function(ctrl, params) {
        var subject = params.subject;
        var vm = params.vm;
        return m('span', m('.badge.pointer', {onclick: function(){
                utils.updateFilter(vm, 'match:subjects:"' + subject + '"', true);
            }}, subject.length < 50 ? subject : subject.substring(0, 47) + '...'),
            ' ');
    }
};

var Footer = {
    controller: function(params) {
        var self = this;
        this.result = params.result;
        this.cleanResult = m.prop(null);
        this.loadRawNorm = function() {
            utils.loadRawNormalized(this.result).then(
                function(cleanData) {
                    self.cleanResult(cleanData);
                }, function(error) {
                    self.cleanResult(error);
                }
            );
        };
    },
    view: function(ctrl, params) {
        var result = params.result;
        var vm = params.vm;
        return m('div', [
            m('span',
                'Released on ' + new $osf.FormattableDate(result.providerUpdatedDateTime).local,
                vm.rawNormedLoaded() ?  m('span', [
                    m('span', {style: {'margin-right': '5px', 'margin-left': '5px'}}, ' | '),
                    m('a', {
                        onclick: function() {
                            ctrl.showRawNormed = ctrl.showRawNormed ? false : true;
                            ctrl.loadRawNorm();
                        }
                    }, 'Data')
                ]) : m('span', [])
            ),
            m('span.pull-right', [
                m('img', {src: vm.ProviderMap[result.shareProperties.source].favicon, alt: 'favicon for ' + result.shareProperties.source, style: {width: '16px', height: '16px'}}),
                ' ',
                m('a', {onclick: function() {utils.updateFilter(vm, 'shareProperties.source:' + result.shareProperties.source);}}, vm.ProviderMap[result.shareProperties.source].long_name),
                m('br')
            ]),
            ctrl.showRawNormed ? m.component(RawNormalizedData, {result: ctrl.cleanResult}) : '',
        ]);
    }
};

var RawNormalizedData = {
    view: function(ctrl, params) {
        var result = params.result();
        // console.log('RESULT IS: ' + result);
        return m('.row', [
            m('.col-md-12',
                m('div', [
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
                                (function(){
                                    return JSON.stringify(result.normalized, undefined, 2);
                                }())
                            )
                        )
                    )
                ])
            )
        ]);
    }
};

module.exports = Results;
