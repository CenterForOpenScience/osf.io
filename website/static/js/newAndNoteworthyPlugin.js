/**
 * New and Noteworthy Projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/quick-project-search-plugin.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var newAndNoteworthy = {
    controller: function() {
        var self = this;
        self.newNodes = m.prop([]);
        self.noteworthyNodes = m.prop([]);
        self.noteworthyContributors = {};

        // Load new nodes
        var newUrl = $osf.apiV2Url('nodes/', { query : { 'embed': 'contributors'}});
        var newPromise = m.request({method: 'GET', url : newUrl, config: xhrconfig});
        newPromise.then(function(result){
            for (var i = 0; i <= 4; i++) {
                self.newNodes().push(result.data[i])
            }
            return newPromise
        });

        var noteworthyUrl = $osf.apiV2Url('nodes/' + window.contextVars.noteworthy + '/node_links/', {});
        var noteworthyPromise = m.request({method: 'GET', url: noteworthyUrl, config: xhrconfig});
        noteworthyPromise.then(function(result){
            for (var l=0; l <= 4; l++) {
                self.noteworthyNodes().push(result.data[l]);
                self.fetchNoteworthyContributors(result.data[l]);
                  }
            return noteworthyPromise
        });

        // Additional API call to fetch node link contributors
        self.fetchNoteworthyContributors = function(nodeLink) {
            url = nodeLink.embeds.target_node.data.relationships.contributors.links.related.href;
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result){
                var firstContrib = result.data[0].embeds.users.data.attributes.full_name;
                var numContrib = result.links.meta.total;
                var nodeId = nodeLink.id;
                self.noteworthyContributors[nodeId] = [firstContrib, numContrib]
            })
        };

        // Gets contrib full name for display
        self.getFullName = function(node) {
            return node.embeds.contributors.data[0].embeds.users.data.attributes.full_name
        };

        // Returns name if one contrib, or adds et al if > 1
        self.contribNameFormat = function(name, number) {
            if (number === 1) {
                    return name
            }
            else {
                return name + ' et al'
            }
        };

        // Formats contrib names for display
        self.getContributors = function (type, node) {
            if (type === 'new') {
                return self.contribNameFormat(self.getFullName(node), node.embeds.contributors.links.meta.total)
            }
            else {
                return self.contribNameFormat(self.noteworthyContributors[node.id][0], self.noteworthyContributors[node.id][1])
            }
        };

        // Grabs title for display
        self.getTitle = function (type, node){
            if (type === 'new') {
                return node.attributes.title
            }
            else {
                return node.embeds.target_node.data.attributes.title

            }
        };

        // Grabs description for display
        self.getDescription = function(type, node){
            if (type === 'new'){
                return node.attributes.description
            }
            else {
                return node.embeds.target_node.data.attributes.description
            }
        };

         // Colors node div and changes cursor to pointer on hover
        self.mouseOver = function (node) {
            node.style.backgroundColor='#E0EBF3';
            node.style.cursor = 'pointer'
        };

        self.mouseOut = function (node) {
            node.style.backgroundColor='#fcfcfc'
        };

         // Onclick, directs user to project page
        self.nodeDirect = function(node) {
            location.href = '/'+ node.id
        };

        self.redirectToSearch = function() {
            location.href = '/search'
        }


    },
    view : function(ctrl) {
        function nodeDisplay(type, node) {
            return m('div', {class: 'row node-styling m-v-md m-r-xs', onmouseover: function(){ctrl.mouseOver(this)}, onmouseout: function(){ctrl.mouseOut(this)}, onclick: function(){{ctrl.nodeDirect(node)}}},
                m('div', {class: 'col-sm-12'},
                    m('h5', m('em', ctrl.getTitle(type, node))),
                    m('h5', ctrl.getDescription(type, node)),
                    m('div', m('h5', {class: 'contributors-bold f-w-xl'}, 'Contributors: '), m('h5', {class: 'contributors-bold'}, ctrl.getContributors(type, node))
                    )
                )
            )
        }

        function newProjectsTemplate () {
            return ctrl.newNodes().map(function(node){
                return nodeDisplay('new', node)
            })

        }
        function noteworthyProjectsTemplate() {
            return ctrl.noteworthyNodes().map(function(node){
                return nodeDisplay('noteworthy', node)
            })

        }

        function findMoreProjectsButton () {
            return m('button', {type:'button', class:'btn btn-default m-v-md', onclick: function(){
                ctrl.redirectToSearch()
            }}, 'Find more projects with advanced search')
        }

        return m('div', {class: 'container'}, [
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-1'}),
                m('div', {class: 'col-sm-11'}, m('h3', 'Discover Public Projects'))),
            m('div', {class: 'row'}, m('div', {class:'col-sm-10 col-sm-offset-1'},
                m('div', {class: 'col-sm-6'}, [m('h4', 'New'), newProjectsTemplate() ]),
                m('div', {class: 'col-sm-6'}, [m('h4', 'Noteworthy', noteworthyProjectsTemplate())])
            )),
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-1'}),
                m('div', {class: 'col-sm-10 text-center'}, findMoreProjectsButton()),
                m('div', {class: 'col-sm-1'})

            )
        ])
    }
};

module.exports = newAndNoteworthy;

