/**
 * Builds full page project browser
 */
'use strict';

var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/project-organizer');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var LogText = require('js/logTextParser');
var AddProject = require('js/addProjectPlugin');
var mC = require('js/mithrilComponents');

var MOBILE_WIDTH = 767; // Mobile view break point for responsiveness
var NODE_PAGE_SIZE = 10; // Load 10 nodes at a time from server

/* Counter for unique ids for link objects */
if (!window.fileBrowserCounter) {
    window.fileBrowserCounter = 0;
}

//Backport of Set
if (!window.Set) {
  window.Set = function Set(initial) {
    this.data = {};
    initial = initial || [];
    for(var i = 0; i < initial.length; i++)
      this.add(initial[i]);
  };

  Set.prototype = {
    has: function(item) {
      return this.data[item] === true;
    },
    clear: function() {
      this.data = {};
    },
    add:function(item) {
      this.data[item] = true;
    },
    delete: function(item) {
      delete this.data[item];
    }
  };
}

function getUID() {
    window.fileBrowserCounter = window.fileBrowserCounter + 1;
    return window.fileBrowserCounter;
}

/* Send with ajax calls to work with api2 */
var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
};

/* Adjust item data for treebeard to be able to filter tags and contributors not in the view */
function _formatDataforPO(item) {
    item.kind = 'folder';
    item.uid = item.id;
    item.name = item.attributes.title;
    item.tags = item.attributes.tags.toString();
    item.contributors = '';
    if (item.embeds.contributors.data){
        item.embeds.contributors.data.forEach(function(c){
            var attr;
            if (c.embeds.users.data) {
                attr = c.embeds.users.data.attributes;
            }
            else {
                attr = c.embeds.users.errors[0].meta;
            }
            item.contributors += attr.full_name + ' ' + attr.middle_names + ' ' + attr.given_name + ' ' + attr.family_name + ' ' ;

        });
    }
    item.date = new $osf.FormattableDate(item.attributes.date_modified);
    return item;
}

/* Small constructor for creating same type of links */
var LinkObject = function _LinkObject (type, data, label, institutionId) {
    if (type === undefined || data === undefined || label === undefined) {
        throw new Error('LinkObject expects type, data and label to be defined.');
    }
    var self = this;
    self.id = getUID();
    self.type = type;
    self.data = data;
    self.label = label;
};

/**
 * Returns the object to send to the API to send a node_link to collection
 * @param id {String} unique id of the node like 'ez8f3'
 * @returns {{data: {type: string, relationships: {nodes: {data: {type: string, id: *}}}}}}
 */
function buildCollectionNodeData (id) {
    return {
        'data' : {
            'type': 'node_links',
            'relationships': {
                'nodes': {
                    'data': {
                        'type': 'nodes',
                        'id': id
                    }
                }
            }
        }
    };
}

/**
 * Initialize File Browser. Prepares an option object within FileBrowser
 * @constructor
 */
