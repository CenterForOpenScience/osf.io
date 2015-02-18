var m = require('mithril');
var $osf = require('osfHelpers');

var SearchBar = {};


SearchBar.view = function(ctrl) {
    return m('.row', [
        m('.col-md-offset-1.col-md-10', [
            m('.row', [
                m('.col-md-12', [
                    m('img[src=/static/img/share-logo-icon.png]', {
                        style: {
                            margin: 'auto',
                            height: 'auto',
                            display: 'block',
                            'max-width': '50%',
                        }
                    }),
                    m('br')
                ])
            ]),
            m('.row', [
                m('.col-md-12', [
                    m('form.input-group', {
                        onsubmit: ctrl.search,
                    },[
                        m('input.share-search-input.form-control[type=text][placeholder=Discover][autofocus]', {
                            value: ctrl.vm.query(),
                            onchange: m.withAttr('value', ctrl.vm.query),
                        }),
                        m('span.input-group-btn', [
                            m('button.btn.osf-search-btn', {onclick: ctrl.search}, m('i.icon-circle-arrow-right.icon-lg')),
                        ])
                    ])
                ])
            ]),
            m('.row', {style: {color: 'darkgrey'}}, [
                m('.col-md-4', m('p.text-center', ctrl.vm.latestDate ? ctrl.vm.totalCount + ' events as of ' + ctrl.vm.latestDate : '')),
                m('.col-md-4', m('p.text-center', ctrl.vm.query().length > 0 ? 'Found ' + ctrl.vm.count + ' events in ' + ctrl.vm.time + ' seconds' : '')),
                m('.col-md-4', m('p.text-center', ctrl.vm.providers + ' content providers'))
            ]),
            m('.row', ctrl.vm.showStats ?
                m('.col-md-12', [
                    m('a.stats-expand', {onclick: function(){ctrl.vm.showStats = false;}}, m('i.icon-angle-up')),

                ]) :
                m('.col-md-12', m('a.stats-expand', {onclick: function(){ctrl.vm.showStats = true;}}, m('i.icon-angle-down')))
            )
        ])
    ]);
};


SearchBar.controller = function(vm) {
    var self = this;

    self.vm = vm;

    self.vm.totalCount = 0;
    self.vm.providers = 26;
    self.vm.latestDate = undefined;
    self.vm.showStats = true;

    m.request({
        method: 'GET',
        url: '/api/v1/share/?size=1'
    }).then(function(data) {
        self.vm.totalCount = data.count;
        self.vm.latestDate = new $osf.FormattableDate(data.results[0].dateUpdated).local;
    });

    self.loadMore = function() {
        self.vm.page++;
        var page = (self.vm.page + 1) * 10;

        m.request({
            method: 'get',
            url: '/api/v1/share/?sort=dateUpdated&from=' + page + '&q=' + self.vm.query(),
        }).then(function(data) {
            self.vm.time = data.time;
            self.vm.count = data.count;

            // push.apply is the same as extend in python
            self.vm.results.push.apply(self.vm.results, data.results);

            self.vm.resultsLoaded = true;
        });
    };

    self.search = function(e) {
        try {
            e.stopPropagation();
        } catch (e) {
            window.event.cancelBubble = true;
        }
        self.vm.page = 0;
        self.vm.results = [];
        self.vm.resultsLoaded = false;
        self.loadMore();

        return false;
    };

};


module.exports = SearchBar;
