/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */
// TODO: Currently, these all pollute global namespace. Either use some module
// system, e.g. requirejs, or use namespaces, e.g. "OSFViewModels.LogsViewModel"



////////////////
// ViewModels //
////////////////

PRIVACY_OPTIONS = [true, false];

PRIVACY_MAP = {
    true: 'Public',
    false: 'Private'
};

privacyLabel = function(item) {
    return PRIVACY_MAP[item];
};

var BaseComment = function() {

    var self = this;

    self.replyVisible = ko.observable(false);
    self.replyContent = ko.observable('');
    self.replyPublic = ko.observable(true);

    self.comments = ko.observableArray();
    self.displayComments = ko.computed(function() {
        return ko.utils.arrayFilter(self.comments(), function(comment) {
            return !comment.isSpam();
        });
    });

};

BaseComment.prototype.showReply = function() {
    this.replyVisible(true);
};

BaseComment.prototype.cancelReply = function() {
    this.replyVisible(false);
};

BaseComment.prototype.submitReply = function() {
    var self = this;
    $.postJSON(
        nodeApiUrl + 'comment/',
        {
            target: self.id,
            content: self.replyContent(),
            isPublic: self.replyPublic()
        },
        function(response) {
            self.cancelReply();
            self.replyContent(null);
            self.comments.push(new CommentViewModel(response.comment, self));
            self.onSubmitSuccess(response);
        }
    );
};

BaseComment.prototype.expandToDepth = function(depth) {
    if (depth > 0) {
        var commentDeferred = this.fetch();
        if (this.showChildren) {
            this.showChildren(true);
        }
        commentDeferred.done(function(comments) {
            for (var i=0; i<comments.length; i++) {
                comments[i].expandToDepth(depth - 1);
            }
        });
    } else {
        this.showChildren(false);
    }
};

// TODO: Move me
var CommentViewModel = function(data, $parent) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    $.extend(self, data);
    self.$parent = $parent;

    self.isPublic = ko.observable(self.isPublic);
    self.isSpam = ko.observable(self.isSpam);
    self.content = ko.observable(self.content);

    self._loaded = false;
    self.showChildren = ko.observable(false);
    self.editing = ko.observable(false);
    self.editVerb = self.modified ? 'edited' : 'posted';

    self.publicIcon = ko.computed(function() {
        return self.isPublic() ? 'icon-unlock-alt' : 'icon-lock';
    });

};

CommentViewModel.prototype = new BaseComment();

CommentViewModel.prototype.fetch = function() {
    var self = this;
    var deferred = $.Deferred();
    if (self._loaded) {
        deferred.resolve(self.comments());
    }
    $.getJSON(
        nodeApiUrl + 'comments/',
        {target: self.id},
        function(response) {
            self.comments(
                ko.utils.arrayMap(response.comments, function(comment) {
                    return new CommentViewModel(comment, self);
                })
            );
            deferred.resolve(self.comments());
            self._loaded = true;
        }
    );
    return deferred;
};

CommentViewModel.prototype.edit = function() {
    this._content = this.content();
    this._isPublic = this.isPublic();
    this.editing(true);
};

CommentViewModel.prototype.cancelEdit = function() {
    this.editing(false);
    this.content(this._content);
    this.isPublic(this._isPublic);
};

CommentViewModel.prototype.submitEdit = function() {
    var self = this;
    $.postJSON(
        nodeApiUrl + 'comment/' + this.id + '/',
        {
            cid: self.id,
            content: self.content(),
            isPublic: self.isPublic()
        },
        function(response) {
            self.content(response.content);
            self.editing(false);
        }
    ).fail(function() {
        self.cancelEdit();
    });
};

CommentViewModel.prototype.reportSpam = function() {
    var self = this;
    $.postJSON(
        nodeApiUrl + 'comment/' + this.id + '/report/spam/',
        {isSpam: !self.isSpam()},
        function(response) {
            self.isSpam(!self.isSpam());
        }
    )
};

CommentViewModel.prototype.remove = function() {
    var self = this;
    $.ajax({
        type: 'DELETE',
        url: nodeApiUrl + 'comment/' + this.id + '/',
        success: function(response) {
            var siblings = self.$parent.comments;
            siblings.splice(siblings.indexOf(self), 1);
        }
    });
};

CommentViewModel.prototype.toggle = function () {
    this.fetch();
    this.showChildren(!this.showChildren());
};

CommentViewModel.prototype.onSubmitSuccess = function(response) {
    this.showChildren(true);
};

// TODO: Move me
var CommentsViewModel = function() {
    BaseComment.prototype.constructor.call(this);
    this.fetch();
};

CommentsViewModel.prototype = new BaseComment();

CommentsViewModel.prototype.fetch = function() {
    var self = this;
    var deferred = $.Deferred();
    $.getJSON(
        nodeApiUrl + 'comments/',
        function(response) {
            self.comments(
                ko.utils.arrayMap(response.comments, function(comment) {
                    return new CommentViewModel(comment, self);
                })
            );
            deferred.resolve(self.comments());
        }
    );
    return deferred;
};

CommentsViewModel.prototype.onSubmitSuccess = function() {};

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
};
