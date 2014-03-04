/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */
// TODO: Currently, these all pollute global namespace. Move these to their
// own module.

////////////////
// ViewModels //
////////////////



/**
 * View model for a log list.
 * @param {Log[]} logs An array of Log model objects to render.
 */
var LogsViewModel = function(logs, url) {
    if (logs.length<10){
        $(".moreLogs").css("display",'none');
    }
    var self = this;
    self.logs = ko.observableArray(logs);
    var page_num=  0;
    self.url = url;

    //send request to get more logs when the more button is clicked
    self.moreLogs = function(){
        page_num+=1;
        $.ajax({
            url: self.url,
            data:{
                pageNum:page_num
            },
            type: "get",
            cache: false,
            success: function(response){
                // Initialize LogViewModel
                var logs = response['logs'];
                if (logs.length<10){
                    $(".moreLogs").css("display",'none');
                }
                var logModelObjects = createLogs(logs);  // Array of Log model objects
                for(var i=0;i<logModelObjects.length;i++)
                {
                    self.logs.push(logModelObjects[i]);
                }
            }
        });
    };

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
        url: url+'watched/logs/',
        type: "get",
        contentType: "application/json",
        dataType: "json",
        cache: false,
        success: function(data){
            // Initialize LogViewModel
            var logs = data['logs'];
            ko.cleanNode($logScope[0]);
            var logModelObjects = createLogs(logs);  // Array of Log model objects
            progressBar.hide();
            logsViewModel = new LogsViewModel(logModelObjects, url+'watched/logs/');

            ko.applyBindings(logsViewModel, $logScope[0]);
        }
    });
};


var LinksViewModel = function(elm) {

    var self = this;
    self.links = ko.observableArray([]);

    $(elm).on('shown.bs.modal', function() {
        if (self.links().length == 0) {
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json',
                success: function(response) {
                    self.links(response.pointed);
                },
                error: function() {
                    elm.modal('hide');
                    bootbox.alert('Could not get links');
                }
            });
        }
    });

};

function attrMap(list, attr) {
    return $.map(list, function(item) {
        return item[attr];
    });
}


var AddPointerViewModel = function(nodeTitle) {

    var self = this;

    self.nodeTitle = nodeTitle;

    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();
    self.errorMsg = ko.observable('');

    self.search = function(includePublic) {
        self.results([]);
        self.errorMsg('');
        $.ajax({
            type: 'POST',
            url: '/api/v1/search/node/',
            data: JSON.stringify({
                query: self.query(),
                nodeId: nodeId,
                includePublic: includePublic
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
        var nodeIds = attrMap(self.selection(), 'id');
        $.ajax({
            type: 'post',
            url: nodeApiUrl + 'pointer/',
            data: JSON.stringify({
                nodeIds: nodeIds
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
