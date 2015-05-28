var m = require('mithril');
var $osf = require('js/osfHelpers');
var fileBrowser = require('js/fileViewTreebeard');

var FileTree = {
    controller: function(nodeApiUrl) {
        var self = this;
        self.load = false;
        self.url = nodeApiUrl + 'files/grid/';

        $.ajax({
            method: 'GET',
            url: self.url,
            beforeSend: $osf.setXHRAuthorization,
        })
        .done(function (data) {
            self.data = data;
            self.loaded = true;
        });

        self.bindFangorn = function(element, isInitialized, context) {
            if (isInitialized) return;
            new fileBrowser(self.data);
        };

    },
    view: function(ctrl) {
        if (!ctrl.loaded) {
            return m('#grid', [
                m('.fangorn-loading', [
                    m('.logo-spin.text-center', [
                        m('img[src="/static/img/logo_spin.png"alt=loader]')
                    ]),
                    m('p.m-t-sm-fg.load-message', 'Loading files...  ')
                ])
            ]);
        }

        return m('.row', m('.col-md-12', m('#grid', {config: ctrl.bindFangorn})));
    }
};

module.exports = FileTree;
