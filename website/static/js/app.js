/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */

////////////
// Models //
////////////

LOCAL_DATEFORMAT = "l h:mm A";
UTC_DATEFORMAT = "l H:mm UTC";

/**
 * A date object with two formats: local time or UTC time.
 * @param {String} date The original date as a string. Should be an standard
 *                      format such as RFC or ISO.
 */
var FormattableDate = function(date) {
    this.date = date;
    this.local = moment(date).format(LOCAL_DATEFORMAT);
    this.utc = moment.utc(date).format(UTC_DATEFORMAT);
}

var Log = function(params) {
    var self = this;
    self.action = params.action;
    self.date = new FormattableDate(params.date);
    self.nodeCategory = params.nodeCategory;
    self.nodeDescription = params.nodeDescription;
    self.nodeTitle = params.nodeTitle;
    self.contributor = params.contributor;
    self.contributors = params.contributors;
    self.nodeUrl = params.nodeUrl;
    self.userFullName = params.userFullName;
    self.userURL = params.userURL;
    self.apiKey = params.apiKey;
    self.params = params.params; // Extra log params
    self.wikiUrl = ko.computed(function() {
        return self.nodeUrl + "wiki/" + self.params.page;
    });

    /**
     * Given an item in self.contributors, return its anchor element representation.
     */
    self._asContribLink = function(person) {
        return '<a class="contrib-link" href="/profile/' + person.id + '/">'
                + person.fullname + "</a>"
    };

    /**
     * Return the html for a comma-delimited list of contributor links, formatted
     * with correct list grammar.
     * e.g. "Dasher and Dancer", "Comet, Cupid, and Blitzen"
     */
    self.displayContributors = ko.computed(function(){
        var ret = "";
        for(var i=0; i < self.contributors.length; i++){
            var person = self.contributors[i];
            if(i == self.contributors.length - 1 && self.contributors.length > 2){
                ret += " and ";
            }
            if (person.registered)
                ret += self._asContribLink(person);
            else
                ret += '<span>' + person.nr_name + '</span>';
            if (i < self.contributors.length - 1 && self.contributors.length > 2){
                ret += ", ";
            } else if (i < self.contributors.length - 1 && self.contributors.length == 2){
                ret += " and ";
            }
        }
        return ret;
    })
};


////////////////
// ViewModels //
////////////////


/**
 * View model for a log list.
 * @param {Log[]} logs An array of Log model objects to render.
 */
var LogsViewModel = function(logs) {
    var self = this;
    self.logs = ko.observableArray(logs);
    self.tzname = ko.computed(function() {
        var logs = self.logs();
        if (logs.length) {
            return moment(logs[0].date).format('ZZ');
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
            "action": item.action,
            "date": item.date,
            "nodeCategory": item.node.category,
            "contributor": item.contributor,
            "contributors": item.contributors,
            "nodeUrl": item.node.url,
            "userFullName": item.user.fullname,
            "userURL": item.user.url,
            "apiKey": item.api_key,
            "params": item.params,
            "nodeTitle": item.node.title,
            "nodeDescription": item.params.description_new
        })
    });
    return mappedLogs;
};

/**
 * Initialize the LogsViewModel. Fetches the logs data from the specified url
 * and binds the LogsViewModel.
 * @param  {String} scopeSelector CSS selector for the scope of the LogsViewModel.
 * @param  {String} url           The url from which to get the logs data.
 *                                The returned object must have a "logs" property mapped to
 *                                an Array of log objects.
 */
var initializeLogs = function(scopeSelector, url){
    // Initiate LogsViewModel
    $logScope = $(scopeSelector);
    ko.cleanNode($logScope[0]);
    progressBar = $("#logProgressBar");
    progressBar.show();
    $.ajax({
        url: url,
        type: "get", contentType: "application/json",
        dataType: "json",
        cache: false,
        success: function(data){
            // Initialize LogViewModel
            var logs = data['logs'];
            ko.cleanNode($logScope[0]);
            var logModelObjects = createLogs(logs);  // Array of Log model objects
            progressBar.hide();
            ko.applyBindings(new LogsViewModel(logModelObjects), $logScope[0]);
        }
    });
};

/**
 * The ProjectViewModel, scoped to the project header.
 * @param {Object} params The parsed project data returned from the project's API url.
 */
