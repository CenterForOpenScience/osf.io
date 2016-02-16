var keen = require('keen-js');
var oop = require('js/oop');

var KeenTracker = oop.defclass({
    constructor: function(keenProjectId, keenWriteKey) {
        this.client = new keen({
            projectId: keenProjectId,
            writeKey: keenWriteKey
        });
        this.init();
    },

    trackVisit: function(){
        if(!$.cookie('keen_visit')){
            console.log("Logged visit");
            this.createOrUpdateCookie();
        }
    },

    trackPageView: function(){
        var pageView = {
            "page_url": document.URL,
            "ip_address": "${keen.ip}",
            "user_agent": "${keen.user_agent}",
            "keen": {
                "addons": [
                    {
                       "name" : "keen:ip_to_geo",
                        "input" : {
                            "ip" : "ip_address"
                        },
                        "output" : "ip_geo_info"
                    },
                    {
                        "name" : "keen:ua_parser",
                        "input" : {
                            "ua_string" : "user_agent"
                        },
                        "output" : "parsed_user_agent"
                    },
                    {
                        "name" : "keen:url_parser",
                        "input" : {
                            "url" : "page_url"
                        },
                        "output" : "parsed_page_url"
                    }
                ]
            },
            "sessionID": $.cookie('keen_visit'),
            "timeSpent": "",
            "pageTitle": document.title,
            "generation_time": ""
        };
        if(window.contextVars.node){
            pageView.node = window.contextVars.node;
        }
        if(window.contextVars.currentUser){
            pageView.user = window.contextVars.currentUser;
        }
        this.createOrUpdateCookie();
        console.log("Logged pageview", pageView);
    },

    trackCustomEvent: function(eventCollection, eventData){},

    createOrUpdateCookie: function() {
        var date = new Date();
        var min = 25;
        var expDate = date.setTime(date.getTime() + (min*60*1000));
        if(!$.cookie('keen_visit')){
            $.cookie('keen_visit','random_key', {expires: expDate});
        } else {
            var sessionHash = $.cookie('keen_visit');
            $.cookie('keen_visit', null);
            $.cookie('keen_visit', sessionHash, {expires: expDate});
        }
    },

    init: function(){
        this.trackVisit();
        this.trackPageView();
    }
});

module.exports = KeenTracker;