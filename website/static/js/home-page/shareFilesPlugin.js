/**
 * UI and function to quick search projects
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var AddProject = require('js/addProjectPlugin');
var NodeFetcher = require('js/myProjects').NodeFetcher;

// CSS
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var ShareFilesProject = {
    controller: function() {
        var self = this;
        self.nodes = m.prop([]); // Master node list
        self.eligibleNodes = m.prop([]); // Array of indices corresponding to self.nodes() that are eligible to be loaded
        self.countDisplayed = m.prop(); // Max number of nodes that can be rendered.  'Load more' increases this by up to ten.
        self.next = m.prop(); // URL for getting the next ten user nodes. When null, all nodes are loaded.
        self.loadingComplete = m.prop(false); // True when all user nodes are loaded.
        self.contributorMapping = {}; // Maps node id to list of contributors for searching
        self.filter = m.prop(); // Search query from user
        self.fieldSort = m.prop(); // For xs screen, either alpha or date
        self.directionSort = m.prop(); // For xs screen, either Asc or Desc
        self.errorLoading = m.prop(false);  // True if error retrieving projects or contributors.
        self.someDataLoaded = m.prop(false);

        // Adds eligible node indices to array - used when no filter
        self.populateEligibleNodes = function (first, last) {
            for (var n = first; n < last; n++) {
                self.eligibleNodes().push(n);
            }
        };

        // Switches errorLoading to true
        self.requestError = function(result) {
            self.errorLoading(true);
            Raven.captureMessage('Error loading user projects on home page.', {
                extra: {requestReturn: result}
            });
        };

        self.templateNodes = new NodeFetcher('nodes');
        self.templateNodes.start();

        // Load up to share node
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'filter[category]' : 'share window'}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig, background: true});
        console.log(promise);
        promise.then(function(result) {
            self.countDisplayed(result.data.length);
            result.data.forEach(function (node) {
                self.nodes().push(node);
            });
            self.populateEligibleNodes(0, self.countDisplayed());
            //self.next(result.links.next);
            self.someDataLoaded = m.prop(true);
            // NOTE: This manual redraw is necessary because we set background: true on
            // the request, which prevents a redraw. This redraw allows the loading
            // indicator to go away and the first 10 nodes to be rendered
        }, function _error(result){
            self.requestError(result);
            m.redraw();
        });
        promise.then(
            function(){
                    self.loadingComplete(true);
                    m.redraw();
            }, function _error(result){
                self.requestError(result);
            });
        // Formats date for display
        self.formatDate = function (node) {
         return new $osf.FormattableDate(node.attributes.date_modified).local;
        };

    },
    view: function(ctrl) {
      function headerTemplate ( ){
          return m('h2.col-xs-9', 'Shared Files');
      }

      if (ctrl.errorLoading()) {
          return m('p.text-center.m-v-md', 'Error loading projects. Please refresh the page. Contact support@osf.io for further assistance.');
      }

      if (!ctrl.someDataLoaded()) {
          return m('.loader-inner.ball-scale.text-center.m-v-xl', m(''));
      }

      return m('.row',
          m('.col-xs-12', headerTemplate()),
          m('.col-xs-12',[
              m('.row.quick-project', m('.col-xs-12',
              m('.quick-search-table', [
                  m('.row.node-col-headers.m-t-md', [
                      m('.col-sm-4.col-md-5', m('.quick-search-col', 'Title')),
                      m('.col-sm-4.col-md-3', m('.quick-search-col','Modified', m('span.sort-group')))
                  ]),
                  m.component(ShareFilesNodeDisplay, {
                      eligibleNodes: ctrl.eligibleNodes,
                      nodes: ctrl.nodes,
                      countDisplayed: ctrl.countDisplayed,
                      formatDate: function(node) {
                          return ctrl.formatDate(node);
                      },
                      loadingComplete: ctrl.loadingComplete
                  }),
                  !ctrl.loadingComplete() ? m('.loader-inner.ball-scale.text-center', m('')) : m('.m-v-md')
                ])
              ))
          ])
      );
    }
};

var ShareFilesNodeDisplay = {
  view: function(ctrl, args) {
          return m('.', args.eligibleNodes().slice(0, args.countDisplayed()).map(function(n){
              var project = args.nodes()[n];
              return m('a', {href: '/' + project.id, onclick: function() {
                  $osf.trackClick('quickSearch', 'navigate', 'navigate-to-specific-project');
              }}, m('.m-v-sm.node-styling',  m('.row', m('div',
                  [
                      m('.col-sm-4.col-md-5.p-v-xs', m('.quick-search-col',  project.attributes.title)),
                      m('.col-sm-4.col-md-3.p-v-xs', m('.quick-search-col', args.formatDate(project)))
                  ]
              ))));
          }));
  }
};


module.exports = ShareFilesProject;
