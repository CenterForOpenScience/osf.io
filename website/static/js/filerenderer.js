/*
 * Refresh rendered file through mfr
 */

'use strict';

var $ = require('jquery');
var $osf = require('osfHelpers');

var FileRenderer = {
    start: function(url, selector){
        this.url = url;
        this.tries = 0;
        this.ALLOWED_RETRIES = 10;
        this.element = $(selector);
        this.getCachedFromServer();
    },

    getCachedFromServer: function() {
        var self = this;
        $.ajax({
            url: self.url
        }).done(function(data) {
            if (data) {
                self.element.html(data);
            } else {
                self.handleRetry();
            }
        }).fail(self.handleRetry);
    },

    handleRetry: $osf.throttle(function() {
        var self = FileRenderer;
        self.tries += 1;

        if(self.tries > self.ALLOWED_RETRIES){
            self.element.html('Timeout occurred while loading, please refresh the page');
        } else {
            self.getCachedFromServer();
        }
    }, 1000)
};

module.exports = FileRenderer;
