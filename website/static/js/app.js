/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */

////////////
// Models //
////////////

/**
 * The project model.
 */
var Project = function(params) {
    var self = this;
    self._id =  params._id;
    self.apiUrl = params.apiUrl;
    self.watchedCount = ko.observable(params.watchCount);
    self.userIsWatching = ko.observable(params.userIsWatching);
    // The button to display (e.g. "Watch" if not watching)
    self.watchButtonDisplay = ko.computed(function() {
        var text = self.userIsWatching() ? "Unwatch" : "Watch"
        var full = text + " " +self.watchedCount().toString();
        return full;
    });
}

var Log = function(params) {
    var self = this;
    self.action = params.action;
    self.date = params.date;
    self.nodeCategory = params.nodeCategory;
    self.nodeTitle = params.nodeTitle;
    self.contributor = params.contributor;
    self.contributors = params.contributors;
    self.nodeUrl = params.nodeUrl;
    self.userFullName = params.userFullName;
    self.apiKey = params.apiKey;
    self.params = params.params; // Extra log params
    self.wikiUrl = ko.computed(function() {
        return self.nodeUrl + "wiki/" + self.params.page;
    })

    self.localDatetime = ko.computed(function() {
        return moment(self.date).format("l h:mm A")
    })
}


////////////////
// ViewModels //
////////////////


var LogsViewModel = function(url) {
    var self = this;
    self.logs = ko.observableArray([]);
    // Get log data via AJAX
    var getUrl = '';
    if (url) {
        getUrl = url;
    } else {
        getUrl = nodeToUseUrl() + "log/";
    };
    $.ajax({
        url: getUrl,
        type: "get",
        dataType: "json",
        success: function(data){
            var logs = data['logs'];
            var mappedLogs = $.map(logs, function(item) {
                return new Log({
                    "action": item.action,
                    "date": item.date,
                    "nodeCategory": item.category,
                    "contributor": item.contributor,
                    "contributors": item.contributors,
                    "nodeUrl": item.node_url,
                    "userFullName": item.user_fullname,
                    "apiKey": item.api_key,
                    "params": item.params,
                    "nodeTitle": item.node_title
                })
            })
            self.logs(mappedLogs);
        }
    })
}

/**
 * The project VM, scoped to the project page header.
 */
var ProjectViewModel = function() {
    var self = this;
    self.projects = ko.observableArray([{"watchButtonDisplay": ""}]);
    $.ajax({
        url: nodeToUseUrl(),
        type: "get", contentType: "application/json",
        dataType: "json",
        success: function(data){
            project = new Project({
                "_id": data.node_id,
                "apiUrl": data.node_api_url,
                "watchCount": data.node_watched_count,
                "userIsWatching": data.user_is_watching,
                "logs": data.logs
            });
            self.projects([project]);
        }
    });

    /**
     * Toggle the watch status for this project.
     */
    self.toggleWatch = function() {
        // Send POST request to node's watch API url and update the watch count
        $.ajax({
            url: self.projects()[0].apiUrl + "togglewatch/",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({}),
            contentType: "application/json",
            success: function(data, status, xhr) {
                // Update watch count in DOM
                self.projects()[0].userIsWatching(data['watched']);
                self.projects()[0].watchedCount(data['watchCount']);
            }
        });
    };
}

/**
 * The add contributor VM, scoped to the add contributor modal dialog.
 */
var AddContributorViewModel = function(initial) {

    var self = this;

    self.query = ko.observable('');
    self.results = ko.observableArray(initial);
    self.selection = ko.observableArray([]);

    self.search = function() {
        $.getJSON(
            '/api/v1/user/search/',
            {query: self.query()},
            function(result) {
                self.results(result);
            }
        )
    };

    self.addTips = function(elements, data) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };

    self.add = function(data, element) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.remove = function(data, element) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id == self.selection()[idx].id)
                return true;
        }
        return false;
    };

    self.submit = function() {
        var user_ids = self.selection().map(function(elm) {
            return elm.id;
        });
        $.ajax(
            nodeToUseUrl() + 'addcontributors/',
            {
                type: 'post',
                data: JSON.stringify({user_ids: user_ids}),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    if (response.status === 'success') {
                        window.location.reload();
                    }
                }
            }
        )
    };

    self.clear = function() {
        self.query('');
        self.results([]);
        self.selection([]);
    };

};

//////////////////
// Data binders //
//////////////////


ko.bindingHandlers.tooltip = {
    init: function(elem, valueAccessor) {
        $(elem).tooltip(valueAccessor())
    }
}

