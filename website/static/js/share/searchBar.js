var m = require('mithril');
var $osf = require('osfHelpers');

var SearchBar = {};


SearchBar.view = function(ctrl) {
    return [
        m('.row', [
            m('.col-md-12', [
                m('img[src=/static/img/share-logo-icon.png]', {
                    style: {
                        margin: 'auto',
                        height: 'auto',
                        display: 'block',
                        'max-width': '40%',
                        '-webkit-animation-duration': '3s'
                    },
                    class: 'animated pulse'
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
        ])
    ];
};


SearchBar.controller = function(vm) {
    var self = this;

    self.vm = vm;

    self.vm.totalCount = 0;
    self.vm.providers = 26;
    self.vm.latestDate = undefined;
    self.vm.showStats = true;

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
        self.vm.showStats = false;
        self.vm.resultsLoaded = false;
        self.loadMore();

        return false;
    };

};


module.exports = SearchBar;
