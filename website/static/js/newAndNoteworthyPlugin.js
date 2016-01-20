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
        self.popularNodes = m.prop([]);
        self.popularContributors = {};

        // Load new and noteworthy nodes
        var newUrl = $osf.apiV2Url('nodes/', { query : { 'embed': 'contributors', 'sort': '-date_created'}});
        var newPromise = m.request({method: 'GET', url : newUrl, config: xhrconfig});
        newPromise.then(function(result){
            for (var i = 0; i <= 4; i++) {
                self.newNodes().push(result.data[i])
            }
            return newPromise
        });

        // Load popular nodes
        var popularUrl = $osf.apiV2Url('nodes/' + window.contextVars.popular + '/node_links/', {});
        var popularPromise = m.request({method: 'GET', url: popularUrl, config: xhrconfig});
        popularPromise.then(function(result){
            var numPopular = Math.min(result.data.length - 1, 4);
            console.log(numPopular);
            for (var l=0; l <= numPopular; l++) {
                self.popularNodes().push(result.data[l]);
                self.fetchPopularContributors(result.data[l]);
                  }
            return popularPromise
        });

        // Additional API call to fetch node link contributors
        self.fetchPopularContributors = function(nodeLink) {
            url = nodeLink.embeds.target_node.data.relationships.contributors.links.related.href;
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result){
                var contribNames = [];
                result.data.forEach(function (contrib){
                    contribNames.push(contrib.embeds.users.data.attributes.family_name)
                });
                var numContrib = result.links.meta.total;
                var nodeId = nodeLink.id;
                self.popularContributors[nodeId] = [contribNames, numContrib]
            })
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node, type) {
            if (type === 'new') {
                return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name
            }
            else {
                return self.popularContributors[node.id][0][i]
            }

        };

        // Returns name if one contrib, or adds et al if > 1
        self.contribNameFormat = function(node, number, type) {
            if (number === 1) {
                return self.getFamilyName(0, node, type)
            }
            else if (number === 2) {
                return self.getFamilyName(0, node, type) + ' and ' +
                    self.getFamilyName(1, node, type)
            }
            else if (number === 3) {
                return self.getFamilyName(0, node, type) + ', ' +
                    self.getFamilyName(1, node, type) + ', and ' +
                    self.getFamilyName(2, node, type)
            }
            else {
                return self.getFamilyName(0, node, type) + ', ' +
                    self.getFamilyName(1, node, type) + ', ' +
                    self.getFamilyName(2, node, type) + ' + ' + (number - 3)
            }
        };

        // Formats contrib names for display
        self.getContributors = function (type, node) {
            if (type === 'new') {
                return self.contribNameFormat(node, node.embeds.contributors.links.meta.total, type)
            }
            else {
                return self.contribNameFormat(node, self.popularContributors[node.id][1], type)
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
        self.nodeDirect = function(type, node) {
            if (type === 'new') {
                location.href = '/'+ node.id
            }
            else {
                location.href = '/' + node.embeds.target_node.data.id
            }
        };

        self.redirectToSearch = function() {
            location.href = '/search'
        }


    },
    view : function(ctrl) {
        function nodeDisplay(type, node) {
            return m('div', {class: 'row node-styling m-v-md m-r-sm', onmouseover: function(){ctrl.mouseOver(this)}, onmouseout: function(){ctrl.mouseOut(this)}, onclick: function(){{ctrl.nodeDirect(type, node)}}},
                m('div', {class: 'col-sm-12'},
                    m('h5', m('em', ctrl.getTitle(type, node))),
                    m('h5', ctrl.getDescription(type, node)),
                    m('div', m('h5', {class: 'contributors-bold f-w-xl'}, 'Contributors: '), m('h5', {class: 'contributors-bold'}, ctrl.getContributors(type, node))
                    )
                )
            )
        }

        function newAndNoteworthyProjectsTemplate () {
            return ctrl.newNodes().map(function(node){
                return nodeDisplay('new', node)
            })

        }
        function popularProjectsTemplate() {
            return ctrl.popularNodes().map(function(node){
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
                m('div', {class: 'col-sm-6'}, [m('h4', 'New and Noteworthy'), newAndNoteworthyProjectsTemplate() ]),
                m('div', {class: 'col-sm-6'}, [m('h4', 'Most Popular', popularProjectsTemplate())])
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

