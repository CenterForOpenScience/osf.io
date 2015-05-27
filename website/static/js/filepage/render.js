var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

var util = require('./util.js');


var FileRenderer = {
    controller: function(url) {
        var self = this;
        self.url = url;
        self.loaded = false;
        self.data = undefined;

        self.reload = function() {
            self.loaded = false;

            $.ajax({
                method: 'GET',
                url: self.url,
                beforeSend: $osf.setXHRAuthorization
            }).done(function(data) {
                self.data = data;
                self.loaded = true;
                m.redraw();
            }).fail(function() {
                //TODO
            });
        };

        self.reload();
    },
    view: function(ctrl) {
        if (!ctrl.loaded) util.Spinner;
        return m('.mfr.mfr-file', m.trust(ctrl.data));
    }
};

module.exports = FileRenderer;