var ProjectViewModel = function(params) {
    var self = this;
    self._id = params.node.id;
    self.apiUrl = params.node.api_url;
    self.dateCreated = new FormattableDate(params.node.date_created);
    self.dateModified = new FormattableDate(params.node.date_modified);
    self.dateForked = new FormattableDate(params.node.forked_date);
    self.watchedCount = ko.observable(params.node.watched_count);
    self.userIsWatching = ko.observable(params.user.is_watching);
    self.userCanEdit = params.user.can_edit;
    self.description = params.node.description;
    self.title = params.node.title;
    // The button text to display (e.g. "Watch" if not watching)
    self.watchButtonDisplay = ko.computed(function() {
        var text = self.userIsWatching() ? "Unwatch" : "Watch"
        var full = text + " " +self.watchedCount().toString();
        return full;
    });

    // Editable Title and Description
    if (self.userCanEdit) {
        $('#nodeTitleEditable').editable({
            type:  'text',
            pk:    self._id,
            name:  'title',
            url:   self.apiUrl + 'edit/',
            ajaxOptions: {
                'type': 'POST',
                "dataType": "json",
                "contentType": "application/json"
            },
            params: function(params){
                // Send JSON data
                return JSON.stringify(params);
            },
            title: 'Edit Title',
            placement: 'bottom',
            success: function(data){
                document.location.reload(true);
            }
        });
        // TODO(sloria): Repetition here. Rethink.
        $('#nodeDescriptionEditable').editable({
            type:  'text',
            pk:    self._id,
            name:  'description',
            url:   self.apiUrl + 'edit/',
            ajaxOptions: {
                'type': 'POST',
                "dataType": "json",
                "contentType": "application/json"
            },
            params: function(params){
                // Send JSON data
                return JSON.stringify(params);
            },
            title: 'Edit Description',
            placement: 'bottom',
            success: function(data){
                document.location.reload(true);
            },
            emptytext: "No description",
            emptyclass: "text-muted"
        });
    }

    /**
     * Toggle the watch status for this project.
     */
    self.toggleWatch = function() {
        // Send POST request to node's watch API url and update the watch count
        $.ajax({
            url: self.apiUrl + "togglewatch/",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({}),
            contentType: "application/json",
            success: function(data, status, xhr) {
                // Update watch count in DOM
                self.userIsWatching(data['watched']);
                self.watchedCount(data['watchCount']);
            }
        });
    };
};


function attrMap(list, attr) {
    return $.map(list, function(item) {
        return item[attr];
    });
}

NODE_OFFSET = 25;

/**
 * The add contributor VM, scoped to the add contributor modal dialog.
 */