var MyProjects = {
    controller : function (options) {
        var self = this;
        self.wrapperSelector = options.wrapperSelector;  // For encapsulating each implementation of this component in multiple use
        self.projectOrganizerOptions = options.projectOrganizerOptions || {};
        self.viewOnly = options.viewOnly || false;
        self.institutionId = options.institutionId || false;
        self.reload = m.prop(false); // Gets set to true when treebeard link changes and it needs to be redrawn
        self.logUrlCache = {}; // dictionary of load urls to avoid multiple calls with little refactor
        self.nodeUrlCache = {}; // Cached returns of the project related urls
        // VIEW STATES
        self.showInfo = m.prop(true); // Show the info panel
        self.showSidebar = m.prop(false); // Show the links with collections etc. used in narrow views
        self.allProjectsLoaded = m.prop(false);
        self.loadingAllNodes = false; // True if we are loading all nodes
        self.loadingNodePages = false;
        self.categoryList = [];
        self.loadValue = m.prop(0); // What percentage of the project loading is done
        //self.loadCounter = m.prop(0); // Count how many items are received from the server
        self.currentView = m.prop({
            collection : null, // Linkobject
            contributor : [],
            tag : [],
            totalRows: 0
        });
        self.filesData = m.prop();
        self.indexes = m.prop({}); // Container of tree indexes for the items

        // Treebeard functions looped through project organizer.
        // We need to pass these in to avoid reinstantiating treebeard but instead repurpose (update) the top level folder
        self.treeData = m.prop({}); // Top level object that houses all the rows
        self.buildTree = m.prop(null); // Preprocess function that adds to each item TB specific attributes
        self.updateFolder = m.prop(null); // Updates view to redraw without messing up scroll location
        self.projectsForTemplates = m.prop([]);

        // Add All my Projects and All my registrations to collections
        self.systemCollections = options.systemCollections || [
                new LinkObject('collection', { nodeType : 'projects'}, 'All my projects'),
                new LinkObject('collection', { nodeType : 'registrations'}, 'All my registrations')
            ];

        self.nodes = {};
        ['projects', 'registrations'].forEach(function(item){
            self.nodes[item] = {
                flatData : {
                    data : [],
                    loaded : 0,
                    total : 0,
                    firstLink : '',
                    nextLink : '',
                },
                treeData : {
                    data : [],
                    loaded : 0,
                    total : 0,
                    firstLink : '',
                    nextLink : ''
                },
                loadMode : 'load', // Can be load, pause, or done load will continue loading next, pause will pause loading next, done is when everything is loaded.
            };
        });
        self.nodes.projects.flatData.firstLink = $osf.apiV2Url('users/me/nodes/', { query : { 'related_counts' : 'children', 'embed' : 'contributors' }});
        self.nodes.registrations.flatData.firstLink = $osf.apiV2Url('users/me/registrations/', { query : { 'related_counts' : 'children', 'embed' : 'contributors' }});
        self.nodes.projects.treeData.firstLink = $osf.apiV2Url('users/me/nodes/', { query : { 'related_counts' : 'children', 'embed' : 'contributors', 'filter[parent]' : 'null' }});
        self.nodes.registrations.treeData.firstLink = $osf.apiV2Url('users/me/registrations/', { query : { 'related_counts' : 'children', 'embed' : 'contributors', 'filter[parent]' : 'null' }});


        self.loadNodes = function (nodeType, dataType){
            var nodeObject = self.nodes[nodeType];
            var typeObject = nodeObject[dataType];
            var url = typeObject.loaded === 0 ? typeObject.firstLink : typeObject.nextLink;
            if(url){
                var promise = m.request({method : 'GET', url : url, config : xhrconfig, background: true});
                promise.then(success, error);
            }
            function success (result) {
                m.redraw(true);
                typeObject.data = typeObject.data.concat(result.data);
                typeObject.loaded += result.data.length;
                typeObject.total = result.links.meta.total;
                typeObject.nextLink = result.links.next;
                if(self.currentView().collection.data.nodeType === nodeType && dataType === 'treeData') {
                    self.loadValue(typeObject.loaded / typeObject.total * 100);
                    if(self.breadcrumbs().length === 1){
                        self.updateList();
                    }
                }
                if(nodeType === 'projects' && dataType === 'flatData' && typeObject.loaded === typeObject.total ){
                    self.generateFiltersList();
                }
                if(nodeType === 'projects' && dataType === 'flatData'){
                    self.projectsForTemplates(self.nodes.projects.flatData.data);
                }

                if(typeObject.nextLink){
                    self.loadNodes(nodeType, dataType);
                }
                if(dataType === 'flatData' && !typeObject.nextLink && typeObject.loaded === typeObject.total){
                    nodeObject.loadMode = 'done';
                    nodeObject.treeData.data = self.makeTree(nodeObject.flatData.data, null, self.indexes);
                }
            }
            function error (result){
                var message = 'Error loading nodes with nodeType ' + nodeType + ' and dataType ' + dataType;
                Raven.captureMessage(message, {requestReturn: result});
            }
        };


        // Initial Breadcrumb for All my projects
        var initialBreadcrumbs = options.initialBreadcrumbs || [new LinkObject('collection', { nodeType : 'projects'}, 'All my projects')];
        self.breadcrumbs = m.prop(initialBreadcrumbs);
        // Calculate name filters
        self.nameFilters = [];
        // Calculate tag filters
        self.tagFilters = [];


        // Load categories to pass in to create project
        self.loadCategories = function _loadCategories () {
            var promise = m.request({method : 'OPTIONS', url : $osf.apiV2Url('nodes/', { query : {}}), config : xhrconfig});
            promise.then(function _success(results){
                if(results.actions && results.actions.POST.category){
                    self.categoryList = results.actions.POST.category.choices;
                    self.categoryList.sort(function(a, b){ // Quick alphabetical sorting
                        if(a.value < b.value) return -1;
                        if(a.value > b.value) return 1;
                        return 0;
                    });
                }
            }, function _error(results){
                var message = 'Error loading project category names.';
                Raven.captureMessage(message, {requestReturn: results});
            });
            return promise;
        };

        /**
         * Turn flat node array into a hierarchical structure
         * @param flatData {Array} List of items returned from survey
         * @param [lastcrumb] {Object} Right most selected breadcrumb linkobject
         * @param [indexes] {Object} Object to save the tree index structure for quick find
         * @returns {Array} A new list with hierarchical structure
         */
        self.makeTree = function _makeTree(flatData, lastcrumb, indexes) {
            var root = {id:0, children: [], data : {} };
            var node_list = { 0 : root};
            var parentID;
            var crumbParent = lastcrumb ? lastcrumb.data.id : null;
            for (var i = 0; i < flatData.length; i++) {
                if(flatData[i].errors){
                    continue;
                }
                var n = _formatDataforPO(flatData[i]);
                if (!node_list[n.id]) { // If this node is not in the object list, add it
                    node_list[n.id] = n;
                    node_list[n.id].children = [];
                } else { // If this node is in object list it's likely because it was created as a parent so fill out the rest of the information
                    n.children = node_list[n.id].children;
                    node_list[n.id] = n;
                }

                if (n.relationships.parent){
                    parentID = n.relationships.parent.links.related.href.split('/')[5]; // Find where parent id string can be extracted
                } else {
                    parentID = null;
                }
                if(parentID && parentID !== crumbParent ) {
                    if(!node_list[parentID]){
                        node_list[parentID] = { children : [] };
                    }
                    node_list[parentID].children.push(node_list[n.id]);
                } else {
                    node_list[0].children.push(node_list[n.id]);
                }
            }
            indexes(node_list);
            return root.children;
        };

        // Activity Logs
        self.activityLogs = m.prop();
        self.logRequestPending = false;
        self.showMoreActivityLogs = m.prop(null);
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
        // separate concerns, wrap getlogs here to get logs for the selected item
        self.getCurrentLogs = function _getCurrentLogs ( ){
            if(self.selected().length === 1 && !self.logRequestPending){
                var item = self.selected()[0];
                var id = item.data.id;
                if(!item.data.attributes.retracted){
                    var urlPrefix = item.data.attributes.registration ? 'registrations' : 'nodes';
                    var url = $osf.apiV2Url(urlPrefix + '/' + id + '/logs/', { query : { 'page[size]' : 6, 'embed' : ['nodes', 'user', 'linked_node', 'template_node', 'contributors']}});
                    var promise = self.getLogs(url);
                    return promise;
                }
            }
        };

        /* filesData is the link that loads tree data. This function refreshes that information. */
        self.updateFilesData = function _updateFilesData (linkObject, itemId) {
            if ((linkObject.type === 'node') && self.viewOnly){
                return;
            }
            self.updateFilter(linkObject);
            self.updateBreadcrumbs(linkObject);
            if(linkObject.data.nodeType === 'collection'){
                self.updateList(false, null, linkObject);
            } else {
                self.updateList(true, itemId); // Reset and load item
            }
            self.showSidebar(false);
        };

        // INFORMATION PANEL
        /* Defines the current selected item so appropriate information can be shown */
        self.selected = m.prop([]);
        self.updateSelected = function _updateSelected (selectedList){
            self.selected(selectedList);
            self.getCurrentLogs();
        };

        /**
         * Update the currentView
         * @param filter
         */
        self.updateFilter = function _updateFilter (filter) {
            var filterIndex;
            // if collection, reset currentView otherwise toggle the item in the list of currentview items
            if(filter.type === 'node'){
                self.currentView().contributor = [];
                self.currentView().tag = [];
                return;
            }
            if(filter.type === 'collection'){
                self.currentView().collection = filter;
                self.currentView().contributor = [];
                self.currentView().tag = [];
                self.generateFiltersList();
            } else {
                filterIndex = self.currentView()[filter.type].indexOf(filter);
                if(filterIndex !== -1){ // if filter already in
                    self.currentView()[filter.type].splice(filterIndex,1);
                } else {
                    self.currentView()[filter.type].push(filter);
                }
            }
        };

        self.removeProjectFromCollections = function _removeProjectFromCollection () {
            // Removes selected items from collect
            var currentCollection = self.currentView().collection;
            var collectionNode = currentCollection.data.node; // If it's not a system collection like projects or registrations this will have a node
            var data = {
                data : []
            };

            self.selected().forEach(function _removeProjectFromCollectionsMap (item){
                var obj = {
                    'type' : 'linked_nodes',
                    'id' : item.data.id
                };
                data.data.push(obj);
            });
            m.request({
                method : 'DELETE',
                url : collectionNode.links.self + 'relationships/' + 'linked_nodes/',  //collection.links.self + 'node_links/' + item.data.id + '/', //collection.links.self + relationship/ + linked_nodes/
                config : xhrconfig,
                data : data
            }).then(function _removeProjectFromCollectionsSuccess(result){
                var linkedNodesUrl = $osf.apiV2Url(currentCollection.data.path, { query : currentCollection.data.query});
                self.nodeUrlCache[linkedNodesUrl] = null;
                currentCollection.data.count(currentCollection.data.count() - data.data.length);
                self.updateList(false, null, currentCollection);
            }, function _removeProjectFromCollectionsFail(result){
                var message = 'Some projects';
                if(data.data.length === 1) {
                    message = self.selected()[0].data.name;
                } else {
                    message += ' could not be removed from the collection';
                }
                $osf.growl(message, 'Please try again.', 'danger', 5000);
            });
        };

        // remove this contributor from list of contributors
        self.unselectContributor = function (id){
            self.currentView().contributor.forEach(function (c, index, arr) {
                if(c.data.id === id){
                    arr.splice(index, 1);
                    self.updateList();
                }
            });
        };

        self.unselectTag = function (tag){
            self.currentView().tag.forEach(function (c, index, arr) {
                if(c.data.tag === tag){
                    arr.splice(index, 1);
                    self.updateList();
                }
            });
        };

        // Update what is viewed
        self.updateList = function _updateList (reset, itemId, collectionObject){
            function collectionUpdateActions (collectionData) {
                self.nodes[self.currentView().collection.data.node.id] = collectionData;
                self.generateFiltersList(collectionData);
                self.currentView().totalRows = collectionData.length;
            }
            function collectionSuccess (result){
                var displayError = false;
                if(result.data.length === 0 ){
                    collectionUpdateActions(collectionData);
                }
                result.data.forEach(function(node, index){
                    var indexedNode = self.indexes()[node.id];
                    if(indexedNode){
                        self.loadValue(++collectionObject.data.loaded / collectionObject.data.count() * 100);
                        collectionData.push(indexedNode);
                        // Update node information here too
                        if(index === result.data.length - 1){
                            collectionUpdateActions(collectionData);
                        }
                    } else {
                        var url = $osf.apiV2Url('nodes/' + node.id + '/', { query : { 'related_counts' : 'children', 'embed' : 'contributors' }});
                        m.request({method : 'GET', url : url, config : xhrconfig, background: true}).then(function(r){
                            self.generateSets(r.data);
                            collectionData.push(r.data);
                            self.indexes()[node.id] = r.data;
                            if(index === result.data.length - 1 && displayError){
                                $osf.growl(' Some projects for this collection could not be loaded', 'Please try again later.', 'warning', 5000);
                            }
                            // Update node information
                            if(index === result.data.length - 1){
                                collectionUpdateActions(collectionData);
                            }

                            self.loadValue(++collectionObject.data.loaded / collectionObject.data.count() * 100);
                            updateTreeData(0, collectionData, true);
                        }, function(r){
                            var message = 'Error loading node not belonging to user for collections with node id  ' + node.id;
                            displayError = true;
                            Raven.captureMessage(message, {requestReturn: r});
                            if(index === result.data.length -1 && displayError){
                                $osf.growl(' Some projects for this collection could not be loaded', 'Please try again later.', 'warning', 5000);
                            }
                        });
                    }
                });

                updateTreeData(0, collectionData, true);
            }

            if(collectionObject){ // A regular collection including bookmarks
                self.loadValue(collectionObject.data.loaded / collectionObject.data.count() * 100);

                var collectionData = [];
                var linkedNodesUrl = $osf.apiV2Url(collectionObject.data.path, { query : collectionObject.data.query});
                if(self.nodeUrlCache[linkedNodesUrl]){
                    collectionSuccess(self.nodeUrlCache[linkedNodesUrl]);
                } else {
                    m.request({method : 'GET', url : linkedNodesUrl, config : xhrconfig, background: true}).then(function(result){
                        self.nodeUrlCache[linkedNodesUrl] = result;
                        collectionSuccess(result);
                    }, function(result){
                        var message = 'Error loading nodes from collection id  ' + collectionObject.data.node.id;
                        Raven.captureMessage(message, {requestReturn: result});
                        $osf.growl(' "' + collectionObject.data.node.attributes.title + '" contents couldn\'t load', 'Please try again later.');
                    });
                }

                return;
            }

            if(itemId) { // A project has been selected. Move context to it.
                var processChildren = function (data) {
                    self.currentView().contributor = [];
                    self.currentView().tag = [];
                    self.currentView().totalRows = data.length;
                    updateTreeData(0, data, true);
                };
                if(!self.indexes()[itemId]){
                    var type = self.currentView().collection.data.nodeType === 'registrations' ? 'registrations' : 'nodes';
                    var itemUrl = $osf.apiV2Url(type + '/' + itemId + '/children/', { query : { 'related_counts' : 'children', 'embed' : 'contributors' }});
                    m.request({method : 'GET', url : itemUrl, config : xhrconfig}).then(function(result){
                        console.log(result);
                        processChildren(result.data);
                    }, function(result){
                        var message = 'Error loading node children from server for node  ' + itemId;
                        Raven.captureMessage(message, {requestReturn: result});
                        $osf.growl('Project or subcomponent details couldn\'t load', 'Please try again later.', 'warning', 5000);
                    });
                } else {
                    processChildren(self.indexes()[itemId].children);
                }
                return;
            }

            // Reset the progress bar
            var progress = self.nodes[self.currentView().collection.data.nodeType].treeData;
            if (progress) self.loadValue(progress.loaded / progress.total * 100);

            var hasFilters = self.currentView().contributor.length || self.currentView().tag.length;
            var nodeType = self.currentView().collection.data.nodeType;
            var nodeObject = self.nodes[nodeType] === 'collection' ? self.nodes[self.currentView().collection.data.node.id] : self.nodes[nodeType];
            var item;
            var viewData = [];

            var nodeData = nodeObject ? nodeObject.treeData.data : self.nodes[self.currentView().collection.data.node.id];

            if(!hasFilters && nodeObject){
                var begin;
                if((nodeObject.treeData.loaded > 0 || nodeObject.loadMode === 'done') && self.treeData().data) {
                    if(reset || nodeObject.treeData.loaded <= NODE_PAGE_SIZE){
                        begin = 0;
                        self.treeData().children = [];
                    } else {
                        begin = self.treeData().children.length;
                    }
                    updateTreeData(begin, nodeData);
                    self.currentView().totalRows = nodeObject.loaded;
                }
                self.generateFiltersList(nodeData);
                self.currentView().totalRows = nodeData.length;
                return;
            }

            var tags = self.currentView().tag;
            var contributors = self.currentView().contributor;

            viewData = nodeData.filter(function(node) {
              var tagMatch = tags.length === 0;
              var contribMatch = contributors.length === 0;

              for (var i = 0; i < contributors.length; i++)
                if (node.contributorSet.has(contributors[i].data.id)) {
                  contribMatch = true;
                  break;
                }

              for (var j = 0; j < tags.length; j++)
                if (node.tagSet.has(tags[j].label)) {
                  tagMatch = true;
                  break;
                }

              return tagMatch && contribMatch;
            });

            updateTreeData(0, viewData, true);
            self.currentView().totalRows = viewData.length;

            function updateTreeData (begin, data, clear) {
                if (clear)
                  self.treeData().children = [];

                for (var i = begin; i < data.length; i++){
                    item = data[i];
                    if (!(item.attributes.retracted === true || item.attributes.pending_registration_approval === true)){
                        // Filter Retractions and Pending Registrations from the "All my registrations" view.
                        _formatDataforPO(item);
                        var child = self.buildTree()(item, self.treeData());
                        self.treeData().add(child);
                    }
                }
                self.selected([]);
                self.updateFolder()(null, self.treeData());
                if(self.treeData().children[0]){
                    $('.tb-row').first().trigger('click');
                }
            }

        };

        self.generateSets = function (item){
            item.tagSet = new Set(item.attributes.tags || []);

            var contributors = item.embeds.contributors.data || [];
            item.contributorSet= new Set(contributors.map(function(contrib) {
              return contrib.id;
            }));
        };

        self.nonLoadTemplate = function (){
            var template = '';
            if(self.currentView().totalRows !== 0 ){
                return;
            }
            var lastcrumb = self.breadcrumbs()[self.breadcrumbs().length-1];
            var hasFilters = self.currentView().contributor.length || self.currentView().tag.length;
            if(hasFilters){
                template = m('.db-non-load-template.m-md.p-md.osf-box', 'No projects match this filter.');
            } else {
                if(lastcrumb.type === 'collection'){
                    if(lastcrumb.data.nodeType === 'projects'){
                        template = m('.db-non-load-template.m-md.p-md.osf-box',
                            'You have not created any projects yet.');
                    } else if (lastcrumb.data.nodeType === 'registrations'){
                        template = m('.db-non-load-template.m-md.p-md.osf-box',
                            'You have not made any registrations yet.');
                    } else {
                        template = m('.db-non-load-template.m-md.p-md.osf-box',
                            'This collection is empty. To add projects or registrations, click "All my projects" or "All my registrations" in the sidebar, and then drag and drop items into the collection link.');
                    }
                } else {
                    if(self.nodes.projects.loadMode !== 'done' && self.nodes.registrations.loadMode !== 'done'){
                        template = m('.db-non-load-template.m-md.p-md.osf-box.text-center',
                            m('.ball-scale.text-center', m(''))
                        );
                    } else {
                        template = m('.db-non-load-template.m-md.p-md.osf-box.text-center', [
                            'This project either has no components or you do not have permission to view them.'
                        ]);
                    }
                }
            }


            return template;
        };

        /**
         * Generate this list from user's projects
         */
        self.generateFiltersList = function _generateFilterList (nodeList) {
            self.users = {};
            self.tags = {};
            var data = nodeList || self.nodes.projects.flatData.data;
            data.map(function _generateFiltersListMap(item){
                var contributors = item.embeds.contributors.data || [];
                self.generateSets(item);
                for(var i = 0; i < contributors.length; i++) {
                    var u = contributors[i];
                    if (u.id === window.contextVars.currentUser.id) {
                        continue;
                    }
                    if(self.users[u.id] === undefined) {
                        self.users[u.id] = {
                            data : u,
                            count: 1
                        };
                    } else {
                        self.users[u.id].count++;
                    }
                }
                var tags = item.attributes.tags || [];
                for(var j = 0; j < tags.length; j++) {
                    var t = tags[j];
                    if(self.tags[t] === undefined) {
                        self.tags[t] = 1;
                    } else {
                        self.tags[t]++;
                    }
                }
            });

            // Sorting by number of items utility function
            function sortByCountDesc (a,b){
                var aValue = a.data.count;
                var bValue = b.data.count;
                if (bValue > aValue) {
                    return 1;
                }
                if (bValue < aValue) {
                    return -1;
                }
                return 0;
            }

            // Add to lists with numbers
            self.nameFilters = [];
            for (var user in self.users){
                var u2 = self.users[user];
                if (u2.data.embeds.users.data) {
                    self.nameFilters.push(new LinkObject('contributor', { id : u2.data.id, count : u2.count, query : { 'related_counts' : 'children' }}, u2.data.embeds.users.data.attributes.full_name, options.institutionId || false));
                }
            }
            // order names
            self.nameFilters.sort(sortByCountDesc);

            self.tagFilters = [];
            for (var tag in self.tags){
                var t2 = self.tags[tag];
                self.tagFilters.push(new LinkObject('tag', { tag : tag, count : t2, query : { 'related_counts' : 'children' }}, tag, options.institutionId || false));
            }
            // order tags
            self.tagFilters.sort(sortByCountDesc);
            m.redraw(true);
        };

        // BREADCRUMBS
        self.updateBreadcrumbs = function _updateBreadcrumbs (linkObject){
            if (linkObject.type === 'collection'){
                self.breadcrumbs([linkObject]);
                return;
            }
            if (linkObject.type === 'contributor' || linkObject.type === 'tag'){
                return;
            }
            if (linkObject.placement === 'breadcrumb'){
                self.breadcrumbs().splice(linkObject.index+1, self.breadcrumbs().length-linkObject.index-1);
                return;
            }
            if(linkObject.ancestors && linkObject.ancestors.length > 0){
                linkObject.ancestors.forEach(function(item){
                    var ancestorLink = new LinkObject('node', item.data, item.data.name);
                    self.breadcrumbs().push(ancestorLink);
                });
            }
            self.breadcrumbs().push(linkObject);
        };

        // GET COLLECTIONS
        // Default system collections
        self.collections = m.prop([].concat(self.systemCollections));
        self.collectionsPageSize = m.prop(5);
        // Load collection list
        self.loadCollections = function _loadCollections (url){
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.forEach(function(node){
                    var count = node.relationships.linked_nodes.links.related.meta.count;
                    self.collections().push(new LinkObject('collection', { path : 'collections/' + node.id + '/relationships/linked_nodes/', query : { 'related_counts' : 'children', 'embed' : 'contributors' }, nodeType : 'collection', node : node, count : m.prop(count), loaded: 1 }, node.attributes.title));
                });
                if(result.links.next){
                    self.loadCollections(result.links.next);
                }
            }, function(){
                var message = 'Collections could not be loaded.';
                $osf.growl(message, 'Please reload the page.');
                Raven.captureMessage(message, { url: url });
            });
            return promise;
        };

        self.sidebarInit = function _sidebarInit (element, isInit) {
            $('[data-toggle="tooltip"]').tooltip();
        };

        // Resets UI to show All my projects and update states
        self.resetUi = function _resetUi(){
            var linkObject = self.systemCollections[0];
            self.updateBreadcrumbs(linkObject);
            self.updateFilter(linkObject);
        };

        self.init = function _init_fileBrowser() {
            self.currentView().collection = self.systemCollections[0]; // Add linkObject to the currentView
            self.loadCategories().then(function(){
                // start loading nodes at the same time
                self.loadNodes('projects', 'treeData');
                self.loadNodes('registrations', 'treeData');
                self.loadNodes('projects', 'flatData');
                self.loadNodes('registrations', 'flatData');
            });
            var collectionsUrl = $osf.apiV2Url('collections/', { query : {'related_counts' : 'linked_nodes', 'page[size]' : self.collectionsPageSize(), 'sort' : 'date_created', 'embed' : 'node_links'}});
            if (!self.viewOnly){
                self.loadCollections(collectionsUrl);
            }
            self.updateFilter(self.collections()[0]);
        };

        self.init();
    },
    view : function (ctrl, args) {
        var mobile = window.innerWidth < MOBILE_WIDTH; // true if mobile view
        var infoPanel = '';
        var poStyle = 'width : 72%'; // Other percentages are set in CSS in file-browser.css These are here because they change
        var sidebarButtonClass = 'btn-default';
        if (ctrl.showInfo() && !mobile){
            infoPanel = m('.db-infobar', m.component(Information, ctrl));
            poStyle = 'width : 47%; display: block';
        }
        if(ctrl.showSidebar()){
            sidebarButtonClass = 'btn-primary';
        }
        if (mobile) {
            poStyle = 'width : 100%; display: block';
            if(ctrl.showSidebar()){
                poStyle = 'display: none';
            }
        } else {
            ctrl.showSidebar(true);
        }
        var projectOrganizerOptions = $.extend(
            {}, {
                filesData : [],
                updateSelected : ctrl.updateSelected,
                updateFilesData : ctrl.updateFilesData,
                LinkObject : LinkObject,
                formatDataforPO : _formatDataforPO,
                wrapperSelector : args.wrapperSelector,
                reload : ctrl.reload,
                resetUi : ctrl.resetUi,
                showSidebar : ctrl.showSidebar,
                loadValue : ctrl.loadValue,
                loadCounter : ctrl.loadCounter,
                treeData : ctrl.treeData,
                buildTree : ctrl.buildTree,
                updateFolder : ctrl.updateFolder,
                currentView: ctrl.currentView,
                nodes : ctrl.nodes,
                indexes : ctrl.indexes
            },
            ctrl.projectOrganizerOptions
        );
        return [
            !ctrl.institutionId ? m('.dashboard-header', m('.row', [
                m('.col-xs-8', m('h3', [
                    'My Projects ',
                    m('small.hidden-xs', 'Browse and organize all your projects')
                ])),
                m('.col-xs-4.p-sm', m('.pull-right', m.component(AddProject, {
                    buttonTemplate: m('.btn.btn-success.btn-success-high-contrast.f-w-xl[data-toggle="modal"][data-target="#addProject"]', {onclick: function() {
                        $osf.trackClick('myProjects', 'add-project', 'open-add-project-modal');
                    }}, 'Create Project'),
                    parentID: null,
                    modalID: 'addProject',
                    title: 'Create new project',
                    categoryList: ctrl.categoryList,
                    stayCallback: function () {
                        ctrl.allProjectsLoaded(false);
                        ctrl.updateList(ctrl.breadcrumbs()[ctrl.breadcrumbs().length - 1]);
                    },
                    trackingCategory: 'myProjects',
                    trackingAction: 'add-project',
                    templates: ctrl.projectsForTemplates
                })))
            ])) : '',
            m('.db-header.row', [
                m('.col-xs-12.col-sm-8.col-lg-9', m.component(Breadcrumbs,ctrl)),
                m('.db-buttonRow.col-xs-12.col-sm-4.col-lg-3', [
                    mobile ? m('button.btn.btn-sm.m-r-sm', {
                        'class' : sidebarButtonClass,
                        onclick : function () {
                            ctrl.showSidebar(!ctrl.showSidebar());
                            $osf.trackClick('myProjects', 'mobile', 'click-bars-to-toggle-collections-or-projects');
                        }
                    }, m('.fa.fa-bars')) : '',
                    m('.db-poFilter.m-r-xs')
                ])
            ]),
            ctrl.showSidebar() ?
            m('.db-sidebar', { config : ctrl.sidebarInit}, [
                mobile ? [ m('.db-dismiss', m('button.close[aria-label="Close"]', {
                    onclick : function () {
                        ctrl.showSidebar(false);
                        $osf.trackClick('myProjects', 'mobile', 'close-toggle-instructions');
                    }
                }, [
                    m('span[aria-hidden="true"]','×')
                ])),
                    m('p.p-sm.text-center.text-muted', [
                        'Select a list below to see the projects. or click ',
                        m('i.fa.fa-bars'),
                        ' button above to toggle.'
                    ])
                ] : '',
                m.component(Collections, ctrl),
                m.component(Filters, ctrl)
            ]) : '',
            m('.db-main', { style : poStyle },[
                ctrl.loadValue() < 100 ? m('.line-loader', [
                    m('.line-empty'),
                    m('.line-full.bg-color-blue', { style : 'width: ' + ctrl.loadValue() +'%'}),
                    m('.load-message', 'Fetching more projects')
                ]) : '',
                ctrl.nonLoadTemplate(),
                m('.db-poOrganizer', {
                    style : ctrl.currentView().totalRows === 0 ? 'display: none' : 'display: block'
                },  m.component( ProjectOrganizer, projectOrganizerOptions))
            ]
            ),
            mobile ? '' : m('.db-info-toggle',{
                    onclick : function _showInfoOnclick(){
                        ctrl.showInfo(!ctrl.showInfo());
                        $osf.trackClick('myProjects', 'information-panel', 'show-hide-information-panel');
                    }
                },
                ctrl.showInfo() ? m('i.fa.fa-chevron-right') :  m('i.fa.fa-chevron-left')
            ),
            infoPanel,
            m.component(Modals, ctrl)
        ];
    }
};

