'use strict';


var $ = require('jquery');
var md5 = require('js-md5');
var Raven = require('raven-js');
var Cookie = require('js-cookie');
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

    function _createOrUpdateKeenSession() {
        var expDate = new Date();
        var expiresInMinutes = 25;
        expDate.setTime(expDate.getTime() + (expiresInMinutes * 60 * 1000));
        var currentSessionId = Cookie.get('keenSessionId') || keenTracking.helpers.getUniqueId();
        Cookie.set('keenSessionId', currentSessionId, {expires: expDate, path: '/'});
    }

    function _getOrCreateKeenId() {
        if (!Cookie.get('keenUserId')) {
            Cookie.set('keenUserId', keenTracking.helpers.getUniqueId(), {expires: 365, path: '/'});
        }
        return Cookie.get('keenUserId');
    }


    function _defaultKeenPayload() {
        _createOrUpdateKeenSession();

        var user = window.contextVars.currentUser;
        var node = window.contextVars.node;
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
            time: {
                local: keenTracking.helpers.getDatetimeIndex(),
                utc: keenTracking.helpers.getDatetimeIndex(_nowUTC()),
            },
            node: {
                id: lodashGet(node, 'id'),
                title: lodashGet(node, 'title'),
                type: lodashGet(node, 'category'),
                tags: lodashGet(node, 'tags'),
            },
            user: {},
            geo: {},
            anon: {
                id: md5(Cookie.get('keenSessionId')),
                continent: user.anon.continent,
                country: user.anon.country,
                latitude: user.anon.latitude,
                longitude: user.anon.longitude,
            },
            keen: {
                addons: [
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
    }  // end _defaultKeenPayload

    function _trackCustomEvent(client, collection, eventData) {
        if (client === null) {
            return;
        }
        client.recordEvent(collection, eventData, function (err) {
            if (err) {
                Raven.captureMessage('Error sending Keen data to ' + collection + ': <' + err + '>', {
                    extra: {payload: eventData}
                });
            }
        });
    }

    function _trackCustomEvents(client, events) {
        if (client === null) {
            return;
        }
        client.recordEvents(events, function (err, res) {
            if (err) {
                Raven.captureMessage('Error sending Keen data for multiple events: <' + err + '>', {
                    extra: {payload: events}
                });
            } else {
                for (var collection in res) {
                    var results = res[collection];
                    for (var idx in results) {
                        if (!results[idx].success) {
                            Raven.captureMessage('Error sending Keen data to ' + collection + '.', {
                                extra: {payload: events[collection][idx]}
                            });
                        }
                    }
                }
            }
        });
    }

    function KeenTracker() {
        if (instance) {
            throw new Error('Cannot instantiate another KeenTracker instance.');
        } else {
            var self = this;

            self._publicClient = null;
            self._privateClient = null;

            self.init = function _initKeentracker(params) {
                var self = this;

                if (params === undefined) {
                    return self;
                }

                self._publicClient = new keenTracking({
                    projectId: params.public.projectId,
                    writeKey: params.public.writeKey,
                });
                self._publicClient.extendEvents(_defaultPublicKeenPayload);

                self._privateClient = new keenTracking({
                    projectId: params.private.projectId,
                    writeKey: params.private.writeKey,
                });
                self._privateClient.extendEvents(_defaultPrivateKeenPayload);

                return self;
            };

            var _defaultPublicKeenPayload = function() { return _defaultKeenPayload(); };
            var _defaultPrivateKeenPayload = function() {
                var payload = _defaultKeenPayload();
                var user = window.contextVars.currentUser;
                payload.visitor = {
                    id: _getOrCreateKeenId(),
                    session: Cookie.get('keenSessionId'),
                    returning: Boolean(Cookie.get('keenUserId')),
                };
                payload.tech = {
                    browser: keenTracking.helpers.getBrowserProfile(),
                    ua: '${keen.user_agent}',
                    ip: '${keen.ip}',
                    info: {},
                };
                payload.user = {
                    id: user.id,
                    entry_point: user.entryPoint,
                    institutions: user.institutions,
                    locale: user.locale,
                    timezone: user.timezone,
                };
                payload.keen.addons.push({
                    name: 'keen:ip_to_geo',
                    input: {
                        ip: 'tech.ip',
                    },
                    output: 'geo',
                });
                payload.keen.addons.push({
                    name: 'keen:ua_parser',
                    input: {
                        ua_string: 'tech.ua'
                    },
                    output: 'tech.info',
                });

                return payload;
            };

            self.trackPageView = function () {
                var self = this;
                if (window.contextVars.node && window.contextVars.node.isPublic) {
                    self.trackPublicEvent('pageviews', {});
                }
                self.trackPrivateEvent('pageviews', {});
            };

            self.trackPrivateEvent = function(collection, event) {
                return _trackCustomEvent(self._privateClient, collection, event);
            };
            self.trackPrivateEvents = function(events) {
                return _trackCustomEvents(self._privateClient, events);
            };

            self.trackPublicEvent = function(collection, event) {
                return _trackCustomEvent(self._publicClient, collection, event);
            };
            self.trackPublicEvents = function(events) {
                return _trackCustomEvents(self._publicClient, events);
            };
        }
    }

    var instance = null;
    return {
        getInstance: function() {
            if (!instance) {
                instance = new KeenTracker();
                instance.init(window.contextVars.keen);
            }
            return instance;
        }
    };
})();

module.exports = KeenTracker;
