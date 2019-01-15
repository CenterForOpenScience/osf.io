/**
 * Builds full page project browser
 */
'use strict';

require('css/log-feed.css');
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/project-organizer');
var $osf = require('js/osfHelpers');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');
var LogText = require('js/logTextParser');
var AddProject = require('js/addProjectPlugin');
var mC = require('js/mithrilComponents');
var lodashGet = require('lodash.get');
var lodashFind = require('lodash.find');

var MOBILE_WIDTH = 767; // Mobile view break point for responsiveness
var NODE_PAGE_SIZE = 10; // Load 10 nodes at a time from server
var PROFILE_IMAGE_SIZE = 16;

/* Counter for unique ids for link objects */
if (!window.fileBrowserCounter) {
    window.fileBrowserCounter = 0;
}

var sparseNodeFields = String([
    'category',
    'children',
    'contributors',
    'current_user_permissions',
    'date_modified',
    'description',
    'parent',
    'public',
    'tags',
    'title'
]);

var sparseRegistrationFields = String([
    sparseNodeFields,
    'registration',
    'pending_registration_approval',
    'withdrawn'
]);

var sparseUserFields = String([
    'family_name',
    'full_name',
    'given_name',
    'middle_names'
]);

var sparseContributorFields = String([
    'bibliographic',
    'unregistered_contributor',
    'users'
]);

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


function NodeFetcher(type, link, handleOrphans, regType, regLink, preprintType, preprintLink) {
    this.type = type || 'nodes';
    this.regType = regType || null;
    this.regLink = regLink || null;
    this.preprintType = preprintType || null;
    this.preprintLink = preprintLink || null;
    this.loaded = 0;
    this._failed = 0;
    this.total = 0;
    this._flat = [];
    this._orphans = [];
    this._cache = {};
    this._promise = null;
    this._started = false;
    this._continue = true;
    // hack to force a re-sort and cleanup when the fetcher is done
    this.forceRedraw = false;
    this._handleOrphans = handleOrphans === undefined ? true : handleOrphans;
    this._callbacks = {
        done: [this._onFinish.bind(this)],
        page: [],
        children: [],
        fetch : []
    };

    var params = {'related_counts' : 'children', 'embed' : 'contributors', 'version': '2.2', 'fields[users]' : sparseUserFields, 'fields[contributors]' : sparseContributorFields};

    if (this.type === 'nodes') {
        params['fields[nodes]'] = sparseNodeFields;
    }

    if (this.type === 'registrations') {
        params['fields[registrations]'] = sparseRegistrationFields;
    }

    // TODO Use sparse fields on preprints, users/contributors already added
    if (this.type === 'preprints') {
        link = link ? link : $osf.apiV2Url('users/me/preprints/', { query : { 'embed' : ['contributors'], 'fields[users]' : sparseUserFields, 'fields[contributors]' : sparseContributorFields}});
    }

    this.nextLink = link ?
        link + '&version=2.2' :
        $osf.apiV2Url('users/me/' + this.type + '/', { query: params});
}

NodeFetcher.prototype = {
  isFinished: function() {
    return this.loaded >= this.total && this._promise === null && this._orphans.length === 0 && !this.nextLink;
  },
  isEmpty: function() {
    return this.loaded === 0 && this.isFinished();
  },
  progress: function() {
    return Math.ceil(this.loaded / (this.total || 1) * 100);
  },
  start: function() {
    return this.resume();
  },
  pause: function() {
    this._continue = false;
  },
  resume: function() {
    this._started = true;
    this._continue = true;
    if (!this.nextLink) return this._promise = null;
    if (this._promise) return this._promise;
    return this._promise = m.request({method: 'GET', url: this.nextLink, config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}), background: true})
      .then(function(results) {this._promise = null; return results;}.bind(this))
      .then(this._success.bind(this), this._fail.bind(this))
      .then((function() {
          m.redraw(true);
          if(this.nextLink && this._continue) return this.resume();
      }).bind(this));
  },
  add: function(item) {
    if (!this._started ||this._flat.indexOf(item) !== - 1) return;

    this.forceRedraw = true;
    this.total++;
    this.loaded++;

    if (!this._cache[item.id])
      this._cache[item.id] = item;

    this._flat.unshift(item);

    // Resort after inserting data
    this._flat = this._orphans.concat(this._flat).sort(function(a,b) {
      a = new Date(a.attributes.date_modified);
      b = new Date(b.attributes.date_modified);
      if (a > b) return -1;
      if (a < b) return 1;
      return 0;
    });
  },
  remove: function(item) {
    item = item.id || item;

    this.forceRedraw = true;
    this.total--;
    this.loaded--;

    if (!this._cache[item]) return;
    delete this._cache[item];
    for(var i = 0; i < this._flat.length; i++)
      if (this._flat[i].id === item) {
        this._flat.splice(i, 1);
        break;
      }
  },
  get: function(id) {
    if (!this._cache[id])
      return this.fetch(id);
    var deferred = m.deferred();
    deferred.resolve(this._cache[id]);
    return deferred.promise;
  },
  getChildren: function(id) {
    //TODO Load via rootNode
    if (this._cache[id].relationships.children.links.related.meta.count !== this._cache[id].children.length) {
      return this.fetchChildren(this._cache[id]);
    }
    var deferred = m.deferred();
    deferred.resolve(this._cache[id].children);
    return deferred.promise;
  },
  fetch: function(id) {
    // TODO This method is currently untested
    // this.type can be 'registrations' when it needs to be 'nodes' based on when this is called
    // TODO assess sparse field usage (some already implemented)
    var url =  $osf.apiV2Url(this.type + '/' + id + '/', {query: {related_counts: 'children', embed: 'contributors', version: '2.2', 'fields[users]' : sparseUserFields, 'fields[contributors]' : sparseContributorFields}});
    return m.request({method: 'GET', url: url, config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}), background: true})
      .then((function(result) {
        this.add(result.data);
        return result.data;
      }).bind(this), this._fail.bind(this));
  },
  fetchChildren: function(parent, link) {
    //TODO Allow suspending of children
    return m.request({method: 'GET', url: link || parent.relationships.children.links.related.href + '&embed=contributors&related_counts=children', config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}), background: true})
      .then(this._childrenSuccess.bind(this, parent), this._fail.bind(this));
  },
  _success: function(results) {
    // Only reset if we're lower as loading children will increment this number
    if (this.total < results.meta.total)
        this.total = results.meta.total;

    this.nextLink = results.links.next;
    this.loaded += results.data.length;
    for(var i = 0; i < results.data.length; i++) {
      if (this.type === 'registrations' && (results.data[i].attributes.withdrawn === true || results.data[i].attributes.pending_registration_approval === true)){
          this.total--;
          this.loaded--;
          continue; // Exclude retracted and pending registrations
      }
      else if (results.data[i].relationships.parent && this._handleOrphans)
          this._orphans.push(results.data[i]);
      else
          this._flat.push(results.data[i]);

      if (this._cache[results.data[i].id]) continue;
      this._cache[results.data[i].id] = _formatDataforPO(results.data[i]);
      this._cache[results.data[i].id].children = [];

      this._orphans = this._orphans.filter((function(item) {
        var parentId = item.relationships.parent.links.related.href.split('/').splice(-2, 1)[0];
        if (!this._cache[parentId]) return true;
        this._cache[parentId].children.push(item);
        return false;
      }).bind(this));
    }
    if(!this.nextLink && this.regLink) {
        this.nextLink = this.regLink;
        this.type = this.regType;
        this.regLink = null;
    }

    if(!this.nextLink && this.preprintLink) {
        this.nextLink = this.preprintLink;
        this.type = this.preprintType;
        this.preprintLink = null;
    }

    this._callbacks.page.forEach((function(cb) {
      cb(this, results.data);
    }).bind(this));

    if (!this.nextLink)
      this._callbacks.done.forEach((function(cb) {
        cb(this);
      }).bind(this));
  },
  _childrenSuccess: function(parent, results) {
    if (!results.links.prev)
      this.total += results.meta.total;

    this.loaded += results.data.length;
    var finder = function(id, item) {return item.id === id;};
    for(var i = 0; i < results.data.length; i++) {
      //TODO Sorting get a bit broken here @chrisseto
      if (this._cache[parent.id].children.find(finder.bind(this, results.data[i].id))) continue;
      this._cache[results.data[i].id] = _formatDataforPO(results.data[i]);
      results.data[i].children = [];
      this._cache[parent.id].children.push(results.data[i]);
    }

    if (results.links.next)
      return this.fetchChildren(parent, results.links.next);

    return this._cache[parent.id].children;
  },
  _fail: function(result) {
    if (++this._failed < 5)
      return this.resume();
    this._continue = false;
    this._promise = null;
    Raven.captureMessage('Error loading nodes with nodeType ' + this.type + ' at url ' + this.nextLink, {
        extra: {requestReturn: result}
    });
    $osf.growl('We\'re having some trouble contacting our servers. Try reloading the page.', 'Something went wrong!', 'danger', 5000);
  },
  _onFinish: function() {
    this.forceRedraw = true;
    this._flat = this._orphans.concat(this._flat).sort(function(a,b) {
      a = new Date(a.attributes.date_modified);
      b = new Date(b.attributes.date_modified);
      if (a > b) return -1;
      if (a < b) return 1;
      return 0;
    });
    this._orphans = [];
  },
  on: function(type, func) {
    if (!Array.isArray(type))
      type = [type];
    //Valid types are children, page, done
    for(var i = 0; i < type.length; i++)
      this._callbacks[type[i]].push(func);
  }
};


