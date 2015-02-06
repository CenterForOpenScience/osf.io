
/*
* Refresh rendered file through mfr
*/
var $ = require('jquery');
FileRenderer = {
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
            url: self.url,
        }).done(function(data) {
            if (data) {
                self.element.html(data);
                clearInterval(self.refreshContent);
            } else {
                self.handleRetry();
            }
        }).fail(self.handleRetry);
    },

    handleRetry: function() {
        var self = FileRenderer;
        self.tries += 1;

        if(self.tries > self.ALLOWED_RETRIES){
            clearInterval(self.refreshContent);
            self.element.html('Timeout occurred while loading, please refresh the page');
        } else {
            self.getCachedFromServer();
        }
    }
};
module.exports = FileRenderer;
