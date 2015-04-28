'use strict';

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');

var SearchBar = {};

SearchBar.view = function(ctrl) {
    return [
        m('.row', [
            m('.col-xs-12', {
                    style: {
                        margin: '30px auto',
                        display: 'block',
                        'text-align': 'center'
                    }
            }, [
                m('img[src=/static/img/share-logo-icon.png]', {
                    style: {
                        height: 'auto',
                        'max-width': '15%',
                        '-webkit-animation-duration': '3s'
                    },
                    // class: 'animated pulse'
                }),
                m('span.about-share-header', 'SHARE'),
                m('div', {style: {color: 'darkgrey'}}, m('p.readable', [
                    'Notice: this is a public beta release'
                ])),
                m('br'),
            ])
        ]),
        m('.row', [
            m('.col-xs-12.col-lg-8.col-lg-offset-2', [
                m('form.input-group', {
                    onsubmit: ctrl.search,
                },[
                    m('input.share-search-input.form-control[type=text][placeholder=Search][autofocus]', {
                        value: ctrl.vm.query(),
                        onchange: m.withAttr('value', ctrl.vm.query),
                    }),
                    m('span.input-group-btn', [
                        m('button.btn.osf-search-btn', m('i.fa.fa-search.fa-lg')),
                        m('button.btn.osf-search-btn', {
                            'data-toggle': 'tooltip',
                            'title': 'View search as ATOM feed',
                            'data-placement': 'bottom',
                            onclick: function(){
                                location.href = '/share/atom/?' + ctrl.atomParams();
                            }
                        }, m('i.fa.fa-rss.fa-lg'))
                    ])
                ])
            ])
        ])
    ];
};


SearchBar.controller = function(vm) {
    var self = this;

    self.vm = vm;

    self.vm.totalCount = 0;
    self.vm.providers = Object.keys(self.vm.ProviderMap).length;
    self.vm.latestDate = undefined;
    self.vm.showStats = true;

    self.atomParams = function(){
        var d = {};
        d.q = utils.buildQuery(self.vm);
        d.sort = self.vm.sortMap[self.vm.sort()] || null;
        return $.param(d);
    };

    self.search = function(e) {
        utils.maybeQuashEvent(e);
        utils.search(self.vm);
    };

    self.search();
};


module.exports = SearchBar;
