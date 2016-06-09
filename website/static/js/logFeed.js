'use strict';

var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var LogText = require('js/logTextParser');
var mC = require('js/mithrilComponents');


/* Send with ajax calls to work with api2 */
var xhrconfig = function (xhr) {
    xhr.withCredentials = window.contextVars.isOnRootDomain,
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
};

var LogFeed = {

    controller: function(options) {
        var self = this;

        self.node = options.node;
        self.activityLogs = m.prop();
        self.logRequestPending = false;
        self.showMoreActivityLogs = m.prop(null);
        self.logUrlCache = {};

        self.getLogs = function _getLogs (url, addToExistingList) {
            var cachedResults;
            if(!addToExistingList){
                self.activityLogs([]); // Empty logs from other projects while load is happening;
                self.showMoreActivityLogs(null);
            }

            function _processResults (result){
                self.logUrlCache[url] = result;
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                    if(addToExistingList){
                        self.activityLogs().push(log);
                    }
                });
                if(!addToExistingList){
                    self.activityLogs(result.data);  // Set activity log data
                }
                self.showMoreActivityLogs(result.links.next); // Set view for show more button
            }

            if(self.logUrlCache[url]){
                cachedResults = self.logUrlCache[url];
                _processResults(cachedResults);
            } else {
                self.logRequestPending = true;
                var promise = m.request({method : 'GET', url : url, config : xhrconfig});
                promise.then(_processResults);
                promise.then(function(){
                    self.logRequestPending = false;
                });
                return promise;
            }

        };

        self.getCurrentLogs = function _getCurrentLogs (node){
            if(!self.logRequestPending) {
                if (!node.is_retracted) {
                    var urlPrefix = node.is_registration ? 'registrations' : 'nodes';
                    var query = node.link ? { 'page[size]': 6, 'embed': ['original_node', 'user', 'linked_node', 'template_node'], 'view_only': node.link} : { 'page[size]': 6, 'embed': ['original_node', 'user', 'linked_node', 'template_node']};
                    var url = $osf.apiV2Url(urlPrefix + '/' + node.id + '/logs/', { query: query});
                    var promise = self.getLogs(url);
                    return promise;
                }
            }
        };

        self.getCurrentLogs(self.node);
    },

    view : function (ctrl) {

        return m('.db-activity-list.m-t-md', [
            ctrl.activityLogs() ? ctrl.activityLogs().map(function(item){
                if (ctrl.node.anonymous) { item.anonymous = true; }
                var image = m('i.fa.fa-desktop');
                if (!item.anonymous && item.embeds.user && item.embeds.user.data) {
                    image = m('img', { src : item.embeds.user.data.links.profile_image});
                } else if (!item.anonymous && item.embeds.user && item.embeds.user.errors[0].meta){
                    image = m('img', { src : item.embeds.user.errors[0].meta.profile_image});
                }
                return m('.db-activity-item', [
                m('', [ m('.db-log-avatar.m-r-xs', image),
                    m.component(LogText, item)]),
                m('.text-right', m('span.text-muted.m-r-xs', item.attributes.formattableDate.local))]);

            }) : '',
            m('.db-activity-nav.text-center', [
                ctrl.showMoreActivityLogs() ? m('.btn.btn-sm.btn-link', { onclick: function(){
                    ctrl.getLogs(ctrl.showMoreActivityLogs(), true);
                    $osf.trackClick('myProjects', 'information-panel', 'show-more-activity');
                }}, [ 'Show more', m('i.fa.fa-caret-down.m-l-xs')]) : ''
            ])
        ]);
    }
};

module.exports = {
    LogFeed: LogFeed
};
