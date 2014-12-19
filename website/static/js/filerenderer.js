
/*
* Refresh rendered file through mfr
*/
var $ = require('jquery');
FileRenderer = {
    start: function(url, selector){
        this.url = url;
        this.element = $(selector);
        this.tries = 0;
        this.refreshContent = window.setInterval(this.getCachedFromServer.bind(this), 1000);
    },

    getCachedFromServer: function() {
        var self = this;
        $.get( self.url, function(data) {
            if (data) {
                self.element.html(data);
                clearInterval(self.refreshContent);
            } else {
                self.tries += 1;
                if(self.tries > 10){
                    clearInterval(self.refreshContent);
                    self.element.html('Timeout occurred while loading, please refresh the page');
                }
            }
        });
        }
};
module.exports = FileRenderer;
