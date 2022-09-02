'use strict';


var $ = require('jquery');
var md5 = require('js-md5');
var Raven = require('raven-js');
var Cookie = require('js-cookie');
var lodashGet = require('lodash.get');
var keenTracking = require('keen-tracking');
var $osf = require('js/osfHelpers');

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
        return currentSessionId;
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
        var pageMeta = lodashGet(window, 'contextVars.analyticsMeta.pageMeta', {});
        return {
            page: {
                title: document.title,
                url: document.URL,
                meta: pageMeta,
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
            anon: {
                id: md5(Cookie.get('keenSessionId')),
                continent: user.anon.continent,
                country: user.anon.country,
            },
            meta: {
                epoch: 1, // version of pageview event schema
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
                // If google analytics is inaccessible keen will throw errors
                var adBlockError = document.getElementsByTagName('iframe').item(0) === null;
                var uselessError = 'An error occurred!' === err;
                if(!adBlockError || !uselessError) {
                    Raven.captureMessage('Error sending Keen data to ' + collection + ': <' + err + '>', {
                        extra: {payload: eventData}
                    });
                }
            }
        });
    }

    function _pageIsPublic() {
        return Boolean(
            lodashGet(window, 'contextVars.node.isPublic', false) &&
            lodashGet(window, 'contextVars.analyticsMeta.pageMeta.public', false)
        );
    }

    function _getActionLabels() {
        const actionLabelMap = {
            'web': true,
            'view': Boolean(lodashGet(window, 'contextVars.analyticsMeta.itemGuid')),
            'search': Boolean(lodashGet(window, 'contextVars.analyticsMeta.searchProviderId')),
        };
        return (
            Object.keys(actionLabelMap)
            .filter(label => Boolean(actionLabelMap[label]))
        );
    }

    function _logPageview() {
        const url = new URL('/_/metrics/events/counted_usage/', window.contextVars.apiV2Domain);
        const sessionId = _createOrUpdateKeenSession();
        const data = {
            type: 'counted-usage',
            attributes: {
                client_session_id: sessionId ? md5(sessionId) : null,
                provider_id: lodashGet(window, 'contextVars.analyticsMeta.searchProviderId'),
                item_guid: lodashGet(window, 'contextVars.analyticsMeta.itemGuid'),
                item_public: _pageIsPublic(),
                action_labels: _getActionLabels(),
                pageview_info: {
                    referer_url: document.referrer,
                    page_url: document.URL,
                    page_title: document.title,
                    route_name: lodashGet(window, 'contextVars.analyticsMeta.pageMeta.routeName'),
                },
            },
        };

        $osf.ajaxJSON('POST', url.toString(), {
            isCors: true,
            data: {data},
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
                        remove_ip_property: true
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
                _logPageview();

                var self = this;
                var guid;
                if (_pageIsPublic()) {
                    guid = lodashGet(window, 'contextVars.node.id', null);
                    if (guid) {
                        var partitioned_collection = 'pageviews-' + guid.charAt(0);
                        self.trackPublicEvent(partitioned_collection, {});
                    }
                }
                self.trackPrivateEvent('pageviews', {});
            };

            self.trackPrivateEvent = function(collection, event) {
                return _trackCustomEvent(self._privateClient, collection, event);
            };

            self.trackPublicEvent = function(collection, event) {
                return _trackCustomEvent(self._publicClient, collection, event);
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
