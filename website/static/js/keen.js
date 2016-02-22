var keen = require('keen-js');
var oop = require('js/oop');
var uuid = require('uuid');

var KeenTracker = oop.defclass({
    constructor: function(keenProjectId, keenWriteKey) {
        this.keenClient = new keen({
            projectId: keenProjectId,
            writeKey: keenWriteKey
        });
        this.init();
    },

    createOrUpdateKeenSession: function() {
        var date = new Date();
        var min = 25;
        var expDate = date.setTime(date.getTime() + (min*60*1000));
        if(!$.cookie('keenSessionId')){
            $.cookie('keenSessionId', uuid.v1(), {expires: expDate, path: '/'});
        } else {
            var sessionId = $.cookie('keenSessionId');
            $.cookie('keenSessionId', sessionId, {expires: expDate, path: '/'});
        }
    },

    getOrCreateKeenId: function() {
        if(!$.cookie('keenId')){
            $.cookie('keenId', uuid.v1(), {expires: 365, path: '/'});
        }

        return $.cookie('keenId');
    },

    trackVisit: function(){
        var ctx = window.contextVars;
        if(!$.cookie('keenSessionId')){
            this.createOrUpdateKeenSession();
            var returning = $.cookie('keenId') ? true : false;
            var visit = {
                'userAgent': '${keen.user_agent}',
                'referrer': {
                    'url': document.referrer
                },
                'ipAddress': '${keen.ip}',
                'sessionId': $.cookie('keenSessionId'),
                'keenId': this.getOrCreateKeenId(),
                'returning': returning,
                'pageUrl': document.URL,
                'keen': {
                    'addons': [
                        {
                            'name': 'keen:ip_to_geo',
                            'input': {
                                'ip': 'ipAddress'
                            },
                            'output': 'ipGeoInfo'
                        },
                        {
                            'name': 'keen:ua_parser',
                            'input': {
                                'ua_string': 'userAgent'
                            },
                            'output': 'parsedUserAgent'
                        },
                        {
                            'name': 'keen:referrer_parser',
                            'input': {
                                'referrer_url': 'referrer.url',
                                'page_url': 'pageUrl'
                            },
                            'output': 'referrer.info'
                        }
                    ]
                }
                // 'daysSinceFirstVisit':'',
                // 'daysSinceLastVisit': '',
                //'resolution': '' //temp user agent stuff
            };

            if(ctx.currentUser){
                visit.currentUser = ctx.currentUser;
            }

            this.keenClient.addEvent('visits', visit, function(err){
                if(err){
                    throw 'Error sending Keen data: ' + err;
                }
            });
        }
    },

    trackPageView: function(){
        this.createOrUpdateKeenSession();
        var ctx = window.contextVars;
        var pageView = {
            'pageUrl': document.URL,
            'keen': {
                'addons': [
                    {
                        'name' : 'keen:url_parser',
                        'input' : {
                            'url' : 'pageUrl'
                        },
                        'output' : 'parsedPageUrl'
                    }
                ]
            },
            'keenId': this.getOrCreateKeenId(),
            'sessionId': $.cookie('keenSessionId'),
            'pageTitle': document.title
            //'generation_time': ''
            //'timeSpend': ''
        };
        if(ctx.node){
            pageView.node = {
                'id': ctx.node.id,
                'title': ctx.node.title,
                'type': ctx.node.category,
                'tags': ctx.node.tags
            };
        }
        if(ctx.currentUser){
            pageView.user = ctx.currentUser;
        }

        this.keenClient.addEvent('pageviews', pageView, function(err){
            if(err){
                throw 'Error sending Keen data: ' + err;
            }
        });
    },

    trackCustomEvent: function(eventCollection, eventData){
        this.keenClient.addEvent(eventCollection, eventData);
    },

    init: function(){
        this.trackVisit();
        this.trackPageView();
    }
});

module.exports = KeenTracker;
