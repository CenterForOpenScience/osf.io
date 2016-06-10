'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var mathrender = require('js/mathrender');
require('truncate');

var LoadingIcon = {
    view: function(ctrl) {
        return m('img', {src: '/static/img/loading.gif', alt: 'loading spinner'});
    }
};

var Results = {
    view: function(ctrl, params) {
        var vm = params.vm;
        var resultViews = $.map(vm.results || [], function(result, i) {
            return m.component(Result, {result: result, vm: vm});
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
                return m('', [m.component(LoadingIcon), 'loading...']);
            }
        };

        return m('', [
            m('.row', m('.col-md-12', {
                config: function(el, ini, ctx) {
                    mathrender.typeset(el); // Adds all results to Mathjax queue at once.
                }
            }, maybeResults(resultViews, vm.resultsLoading()))),
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
            m('a[href=' + result.uris.canonicalUri + ']', ((result.title || 'No title provided'))),
            m('br'),
            m.component(Description, params)
        ]);
    }
};

/* Render the description of a single result. Will highlight the matched text */
var Description = {
    controller: function(vm) {
        var self = this;
        self.showAll = m.prop(false);
    },
    view: function(ctrl, params) {
        var result = params.result;
        var showOnClick = function() {
            ctrl.showAll(!ctrl.showAll());
        };
        if ((result.description || '').length > 350) {
            return m('', [
                m('p.readable.pointer', {
                    onclick: showOnClick,
                }, ctrl.showAll() ? result.description : $.truncate(result.description, {length: 350})),
                m('a.sr-only', {href: '#', onclick: showOnClick}, ctrl.showAll() ? 'See less' : 'See more')
            ]);
        } else {
            return m('p.readable', result.description);
        }
    }
};

var Contributors = {
    controller: function(vm) {
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
        return m('span', [
            m('span', index !== 0 ? ' · ' : ''),
            m('a', {
                href: '#',
                onclick: function() {
                    var givenNameLength = contributor.givenName ? contributor.givenName.length : 0;
                    var familyNameLength = contributor.familyName ? contributor.familyName.length : 0;
                    if (givenNameLength <= 0 && familyNameLength <= 0) {
                        utils.updateFilter(vm, 'match:contributors.name:' + contributor.name, true);
                    } else {
                        var filters = [];
                        if (givenNameLength > 0) {
                            filters.push('match:contributors.givenName:' + contributor.givenName);
                        }
                        if (familyNameLength > 0) {
                            filters.push('match:contributors.familyName:' + contributor.familyName);
                        }
                        if(filters.length>0){
                           utils.updateFilter(vm, filters, true);
                        }
                    }
                }
            }, contributor.name)
        ]);
    }
};

var Subjects = {
    controller: function(vm) {
        var self = this;
        self.showAll = false;
    },
    view: function(ctrl, params){
        var result = params.result;
        var subjectViews = $.map(result.subjects || [], function(subject, i) {
            return m.component(Subject, $.extend({subject: subject}, params));
        });
        if (ctrl.showAll || (result.subjects || []).length <= 5) {
            return m('span', subjectViews);
        }
        return m('span', [
            subjectViews.slice(0, 5),
            m('br'),
            m('div', m('a', {onclick: function() {ctrl.showAll = !ctrl.showAll;}},'See All'))
        ]);

    }
};

var Subject = {
    view: function(ctrl, params) {
        var subject = params.subject;
        var vm = params.vm;
        return m('span', m('a.badge.pointer', {onclick: function(){
                utils.updateFilter(vm, 'match:subjects:"' + subject + '"', true);
            }}, $.truncate(subject, {length: 50}), ' '
        ));
    }
};

var Footer = {
    controller: function(params) {
        var self = this;
        this.result = params.result;
        this.cleanResult = m.prop(null);
        this.missingError = m.prop(null);
        this.showRawNormalized = m.prop(false);
        this.loadRawNormalized = function() {
            utils.loadRawNormalized(this.result).then(
                function(cleanData) {
                    self.cleanResult(cleanData);
                }, function(error) {
                    self.missingError(error);
                }
            );
        };
    },
    view: function(ctrl, params) {
        var result = params.result;
        var vm = params.vm;
        return m('div', [
            m('span.text-muted',
                'Released on ' + new $osf.FormattableDate(result.providerUpdatedDateTime).local,
                vm.rawNormedLoaded() ?  m('span', [
                    m('span', {style: {'margin-right': '5px', 'margin-left': '5px'}}, ' | '),
                    m('a', {
                        onclick: function() {
                            ctrl.showRawNormalized(!ctrl.showRawNormalized());
                            ctrl.loadRawNormalized();
                        }
                    }, 'Data')
                ]) : m('span', [])
            ),
            m('span.pull-right', [
                m('img', {src: vm.ProviderMap[result.shareProperties.source].favicon, alt: 'favicon for ' + result.shareProperties.source, style: {width: '16px', height: '16px'}}),
                ' ',
                m('a', {
                    onclick: function() {utils.updateFilter(vm, 'match:shareProperties.source:' + result.shareProperties.source);}
                }, vm.ProviderMap[result.shareProperties.source].long_name),
                m('br'),
                m('hr')
            ]),
            ctrl.showRawNormalized() ? m.component(RawNormalizedData, {result: ctrl.cleanResult(), missingError: ctrl.missingError()}) : '',
        ]);
    }
};

var RawNormalizedData = {
    view: function(ctrl, params) {
        var result = params.result || params.missingError;
        var divID = params.missingError ? '' : (result.normalized.shareProperties.docID + result.normalized.shareProperties.source).replace( /(:|\.|\[|\]|,|\/)/g, '-' );
        return m('.row', [
            m('.col-md-12',
                m('div', [
                    m('ul', {className: 'nav nav-tabs'}, [
                        m('li', m('a', {href: '#raw' + divID, 'data-toggle': 'tab'}, 'Raw')),
                        m('li', m('a', {href: '#normalized' + divID, 'data-toggle': 'tab'}, 'Normalized'))
                    ]),
                    m('div', {className: 'tab-content'},
                        m('div',
                            {className: 'tab-pane active', id:'raw' + divID},
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
                            {className: 'tab-pane', id:'normalized' + divID},
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
