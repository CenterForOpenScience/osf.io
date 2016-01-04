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
            var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
            var promise = m.request({method: 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                //console.log(result)
                result.data.forEach(function(node){
                    self.nodes.push(node)
                })
            });
            return promise;
        };
        self.getContributors = function (node) {
            var numContributors = node.embeds.contributors.links.meta.total
            if (numContributors === 1) {
                return node.embeds.contributors.data[0].embeds.users.data.attributes.family_name
            }
            else if (numContributors == 2) {
                return node.embeds.contributors.data[0].embeds.users.data.attributes.family_name + ' and ' +
                        node.embeds.contributors.data[1].embeds.users.data.attributes.family_name
            }
            else {
                return node.embeds.contributors.data[0].embeds.users.data.attributes.family_name + ', ' +
                        node.embeds.contributors.data[1].embeds.users.data.attributes.family_name + ', ' +
                        node.embeds.contributors.data[2].embeds.users.data.attributes.family_name + ' and ' +
                    (numContributors - 3) + ' others'
            }

        };
        self.getMyNodes()

    },
    view : function(ctrl) {
        console.log(ctrl.nodes);
        return [
            m("h1", 'My nodes'),
            m('div', 'Name', 'Contributors', 'Modified'),
            m('p', ctrl.nodes.map(function(n){
               return m('div', n.attributes.title, ctrl.getContributors(n),  n.attributes.date_modified)}))]
    }
};

module.exports = quickSearchProject;

