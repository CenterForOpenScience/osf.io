
/*
* Refresh rendered file through mfr
*/
var $ = require('jquery');
FileRenderer = {
    start: function(url, selector){
        this.url = url;
        this.element = $(selector);
        this.tries = 0;
        // this.refreshContent = window.setInterval(this.getCachedFromServer.bind(this), 1000);
        this.getCachedFromServer();
    },

    getCachedFromServer: function() {
        var self = this;
        var fut = $.ajax({
            url: self.url,
        });

        fut.done(function(data) {
            if (data) {
                self.element.html(data);
                clearInterval(self.refreshContent);
            } else {
                self.handleRetry();
            }
        });

        fut.fail(self.handleRetry);
    },

    handleRetry: function() {
        var self = this;
        self.tries += 1;
        if(self.tries > 10){
            clearInterval(self.refreshContent);
            self.element.html('Timeout occurred while loading, please refresh the page');
        } else {
            self.getCachedFromServer();
        }
    }
};
module.exports = FileRenderer;
