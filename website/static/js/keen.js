'use strict';

var keen = require('keen-js');
var oop = require('js/oop');
var $ = require('jquery');
var uuid = require('uuid');

var KeenTracker = oop.defclass({
    constructor: function(keenProjectId, keenWriteKey, params) {
        this.keenClient = new keen({
            projectId: keenProjectId,
            writeKey: keenWriteKey
        });
        this.currentUser = params.currentUser || null;
        this.node = params.node || null;
        this.init();
    },

    createOrUpdateKeenSession: function() {
        var date = new Date();
        var expiresInMinutes = 25;
        var expDate = date.setTime(date.getTime() + (expiresInMinutes*60*1000));
        if(!$.cookie('keenSessionId')){
            $.cookie('keenSessionId', uuid.v1(), {expires: expDate, path: '/'});
        } else {
            var sessionId = $.cookie('keenSessionId');
            $.cookie('keenSessionId', sessionId, {expires: expDate, path: '/'});
        }
    },

    getOrCreateKeenId: function() {
        if(!$.cookie('keenUserId')){
            $.cookie('keenUserId', uuid.v1(), {expires: 365, path: '/'});
        }

        return $.cookie('keenUserId');
    },

    trackPageView: function(){
        this.createOrUpdateKeenSession();
        var returning = Boolean($.cookie('keenUserId'));
        var pageView = {
            'pageUrl': document.URL,
            'keenUserId': this.getOrCreateKeenId(),
            'sessionId': $.cookie('keenSessionId'),
            'pageTitle': document.title,
            'userAgent': '${keen.user_agent}',
            'referrer': {
                'url': document.referrer
            },
            'ipAddress': '${keen.ip}',
            'returning': returning,
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
                    },
                    {
                        'name' : 'keen:url_parser',
                        'input' : {
                            'url' : 'pageUrl'
                        },
                        'output' : 'parsedPageUrl'
                    },
                    {
                        'name' : 'keen:url_parser',
                        'input' : {
                            'url' : 'referrer.url'
                        },
                        'output' : 'parsedReferrerUrl'
                    }
                ]
            }
            // 'daysSinceFirstVisit':'',
            // 'daysSinceLastVisit': '',
            //'resolution': '' //temp user agent stuff
            //'generationTime': ''
            //'timeSpent': ''
        };
        if(this.node){
            pageView.node = {
                'id': this.node.id,
                'title': this.node.title,
                'type': this.node.category,
                'tags': this.node.tags
            };
        }
        if(this.currentUser){
            pageView.user = this.currentUser;
        }

        this.keenClient.addEvent('pageviews', pageView, function(err){
            if(err){
                throw new Error('Error sending Keen data: ' + err, pageView);
            }
        });
    },

    init: function(){
        this.trackPageView();
    }
});

module.exports = KeenTracker;
