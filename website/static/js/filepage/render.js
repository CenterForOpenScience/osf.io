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
            self.element = '.mfr-file';

            $.ajax({
                method: 'GET',
                url: self.url,
                beforeSend: $osf.setXHRAuthorization
            }).done(function(data) {
                m.startComputation();
                self.data = data;
                self.loaded = true;
                $(self.element).html(self.data);
                m.endComputation();
            }).fail(function() {
                //TODO
            });
        };

        self.reload();
    },
    view: function(ctrl) {
        return m('.mfr.mfr-file', util.Spinner);
    }
};

module.exports = FileRenderer;
