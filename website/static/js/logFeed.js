/**
 * Renders a log feed.
 *
 */
'use strict';
var ko = require('knockout');
var $ = require('jquery');
var moment = require('moment');
var Paginator = require('js/paginator');
var oop = require('js/oop');
require('knockout.punches');

var $osf = require('js/osfHelpers');  // Injects 'listing' binding handler to to Knockout
var nodeCategories = require('json!built/nodeCategories.json');

ko.punches.enableAll();  // Enable knockout punches

/**
  * Log model.
  */
var Log = function(params) {
    var self = this;

    $.extend(self, params);
    self.date = new $osf.FormattableDate(params.date);

    if(params.params.submitted_time)
        self.params.submitted_time = new $osf.FormattableDate(params.params.submitted_time);

    self.wikiUrl = ko.computed(function() {
        return self.nodeUrl + 'wiki/' + encodeURIComponent(self.params.page);
    });
    self.wikiIdUrl = ko.computed(function() {
        return self.nodeUrl + 'wiki/id/' + encodeURIComponent(self.params.page_id);
    });

    /**
      * Given an item in self.contributors, return its anchor element representation.
      */
    self._asContribLink = function(person) {
        var fullnameText = $osf.htmlEscape(person.fullname);
        return '<a class="contrib-link" href="/profile/' + person.id + '/">' + fullnameText + '</a>';
    };

    self.hasUser = ko.pureComputed(function() {
        return Boolean(self.user && self.user.fullname);
    });

    /**
      * Return whether a knockout template exists for the log.
      */
    self.hasTemplate = ko.computed(function() {
        if (!self.hasUser()) {
            return $('script#' + self.action + '_no_user').length > 0;
        } else {
            return $('script#' + self.action).length > 0;
        }
    });

    self.mapUpdates = function(key, item) {
        if (key === 'category') {
            return key + ' to ' + nodeCategories[item['new']];
        }
        else {
            return key + ' to ' + item;
        }
    };

    /**
      * Return the html for a comma-delimited list of contributor links, formatted
      * with correct list grammar.
      * e.g. "Dasher and Dancer", "Comet, Cupid, and Blitzen"
      */
    self.displayContributors = ko.computed(function(){
        var ret = '';
        if (self.anonymous){
            ret += '<span class="contributor-anonymous">some anonymous contributor(s)</span>';
        } else {
            for (var i = 0; i < self.contributors.length; i++) {
                var person = self.contributors[i];
                if (i === self.contributors.length - 1 && self.contributors.length > 2) {
                    ret += ' and ';
                }
                if (person.registered) {
                    ret += self._asContribLink(person);
                } else {
                    var fullnameText = $osf.htmlEscape(person.fullname);
                    ret += '<span>' + fullnameText + '</span>';
                }
                if (i < self.contributors.length - 1 && self.contributors.length > 2) {
                    ret += ', ';
                } else if (i < self.contributors.length - 1 && self.contributors.length === 2) {
                    ret += ' and ';
                }
            }
        }
        return ret;
    });

    //helper function to strip the slash for file or folder in log template
    self.stripSlash = function(path){
        return path.replace(/(^\/)|(\/$)/g, '');
    };

    //helper funtion to determine the type for removing in log template
    self.pathType = function(path){
        return path.match(/\/$/) ? 'folder' : 'file';
    };
};

/**
  * View model for a log list.
  * @param {Log[]} logs An array of Log model objects to render.
  * @param url the url ajax request post to
  */
var LogsViewModel = oop.extend(Paginator, {
    constructor: function(logs, url) {
        this.super.constructor.call(this);
        var self = this;
        self.loading = ko.observable(false);
        self.logs = ko.observableArray(logs);
        self.url = url;
        self.anonymousUserName = '<em>A user</em>';

        self.tzname = ko.pureComputed(function() {
            var logs = self.logs();
            if (logs.length) {
                var tz =  moment(logs[0].date.date).format('ZZ');
                return tz;
            }
            return '';
        });
    },
    //send request to get more logs when the more button is clicked
    fetchResults: function(){
        var self = this;
        self.loading(true); // show loading indicator

        return $.ajax({
            type: 'get',
            url: self.url,
            data:{
                page: self.pageToGet()
            },
            cache: false
        }).done(function(response) {
            // Initialize LogViewModel
            var logModelObjects = createLogs(response.logs); // Array of Log model objects
            self.logs.removeAll();
            for (var i=0; i<logModelObjects.length; i++) {
                self.logs.push(logModelObjects[i]);
            }
            self.currentPage(response.page);
            self.numberOfPages(response.pages);
            self.addNewPaginators();
        }).fail(
            $osf.handleJSONError
        ).always( function (){
            self.loading(false);
        });

    }
});


/**
  * Create an Array of Log model objects from data returned from an endpoint
  * @param  {Object[]} logData Log data returned from an endpoint.
  * @return {Log[]}         Array of Log objects.
  */
var createLogs = function(logData){
    var mappedLogs = $.map(logData, function(item) {
        return new Log({
            anonymous: item.anonymous,
            action: item.action,
            date: item.date,
            // The node type, either 'project' or 'component'
            // NOTE: This is NOT the component category (e.g. 'hypothesis')
            nodeType: item.node.is_registration ? 'registration': item.node.node_type,
            nodeCategory: item.node.category,
            contributors: item.contributors,
            nodeUrl: item.node.url,
            userFullName: item.user.fullname,
            userURL: item.user.url,
            params: item.params,
            nodeTitle: item.node.title,
            nodeDescription: item.params.description_new,
            nodePath: item.node.path,
            user: item.user,
            isActive: item.user.is_active,
            registrationCancelled: item.node.is_registration && item.node.registered_from_id == null
        });
    });
    return mappedLogs;
};

////////////////
// Public API //
////////////////

var defaults = {
    /** Selector for the progress bar. */
    progBar: '#logProgressBar'
};


var initViewModel = function(self, logs, url){
    self.logs = createLogs(logs);
    self.viewModel = new LogsViewModel(self.logs, url);
    if(url) {
        self.viewModel.fetchResults();
    }
    self.init();
};

/**
  * A log list feed.
  * @param {string} selector
  * @param {string} url
  * @param {object} options
  */
function LogFeed(selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.options = $.extend({}, defaults, options);
    self.$progBar = $(self.options.progBar);
    //for recent activities logs
    if (Array.isArray(data)) { // data is an array of log object from server
        initViewModel(self, data, self.options.url);
    } else { // data is an URL, for watch logs and project logs
        var noLogs =[];
        initViewModel(self, noLogs, data);
    }
}

LogFeed.prototype.init = function() {
    var self = this;
    self.$progBar.hide();
    ko.cleanNode(self.$element[0]);
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = LogFeed;
