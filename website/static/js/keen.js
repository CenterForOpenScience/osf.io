'use strict';


var keenTracking = require('keen-tracking');
var oop = require('js/oop');
var $ = require('jquery');
var Cookie = require('js-cookie');
var uuid = require('uuid');
var Raven = require('raven-js');

var KeenTracker = (function() {

    function KeenTracker() {
        if (instance) {
            throw new Error("Cannot instantiate another KeenTracker instance");
        } else {
            var self = this;
            self._keenClient = null;

            self.setKeenClient = function (params) {
                self._keenClient = new keenTracking({
                    projectId: params.keenProjectId,
                    writeKey: params.keenWriteKey
                });
            };

            self.createOrUpdateKeenSession = function () {
                var expDate = new Date();
                var expiresInMinutes = 25;
                expDate.setTime(expDate.getTime() + (expiresInMinutes * 60 * 1000));
                var currentSessionId = Cookie.get('keenSessionId') || uuid.v1();
                Cookie.set('keenSessionId', currentSessionId, {expires: expDate, path: '/'});
            };

            self.getOrCreateKeenId = function () {
                if (!Cookie.get('keenUserId')) {
                    Cookie.set('keenUserId', uuid.v1(), {expires: 365, path: '/'});
                }

                return Cookie.get('keenUserId');
            };

            self.trackPageView = function (params) {
                self.createOrUpdateKeenSession();
                var returning = Boolean(Cookie.get('keenUserId'));
                var pageView = {
                    'pageUrl': document.URL,
                    'keenUserId': this.getOrCreateKeenId(),
                    'sessionId': Cookie.get('keenSessionId'),
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
                                'name': 'keen:url_parser',
                                'input': {
                                    'url': 'pageUrl'
                                },
                                'output': 'parsedPageUrl'
                            },
                            {
                                'name': 'keen:url_parser',
                                'input': {
                                    'url': 'referrer.url'
                                },
                                'output': 'parsedReferrerUrl'
                            }
                        ]
                    }
                };
                if (params.node) {
                    pageView.node = {
                        'id': params.node.id,
                        'title': params.node.title,
                        'type': params.node.category,
                        'tags': params.node.tags
                    };
                }
                if (params.currentUser) {
                    pageView.user = {
                        id: params.currentUser.id,
                        locale: params.currentUser.locale,
                        timezone: params.currentUser.timezone,
                        entryPoint: params.currentUser.entryPoint
                    };
                }

                self._keenClient.recordEvent('pageviews', pageView, function (err) {
                    if (err) {
                        Raven.captureMessage('Error sending Keen data: <' + err + '>', {
                            extra: {payload: pageView}
                        });
                    }
                });
            };

            self.trackCustomEvent = function (collection, eventData) {
                self._keenClient.recordEvent(collection, eventData, function (err) {
                    if (err) {
                        Raven.captureMessage('Error sending Keen data to ' + collection + ': <' + err + '>', {
                            extra: {payload: eventData}
                        });
                    }
                });
            };
        }

    }

    var instance = null;
    return {
        getKeenInstance: function () {
            instance = instance || new KeenTracker();
            return instance;
        }
    };
})();

module.exports = KeenTracker;
