/**
 * Renders a log feed.
 *
 */
'use strict';
var ko = require('knockout');
var $ = require('jquery');
var moment = require('moment');
require('knockout-punches');
var $osf = require('osfHelpers');

ko.punches.enableAll();  // Enable knockout punches
/**
  * Log model.
  */
var Log = function(params) {
    var self = this;

    $.extend(self, params);
    self.date = new $osf.FormattableDate(params.date);
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
        return '<a class="contrib-link" href="/profile/' + person.id + '/">' + person.fullname + '</a>';
    };

    /**
      * Return whether a knockout template exists for the log.
      */
    self.hasTemplate = ko.computed(function() {
        return $('script#' + self.action).length > 0;
    });


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
                    ret += '<span>' + person.fullname + '</span>';
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
};

/**
  * View model for a log list.
  * @param {Log[]} logs An array of Log model objects to render.
  * @param hasMoreLogs boolean value if there are more logs or not
  * @param url the url ajax request post to
  */
var LogsViewModel = function(logs, hasMoreLogs, url) {
    var self = this;
    self.enableMoreLogs = ko.observable(hasMoreLogs);
    self.logs = ko.observableArray(logs);
    var pageNum=  0;
    self.url = url;

    //send request to get more logs when the more button is clicked
    self.moreLogs = function(){
        pageNum+=1;
        $.ajax({
            type: 'get',
            url: self.url,
            data:{
                pageNum: pageNum
            },
            cache: false
        }).done(function(response) {
            // Initialize LogViewModel
            var logModelObjects = createLogs(response.logs); // Array of Log model objects
            for (var i=0; i<logModelObjects.length; i++) {
                self.logs.push(logModelObjects[i]);
            }
            self.enableMoreLogs(response.has_more_logs);
        }).fail(
            $osf.handleJSONError
        );
    };

    self.tzname = ko.computed(function() {
        var logs = self.logs();
        if (logs.length) {
            var tz =  moment(logs[0].date).format('ZZ');
            return tz;
        }
        return '';
    });
};

/**
  * Create an Array of Log model objects from data returned from an endpoint
  * @param  {Object[]} logData Log data returned from an endpoint.
  * @return {Log[]}         Array of Log objects.
  */
var createLogs = function(logData){
    var mappedLogs = $.map(logData, function(item) {
        return new Log({
            'anonymous': item.anonymous,
            'action': item.action,
            'date': item.date,
            // The node type, either 'project' or 'component'
            // NOTE: This is NOT the component category (e.g. 'hypothesis')
            'nodeType': item.node.is_registration ? 'registration': item.node.node_type,
            'nodeCategory': item.node.category,
            'contributors': item.contributors,
            'nodeUrl': item.node.url,
            'userFullName': item.user.fullname,
            'userURL': item.user.url,
            'apiKey': item.api_key,
            'params': item.params,
            'nodeTitle': item.node.title,
            'nodeDescription': item.params.description_new
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


var initViewModel = function(self, logs, hasMoreLogs, url){
    self.logs = createLogs(logs);
    self.viewModel = new LogsViewModel(self.logs, hasMoreLogs, url);
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
    if (Array.isArray(data)) { // data is an array of log object from server
        initViewModel(self, data, self.options.hasMoreLogs, self.options.url);
    } else { // data is an URL
        $.getJSON(data, function(response) {
            initViewModel(self, response.logs, response.has_more_logs, data);
        });
    }
}

LogFeed.prototype.init = function() {
    var self = this;
    self.$progBar.hide();
    ko.cleanNode(self.$element[0]);
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = LogFeed;