/**
 * Collections Module.
 * @constructor
 */
var Collections = {
    controller : function(args){
        var self = this;
        self.collections = args.collections;
        self.pageSize = args.collectionsPageSize;
        self.newCollectionName = m.prop('');
        self.newCollectionRename = m.prop('');
        self.dismissModal = function () {
            $('.modal').modal('hide');
        };
        self.currentPage = m.prop(1);
        self.totalPages = m.prop(1);
        self.calculateTotalPages = function _calculateTotalPages(result){
            if(result){ // If this calculation comes after GET call to collections
                self.totalPages(Math.ceil((result.links.meta.total + args.systemCollections.length)/self.pageSize()));
            } else {
                self.totalPages(Math.ceil((self.collections().length)/self.pageSize()));
            }
        };
        self.pageSize = m.prop(5);
        self.isValid = m.prop(false);
        self.validationError = m.prop('');
        self.showCollectionMenu = m.prop(false); // Show hide ellipsis menu for collections
        self.collectionMenuObject = m.prop({item : {label:null}, x : 0, y : 0}); // Collection object to complete actions on menu
        self.resetCollectionMenu = function () {
            self.collectionMenuObject({item : {label:null}, x : 0, y : 0});
        };
        self.updateCollectionMenu = function _updateCollectionMenu (item, event) {
            var offset = $(event.target).offset();
            var x = offset.left;
            var y = offset.top;
            if (event.view.innerWidth < MOBILE_WIDTH){
                x = x-105; // width of this menu plus padding
                y = y-270; // fixed height from collections parent to top with adjustments for this menu div
            }
            self.showCollectionMenu(true);
            item.renamedLabel = item.label;
            self.collectionMenuObject({
                item : item,
                x : x,
                y : y
            });
        };

        self.init = function _collectionsInit (element, isInit) {
            self.calculateTotalPages();
            $(window).click(function(event){
                var target = $(event.target);
                if(!target.hasClass('collectionMenu') && !target.hasClass('fa-ellipsis-v') && target.parents('.collection').length === 0) {
                    self.showCollectionMenu(false);
                    m.redraw(); // we have to force redraw here
                }
            });
        };

        self.addCollection = function _addCollection () {
            var url = $osf.apiV2Url('collections/', {});
            var data = {
                'data': {
                    'type': 'collections',
                    'attributes': {
                        'title': self.newCollectionName(),
                    }
                }
            };
            var promise = m.request({method : 'POST', url : url, config : xhrconfig, data : data});
            promise.then(function(result){
                var node = result.data;
                var count = node.relationships.linked_nodes.links.related.meta.count || 0;
                self.collections().push(new LinkObject('collection', { path : 'collections/' + node.id + '/linked_nodes/', query : { 'related_counts' : 'children' }, node : node, count : m.prop(count), nodeType : 'collection' }, node.attributes.title));
                self.newCollectionName('');
                self.calculateTotalPages();
                self.currentPage(self.totalPages()); // Go to last page
                args.sidebarInit();
            }, function(){
                var name = self.newCollectionName();
                var message = '"' + name + '" collection could not be created.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, { url: url, data : data });
                self.newCollectionName('');
            });
            self.dismissModal();
            return promise;
        };
        self.deleteCollection = function _deleteCollection(){
            var url = self.collectionMenuObject().item.data.node.links.self;
            var promise = m.request({method : 'DELETE', url : url, config : xhrconfig});
            promise.then(function(result){
                for ( var i = 0; i < self.collections().length; i++) {
                    var item = self.collections()[i];
                    if (item.data.node && item.data.node.id === self.collectionMenuObject().item.data.node.id){
                        self.collections().splice(i, 1);
                        break;
                    }
                }
                self.calculateTotalPages();
            }, function(){
                var name = self.collectionMenuObject().item.label;
                var message = '"' + name + '" could not be deleted.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, {collectionObject: self.collectionMenuObject() });
            });
            self.dismissModal();
            return promise;
        };
        self.renameCollection = function _renameCollection() {
            var url = self.collectionMenuObject().item.data.node.links.self;
            var nodeId = self.collectionMenuObject().item.data.node.id;
            var title = self.collectionMenuObject().item.renamedLabel;
            var data = {
                'data': {
                    'type': 'collections',
                    'id':  nodeId,
                    'attributes': {
                        'title': title
                    }
                }
            };
            var promise = m.request({method : 'PATCH', url : url, config : xhrconfig, data : data});
            promise.then(function(result){
                self.collectionMenuObject().item.label = title;
            }, function(){
                var name = self.collectionMenuObject().item.label;
                var message = '"' + name + '" could not be renamed.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, {collectionObject: self.collectionMenuObject() });
            });
            self.dismissModal();
            self.isValid(false);
            return promise;
        };
        self.applyDroppable = function _applyDroppable ( ){
            $('.db-collections ul>li.acceptDrop').droppable({
                hoverClass: 'bg-color-hover',
                drop: function( event, ui ) {
                    var collection = self.collections()[$(this).attr('data-index')];
                    var collectionLink = $osf.apiV2Url(collection.data.path, { query : collection.data.query});
                    args.nodeUrlCache[collectionLink] = null;
                    var dataArray = [];
                    // If multiple items are dragged they have to be selected to make it work
                    if (args.selected().length > 1) {
                        args.selected().map(function(item){
                            dataArray.push(buildCollectionNodeData(item.data.id));
                            $osf.trackClick('myProjects', 'projectOrganizer', 'multiple-projects-dragged-to-collection');
                        });
                    } else {
                        // if single items are passed use the event information
                        dataArray.push(buildCollectionNodeData(ui.draggable.find('.title-text>a').attr('data-nodeID'))); // data-nodeID attribute needs to be set in project organizer building title column
                        $osf.trackClick('myProjects', 'projectOrganizer', 'single-project-dragged-to-collection');
                    }
                    function saveNodetoCollection (index) {
                        function doNext (skipCount){
                            if(dataArray[index+1]){
                                saveNodetoCollection(index+1);
                            } else {
                                self.updateList(false, null, collection);
                            }
                            if(!skipCount){
                                collection.data.count(collection.data.count()+1);
                            }
                        }
                        m.request({
                            method : 'POST',
                            url : collection.data.node.links.self + 'node_links/', //collection.data.node.relationships.linked_nodes.links.related.href,
                            config : xhrconfig,
                            data : dataArray[index]
                        }).then(function(){
                            doNext(false);
                        }, function(result){
                            var message = '';
                            var name = args.selected()[index] ? args.selected()[index].data.name : 'Item ';
                            if (result.errors.length > 0) {
                                result.errors.forEach(function(error){
                                    if(error.detail.indexOf('already pointed') > -1 ){
                                        message = '"' + name + '" is already in "' + collection.label + '"' ;
                                    }
                                });
                            }
                            $osf.growl(message,null, 'warning', 4000);
                            doNext(true); // don't add to count
                        }); // In case of success or error. It doesn't look like mithril has a general .done method
                    }
                    if(dataArray.length > 0){
                        saveNodetoCollection(0);
                    }
                }
            });
        };
        self.validateName = function _validateName (val){
            if (val === 'Bookmarks') {
                self.isValid(false);
                self.validationError('"Bookmarks" is a reserved collection name. Please use another name.');
            } else {
                self.validationError('');
                self.isValid(val.length);
            }
        };
        self.init();
    },
    view : function (ctrl, args) {
        var selectedCSS;
        var submenuTemplate;
        var viewOnly = args.viewOnly;
        ctrl.calculateTotalPages();

        var collectionOnclick = function (item){
            args.updateFilesData(item);
            $osf.trackClick('myProjects', 'projectOrganizer', 'open-collection');
        };
        var collectionList = function () {
            var item;
            var index;
            var list = [];
            var childCount;
            var dropAcceptClass;
            if(ctrl.currentPage() > ctrl.totalPages()){
                ctrl.currentPage(ctrl.totalPages());
            }
            var begin = ((ctrl.currentPage()-1)*ctrl.pageSize()); // remember indexes start from 0
            var end = ((ctrl.currentPage()) *ctrl.pageSize()); // 1 more than the last item
            if (ctrl.collections().length < end) {
                end = ctrl.collections().length;
            }
            var openCollectionMenu = function _openCollectionMenu(e) {
                var index = $(this).attr('data-index');
                var selectedItem = ctrl.collections()[index];
                ctrl.updateCollectionMenu(selectedItem, e);
                $osf.trackClick('myProjects', 'edit-collection', 'open-edit-collection-menu');

            };
            for (var i = begin; i < end; i++) {
                item = ctrl.collections()[i];
                index = i;
                dropAcceptClass = index > 1 ? 'acceptDrop' : '';
                childCount = item.data.count ? ' (' + item.data.count() + ')' : '';
                if (args.currentView().collection === item) {
                    selectedCSS = 'active';
                } else if (item.id === ctrl.collectionMenuObject().item.id) {
                    selectedCSS = 'bg-color-hover';
                } else {
                    selectedCSS = '';
                }
                if (item.data.nodeType === 'collection' && !item.data.node.attributes.bookmarks) {
                    submenuTemplate = m('i.fa.fa-ellipsis-v.pull-right.text-muted.p-xs.pointer', {
                        'data-index' : i,
                        onclick : openCollectionMenu
                        });
                } else {
                    submenuTemplate = '';
                }
                list.push(m('li', { className : selectedCSS + ' ' + dropAcceptClass, 'data-index' : index },
                    [
                        m('a[role="button"]', {
                            onclick : collectionOnclick.bind(null, item)
                        },  item.label + childCount),
                        submenuTemplate
                    ]
                ));
            }
            return list;
        };
        var collectionListTemplate = [
            m('h5.clearfix', [
                'Collections ',
                m('i.fa.fa-question-circle.text-muted', {
                    'data-toggle':  'tooltip',
                    'title':  'Collections are groups of projects. You can create custom collections. Drag and drop your projects or bookmarked projects to add them.',
                    'data-placement' : 'bottom'
                }, ''),
                !viewOnly ? m('button.btn.btn-xs.btn-default[data-toggle="modal"][data-target="#addColl"].m-h-xs', {onclick: function() {
                        $osf.trackClick('myProjects', 'add-collection', 'open-add-collection-modal');
                    }}, m('i.fa.fa-plus')) : '',
                m('.pull-right',
                    ctrl.totalPages() > 1 ? m.component(MicroPagination, { currentPage : ctrl.currentPage, totalPages : ctrl.totalPages, type: 'collections' }) : ''
                )
            ]),
            m('ul', { config: ctrl.applyDroppable },[
                collectionList(),
                ctrl.showCollectionMenu() ? m('.collectionMenu',{
                    style : 'position:absolute;top: ' + ctrl.collectionMenuObject().y + 'px;left: ' + ctrl.collectionMenuObject().x + 'px;'
                }, [
                    m('.menuClose', { onclick : function (e) {
                        ctrl.showCollectionMenu(false);
                        ctrl.resetCollectionMenu();
                        $osf.trackClick('myProjects', 'edit-collection', 'click-close-edit-collection-menu');
                    }
                    }, m('.text-muted','×')),
                    m('ul', [
                        m('li[data-toggle="modal"][data-target="#renameColl"].pointer',{
                            onclick : function (e) {
                                ctrl.showCollectionMenu(false);
                                $osf.trackClick('myProjects', 'edit-collection', 'open-rename-collection-modal');
                            }
                        }, [
                            m('i.fa.fa-pencil'),
                            ' Rename'
                        ]),
                        m('li[data-toggle="modal"][data-target="#removeColl"].pointer',{
                            onclick : function (e) {
                                ctrl.showCollectionMenu(false);
                                $osf.trackClick('myProjects', 'edit-collection', 'open-delete-collection-modal');
                            }
                        }, [
                            m('i.fa.fa-trash'),
                            ' Delete'
                        ])
                    ])
                ]) : ''
            ])
        ];
        return m('.db-collections', [
            collectionListTemplate,
            m('.db-collections-modals', [
                m.component(mC.modal, {
                    id: 'addColl',
                    header : m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]', {onclick: function() {
                            $osf.trackClick('myProjects', 'add-collection', 'click-close-add-collection-modal');
                        }}, [
                            m('span[aria-hidden="true"]','×')
                        ]),
                        m('h3.modal-title', 'Add new collection')
                    ]),
                    body : m('.modal-body', [
                        m('p', 'Collections are groups of projects that help you organize your work. After you create your collection, you can add projects by dragging them into the collection.'),
                        m('.form-group', [
                            m('label[for="addCollInput].f-w-lg.text-bigger', 'Collection name'),
                            m('input[type="text"].form-control#addCollInput', {
                                onkeyup: function (ev){
                                    var val = $(this).val();
                                    ctrl.validateName(val);
                                    if(ctrl.isValid()){
                                        if(ev.which === 13){
                                            ctrl.addCollection();
                                        }
                                    }
                                    ctrl.newCollectionName(val);
                                },
                                onchange: function() {
                                    $osf.trackClick('myProjects', 'add-collection', 'type-collection-name');
                                },
                                placeholder : 'e.g.  My Replications',
                                value : ctrl.newCollectionName()
                            }),
                            m('span.help-block', ctrl.validationError())
                        ])
                    ]),
                    footer: m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]',
                            {
                                onclick : function(){
                                    ctrl.dismissModal();
                                    ctrl.newCollectionName('');
                                    ctrl.isValid(false);
                                    $osf.trackClick('myProjects', 'add-collection', 'click-cancel-button');

                                }
                            }, 'Cancel'),
                        ctrl.isValid() ? m('button[type="button"].btn.btn-success', { onclick : function() {
                            ctrl.addCollection();
                            $osf.trackClick('myProjects', 'add-collection', 'click-add-button');
                        }},'Add')
                            : m('button[type="button"].btn.btn-success[disabled]', 'Add')
                    ])
                }),
                m.component(mC.modal, {
                    id : 'renameColl',
                    header: m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]', {onclick: function() {
                            $osf.trackClick('myProjects', 'edit-collection', 'click-close-rename-modal');
                        }}, [
                            m('span[aria-hidden="true"]','×')
                        ]),
                        m('h3.modal-title', 'Rename collection')
                    ]),
                    body: m('.modal-body', [
                        m('.form-inline', [
                            m('.form-group', [
                                m('label[for="addCollInput]', 'Rename to: '),
                                m('input[type="text"].form-control.m-l-sm',{
                                    onkeyup: function(ev){
                                        var val = $(this).val();
                                        ctrl.validateName(val);
                                        if(ctrl.isValid()) {
                                            if (ev.which === 13) { // if enter is pressed
                                                ctrl.renameCollection();
                                            }
                                        }
                                        ctrl.collectionMenuObject().item.renamedLabel = val;
                                    },
                                    onchange: function() {
                                        $osf.trackClick('myProjects', 'edit-collection', 'type-rename-collection');
                                    },
                                    value: ctrl.collectionMenuObject().item.renamedLabel}),
                                m('span.help-block', ctrl.validationError())

                            ])
                        ])
                    ]),
                    footer : m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {
                            onclick : function(){
                                ctrl.isValid(false);
                                $osf.trackClick('myProjects', 'edit-collection', 'click-cancel-rename-button');
                            }
                        },'Cancel'),
                        ctrl.isValid() ? m('button[type="button"].btn.btn-success', { onclick : function() {
                            ctrl.renameCollection();
                            $osf.trackClick('myProjects', 'edit-collection', 'click-rename-button');
                        }},'Rename')
                            : m('button[type="button"].btn.btn-success[disabled]', 'Rename')
                    ])
                }),
                m.component(mC.modal, {
                    id: 'removeColl',
                    header: m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]', {onclick: function() {
                            $osf.trackClick('myProjects', 'edit-collection', 'click-close-delete-collection');
                        }}, [
                            m('span[aria-hidden="true"]','×')
                        ]),
                        m('h3.modal-title', 'Delete collection "' + ctrl.collectionMenuObject().item.label + '"?')
                    ]),
                    body: m('.modal-body', [
                        m('p', 'This will delete your collection, but your projects will not be deleted.')
                    ]),
                    footer : m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {onclick: function() {
                            $osf.trackClick('myProjects', 'edit-collection', 'click-cancel-delete-collection');
                        }}, 'Cancel'),
                        m('button[type="button"].btn.btn-danger', {
                            onclick : function() {
                                ctrl.deleteCollection();
                                $osf.trackClick('myProjects', 'edit-collection', 'click-delete-collection-button');
                            }},'Delete')
                    ])
                })
            ])
        ]);
    }
};
/**
 * Small view component for compact pagination
 * Requires currentPage and totalPages to be m.prop
 * @type {{view: MicroPagination.view}}
 */
