var keen = require('keen-js');
var oop = require('js/oop');
var uuid = require('uuid');

var KeenTracker = oop.defclass({
    constructor: function(keenProjectId, keenWriteKey) {
        this.client = new keen({
            projectId: keenProjectId,
            writeKey: keenWriteKey
        });
        this.init();
    },

    getOrCreateKeenID: function() {
        if(!$.cookie('keenID')){
                $.cookie('keenID', uuid.v1(), {expires: 365, path: '/'})
        }

        return $.cookie('keenID');
    },

    trackVisit: function(){
        var ctx = window.contextVars;
        if(!$.cookie('keenSessionID')){
            this.createOrUpdateKeenSession();
            var returning = $('keenID') ? true : false;
            var visit = {
                "user_agent": "${keen.user_agent}",
                "referrer": {
                    "url": document.referrer
                },
                "ip_address": "${keen.ip}",
                "sessionID": $.cookie('keenSessionID'),
                "keenID": this.getOrCreateKeenID(),
                "returning": returning,
                "keen": {
                    "addons": [
                        {
                            "name": "keen:ip_to_geo",
                            "input": {
                                "ip": "ip_address"
                            },
                            "output": "ip_geo_info"
                        },
                        {
                            "name": "keen:ua_parser",
                            "input": {
                                "ua_string": "user_agent"
                            },
                            "output": "parsed_user_agent"
                        },
                        {
                            "name": "keen:referrer_parser",
                            "input": {
                                "referrer_url": "referrer.url",
                                "page_url": document.URL
                            },
                            "output": "referrer.info"
                        }
                    ]
                }
                // "daysSinceFirstVisit":"",
                // "daysSinceLastVisit": "",
                //"resolution": "" //temp user agent stuff
            };

            if(ctx.currentUser){
                visit.currentUser = ctx.currentUser;
            }

            console.log("Logged visit", visit);
        }
    },

    trackPageView: function(){
        this.createOrUpdateKeenSession();
        var ctx = window.contextVars;
        var pageView = {
            "page_url": document.URL,
            "keen": {
                "addons": [
                    {
                        "name" : "keen:url_parser",
                        "input" : {
                            "url" : "page_url"
                        },
                        "output" : "parsed_page_url"
                    }
                ]
            },
            "keenID": this.getOrCreateKeenID(),
            "sessionID": $.cookie('keenSessionID'),
            "pageTitle": document.title
            //"generation_time": ""
            //"timeSpend": ""
        };
        if(ctx.node){
            pageView.node = {
                "id": ctx.node.id,
                "title": ctx.node.title,
                "type": ctx.node.category,
                "tags": ctx.node.tags

            };
        }
        if(ctx.currentUser){
            pageView.user = ctx.currentUser;
        }
        console.log("Logged pageview", pageView);
    },

    trackCustomEvent: function(eventCollection, eventData){},

    createOrUpdateKeenSession: function() {
        var date = new Date();
        var min = 25;
        var expDate = date.setTime(date.getTime() + (min*60*1000));
        if(!$.cookie('keenSessionID')){
            $.cookie('keenSessionID', uuid.v1(), {expires: expDate, path: '/'});
        } else {
            var sessionID = $.cookie('keenSessionID');
            $.cookie('keenSessionID', sessionID, {expires: expDate, path: '/'});
        }
    },

    init: function(){
        this.trackVisit();
        this.trackPageView();
    }
});

module.exports = KeenTracker;
