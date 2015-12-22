var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var LogText = require('js/logTextParser');

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');

};

var LogWrap = {
    controller: function(args){
        var self = this;
        self.userId = args.userId;
        self.activityLogs = m.prop();
        self.page = 1;
        self.getLogs = function (userId) {
            var url = $osf.apiV2Url('users/' + userId + '/node_logs/', { query : { 'embed' : ['nodes', 'user', 'linked_node', 'template_node'], 'page':self.page}});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                self.activityLogs(result.data);
                self.lastPage = (result.links.meta.total/result.links.meta.per_page | 0) + 1;
            });
            return promise;
        };
        self.getLogs(self.userId);
    },
    view: function(ctrl, args){
        return m('.fb-activity-list.m-t-md', [
            ctrl.activityLogs() ? ctrl.activityLogs().map(function(item){
                return m('.fb-activity-item', [
                    m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                    m.component(LogText,item)
                ]);
            }) : '',
            ctrl.page > 1 ?m('button', {onclick: function(){
                ctrl.page--;
                ctrl.getLogs(ctrl.userId)
            }}, 'Previous') : '',
            ctrl.lastPage > ctrl.page ? m('button', {onclick: function(){
                ctrl.page++;
                ctrl.getLogs(ctrl.userId)
            }}, 'Next') : '',
        ]);
    }
}


$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {userId: window.contextVars.userId}));
});
