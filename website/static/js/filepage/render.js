var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

var util = require('./util.js');


var FileRenderer = {
    controller: function(url, error) {
        var self = this;
        self.url = url;
        self.error = error;
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
            }).fail(function(response) {
                m.startComputation();
                self.data = response.responseText;
                self.loaded = true;
                $(self.element).html(self.data);
                m.endComputation();
            });
        };

        if (self.url) {
            self.reload();
        }
    },
    view: function(ctrl) {
        if (!ctrl.url) return m('.mfr.mfr-error', {style: {margin: '10px'}}, m.trust(ctrl.error));
        return m('.mfr.mfr-file', util.Spinner);
    }
};

module.exports = FileRenderer;
