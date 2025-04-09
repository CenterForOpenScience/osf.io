'use strict';


var md5 = require('js-md5');
var Cookie = require('js-cookie');
var lodashGet = require('lodash.get');
var $osf = require('js/osfHelpers');

var MetricsTracker = (function() {

    // approach taken from: https://github.com/keen/keen-tracking.js/blob/master/lib/helpers/getUniqueId.js
    // which originally came from: http://stackoverflow.com/a/2117523/2511985
    function getUniqueId() {
        if (typeof window.crypto !== 'undefined' && window.crypto.getRandomValues) {
            return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
              (c ^ window.crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            );
          } else {
            let str = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
            return str.replace(/[xy]/g, function(c) {
              let r = Math.random()*16|0, v = c === 'x' ? r : (r&0x3|0x8);
              return v.toString(16);
            });
          }
    }

    function _createOrUpdateMetricsSession() {
        var expDate = new Date();
        var expiresInMinutes = 25;
        expDate.setTime(expDate.getTime() + (expiresInMinutes * 60 * 1000));
        var currentSessionId = Cookie.get('osfMetricsSessionId') || getUniqueId();
        Cookie.set('osfMetricsSessionId', currentSessionId, {expires: expDate, path: '/'});
        return currentSessionId;
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
        const sessionId = _createOrUpdateMetricsSession();
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

    function MetricsTracker() {
        if (instance) {
            throw new Error('Cannot instantiate another MetricsTracker instance.');
        } else {
            var self = this;

            self.trackPageView = function () {
                _logPageview();
            };

        }
    }

    var instance = null;
    return {
        getInstance: function() {
            if (!instance) {
                instance = new MetricsTracker();
            }
            return instance;
        }
    };
})();

module.exports = MetricsTracker;
