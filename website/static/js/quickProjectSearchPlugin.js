/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var quickSearchProject = {
    controller: function() {
        var self = this;
        self.nodes = [];
        self.getMyNodes = function () {
            var url = $osf.apiV2Url('users/me/nodes/', {});
            var promise = m.request({method: 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                //console.log(result)
                result.data.forEach(function(node){
                    self.nodes.push(node)
                })
            });
            return promise;
        };
        self.getMyNodes()

    },
    view : function(ctrl) {
        console.log(ctrl.nodes);
        return [
            m("h1", 'My nodes'),
            m('p', ctrl.nodes.map(function(n){
               return m('li', n.attributes.title)}))]
    }
};

module.exports = quickSearchProject;