var AddContributorViewModel = function(title, parentId, parentTitle) {

    var self = this;

    self.title = title;
    self.parentId = parentId;
    self.parentTitle = parentTitle;

    self.page = ko.observable('whom');
    self.pageTitle = ko.computed(function() {
        return {
            whom: 'Add contributors',
            which: 'Select components'
        }[self.page()];
    });

    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();
    self.errorMsg = ko.observable('');

    self.nodes = ko.observableArray([]);
    self.nodesToChange = ko.observableArray();
    $.getJSON(
        nodeApiUrl + 'get_editable_children/',
        {},
        function(result) {
            $.each(result['children'] || [], function(idx, child) {
                child['margin'] = NODE_OFFSET + child['indent'] * NODE_OFFSET + 'px';
            });
            self.nodes(result['children']);
        }
    );

    self.selectWhom = function() {
        self.page('whom');
    };
    self.selectWhich = function() {
        self.page('which');
    };

    self.search = function() {
        self.errorMsg('');
        $.getJSON(
            '/api/v1/user/search/',
            {query: self.query()},
            function(result) {
                if (!result.users.length) {
                    self.errorMsg('No results found.');
                }
                self.results(result['users']);
            }
        )
    };

    self.importFromParent = function() {
        self.errorMsg('');
        $.getJSON(
            nodeApiUrl + 'get_contributors_from_parent/',
            {},
            function(result) {
                if (!result.contributors.length) {
                    self.errorMsg('All contributors from parent already included.');
                }
                self.results(result['contributors']);
            }
        )
    };

    self.recentlyAdded = function() {
        self.errorMsg('');
        $.getJSON(
            nodeApiUrl + 'get_recently_added_contributors/',
            {},
            function(result) {
                if (!result.contributors.length) {
                    self.errorMsg('All recently added contributors already included.');
                }
                self.results(result['contributors']);
            }
        )
    };


    self.addTips = function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };


    self.add = function(data) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };


    self.remove = function(data) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.addAll = function() {
        $.each(self.results(), function(idx, result) {
            if (self.selection().indexOf(result) == -1) {
                self.add(result);
            }
        });
    };

    self.removeAll = function() {
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    };

    self.cantSelectNodes = function() {
        return self.nodesToChange().length == self.nodes().length;
    };
    self.cantDeselectNodes = function() {
        return self.nodesToChange().length == 0;
    };

    self.selectNodes = function() {
        self.nodesToChange(attrMap(self.nodes(), 'id'));
    };
    self.deselectNodes = function() {
        self.nodesToChange([]);
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id == self.selection()[idx].id)
                return true;
        }
        return false;
    };


    self.addingSummary = ko.computed(function() {
        var names = $.map(self.selection(), function(result) {
            return result.fullname
        });
        return names.join(', ');
    });

    self.submit = function() {
        var user_ids = attrMap(self.selection(), 'id');
        $.ajax(
            nodeApiUrl + 'addcontributors/',
            {
                type: 'post',
                data: JSON.stringify({
                    user_ids: user_ids,
                    node_ids: self.nodesToChange()
                }),
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
        self.page('whom');
        self.query('');
        self.results([]);
        self.selection([]);
        self.nodesToChange([]);
    };

};

var AddPointerViewModel = function(nodeTitle) {

    var self = this;

    self.TITLES = {
        'addPointer': 'Add pointers from {title} to other projects',
        'addAsPointer': 'Add pointers to {title} from other projects'
    };

    self.nodeTitle = nodeTitle;

    self.mode = ko.observable();
    self.title = ko.computed(function() {
        if (self.mode()) {
            return self.TITLES[self.mode()].replace('{title}', self.nodeTitle);
        }
    });

    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();
    self.errorMsg = ko.observable('');

    self.search = function(includePublic) {
        self.errorMsg('');
        $.ajax({
            type: 'POST',
            url: '/api/v1/search/node/',
            data: JSON.stringify({
                query: self.query(),
                nodeId: nodeId,
                includePublic: includePublic,
                ignorePointers: self.mode() == 'addAsPointer'
            }),
            contentType: 'application/json',
            dataType: 'json',
            success: function(result) {
                if (!result.nodes.length) {
                    self.errorMsg('No results found.');
                }
                self.results(result['nodes']);
            }
        })
    };

    self.addTips = function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };

    self.add = function(data) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.remove = function(data) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.addAll = function() {
        $.each(self.results(), function(idx, result) {
            if (self.selection().indexOf(result) == -1) {
                self.add(result);
            }
        });
    };

    self.removeAll = function() {
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id == self.selection()[idx].id)
                return true;
        }
        return false;
    };

    self.submit = function() {
        var node_ids = attrMap(self.selection(), 'id');
        $.ajax({
            type: 'post',
            url: nodeApiUrl + 'pointer/',
            data: JSON.stringify({
                node_ids: node_ids,
                mode: self.mode()
            }),
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                window.location.reload();
            }
        });
    };

    self.clear = function() {
        self.query('');
        self.results([]);
        self.selection([]);
    };

    self.authorText = function(node) {
        rv = node.firstAuthor;
        if (node.etal) {
            rv += ' et al.';
        }
        return rv;
    }

};

//////////////////
// Data binders //
//////////////////

/**
 * Tooltip data binder. The value accessor should be an object containing
 * parameters for the tooltip.
 * Example:
 * <span data-bind="tooltip: {title: 'Tooltip text here'}"></span>
 */
ko.bindingHandlers.tooltip = {
    init: function(elem, valueAccessor) {
        $(elem).tooltip(valueAccessor())
    }
};

///////////
// Piwik //
///////////

var trackPiwik = function(host, siteId, cvars, useCookies) {
    cvars = Array.isArray(cvars) ? cvars : [];
    useCookies = typeof(useCookies) !== 'undefined' ? useCookies : false;
    try {
        var piwikTracker = Piwik.getTracker(host + 'piwik.php', siteId);
        piwikTracker.enableLinkTracking(true);
        for(var i=0; i<cvars.length;i++)
        {
            piwikTracker.setCustomVariable.apply(null, cvars[i]);
        }
        if (!useCookies) {
            piwikTracker.disableCookies();
        }
        piwikTracker.trackPageView();

    } catch(err) { return false; }
    return true;
}
