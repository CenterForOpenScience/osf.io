'use strict';


var $ = require('jquery');
var Cookie = require('js-cookie');
var Raven = require('raven-js');
var lodashGet = require('lodash.get');
var keenTracking = require('keen-tracking');

var KeenTracker = (function() {

    function _nowUTC() {
        var now = new Date();
        return new Date(
            now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(),
            now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()
        );
    }

    function KeenTracker() {
        if (instance) {
            throw new Error('Cannot instantiate another KeenTracker instance.');
        } else {
            var self = this;
            self._keenClient = null;

            self.setKeenClient = function (params) {
                self._keenClient = new keenTracking({
                    projectId: params.keenProjectId,
                    writeKey: params.keenWriteKey
                });

                self._keenClient.extendEvents(function _defaultKeenPayload() {
                    self.createOrUpdateKeenSession();
                    var returning = Boolean($.cookie('keenUserId'));

                    var user = window.contextVars.currentUser;
                    var node = window.contextVars.node;
                    var loggableNode = {
                        id: lodashGet(node, 'id'),
                        title: lodashGet(node, 'title'),
                        type: lodashGet(node, 'category'),
                        tags: lodashGet(node, 'tags'),
                    };

                    return {
                        page: {
                            title: document.title,
                            url: document.URL,
                            info: {},
                        },
                        referrer: {
                            url: document.referrer,
                            info: {},
                        },
                        tech: {
                            browser: keenTracking.helpers.getBrowserProfile(),
                            ua: '${keen.user_agent}',
                            info: {},
                        },
                        time: {
                            local: keenTracking.helpers.getDatetimeIndex(),
                            utc: keenTracking.helpers.getDatetimeIndex(_nowUTC()),
                        },
                        visitor: {
                            id: self.getOrCreateKeenId(),
                            // time_on_page: sessionTimer.value(),
                            session: $.cookie('keenSessionId'),
                            returning: returning,
                        },
                        node: loggableNode,
                        user: {
                            entryPoint: user.entryPoint,
                        },
                        geo: {},
                        anon: {
                            id: user.anon.id,
                            continent: user.anon.continent,
                            country: user.anon.country,
                            latitude: user.anon.latitude,
                            longitude: user.anon.longitude,
                        },
                        keen: {
                            addons: [
                                {
                                    name: 'keen:ua_parser',
                                    input: {
                                        ua_string: 'tech.ua'
                                    },
                                    output: 'tech.info',
                                },
                                {
                                    name: 'keen:url_parser',
                                    input: {
                                        url: 'page.url',
                                    },
                                    output: 'page.info',
                                },
                                {
                                    name: 'keen:url_parser',
                                    input: {
                                        url: 'referrer.url',
                                    },
                                    output: 'referrer.info',
                                },
                                {
                                    name: 'keen:referrer_parser',
                                    input: {
                                        referrer_url: 'referrer.url',
                                        page_url: 'page.url',
                                    },
                                    output: 'referrer.info',
                                },
                            ]
                        },
                    };
                });
            };

            self.createOrUpdateKeenSession = function () {
                var expDate = new Date();
                var expiresInMinutes = 25;
                expDate.setTime(expDate.getTime() + (expiresInMinutes * 60 * 1000));
                var currentSessionId = Cookie.get('keenSessionId') || keenTracking.helpers.getUniqueId();
                Cookie.set('keenSessionId', currentSessionId, {expires: expDate, path: '/'});
            };

            self.getOrCreateKeenId = function () {
                if (!Cookie.get('keenUserId')) {
                    Cookie.set('keenUserId', keenTracking.helpers.getUniqueId(), {expires: 365, path: '/'});
                }
                return Cookie.get('keenUserId');
            };

            self.trackPageView = function (user, node) {
                self.trackCustomEvents({
                    'public-pageviews': [{}],
                    'private-pageviews': [{
                        tech: {
                            ip: '${keen.ip}',
                        },
                        user: {
                            id: user.id,
                            locale: user.locale,
                            timezone: user.timezone,
                        },
                        keen: {
                            addons:[{
                                name: 'keen:ip_to_geo',
                                input: {
                                    ip: 'tech.ip',
                                },
                                output: 'geo',
                            }],
                        },
                    }],
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

            self.trackCustomEvents = function (multipleEvents) {
                self._keenClient.recordEvents(multipleEvents, function (err, res) {
                    if (err) {
                        Raven.captureMessage('Error sending Keen data for multiple events: <' + err + '>', {
                            extra: {payload: multipleEvents}
                        });
                    } else {
                        for (var collection in res) {
                            var results = res[collection];
                            for (var idx in results) {
                                if (!results[idx].success) {
                                    Raven.captureMessage('Error sending Keen data to ' + collection + '.', {
                                        extra: {payload: multipleEvents[collection][idx]}
                                    });
                                }
                            };
                        };
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