var MicroPagination = {
    view : function(ctrl, args) {
        if (args.currentPage() > args.totalPages()) {
            args.currentPage(args.totalPages());
        }
        return m('span.osf-micro-pagination.m-l-xs', [
            args.currentPage() > 1 ? m('span.m-r-xs.arrow.left.live', { onclick : function(){
                    args.currentPage(args.currentPage() - 1);
                    $osf.trackClick('myProjects', 'paginate', 'get-prev-page-' + args.type);
             }}, m('i.fa.fa-angle-left')) : m('span.m-r-xs.arrow.left', m('i.fa.fa-angle-left')),
            m('span', args.currentPage() + '/' + args.totalPages()),
            args.currentPage() < args.totalPages() ? m('span.m-l-xs.arrow.right.live', { onclick : function(){
                    args.currentPage(args.currentPage() + 1);
                    $osf.trackClick('myProjects', 'paginate', 'get-next-page-' + args.type);
            }}, m('i.fa.fa-angle-right')) : m('span.m-l-xs.arrow.right', m('i.fa.fa-angle-right'))
        ]);
    }
};

/**
 * Breadcrumbs Module
 * @constructor
 */

var Breadcrumbs = {
    view : function (ctrl, args) {
        var viewOnly = args.viewOnly;
        var mobile = window.innerWidth < MOBILE_WIDTH; // true if mobile view
        var updateFilesOnClick = function (item) {
          if (item.type === 'node')
            args.updateFilesData(item, item.data.id);
          else
            args.updateFilesData(item);
          $osf.trackClick('myProjects', 'projectOrganizer', 'click-on-breadcrumbs');
        };
        var contributorsTemplate = [];
        var tagsTemplate = [];
        if(args.currentView().contributor.length) {
            contributorsTemplate.push(m('span.text-muted', 'with '));
            args.currentView().contributor.forEach(function (c) {
                contributorsTemplate.push(m('span.comma-separated.filter-breadcrumb', [
                    c.label,
                    ' ',
                    m('i.fa.fa-times-circle-o.text-muted', { onclick: function(){
                        args.unselectContributor(c.data.id);
                    }})
                ]));
            });
        }
        if(args.currentView().tag.length){
            tagsTemplate.push(m('span.text-muted.m-l-sm', 'tagged '));
            args.currentView().tag.forEach(function(t){
                tagsTemplate.push(m('span.comma-separated.filter-breadcrumb', [
                    t.label,
                    ' ',
                    m('i.fa.fa-times-circle-o.text-muted', { onclick: function(){
                        args.unselectTag(t.data.tag);
                    }})
                ]));
            });
        }
        var items = args.breadcrumbs();
        if (mobile && items.length > 1) {
            return m('.db-breadcrumbs', [
                m('ul', [
                    m('li', [
                        m('.btn.btn-link[data-toggle="modal"][data-target="#parentsModal"]', '...'),
                        m('i.fa.fa-angle-right')
                    ]),
                    m('li', m('span.btn', items[items.length-1].label))
                ]),
                m('#parentsModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-body', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×')
                                ]),
                                m('h4', 'Parent projects'),
                                args.breadcrumbs().map(function(item, index, array){
                                    if(index === array.length-1){
                                        return m('.db-parent-row.btn', {
                                            style : 'margin-left:' + (index*20) + 'px;'
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ]);
                                    }
                                    item.index = index; // Add index to update breadcrumbs
                                    item.placement = 'breadcrumb'; // differentiate location for proper breadcrumb actions
                                    return m('.db-parent-row',[
                                        m('span.btn.btn-link', {
                                            style : 'margin-left:' + (index*20) + 'px;',
                                            onclick : function() {
                                                args.updateFilesData(item);
                                                $('.modal').modal('hide');
                                            }
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ]),
                                        contributorsTemplate,
                                        tagsTemplate
                                        ]
                                    );
                                })
                            ])
                        ])
                    )
                )
            ]);
        }
        return m('.db-breadcrumbs', m('ul', [
            items.map(function(item, index, array){
                if(index === array.length-1){
                    if(item.type === 'node'){
                        var parentID = args.breadcrumbs()[args.breadcrumbs().length - 1].data.id;
                        var showAddProject = true;
                        var addProjectTemplate = '';
                        var permissions = item.data.attributes.current_user_permissions;
                        showAddProject = permissions.indexOf('admin') > -1 || permissions.indexOf('write') > -1;
                        if (item.type === 'registration' || item.data.type === 'registrations' || item.data.nodeType === 'registrations'){
                            showAddProject = false;
                        }
                        if(showAddProject && !viewOnly){
                            addProjectTemplate = m.component(AddProject, {
                                buttonTemplate: m('.btn.btn-sm.text-muted[data-toggle="modal"][data-target="#addSubComponent"]', {onclick: function() {
                                    $osf.trackClick('myProjects', 'add-component', 'open-add-component-modal');
                                }}, [m('i.fa.fa-plus.m-r-xs', {style: 'font-size: 10px;'}), 'Create component']),
                                parentID: parentID,
                                modalID: 'addSubComponent',
                                title: 'Create new component',
                                categoryList: args.categoryList,
                                stayCallback: function () {
                                    args.allProjectsLoaded(false);
                                    args.updateList(args.breadcrumbs()[args.breadcrumbs().length - 1]);
                                },
                                trackingCategory: 'myProjects',
                                trackingAction: 'add-component'
                            });
                        }
                        return [
                            m('li', [
                                m('span.btn', item.label),
                                contributorsTemplate,
                                tagsTemplate,
                                m('i.fa.fa-angle-right')
                            ]),
                            addProjectTemplate
                        ];
                    }
                }
                item.index = index; // Add index to update breadcrumbs
                item.placement = 'breadcrumb'; // differentiate location for proper breadcrumb actions
                return m('li',[
                    m('span.btn.btn-link', {onclick : updateFilesOnClick.bind(null, item)},  item.label),
                    contributorsTemplate,
                    tagsTemplate,
                    m('i.fa.fa-angle-right')
                    ]
                );
            })
        ]));
    }
};


