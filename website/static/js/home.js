var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var LogText = require('js/logTextParser');

var recentActivity = {
    view : function (ctrl, args) {
        return m('.fb-activity-list.m-t-md', [
            args.activityLogs() ? args.activityLogs().map(function(item){
                return m('.fb-activity-item', [
                    m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                    m.component(LogText,item)
                ]);
            }) : ''
        ]);
    }
};

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');

};

var LogWrap = {
    controller: function(args){
        var self = this;
        self.activityLogs = m.prop();
        self.getLogs = function (userId) {
            var url = $osf.apiV2Url('users/' + userId + '/node_logs/', { query : { 'embed' : ['nodes', 'user', 'linked_node', 'template_node']}});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                self.activityLogs(result.data);
            });
            return promise;
        };
        self.getLogs('ywmp6');
    },
    view: function(ctrl, args){
        return m('.heyoDiv', m.component(recentActivity, { activityLogs : ctrl.activityLogs } ));
    }
}


$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap));
});
