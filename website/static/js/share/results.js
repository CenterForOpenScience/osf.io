'use strict';

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

    self.renderResult = function(result, index) {
        return m( '.animated.fadeInUp', [
            m('div', [
                m('h4', [
                    m('a[href=' + result.id.url + ']', result.title || 'No title provided'),
                    m('br'),
                    (function(){
                        if (result.description.length > 350) {
                            return m('p.readable.pointer',
                                {onclick:function(){result.showAll = result.showAll ? false : true;}},
                                result.showAll ? result.description : $.trim(result.description.substring(0, 350)) + '...'
                            );
                        }
                        return m('p.readable', result.description);
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
                                            utils.updateFilter(self.vm, '(contributors.family:' + person.family + ' AND contributors.given:' + person.given + ')', true);
                                        }
                                    }, person.given + ' ' + person.family)
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
                                var renderTag = function(tag) {
                                    return [
                                        m('.badge.pointer', {onclick: function(){
                                            utils.updateFilter(self.vm, 'tags:"' + tag + '"', true);
                                        }}, tag.length < 50 ? tag : tag.substring(0, 47) + '...'),
                                        ' '
                                    ];
                                };

                                if (result.showAllTags || result.tags.length < 5) {
                                    return $.map(result.tags, renderTag);
                                }
                                return m('span', [
                                    $.map(result.tags.slice(0, 5), renderTag),
                                    m('br'),
                                    m('div', m('a', {onclick: function() {result.showAllTags = result.showAllTags ? false : true;}},'See All'))
                                ]);
                            }())))
                ]),
                m('br'),
                m('br'),
                m('div', [
                    m('span', 'Released on ' + new $osf.FormattableDate(result.dateUpdated).local),
                    m('span.pull-right', [
                        m('img', {src: self.vm.ProviderMap[result.source].favicon, style: {width: '16px', height: '16px'}}),
                        ' ',
                        m('a', {onclick: function() {utils.updateFilter(self.vm, 'source:' + result.source);}}, self.vm.ProviderMap[result.source].long_name)
                    ])
                ])
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

module.exports = Results;