/**
 * Filters Module.
 * @constructor
 */
var Filters = {
    controller : function (args) {
        var self = this;
        self.nameCurrentPage = m.prop(1);
        self.namePageSize = m.prop(4);
        self.nameTotalPages = m.prop(1);
        self.tagCurrentPage = m.prop(1);
        self.tagPageSize = m.prop(4);
        self.tagTotalPages = m.prop(1);
    },
    view : function (ctrl, args) {
        if(args.nameFilters.length > 0) {
            ctrl.nameTotalPages(Math.ceil(args.nameFilters.length/ctrl.namePageSize()));
        }
        if(args.tagFilters.length > 0){
            ctrl.tagTotalPages(Math.ceil(args.tagFilters.length/ctrl.tagPageSize()));
        }
        var filterContributor = function(item, tracking) {
            args.updateFilesData(item);
            $osf.trackClick('myProjects', 'filter', 'filter-by-contributor');
        };

        var filterTag = function(item, tracking) {
            args.updateFilesData(item);
            $osf.trackClick('myProjects', 'filter', 'filter-by-tag');
        };

        var returnNameFilters = function _returnNameFilters(){
            if(args.nodes.projects.flatData.total && args.nameFilters.length === 0){
                return m('.text-muted.text-smaller', 'There are no collaborators in this collection yet.');
            }
            var list = [];
            var item;
            var i;
            var selectedCSS;
            var begin = ((ctrl.nameCurrentPage()-1) * ctrl.namePageSize()); // remember indexes start from 0
            var end = ((ctrl.nameCurrentPage()) * ctrl.namePageSize()); // 1 more than the last item
            if (args.nameFilters.length < end) {
                end = args.nameFilters.length;
            }
            for (i = begin; i < end; i++) {
                item = args.nameFilters[i];
                selectedCSS = args.currentView().contributor.indexOf(item) !== -1 ? '.active' : '';
                list.push(m('li' + selectedCSS,
                    m('a[role="button"]', {onclick : filterContributor.bind(null, item)},
                        item.label)
                ));
            }
            return list;
        };
        var returnTagFilters = function _returnTagFilters(){
            if(args.nodes.projects.flatData.total && args.tagFilters.length === 0){
                return m('.text-muted.text-smaller', 'Projects in this collection don\'t have any tags yet.');
            }
            var list = [];
            var selectedCSS;
            var item;
            var i;
            var begin = ((ctrl.tagCurrentPage()-1) * ctrl.tagPageSize()); // remember indexes start from 0
            var end = ((ctrl.tagCurrentPage()) * ctrl.tagPageSize()); // 1 more than the last item
            if (args.tagFilters.length < end) {
                end = args.tagFilters.length;
            }
            for (i = begin; i < end; i++) {
                item = args.tagFilters[i];
                selectedCSS = args.currentView().tag.indexOf(item) !== -1  ? '.active' : '';
                list.push(m('li' + selectedCSS,
                    m('a[role="button"]', {onclick : filterTag.bind(null, item)},
                        item.label
                    )
                ));
            }
            return list;
        };
        return m('.db-filters.m-t-lg',
            [
                m('h5.m-t-sm', [
                    'Contributors ',
                    m('i.fa.fa-question-circle.text-muted', {
                        'data-toggle':  'tooltip',
                        'title': 'Click a name to display the selected contributor’s public projects, as well as their private projects on which you are at least a read contributor.',
                        'data-placement' : 'bottom'
                    }, ''),
                    m('.pull-right',
                        args.nameFilters.length && ctrl.nameTotalPages() > 1 ? m.component(MicroPagination, { currentPage : ctrl.nameCurrentPage, totalPages : ctrl.nameTotalPages, type: 'contributors'}) : ''
                        )
                ]),
                m('ul', [
                    args.nodes.projects.flatData.loaded === 0 ? m('.ball-beat.text-center.m-t-md', m('')) : returnNameFilters()
                ]),
                m('h5.m-t-sm', [
                    'Tags',
                    m('.pull-right',
                        args.tagFilters.length && ctrl.tagTotalPages() > 1 ? m.component(MicroPagination, { currentPage : ctrl.tagCurrentPage, totalPages : ctrl.tagTotalPages, type: 'tags' }) : ''
                        )
                ]), m('ul', [
                    args.nodes.projects.flatData.loaded === 0 ? m('.ball-beat.text-center.m-t-md', m('')) : returnTagFilters()
                ])
            ]
        );
    }
};