function getUID() {
    window.fileBrowserCounter = window.fileBrowserCounter + 1;
    return window.fileBrowserCounter;
}

/* Adjust item data for treebeard to be able to filter tags and contributors not in the view */
function _formatDataforPO(item) {
    item.kind = 'folder';
    item.uid = item.id;
    item.name = $osf.decodeText(item.attributes.title);
    item.tags = item.attributes.tags.toString();
    item.contributors = '';
    var contributorsData = lodashGet(item, 'embeds.contributors.data', null);
    if (contributorsData){
        item.embeds.contributors.data.forEach(function(c){
            var attr;
            var contribNames = $osf.extractContributorNamesFromAPIData(c);

            if (lodashGet(c, 'attributes.unregistered_contributor', null)) {
                item.contributors += contribNames.fullName;
            }
            else {
                item.contributors += contribNames.fullName + ' ' + contribNames.middleNames + ' ' + contribNames.givenName + ' ' + contribNames.familyName + ' ' ;
            }
        });
    }
    item.date = new $osf.FormattableDate(item.attributes.date_modified);
    item.sortDate = item.date.date;
    //
    //Sets for filtering
    item.tagSet = new Set(item.attributes.tags || []);
    var contributors = lodashGet(item, 'embeds.contributors.data', []);
    item.contributorSet= new Set(contributors.map(function(contrib) {
      return contrib.id;
    }));
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
function buildCollectionNodeData (id, type) {
    return {
        'data': [{
            'type': 'linked_'+type,
            'id': id
        }]
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
        self.logUrlCache = {}; // dictionary of load urls to avoid multiple calls with little refactor
        self.nodeUrlCache = {}; // Cached returns of the project related urls
        // VIEW STATES
        self.showInfo = m.prop(false); // Show the info panel
        self.showSidebar = m.prop(false); // Show the links with collections etc. used in narrow views
        self.allProjectsLoaded = m.prop(false);
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

        // Treebeard functions looped through project organizer.
        // We need to pass these in to avoid reinstantiating treebeard but instead repurpose (update) the top level folder
        self.treeData = m.prop({}); // Top level object that houses all the rows
        self.buildTree = m.prop(null); // Preprocess function that adds to each item TB specific attributes
        self.updateFolder = m.prop(null); // Updates view to redraw without messing up scroll location
        self.multiselected = m.prop(); // Updated the selected list in treebeard
        self.highlightMultiselect = m.prop(null); // does highlighting background of the row

        // Add All my Projects and All my registrations to collections
        self.systemCollections = options.systemCollections || [
            new LinkObject('collection', { nodeType : 'projects'}, 'All my projects'),
            new LinkObject('collection', { nodeType : 'registrations'}, 'All my registrations'),
            new LinkObject('collection', { nodeType : 'preprints'}, 'All my preprints')
        ];

        self.fetchers = {};
        if (!options.systemCollections) {
          self.fetchers[self.systemCollections[0].id] = new NodeFetcher('nodes');
          self.fetchers[self.systemCollections[1].id] = new NodeFetcher('registrations');
          self.fetchers[self.systemCollections[2].id] = new NodeFetcher('preprints', self.systemCollections[2].data.link);
        } else {
            // TODO: This assumes that there are two systemcolelctiosn passes and what they are. It should ideally loop through passed collections.
          self.fetchers[self.systemCollections[0].id] = new NodeFetcher('nodes', self.systemCollections[0].data.link);
          self.fetchers[self.systemCollections[1].id] = new NodeFetcher('registrations', self.systemCollections[1].data.link);
        }

        // Initial Breadcrumb for All my projects
        var initialBreadcrumbs = options.initialBreadcrumbs || [self.systemCollections[0]];
        self.breadcrumbs = m.prop(initialBreadcrumbs);
        // Calculate name filters
        self.nameFilters = [];
        // Calculate tag filters
        self.tagFilters = [];


        // Load categories to pass in to create project
        self.loadCategories = function _loadCategories () {
            var promise = m.request({method : 'OPTIONS', url : $osf.apiV2Url('nodes/', { query : {}}), config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})});
            promise.then(function _success(results){
                if(results.actions && results.actions.POST.category){
                    self.categoryList = results.actions.POST.category.choices;
                }
            }, function _error(results){
                var message = 'Error loading project category names.';
                Raven.captureMessage(message, {extra: {requestReturn: results}});
            });
            return promise;
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
                var promise = m.request({method : 'GET', url : url, config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})});
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
                // Hiding preprint logs for now
                if (item.data.type === 'preprints') {
                    return [];
                }
                if(!item.data.attributes.retracted){
                    var urlPrefix = item.data.attributes.registration ? 'registrations' : 'nodes';
                    // TODO assess sparse field usage (some already implemented)
                    var url = $osf.apiV2Url(urlPrefix + '/' + id + '/logs/', { query : { 'page[size]' : 6, 'embed' : ['original_node', 'user', 'linked_node', 'linked_registration', 'template_node'], 'profile_image_size': PROFILE_IMAGE_SIZE, 'fields[users]' : sparseUserFields}});
                    var promise = self.getLogs(url);
                    return promise;
                }
            }
        };

        /* filesData is the link that loads tree data. This function refreshes that information. */
        self.updateFilesData = function _updateFilesData(linkObject) {
            if ((linkObject.type === 'node' || linkObject.type === 'registration') && self.viewOnly){
                return;
            }

            self.updateTbMultiselect([]); // clear multiselected, updateTreeData will repick
            self.updateFilter(linkObject); // Update what filters currently selected
            self.updateBreadcrumbs(linkObject); // Change breadcrumbs
            self.updateList(); // Reset and load item
            $('.tb-tbody-inner>div').css('margin-top' , '0px'); // We change contents of treebeard folder, we need to manage margin-top for view to work
            $('.tb-row-titles .fa').addClass('tb-sort-inactive');// make all toggle buttons inactive
            self.showSidebar(false);
        };

        // INFORMATION PANEL
        /* Defines the current selected item so appropriate information can be shown */
        self.selected = m.prop([]);
        self.updateSelected = function _updateSelected (selectedList){
            self.selected(selectedList);
            self.getCurrentLogs();
        };

        self.filterHistoryData = {
            undefined: {title: 'My Projects', name: ''},
            1: {title: 'My Registrations', name: '#registrations'},
            2: {title: 'My Preprints', name: '#preprints'}
        };

        /**
         * Sets the url history with filter param when filter is updated
         * @param index {Number} the filter id - 1 or index of the filter in the collections array
         */
        self.setFilterHistory = function(index) {
            // if not on the myprojects version of this page, don't change state (e.g., institutions)
            if (window.location.href.indexOf('/myprojects') === -1 ) {
                return;
            }
            var filter;
            if (index in self.filterHistoryData) {
                filter = self.filterHistoryData[index];
            }   else {
                filter = self.filterHistoryData[undefined];
            }
            // Uses replaceState instead of pushState because back buttons will not reset the filter on back without forcing a page refresh
            // A bug in history causes titles not to change despite setting them here.
            window.history.replaceState({setFilter: index}, 'OSF | ' + filter.title, '/myprojects/' + filter.name);
        };

        /**
         * Sets the initial filter based on href
         */
        self.getFilterIndex = function() {
            // if not on the myprojects version of this page, don't change state (e.g., institutions)
            if (window.location.href.indexOf('/myprojects') === -1 ) {
                return 0;
            }
            // Cast to string undefined => "undefined" to handle upper/lower case anchors
            var name = String(window.location.href.split('#')[1]).toLowerCase();
            switch(name) {
                case 'registrations':
                    return 1;
                case 'preprints':
                    return 2;
                default:
                    return 0;
            }
        };

        /**
         * Update the currentView
         * @param filter
         */
        self.updateFilter = function _updateFilter(filter) {
            // index for the filter is id - 1
            self.setFilterHistory(filter.id - 1);

            // if collection, reset currentView otherwise toggle the item in the list of currentview items
            if (['node', 'collection'].indexOf(filter.type) === -1 ) {
                var filterIndex = self.currentView()[filter.type].indexOf(filter);
                if(filterIndex !== -1)
                  self.currentView()[filter.type].splice(filterIndex,1);
                else
                  self.currentView()[filter.type].push(filter);

                return self.generateFiltersList();
            }

            if (self.currentView().fetcher)
              self.currentView().fetcher.pause();

            self.currentView().tag = [];
            self.currentView().contributor = [];

            self.currentView().fetcher = self.fetchers[filter.id];
            self.currentView().fetcher.resume();
            self.loadValue(self.currentView().fetcher.isFinished() ? 100 : self.currentView().fetcher.progress());

            self.generateFiltersList();

            if (filter.type === 'collection')
              self.currentView().collection = filter;
        };

        self.removeProjectFromCollections = function _removeProjectFromCollection () {
            // Removes selected items from collect
            var currentCollection = self.currentView().collection;
            var collectionNode = currentCollection.data.node; // If it's not a system collection like projects or registrations this will have a node

            var link_types = {'linked_nodes': {'data': []},
                              'linked_registrations': {'data': []},
                              'linked_preprints': {'data': []}};
            self.selected().map(function(item){
                if(item.data.type === 'nodes') {
                    link_types.linked_nodes.data.push({id: item.data.id,
                                                       type: 'linked_nodes'});
                } else if (item.data.type === 'registrations') {
                    link_types.linked_registrations.data.push({id: item.data.id,
                                                 type: 'linked_registrations'});
                } else {
                    link_types.linked_preprints.data.push({id: item.data.id,
                                                 type: 'linked_preprints'});
                }
            });

            $.each(link_types, function(link_type, data) {
                if(link_types[link_type].data.length > 0) {
                    m.request({
                        method : 'DELETE',
                        url : collectionNode.links.self + 'relationships/' + link_type  + '/',
                        config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}),
                        data : data
                    }).then(function(result) {
                      data.data.forEach(function(item) {
                          self.fetchers[currentCollection.id].remove(item.id);
                          currentCollection.data.count(currentCollection.data.count()-1);
                          self.updateSelected([]);
                      });
                      self.updateList();
                    }, function _removeProjectFromCollectionsFail(result){
                        var message = 'Some projects';
                        if(data.data.length === 1) {
                            message = self.selected()[0].data.name;
                        } else {
                            message += ' could not be removed from the collection';
                        }
                        $osf.growl(message, 'Please try again.', 'danger', 5000);
                    });
                }
            });
        };

        // remove this contributor from list of contributors
        self.unselectContributor = function (id){
            self.currentView().contributor.forEach(function (c, index, arr) {
                if(c.data.id === id){
                    self.updateFilesData(c);
                }
            });
        };

        self.unselectTag = function (tag){
            self.currentView().tag.forEach(function (t, index, arr) {
                if(t.data.tag === tag){
                    self.updateFilesData(t);
                }
            });
        };

        // Update what is viewed
        self.updateList = function _updateList (){
            if (!self.buildTree()) return; // Treebeard hasn't loaded yet
            var viewData = self.filteredData();
            self.updateTreeData(0, viewData, true);
            self.currentView().totalRows = viewData.length;
        };

        self.filteredData = function() {
            var tags = self.currentView().tag;
            var contributors = self.currentView().contributor;

            return self.currentView().fetcher._flat.filter(function(node) {
              var tagMatch = true;
              var contribMatch = true;

              for (var i = 0; i < contributors.length; i++)
                if (!node.contributorSet.has(contributors[i].data.id)) {
                  contribMatch = false;
                  break;
                }

              for (var j = 0; j < tags.length; j++)
                if (!node.tagSet.has(tags[j].label)) {
                  tagMatch = false;
                  break;
                }

              return tagMatch && contribMatch;
            });
        };

        self.updateTbMultiselect = function (itemsArray) {
          self.multiselected()(itemsArray);
          self.highlightMultiselect()();
          self.updateSelected(itemsArray);
        };

        self.updateTreeData = function (begin, data, clear) {
          var item;
            if (clear) {
              self.treeData().children = [];
            }
            for (var i = begin; i < data.length; i++){
                item = data[i];
                _formatDataforPO(item);
                var child = self.buildTree()(item, self.treeData());
                self.treeData().add(child);
            }
            self.updateFolder()(null, self.treeData());
            // Manually select first item without triggering a click
            if (self.treeData().children[0] && ((self.multiselected()().length === 0 && self.currentView().fetcher.isFinished()) || self.currentView().fetcher.forceRedraw === true)) {
              self.updateTbMultiselect([self.treeData().children[0]]);
            }
            m.redraw(true);
        };

        self.nonLoadTemplate = function (){
            var template = '';
            if(!self.currentView().fetcher.isEmpty()) {
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
                        if (self.institutionId) {
                            template = m('.db-non-load-template.m-md.p-md.osf-box',
                                'There have been no completed registrations for this institution, but you can view the ',
                                m('a', {href: 'https://osf.io/explore/activity/#newPublicRegistrations'}, 'newest public registrations'),
                                ' or ',
                                m('a', {href: 'https://osf.io/explore/activity/#popularPublicRegistrations'}, 'popular public registrations.'));
                        } else {
                            template = m('.db-non-load-template.m-md.p-md.osf-box',
                            'You have not made any registrations yet. Go to ',
                            m('a', {href: 'http://help.osf.io/m/registrations'}, 'Getting Started'), ' to learn how registrations work.' );
                        }
                    } else if (lastcrumb.data.nodeType === 'preprints'){
                        template = m('.db-non-load-template.m-md.p-md.osf-box', [m('span', 'You have not made any preprints yet. Learn more about preprints in the '), m('a[href="http://help.osf.io/m/preprints"]', 'OSF Guides'), m('span', ' or '), m('a[href="/preprints/"]', 'make one now.')]);
                    } else if (lodashGet(lastcrumb, 'data.node.attributes.bookmarks')) {
                        template = m('.db-non-load-template.m-md.p-md.osf-box', 'You have no bookmarks. You can add projects or registrations by dragging them into your bookmarks or by clicking the Add to Bookmark button on the project or registration.');
                    } else {
                        var helpText = 'This collection is empty.';
                        if (!self.viewOnly) {
                            helpText +=' You can add projects, registrations, or preprints by dragging them into the collection.';
                        }
                        template = m('.db-non-load-template.m-md.p-md.osf-box', helpText);
                    }
                } else {
                    if(!self.currentView().fetcher.isEmpty()){
                        template = m('.db-non-load-template.m-md.p-md.osf-box.text-center',
                            m('.ball-scale.text-center', m(''))
                        );
                    } else {
                        template = m('.db-non-load-template.m-md.p-md.osf-box.text-center', [
                            'No components to display. Either there are no components, or there are private components in which you are not a contributor.'
                        ]);
                    }
                }
            }


            return template;
        };

        /**
         * Generate this list from user's projects
         */
        self.generateFiltersList = function(noClear) {
            self.tags = {};
            self.users = {};

            self.filteredData().forEach(function(item) {
                var contributors = lodashGet(item, 'embeds.contributors.data', []);
                var isContributor = lodashFind(contributors, ['id', window.contextVars.currentUser.id]);
                if (contributors) {
                    for(var i = 0; i < contributors.length; i++) {
                        var u = contributors[i];
                        u.id = (u.id.indexOf('-') > -1) ? u.id.split('-')[1] : u.id;
                        if ((u.id === window.contextVars.currentUser.id) && !(self.institutionId)) {
                          continue;
                        }
                        if (!isContributor && !u.attributes.bibliographic) {
                            continue;
                        }

                        if(self.users[u.id] === undefined) {
                            self.users[u.id] = {
                                data : u,
                                count: 1,
                                unregistered_contributors: u.attributes.unregistered_contributor
                        };
                    } else {
                        self.users[u.id].count++;
                            var currentUnregisteredName = lodashGet(u, 'attributes.unregistered_contributor');
                            if (currentUnregisteredName) {
                                var otherUnregisteredName = lodashGet(self.users[u.id], 'unregistered_contributors');
                                if (otherUnregisteredName) {
                                     if (otherUnregisteredName.indexOf(currentUnregisteredName) === -1) {
                                         self.users[u.id].unregistered_contributors += ' a.k.a. ' + currentUnregisteredName;
                                     }
                                }
                                else {
                                    self.users[u.id].unregistered_contributors = currentUnregisteredName;
                                }
                            }
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

            var oldNameFilters = self.nameFilters;
            self.nameFilters = [];

            var userFinder = function(lo) {
                if (u2.unregistered_contributors) {
                    return lo.label === u2.unregistered_contributors;
                }
              return lo.label === u2.data.embeds.users.data.attributes.full_name;
            };

            // Add to lists with numbers
            for (var user in self.users) {
                var u2 = self.users[user];
                if (u2.data.embeds.users.data) {
                    var name;
                    if (u2.unregistered_contributors) {
                        name = u2.unregistered_contributors;
                    }
                    else {
                        name = u2.data.embeds.users.data.attributes.full_name;
                    }
                  var link = oldNameFilters.find(userFinder) || new LinkObject('contributor', {id: u2.data.id, count: u2.count, query: { 'related_counts' : 'children' }}, name, options.institutionId || false);
                  link.data.count = u2.count;
                  self.nameFilters.push(link);
                }
            }

            var oldTagFilters = self.tagFilters;
            self.tagFilters = [];

            var tagFinder = function(lo) {
              return lo.label === tag;
            };

            for (var tag in self.tags){
                var t2 = self.tags[tag];
                var tLink = oldTagFilters.find(tagFinder) || new LinkObject('tag', { tag : tag, count : t2, query : { 'related_counts' : 'children' }}, tag, options.institutionId || false);
                tLink.data.count = t2;
                self.tagFilters.push(tLink);
            }

            // order filters
            self.tagFilters.sort(sortByCountDesc);
            self.nameFilters.sort(sortByCountDesc);
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
                    self.fetchers[ancestorLink.id] = new NodeFetcher(item.data.types, item.data.relationships.children.links.related.href + '?embed=contributors');
                    self.fetchers[ancestorLink.id].on(['page', 'done'], self.onPageLoad);
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
            var promise = m.request({method : 'GET', url : url, config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})});
            promise.then(function(result){
                result.data.forEach(function(node){
                    var count = node.relationships.linked_registrations.links.related.meta.count + node.relationships.linked_nodes.links.related.meta.count + node.relationships.linked_preprints.links.related.meta.count;
                    self.collections().push(new LinkObject('collection', {nodeType : 'collection', node : node, count : m.prop(count), loaded: 1 }, $osf.decodeText(node.attributes.title)));
                    // TODO assess whether more sparse fields can be used
                    var preprintLink = $osf.apiV2Url('collections/' + node.id + '/linked_preprints/', { query : {'embed' : 'contributors', 'version': '2.2'}});
                    var regLink = $osf.apiV2Url('collections/' + node.id + '/linked_registrations/', { query : { 'related_counts' : 'children', 'embed' : 'contributors', 'version': '2.2', 'fields[registrations]' : sparseRegistrationFields}});
                    var link = $osf.apiV2Url('collections/' + node.id + '/linked_nodes/', { query : { 'related_counts' : 'children', 'embed' : 'contributors', 'fields[nodes]' : sparseNodeFields }});
                    self.fetchers[self.collections()[self.collections().length-1].id] = new NodeFetcher('nodes', link, false, 'registrations', regLink, 'preprints', preprintLink);
                    self.fetchers[self.collections()[self.collections().length-1].id].on(['page'], self.onPageLoad);
                });
                if(result.links.next){
                    self.loadCollections(result.links.next);
                }
            }, function(){
                var message = 'Collections could not be loaded.';
                $osf.growl(message, 'Please reload the page.');
                Raven.captureMessage(message, {extra: { url: url }});
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

        self.onPageLoad = function(fetcher, pageData) {
          if (!self.buildTree()) return; // Treebeard hasn't loaded yet
          if(self.currentView().fetcher === fetcher) {
              self.loadValue(fetcher.isFinished() ? 100 : fetcher.progress());
              self.generateFiltersList();
              if (!pageData) {
                for(var i = 0; i < fetcher._flat.length; i++){
                    var fetcherItem = fetcher._flat[i];
                    var tbItem = self.treeData().children[i] ? self.treeData().children[i].data : {};
                    if(fetcherItem === tbItem){
                        continue;
                    }
                    var itemToAdd = self.buildTree()(fetcherItem, self.treeData());
                    itemToAdd.parentID = self.treeData().id;
                    itemToAdd.open = false;
                    itemToAdd.load = false;
                    self.treeData().children.splice(i, 0, itemToAdd);
                }
                self.updateFolder()(null, self.treeData(), true);
                return m.redraw();
              }
              if(self.treeData().children){
                var begin = self.treeData().children.length;
                var data = self.filteredData();
                self.updateTreeData(begin, data);
                self.currentView().totalRows = fetcher._flat.length;
              }
          }
        };

        self.onLoadReset = function() {
            var current = self.currentView().fetcher;
            if (current.isFinished() && current.forceRedraw && !current.isEmpty()) {

                // If data loads before treebeard force redrawing
                self.loadValue(100);
                self.generateFiltersList();
                self.updateList();

                // Hack to force redraws when things get out of sync due to race condition
                // If the believed number of rows is different from the actual number, force another redraw
                if (!(self.currentView().totalRows === 0 && current._flat.length !== 0)) {
                    current.forceRedraw = false;
                }
                // TB/Mithril interaction requires the redraw to be called a bit later
                // TODO Figure out why
                setTimeout(m.redraw.bind(this, true), 250);
            }
        };

        self.init = function _init_fileBrowser() {
            self.loadCategories().then(function(){
                self.fetchers[self.systemCollections[0].id].on(['page', 'done'], self.onPageLoad);
                self.fetchers[self.systemCollections[1].id].on(['page', 'done'], self.onPageLoad);
                if(self.systemCollections[2]){
                    self.fetchers[self.systemCollections[2].id].on(['page', 'done'], self.onPageLoad);
                }
            });
            if (!self.viewOnly){
                // TODO use sparse fields
                var collectionsUrl = $osf.apiV2Url('collections/', { query : {'related_counts' : 'linked_registrations,linked_nodes,linked_preprints', 'page[size]' : self.collectionsPageSize(), 'sort' : 'date_created', 'embed' : 'linked_nodes'}});
                self.loadCollections(collectionsUrl);
            }
            // Add linkObject to the currentView
            var filterIndex = self.getFilterIndex();
            self.updateBreadcrumbs(self.collections()[filterIndex]);
            self.updateFilter(self.collections()[filterIndex]);
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
                onPageLoad: ctrl.onPageLoad,
                updateSelected : ctrl.updateSelected,
                updateFilesData : ctrl.updateFilesData,
                LinkObject : LinkObject,
                NodeFetcher : NodeFetcher,
                formatDataforPO : _formatDataforPO,
                wrapperSelector : args.wrapperSelector,
                resetUi : ctrl.resetUi,
                showSidebar : ctrl.showSidebar,
                loadValue : ctrl.loadValue,
                loadCounter : ctrl.loadCounter,
                treeData : ctrl.treeData,
                buildTree : ctrl.buildTree,
                updateFolder : ctrl.updateFolder,
                currentView: ctrl.currentView,
                fetchers : ctrl.fetchers,
                indexes : ctrl.indexes,
                multiselected : ctrl.multiselected,
                highlightMultiselect : ctrl.highlightMultiselect,
                _onload: function(tb) {
                    ctrl.onLoadReset();
                }
            },
            ctrl.projectOrganizerOptions
        );
        ctrl.onLoadReset();
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
                        var ap = this; // AddProject controller
                        // Fetch details of added item from server and redraw treebeard
                        var projects = ctrl.fetchers[ctrl.systemCollections[0].id];
                        projects.fetch(ap.saveResult().data.id).then(function(){
                          ctrl.updateSelected([]);
                          ctrl.multiselected()([]);
                          ctrl.updateTreeData(0, projects._flat, true);
                          ap.mapTemplates();
                        });
                    },
                    trackingCategory: 'myProjects',
                    trackingAction: 'add-project',
                    templatesFetcher: ctrl.fetchers[ctrl.systemCollections[0].id]
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
                    style : ctrl.currentView().fetcher.isEmpty() ? 'display: none' : 'display: block'
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
                self.totalPages(Math.ceil((result.meta.total + args.systemCollections.length)/self.pageSize()));
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
            var promise = m.request({method : 'POST', url : url, config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}), data : data});
            promise.then(function(result){
                var node = result.data;
                var count = node.relationships.linked_nodes.links.related.meta.count || 0;
                self.collections().push(new LinkObject('collection', { path : 'collections/' + node.id + '/linked_nodes/', query : { 'related_counts' : 'children' }, node : node, count : m.prop(count), nodeType : 'collection' }, $osf.decodeText(node.attributes.title)));
                var link = $osf.apiV2Url('collections/' + node.id + '/linked_nodes/', { query : { 'related_counts' : 'children', 'embed' : 'contributors'}});
                args.fetchers[self.collections()[self.collections().length-1].id] = new NodeFetcher('nodes', link);
                args.fetchers[self.collections()[self.collections().length-1].id].on(['page', 'done'], args.onPageLoad);

                self.newCollectionName('');
                self.calculateTotalPages();
                self.currentPage(self.totalPages()); // Go to last page
                args.sidebarInit();
            }, function(){
                var name = self.newCollectionName();
                var message = '"' + name + '" collection could not be created.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, {extra: { url: url, data : data }});
                self.newCollectionName('');
            });
            self.resetAddCollection();

            return promise;
        };
        self.resetAddCollection = function (){
            self.dismissModal();
            self.newCollectionName('');
            self.isValid(false);
            $('#addCollInput').val('');
        },
        self.deleteCollection = function _deleteCollection(){
            var url = self.collectionMenuObject().item.data.node.links.self;
            var promise = m.request({method : 'DELETE', url : url, config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})});
            promise.then(function(result){
                for ( var i = 0; i < self.collections().length; i++) {
                    var item = self.collections()[i];
                    if (item.data.node && item.data.node.id === self.collectionMenuObject().item.data.node.id) {
                        if (args.currentView().fetcher === args.fetchers[item.id])
                          args.updateFilesData(self.collections()[0]); // Reset to all my projects
                        delete args.fetchers[item.id];
                        self.collections().splice(i, 1);
                        break;
                    }
                }
                self.calculateTotalPages();
            }, function(){
                var name = self.collectionMenuObject().item.label;
                var message = '"' + name + '" could not be deleted.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, {extra: {collectionObject: self.collectionMenuObject() }});
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
            var promise = m.request({method : 'PATCH', url : url, config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}), data : data});
            promise.then(function(result){
                self.collectionMenuObject().item.label = title;
            }, function(){
                var name = self.collectionMenuObject().item.label;
                var message = '"' + name + '" could not be renamed.';
                $osf.growl(message, 'Please try again', 'danger', 5000);
                Raven.captureMessage(message, {extra: {collectionObject: self.collectionMenuObject() }});
            });
            self.dismissModal();
            self.isValid(false);
            return promise;
        };
        self.applyDroppable = function _applyDroppable ( ){
            $('.db-collections ul>li.acceptDrop').droppable({
                hoverClass: 'bg-color-hover',
                drop: function( event, ui ) {
                    var dataArray = [];
                    var collection = self.collections()[$(this).attr('data-index')];
                    // If multiple items are dragged they have to be selected to make it work
                    if (args.selected().length > 1) {
                        dataArray = args.selected().map(function(item){
                            return buildCollectionNodeData(item.data.id,
                                                           item.data.type);
                        });
                        $osf.trackClick('myProjects', 'projectOrganizer', 'multiple-projects-dragged-to-collection');
                    } else {
                        // if single items are passed use the event information
                        dataArray.push(buildCollectionNodeData(ui.draggable.find('.title-text>a').attr('data-nodeID'), ui.draggable.find('.title-text>a').attr('data-nodeType'))); // data-nodeID and data-nodeType attribute needs to be set in project organizer building title column
                        var projectName = ui.draggable.find('.title-text>a').attr('data-nodeTitle');
                        $osf.trackClick('myProjects', 'projectOrganizer', 'single-project-dragged-to-collection');
                    }

                    function save(index, data) {
                      if (!data[index])
                        return args.currentView().fetcher === args.fetchers[collection.id] ? args.updateList() : null;
                      m.request({
                          method : 'POST',
                          url : collection.data.node.links.self + 'relationships/' + data[index].data[0].type  + '/',
                          config : mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain}),
                          data : data[index]
                      }).then(function(result){
                          if (result){
                              return args.currentView().fetcher
                                .get(result.data[(result.data).length - 1].id)
                                .then(function(item) {
                                    args.fetchers[collection.id].add(item);
                                    collection.data.count(collection.data.count() + 1);
                                    save(index + 1, data);
                            });
                          }
                          else {
                              var name = projectName ? projectName : args.selected()[index] ? args.selected()[index].data.name : 'Item ';
                              var message = '"' + name + '" is already in "' + collection.label + '"' ;
                              $osf.growl(message,null, 'warning', 4000);
                              save(index + 1, data);
                          }
                      });
                    }

                    save(0, dataArray);
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
                e.stopPropagation();
                var index = $(this).attr('data-index');
                var selectedItem = ctrl.collections()[index];
                ctrl.updateCollectionMenu(selectedItem, e);
                $osf.trackClick('myProjects', 'edit-collection', 'open-edit-collection-menu');

            };
            for (var i = begin; i < end; i++) {
                item = ctrl.collections()[i];
                index = i;
                dropAcceptClass = index > 2 ? 'acceptDrop' : '';
                childCount = item.data.count ? ' (' + item.data.count() + ')' : '';
                if (args.currentView().collection === item) {
                    selectedCSS = 'active';
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
                list.push(m('li.pointer', {
                    className : selectedCSS + ' ' + dropAcceptClass,
                    'data-index' : index,
                    onclick : collectionOnclick.bind(null, item)
                  },[
                        m('span', item.label + childCount),
                        submenuTemplate
                    ]
                ));
            }
            return list;
        };
        var collectionListTemplate = [
            m('h5.clearfix', [
                'Collections ',
                 viewOnly ? '' : m('i.fa.fa-question-circle.text-muted', {
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
                            ctrl.resetAddCollection();
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
                                placeholder : 'e.g.  My Replications'
                            }),
                            m('span.help-block', ctrl.validationError())
                        ])
                    ]),
                    footer: m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]',
                            {
                                onclick : function(){
                                    ctrl.resetAddCollection();
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
                contributorsTemplate.push(m('span.filter-breadcrumb.myprojects', [
                    c.label,
                    ' ',
                    m('button', { onclick: function(){
                        args.unselectContributor(c.data.id);
                         $osf.trackClick('myProjects', 'filter', 'unselect-contributor');
                    }}, m('span', '×'))
                ]));
            });
        }
        if(args.currentView().tag.length){
            tagsTemplate.push(m('span.text-muted.m-l-sm', 'tagged '));
            args.currentView().tag.forEach(function(t){
                tagsTemplate.push(m('span.filter-breadcrumb.myprojects', [
                    t.label,
                    ' ',
                    m('button', { onclick: function(){
                        $osf.trackClick('myProjects', 'filter', 'unselect-tag');
                        args.unselectTag(t.data.tag);
                    }}, m('span', '×'))
                ]));
            });
        }
        var items = args.breadcrumbs();
        if (mobile && items.length > 1) {
            return m('.db-breadcrumbs', [
                m('ul', [
                    m('li', [
                        m('.btn.btn-link[data-toggle="modal"][data-target="#parentsModal"]', {onclick: function(){
                            $osf.trackClick('myProjects', 'mobile', 'open-ellipsis-parent-modal');
                        }}, '...'),
                        m('i.fa.fa-angle-right')
                    ]),
                    m('li', [
                      m('span.btn', items[items.length-1].label),
                      contributorsTemplate,
                      tagsTemplate
                    ])
                ]),
                m('#parentsModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-body', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', {onclick: function(){
                                    $osf.trackClick('myProjects', 'mobile', 'click-close-ellipsis-parent-modal');
                                }}, [
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
                                                $osf.trackClick('myProjects', 'mobile', 'open-parent-project');
                                                $('.modal').modal('hide');
                                                args.updateFilesData(item);
                                            }
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ])
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
            items.map(function(item, index, arr){
                if(index === arr.length-1){
                    if(item.type === 'node'){
                        var linkObject = args.breadcrumbs()[args.breadcrumbs().length - 1];
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
                                parentID: linkObject.data.id,
                                parentTitle: $osf.decodeText(linkObject.data.name),
                                modalID: 'addSubComponent',
                                title: 'Create new component',
                                categoryList: args.categoryList,
                                stayCallback: function () {
                                    var ap = this; // AddProject controller
                                    var topLevelProject = args.fetchers[linkObject.id];
                                    topLevelProject.fetch(ap.saveResult().data.id).then(function(newNode){
                                        if (args.breadcrumbs().length > 1) {
                                            var plo = args.breadcrumbs()[args.breadcrumbs().length-2];
                                            if (args.fetchers[plo.id] && args.fetchers[plo.id]._cache[linkObject.data.id]) {
                                                args.fetchers[plo.id]._cache[linkObject.data.id].open = false;
                                                args.fetchers[plo.id]._cache[linkObject.data.id].kind = 'folder';
                                                args.fetchers[plo.id]._cache[linkObject.data.id].children.unshift(newNode);
                                                args.fetchers[plo.id]._cache[linkObject.data.id].relationships.children.links.related.meta.count++;
                                            }
                                        }
                                        args.updateSelected([]);
                                        args.multiselected()([]);
                                        args.updateTreeData(0, topLevelProject._flat, true);
                                        ap.mapTemplates();
                                    });
                                },
                                trackingCategory: 'myProjects',
                                trackingAction: 'add-component',
                                contributors: Array.from(linkObject.data.contributorSet),
                                currentUserCanEdit: ~linkObject.data.attributes.current_user_permissions.indexOf('write')
                            });
                        }
                        return [
                            m('li', [
                                m('span.btn', $osf.decodeText(item.label)),
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
                    m('span.btn.btn-link', {onclick : updateFilesOnClick.bind(null, item)},  $osf.decodeText(item.label)),
                    index === 0 && arr.length === 1 ? [contributorsTemplate, tagsTemplate] : '',
                    m('i.fa.fa-angle-right'),
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
            if (args.currentView().fetcher.isEmpty() || args.nameFilters.length < 1)
                return m('.text-muted.text-smaller', 'No contributors to display in this collection. Project administrators can add contributors.');
            var list = [];
            var item;
            var i;
            var selectedCSS;
            if (ctrl.nameCurrentPage() > Math.ceil(args.nameFilters.length / ctrl.namePageSize()))
              ctrl.nameCurrentPage(Math.ceil(args.nameFilters.length / ctrl.namePageSize()));
            var begin = ((ctrl.nameCurrentPage()-1) * ctrl.namePageSize()); // remember indexes start from 0
            var end = ((ctrl.nameCurrentPage()) * ctrl.namePageSize()); // 1 more than the last item
            if (args.nameFilters.length < end) {
                end = args.nameFilters.length;
            }
            for (i = begin; i < end; i++) {
                item = args.nameFilters[i];
                selectedCSS = args.currentView().contributor.indexOf(item) !== -1 ? '.active' : '';
                list.push(m('li.pointer' + selectedCSS, {onclick : filterContributor.bind(null, item)},
                    m('span', item.label)
                ));
            }
            return list;
        };
        var returnTagFilters = function _returnTagFilters(){
            if (args.currentView().fetcher.isEmpty() || args.tagFilters.length < 1)
                return m('.text-muted.text-smaller', 'No tags to display in this collection. Project administrators and write contributors can add tags.');

            var list = [];
            var selectedCSS;
            var item;
            var i;
            if (ctrl.tagCurrentPage() > Math.ceil(args.tagFilters.length / ctrl.tagPageSize()))
              ctrl.tagCurrentPage(Math.ceil(args.tagFilters.length / ctrl.tagPageSize()));
            var begin = ((ctrl.tagCurrentPage()-1) * ctrl.tagPageSize()); // remember indexes start from 0
            var end = ((ctrl.tagCurrentPage()) * ctrl.tagPageSize()); // 1 more than the last item
            if (args.tagFilters.length < end) {
                end = args.tagFilters.length;
            }
            for (i = begin; i < end; i++) {
                item = args.tagFilters[i];
                selectedCSS = args.currentView().tag.indexOf(item) !== -1  ? '.active' : '';
                list.push(m('li.pointer' + selectedCSS, {onclick : filterTag.bind(null, item)},
                    m('span', item.label
                    )
                ));
            }
            return list;
        };
        return m('.db-filters.m-t-lg',
            [
                m('h5.m-t-sm', [
                    'Contributors ',
                    args.viewOnly ? '' : m('i.fa.fa-question-circle.text-muted', {
                        'data-toggle':  'tooltip',
                        'title': 'Click a contributor\'s name to see projects that you have in common.',
                        'data-placement' : 'bottom'
                    }, ''),
                    m('.pull-right',
                        args.nameFilters.length && ctrl.nameTotalPages() > 1 ? m.component(MicroPagination, { currentPage : ctrl.nameCurrentPage, totalPages : ctrl.nameTotalPages, type: 'contributors'}) : ''
                        )
                ]),
                m('ul', [
                    args.currentView().fetcher.loaded === 0 && !args.currentView().fetcher.isEmpty() ? m('.ball-beat.text-center.m-t-md', m('')) : returnNameFilters()
                ]),
                m('h5.m-t-sm', [
                    'Tags',
                    m('.pull-right',
                        args.tagFilters.length && ctrl.tagTotalPages() > 1 ? m.component(MicroPagination, { currentPage : ctrl.tagCurrentPage, totalPages : ctrl.tagTotalPages, type: 'tags' }) : ''
                        )
                ]), m('ul', [
                    args.currentView().fetcher.loaded === 0 && !args.currentView().fetcher.isEmpty() ? m('.ball-beat.text-center.m-t-md', m('')) : returnTagFilters()
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

        var template = '';
        var category;
        var showRemoveFromCollection;
        var collectionFilter = args.currentView().collection;
        if (args.selected().length === 0) {
            template = m('.db-info-empty.text-muted.p-lg', 'Select a row to view project details.');
        }
        if (args.selected().length === 1) {
            var item = args.selected()[0].data;
            var resourceType = item.type;
            var permission = item.attributes.current_user_permissions.slice(-1)[0];
            showRemoveFromCollection = collectionFilter.data.nodeType === 'collection' && args.selected()[0].depth === 1 && args.fetchers[collectionFilter.id]._flat.indexOf(item) !== -1; // Be able to remove top level items but not their children
            if (resourceType === 'preprints') {
                category = 'Preprint';
            } else {
                category = item.attributes.category === '' ? 'Uncategorized' : item.attributes.category;
            }
            template = m('.p-sm', [
                showRemoveFromCollection ? m('.clearfix', m('.btn.btn-default.btn-sm.btn.p-xs.text-danger.pull-right', { onclick : function() {
                    args.removeProjectFromCollections();
                    $osf.trackClick('myProjects', 'information-panel', 'remove-project-from-collection');
                } }, 'Remove from collection')) : '',
                    m('h3', m('a', { href : item.links.html, onclick: function(){
                        $osf.trackClick('myProjects', 'information-panel', 'navigate-to-project');
                    }}, $osf.decodeText(item.attributes.title))),
                m('[role="tabpanel"]', [
                    m('ul.nav.nav-tabs.m-b-md[role="tablist"]', [
                        m('li[role="presentation"].active', m('a[href="#tab-information"][aria-controls="information"][role="tab"][data-toggle="tab"]', {onclick: function(){
                            $osf.trackClick('myProjects', 'information-panel', 'open-information-tab');
                        }}, 'Information')),
                        resourceType === 'preprints' ? '' : m('li[role="presentation"]', m('a[href="#tab-activity"][aria-controls="activity"][role="tab"][data-toggle="tab"]', {onclick : function() {
                            args.getCurrentLogs();
                            $osf.trackClick('myProjects', 'information-panel', 'open-activity-tab');
                        }}, 'Activity'))
                    ]),
                    m('.tab-content', [
                        m('[role="tabpanel"].tab-pane.active#tab-information',[
                            m('p.db-info-meta.text-muted', [
                                resourceType === 'preprints' && item.attributes.reviews_state !== 'initial' && item.attributes.reviews_state !== null ? m('.text-capitalize', 'Status: ' + item.attributes.reviews_state) : resourceType === 'preprints' && item.attributes.date_withdrawn !== null ? 'Status: Withdrawn' : '',  // is a preprint, has a state, provider uses moderation
                                resourceType === 'preprints' && item.attributes.is_published === true ? m('.text-capitalize', 'Published: ' + item.attributes.is_published) : '',
                                m('', 'Visibility: ' + (item.attributes.public ? 'Public' : 'Private')),
                                m('', [
                                  m('span', 'Category: '),
                                  m('span', { className : mHelpers.getIcon(category) }),
                                  m('span.text-capitalize', ' ' + category)
                                ]),
                                m('.text-capitalize', 'Permission: ' + permission),
                                m('', 'Last Modified on: ' + (item.date ? item.date.local : ''))
                            ]),
                            m('p', [
                                m('span', {style: 'white-space:pre-wrap'}, $osf.decodeText(item.attributes.description))
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
                            item.type !== 'preprints' ? m.component(ActivityLogs, args) : ''
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
                    var resourceType = item.data.type;
                    if (resourceType === 'preprints') {
                        category = 'Preprint';
                    } else {
                        category = item.data.attributes.category === '' ? 'Uncategorized' : item.data.attributes.category;
                    }
                    return m('.db-info-multi', [
                        m('h4', m('a', { href : item.data.links.html, onclick: function(){
                            $osf.trackClick('myProjects', 'information-panel', 'navigate-to-project-multiple-selected');
                        }}, $osf.decodeText(item.data.attributes.title))),
                        m('p.db-info-meta.text-muted', [
                            resourceType === 'preprints'? m('span', (item.data.attributes.is_published ? 'Published' : 'Unpublished') + ' ' + category) : m('span', (item.data.attributes.public ? 'Public' : 'Private') + ' ' + category),
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
                var image = m('i.fa.fa-desktop');
                if (item.embeds.user && item.embeds.user.data) {
                    image = m('img', { src : item.embeds.user.data.links.profile_image});
                }
                else if (item.embeds.user && item.embeds.user.errors[0].meta){
                    image = m('img', { src : item.embeds.user.errors[0].meta.profile_image});
                }
                return m('.db-activity-item', [
                m('', [ m('.db-log-avatar.m-r-xs', image),
                    m.component(LogText.LogText, item)]),
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
    LinkObject: LinkObject,
    NodeFetcher: NodeFetcher,
};
