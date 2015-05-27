/*
 * Refresh rendered file through mfr
 */

var $ = require('jquery');
var $osf = require('js/osfHelpers');

function FileRenderer(url, selector) {
    var self = this;

    self.url = url;
    self.tries = 0;
    self.selector = selector;
    self.ALLOWED_RETRIES = 10;
    self.element = $(selector);


    self.start = function() {
        self.getCachedFromServer();
    };

    self.reload = function() {
        self.tries = 0;
        self.start();
    };

    self.getCachedFromServer = function() {
        $.ajax({
            method: 'GET',
            url: self.url,
            beforeSend: $osf.setXHRAuthorization
        }).done(function(data) {
            if (data) {
                self.element.html(data);
            } else {
                self.handleRetry();
            }
        }).fail(self.handleRetry);
    };

    self.handleRetry = $osf.throttle(function() {
        self.tries += 1;

        if(self.tries > self.ALLOWED_RETRIES){
            self.element.html('Timeout occurred while loading, please refresh the page');
        } else {
            self.getCachedFromServer();
        }
    }, 1000);
}

module.exports = FileRenderer;