/**
 * Information Module.
 * @constructor
 */
var Information = {
    view : function (ctrl, args) {
        function categoryMap(category) {
            // TODO, you don't need to do this, CSS will do this case change
            switch (category) {
                case 'analysis':
                    return 'Analysis';
                case 'communication':
                    return 'Communication';
                case 'data':
                    return 'Data';
                case 'hypothesis':
                    return 'Hypothesis';
                case 'methods and measures':
                    return 'Methods and Measures';
                case 'procedure':
                    return 'Procedure';
                case 'project':
                    return 'Project';
                case 'software':
                    return 'Software';
                case 'other':
                    return 'Other';
                default:
                    return 'Uncategorized';
            }
        }
        var template = '';
        var showRemoveFromCollection;
        var collectionFilter = args.currentView().collection;
        if (args.selected().length === 0) {
            template = m('.db-info-empty.text-muted.p-lg', 'Select a row to view project details.');
        }
        if (args.selected().length === 1) {
            var item = args.selected()[0].data;
            showRemoveFromCollection = collectionFilter.data.nodeType === 'collection' && args.selected()[0].depth === 1; // Be able to remove top level items but not their children
            if(item.attributes.category === ''){
                item.attributes.category = 'Uncategorized';
            }
            template = m('.p-sm', [
                showRemoveFromCollection ? m('.clearfix', m('.btn.btn-default.btn-sm.btn.p-xs.text-danger.pull-right', { onclick : function() {
                    args.removeProjectFromCollections();
                    $osf.trackClick('myProjects', 'information-panel', 'remove-project-from-collection');
                } }, 'Remove from collection')) : '',
                    m('h3', m('a', { href : item.links.html, onclick: function(){
                        $osf.trackClick('myProjects', 'information-panel', 'navigate-to-project');
                    }}, item.attributes.title)),
                m('[role="tabpanel"]', [
                    m('ul.nav.nav-tabs.m-b-md[role="tablist"]', [
                        m('li[role="presentation"].active', m('a[href="#tab-information"][aria-controls="information"][role="tab"][data-toggle="tab"]', {onclick: function(){
                            $osf.trackClick('myProjects', 'information-panel', 'open-information-tab');
                        }}, 'Information')),
                        m('li[role="presentation"]', m('a[href="#tab-activity"][aria-controls="activity"][role="tab"][data-toggle="tab"]', {onclick : function() {
                            args.getCurrentLogs();
                            $osf.trackClick('myProjects', 'information-panel', 'open-activity-tab');
                        }}, 'Activity'))
                    ]),
                    m('.tab-content', [
                        m('[role="tabpanel"].tab-pane.active#tab-information',[
                            m('p.db-info-meta.text-muted', [
                                m('', 'Visibility : ' + (item.attributes.public ? 'Public' : 'Private')),
                                m('', 'Category: ' + categoryMap(item.attributes.category)),
                                m('', 'Last Modified on: ' + (item.date ? item.date.local : ''))
                            ]),
                            m('p', [
                                m('span', {style: 'white-space:pre-wrap'}, item.attributes.description)
                            ]),
                            item.attributes.tags.length > 0 ?
                            m('p.m-t-md', [
                                m('h5', 'Tags'),
                                item.attributes.tags.map(function(tag){
                                    return m('a.tag', { href : '/search/?q=(tags:' + tag + ')', onclick: function(){
                                        $osf.trackClick('myProjects', 'information-panel', 'navigate-to-search-by-tag');
                                    }}, tag);
                                })
                            ]) : ''
                        ]),
                        m('[role="tabpanel"].tab-pane#tab-activity',[
                            m.component(ActivityLogs, args)
                        ])
                    ])
                ])
            ]);
        }
        if (args.selected().length > 1) {
            showRemoveFromCollection = collectionFilter.data.nodeType === 'collection'  && args.selected()[0].depth === 1;
            template = m('.p-sm', [
                showRemoveFromCollection ? m('.clearfix', m('.btn.btn-default.btn-sm.p-xs.text-danger.pull-right', { onclick : function() {
                    args.removeProjectFromCollections();
                    $osf.trackClick('myProjects', 'information-panel', 'remove-multiple-projects-from-collections');
                } }, 'Remove selected from collection')) : '',
                args.selected().map(function(item){
                    return m('.db-info-multi', [
                        m('h4', m('a', { href : item.data.links.html}, item.data.attributes.title)),
                        m('p.db-info-meta.text-muted', [
                            m('span', item.data.attributes.public ? 'Public' : 'Private' + ' ' + item.data.attributes.category),
                            m('span', ', Last Modified on ' + item.data.date.local)
                        ])
                    ]);
                })
            ]);
        }
        return m('.db-information', template);
    }
};


