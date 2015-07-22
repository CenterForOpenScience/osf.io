'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var Results = {};


Results.view = function(ctrl) {
    var res = [];
    var len = 0;
    if (ctrl.vm.results){
        res = $.map(ctrl.vm.results, ctrl.renderResult);
        len = ctrl.vm.results.length;
    }
    return m('', [
        m('.row', m('.col-md-12', (!utils.arrayEqual(res, [])) ? res : (!ctrl.vm.resultsLoading() && (ctrl.vm.results !== null)) ? m('span', {style: {margin: 'auto'}}, 'No results for this query') : [])),
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

Results.controller = function(vm) {
    var self = this;
    self.vm = vm;
    self.vm.resultsLoading = m.prop(false);
    self.vm.rawNormedLoaded = {onload: function(vm) {
        return utils.checkRawNormalizedResponse(vm);
    }};

    self.renderResult = function(result, index) {
        return m( '.animated.fadeInUp', [
            m('div', [
                m('h4', [
                    m('a[href=' + result.uris.canonicalUri + ']', m.trust(result.title) || 'No title provided'),
                    m('br'),
                    (function(){
                        if ((result.description || '').length > 350) {
                            return m('p.readable.pointer',
                                {onclick:function(){result.showAll = result.showAll ? false : true;}},
                                m.trust(result.showAll ? result.description : $.trim(result.description.substring(0, 350)) + '...')
                            );
                        }
                        return m('p.readable', m.trust(result.description));
                    }()),
                ]),
                m('.row', [
                    m('.col-md-7', m('span.pull-left', (function(){
                        var renderPeople = function(people) {
                            return $.map(people, function(person, index) {
                                return m('span', [
                                    m('span', index !== 0 ? ' · ' : ''),
                                    m('a', {
                                        onclick: function() {
                                            utils.updateFilter(self.vm, 'contributors.familyName:' + person.familyName, true);
                                            utils.updateFilter(self.vm, 'contributors.givenName:' + person.givenName, true);
                                        }
                                    }, person.name)
                                ]);
                            });
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
                    }()))),
                    m('.col-md-5',
                        m('.pull-right', {style: {'text-align': 'right'}},
                            (function(){
                                var rendersubject = function(subject) {
                                    return [
                                        m('.badge.pointer', {onclick: function(){
                                            utils.updateFilter(self.vm, 'subjects:"' + subject + '"', true);
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
                            }())
                        )
                    )
                ]),
                m('br'),
                m('br'),
                m('div', [
                    m('span', 
                        'Released on ' + new $osf.FormattableDate(result.providerUpdatedDateTime).local,
                        m('span',
                            function() {
                                if (vm.rawNormedLoaded) {
                                    return m('span', [
                                        m('span', {style: {'margin-right': '5px', 'margin-left': '5px'}}, ' | '),
                                        m('a', {
                                            onclick: function() {
                                                result.showRawNormed = result.showRawNormed ? false : true;
                                                if (!result.raw) {
                                                    utils.loadRawNormalized(result);
                                                }
                                            }
                                        }, 'Data')
                                    ]);
                                }
                            }
                        )
                    ),
                    m('span.pull-right', [
                        m('img', {src: self.vm.ProviderMap[result.shareProperties.source].favicon, style: {width: '16px', height: '16px'}}),
                        ' ',
                        m('a', {onclick: function() {utils.updateFilter(self.vm, 'shareProperties.source:' + result.shareProperties.source);}}, self.vm.ProviderMap[result.shareProperties.source].long_name),
                        m('br')
                    ])
                ]),
                m('.row', [
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
                ]),
                m('hr')
            ])
        ]);
    };

    // Uncomment for infinite scrolling!
    // $(window).scroll(function() {
    //     if  ($(window).scrollTop() === $(document).height() - $(window).height()){
    //         utils.loadMore(self.vm);
    //     }
    // });
};

module.exports = Results;
