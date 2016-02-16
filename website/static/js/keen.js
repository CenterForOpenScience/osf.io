var keen = require('keen-js');
var ctx = window.contextVars;

var KeenTracker = function(keenioProjectId, keenioWriteKey){

    var self = this;

    var keenClient = new keen({
        projectId: keenioProjectId,
        writeKey: keenioWriteKey
    });


    self.trackVisit = function(){
        self.createOrUpdateCookie();
    };

    self.trackPageView = function(){
        self.createOrUpdateCookie();
        console.log(ctx);
    };

    self.trackCustomEvent = function(eventCollection, eventData){};

    self.createOrUpdateCookie = function() {
        var date = new Date();
        var min = 25;
        var expDate = date.setTime(date.getTime() + (30*60*1000));
        if(!$.cookie('keen_visit')){
            $.cookie('keen_visit','true', {expires: expDate});
        } else {
            var sessionHash = $.cookie('keen_visit');
            $.cookie('keen_visit', null);
            $.cookie('keen_visit', sessionHash, {expires: expDate});
        }
    };

    self.init = function(){
        self.trackVisit();
        self.trackPageView();
    }

};

module.exports = {
    KeenTracker: KeenTracker
};