/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */
// TODO: Currently, these all pollute global namespace. Either use some module
// system, e.g. requirejs, or use namespaces, e.g. "OSFViewModels.LogsViewModel"



////////////////
// ViewModels //
////////////////

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
            which: 'Select components',
            invite: 'Add An Unregistered User'
        }[self.page()];
    });
    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();
    self.errorMsg = ko.observable('');
    self.inviteError = ko.observable('');

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

    self.inviteName = ko.observable();
    self.inviteEmail = ko.observable();

    self.selectWhom = function() {
        self.page('whom');
    };
    self.selectWhich = function() {
        self.page('which');
    };

    self.gotoInvite = function() {
        self.inviteName(self.query());
        self.inviteError('');
        self.inviteEmail('');
        self.page('invite');
    }

    self.search = function() {
        self.errorMsg('');
        if (self.query()) {
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
        } else {
            self.results([]);
        }
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

    function postInviteRequest(fullname, email, options) {
        var ajaxOpts = $.extend({
            url: nodeApiUrl + 'invite_contributor/',
            type: 'POST',
            data: JSON.stringify({'fullname': fullname, 'email': email}),
            dataType: 'json', contentType: 'application/json'
        }, options);
        return $.ajax(ajaxOpts);
    };

    function onInviteSuccess(result) {
        self.page('whom');
        self.add(result.contributor);
    }

    function onInviteError(xhr, status, error) {
        var response = JSON.parse(xhr.responseText);
        // Update error message
        self.inviteError(response.message);
    }

    self.sendInvite = function() {
        self.inviteError('');
        return postInviteRequest(self.inviteName(), self.inviteEmail(),
            {
                success: onInviteSuccess,
                error: onInviteError
            }
        );
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