var ActivityLogs = {
    view : function (ctrl, args) {
        return m('.db-activity-list.m-t-md', [
            args.activityLogs() ? args.activityLogs().map(function(item){
                item.trackingCategory = 'myProjects';
                item.trackingAction = 'information-panel';
                var image = m('i.fa.fa-question');
                if (item.embeds.user && item.embeds.user.data) {
                    image = m('img', { src : item.embeds.user.data.links.profile_image});
                }
                else if (item.embeds.user && item.embeds.user.errors){
                    image = m('img', { src : item.embeds.user.errors[0].meta.profile_image});
                }
                return m('.db-activity-item', [
                m('', [ m('.db-log-avatar.m-r-xs', image),
                    m.component(LogText, item)]),
                m('.text-right', m('span.text-muted.m-r-xs', item.attributes.formattableDate.local))]);

            }) : '',
            m('.db-activity-nav.text-center', [
                args.showMoreActivityLogs() ? m('.btn.btn-sm.btn-link', { onclick: function(){
                    args.getLogs(args.showMoreActivityLogs(), true);
                    $osf.trackClick('myProjects', 'information-panel', 'show-more-activity');
                }}, [ 'Show more', m('i.fa.fa-caret-down.m-l-xs')]) : ''
            ])

        ]);
    }
};

/**
 * Modals views.
 * @constructor
 */

var Modals = {
    view : function(ctrl, args) {
        return m('.db-fbModals', [
            m('#infoModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-body', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m.component(Information, args)
                        ])
                    ])
                )
            )
        ]);
    }
};


module.exports = {
    MyProjects : MyProjects,
    Collections : Collections,
    MicroPagination : MicroPagination,
    ActivityLogs : ActivityLogs,
    LinkObject: LinkObject
};
