/**
* Controller for the comments.
*/
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var moment = require('moment');
require('knockout-mapping');
require('knockout-punches');
require('jquery-autosize');
ko.punches.enableAll();

var osfHelpers = require('osfHelpers');
var CommentPane = require('./commentpane.js');

var nodeApiUrl = window.contextVars.node.urls.api;
var nodeUrl = '/' + window.contextVars.node.id + '/';

// Maximum length for comments, in characters
var MAXLENGTH = 500;
var MAXLEVEL = 5;

var ABUSE_CATEGORIES = {
    spam: 'Spam or advertising',
    hate: 'Hate speech',
    violence: 'Violence or harmful behavior'
};

/*
    * Format UTC datetime relative to current datetime, ensuring that time
    * is in the past.
    */
var relativeDate = function(datetime) {
    var now = moment.utc();
    var then = moment.utc(datetime);
    then = then > now ? now : then;
    return then.fromNow();
};

var notEmpty = function(value) {
    return !!$.trim(value);
};

var exclusify = function(subscriber, subscribees) {
    subscriber.subscribe(function(value) {
        if (value) {
            for (var i=0; i<subscribees.length; i++) {
                subscribees[i](false);
            }
        }
    });
};

var exclusifyGroup = function() {
    var observables = Array.prototype.slice.call(arguments);
    for (var i=0; i<observables.length; i++) {
        var subscriber = observables[i];
        var subscribees = observables.slice();
        subscribees.splice(i, 1);
        exclusify(subscriber, subscribees);
    }
};

/*
    *
    */
var BaseComment = function() {

    var self = this;
    self.MAXLEVEL = MAXLEVEL;

    self.abuseOptions = Object.keys(ABUSE_CATEGORIES);

    self._loaded = false;
    self.id = ko.observable();

    self.page = ko.observable('node'); // Default
    self.mode = 'pane'; // Default

    self.errorMessage = ko.observable();
    self.editErrorMessage = ko.observable();
    self.replyErrorMessage = ko.observable();

    self.replying = ko.observable(false);
    self.replyContent = ko.observable('');

    self.submittingReply = ko.observable(false);

    self.comments = ko.observableArray();
    self.unreadComments = ko.observable(0);

    self.pageNumber = ko.observable(0);

    self.level = -1;

    self.displayCount = ko.computed(function() {
        if (self.unreadComments() !== 0) {
            return self.unreadComments().toString();
        } else {
            return ' ';
        }
    });

    /* Removes number of unread comments from tab when comments pane is opened  */
    self.removeCount = function() {
        self.unreadComments(0);
    };

    self.replyNotEmpty = ko.computed(function() {
        return notEmpty(self.replyContent());
    });
    self.saveButtonText = ko.computed(function() {
        return self.submittingReply() ? 'Saving' : 'Save';
    });

};

BaseComment.prototype.abuseLabel = function(item) {
    return ABUSE_CATEGORIES[item];
};

BaseComment.prototype.showReply = function() {
    this.replying(true);
};

BaseComment.prototype.cancelReply = function() {
    this.replyContent('');
    this.replying(false);
    this.submittingReply(false);
    this.replyErrorMessage('');
};

BaseComment.prototype.setupToolTips = function(elm) {
    $(elm).each(function(idx, item) {
        var $item = $(item);
        if ($item.attr('data-toggle') === 'tooltip') {
            $item.tooltip();
        } else {
            $item.find('[data-toggle="tooltip"]').tooltip();
        }
    });
};

BaseComment.prototype.fetch = function(thread) {
    var self = this;
    var deferred = $.Deferred();
    if (self._loaded) {
        deferred.resolve(self.comments());
    }
    if (thread !== undefined) {
        return self.getThread(thread);
    }
    $.getJSON(
        nodeApiUrl + 'comments/',
        {
            page: self.page(),
            target: self.id(),
            rootId: self.rootId()
        },
        function(response) {
            self.comments(
                ko.utils.arrayMap(response.comments.reverse(), function (comment) {
                    return new CommentModel(comment, self, self.$root);
                })
            );
            self.unreadComments(response.nUnread);
            deferred.resolve(self.comments());
            self._loaded = true;
        }
    );
    return deferred;
};

BaseComment.prototype.getThread = function(thread_id) {
    var self = this;
    var deferred = $.Deferred();
    if (self._loaded) {
        deferred.resolve(self.comments());
    }
    $.getJSON(
        nodeApiUrl + 'comment/' + thread_id + '/',
        {},
        function(response) {
            self.comments([]);
            self.comments.push(new CommentModel(response.comment, self, self.$root));
            deferred.resolve(self.comments());
            self._loaded = true;
        }
    );
    return deferred;
}

BaseComment.prototype.submitReply = function() {
    var self = this;
    if (!self.replyContent()) {
        self.replyErrorMessage('Please enter a comment');
        return;
    }
    // Quit if already submitting reply
    if (self.submittingReply()) {
        return;
    }
    self.submittingReply(true);
    osfHelpers.postJSON(
        nodeApiUrl + 'comment/',
        {
            page: self.page(),
            target: self.id(),
            content: self.replyContent(),
        }
    ).done(function(response) {
        self.cancelReply();
        self.replyContent(null);
        self.comments.unshift(new CommentModel(response.comment, self, self.$root));
        if (!self.hasChildren()) {
            self.hasChildren(true);
        }
        self.replyErrorMessage('');
        // Update discussion in case we aren't already in it
        // TODO: This can lead to unnecessary API calls; fix this
        if (!self.$root.commented()) {
            self.$root.fetchDiscussion();
        }
        self.onSubmitSuccess(response);
    }).fail(function() {
        self.cancelReply();
        self.errorMessage('Could not submit comment');
    });
};

/*
    *
    */
var CommentModel = function(data, $parent, $root) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$parent = $parent;
    self.$root = $root;

    $.extend(self, ko.mapping.fromJS(data));
    self.dateCreated(data.dateCreated);
    self.dateModified(data.dateModified);

    self.prettyDateCreated = ko.computed(function() {
        return relativeDate(self.dateCreated());
    });
    self.prettyDateModified = ko.computed(function() {
        return 'Modified ' + relativeDate(self.dateModified());
    });

    self.mode = $parent.mode;

    self.level = $parent.level + 1;

    self.showChildren = ko.observable(false);

    self.hoverContent = ko.observable(false);

    self.reporting = ko.observable(false);
    self.deleting = ko.observable(false);
    self.unreporting = ko.observable(false);
    self.undeleting = ko.observable(false);

    self.abuseCategory = ko.observable('spam');
    self.abuseText = ko.observable();

    self.editing = ko.observable(false);
    self.editVerb = self.modified ? 'edited' : 'posted';

    exclusifyGroup(
        self.editing, self.replying, self.reporting, self.deleting,
        self.unreporting, self.undeleting
    );

    self.isVisible = ko.computed(function() {
        return !self.isDeleted() && !self.isHidden() && !self.isAbuse();
    });

    self.editNotEmpty = ko.computed(function() {
        return notEmpty(self.content());
    });

    self.toggleIcon = ko.computed(function() {
        return self.showChildren() ? 'icon-collapse-alt' : 'icon-expand-alt';
    });
    self.editHighlight = ko.computed(function() {
        return self.canEdit() && self.hoverContent() && self.mode !== 'widget';
    });
    self.canReport = ko.computed(function() {
        return self.$root.canComment() && !self.canEdit();
    });

    self.shouldShow = ko.computed(function() {
        return (!self.isDeleted() && !self.isHidden()) || self.hasChildren() || self.canEdit();
    });

    self.shouldShowChildren = ko.computed(function() {
        return self.level < MAXLEVEL;
    })

    self.rootUrl = ko.computed(function(){
        var url = 'discussions';
        if (self.page() !== 'node') {
            url = url + '/' + self.page();
        }
        return url;
    });

    self.parentUrl = ko.computed(function(){
        var url = 'discussions/';
        if (self.targetId() === self.rootId()) {
            return self.rootUrl();
        }
        return url + self.targetId();
    });

    self.targetUrl = ko.computed(function(){
        if (self.page() == 'node') {
            return nodeUrl;
        } else if (self.page() == 'wiki') {
            return nodeUrl + self.page() + '/' + self.rootId();
        } else if (self.page() == 'files') {
            return '/' + self.rootId() + '/';
        }
    });

};

CommentModel.prototype = new BaseComment();

CommentModel.prototype.edit = function() {
    if (this.canEdit() && this.mode !== 'widget') {
        this._content = this.content();
        this.editing(true);
        this.$root.editors += 1;
    }
};

CommentModel.prototype.autosizeText = function(elm) {
    $(elm).find('textarea').autosize().focus();
};

CommentModel.prototype.cancelEdit = function() {
    this.editing(false);
    this.$root.editors -= 1;
    this.editErrorMessage('');
    this.hoverContent(false);
    this.content(this._content);
};

CommentModel.prototype.submitEdit = function(data, event) {
    var self = this;
    var $tips = $(event.target)
        .closest('.comment-container')
        .find('[data-toggle="tooltip"]');
    if (!self.content()) {
        self.errorMessage('Please enter a comment');
        return;
    }
    osfHelpers.putJSON(
        nodeApiUrl + 'comment/' + self.id() + '/',
        {content: self.content()}
    ).done(function(response) {
        self.content(response.content);
        self.dateModified(response.dateModified);
        self.editing(false);
        self.modified(true);
        self.editErrorMessage('');
        self.$root.editors -= 1;
        // Refresh tooltip on date modified, if present
        $tips.tooltip('destroy').tooltip();
    }).fail(function() {
        self.cancelEdit();
        self.errorMessage('Could not submit comment');
    });
};

CommentModel.prototype.reportAbuse = function() {
    this.reporting(true);
};

CommentModel.prototype.cancelAbuse = function() {
    this.abuseCategory(null);
    this.abuseText(null);
    this.reporting(false);
};

CommentModel.prototype.submitAbuse = function() {
    var self = this;
    osfHelpers.postJSON(
        nodeApiUrl + 'comment/' + self.id() + '/report/',
        {
            category: self.abuseCategory(),
            text: self.abuseText()
        }
    ).done(function() {
        self.isAbuse(true);
    }).fail(function() {
        self.errorMessage('Could not report abuse.');
    });
};

CommentModel.prototype.startDelete = function() {
    this.deleting(true);
};

CommentModel.prototype.submitDelete = function() {
    var self = this;
    $.ajax({
        type: 'DELETE',
        url: nodeApiUrl + 'comment/' + self.id() + '/',
    }).done(function() {
        self.isDeleted(true);
        self.deleting(false);
    }).fail(function() {
        self.deleting(false);
    });
};

CommentModel.prototype.cancelDelete = function() {
    this.deleting(false);
};

CommentModel.prototype.startUndelete = function() {
    this.undeleting(true);
};

CommentModel.prototype.submitUndelete = function() {
    var self = this;
    osfHelpers.putJSON(
        nodeApiUrl + 'comment/' + self.id() + '/undelete/',
        {}
    ).done(function() {
        self.isDeleted(false);
    }).fail(function() {
        self.undeleting(false);
    });
};

CommentModel.prototype.cancelUndelete = function() {
    this.undeleting(false);
};

CommentModel.prototype.startUnreportAbuse = function() {
    this.unreporting(true);
};

CommentModel.prototype.submitUnreportAbuse = function() {
    var self = this;
    osfHelpers.postJSON(
        nodeApiUrl + 'comment/' + self.id() + '/unreport/',
        {}
    ).done(function() {
        self.isAbuse(false);
    }).fail(function() {
        self.unreporting(false);
    });
};

CommentModel.prototype.cancelUnreportAbuse = function() {
    this.unreporting(false);
};

CommentModel.prototype.startHoverContent = function() {
    this.hoverContent(true);
};

CommentModel.prototype.stopHoverContent = function() {
    this.hoverContent(false);
};

CommentModel.prototype.toggle = function () {
    this.fetch();
    this.showChildren(!this.showChildren());
};

CommentModel.prototype.onSubmitSuccess = function() {
    this.showChildren(true);
};

/*
    *
    */
var CommentListModel = function(userName, host_page, host_name, mode, canComment, hasChildren, thread) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$root = self;
    self.MAXLENGTH = MAXLENGTH;

    self.mode = mode;

    self.editors = 0;
    self.userName = ko.observable(userName);
    self.canComment = ko.observable(canComment);
    self.hasChildren = ko.observable(hasChildren);

    self.discussion_by_frequency = ko.observableArray();
    self.discussion_by_recency = ko.observableArray();
    self.discussion = ko.observableArray();

    self.page(host_page);
    self.id = ko.observable(host_name);
    self.rootId = ko.observable(host_name);

    self.commented = ko.computed(function(){
        return self.comments().length > 0;
    });
    self.rootUrl = ko.computed(function(){
        if (self.comments().length == 0) {
            return '';
        }
        return self.comments()[0].rootUrl();
    });

    self.parentUrl = ko.computed(function() {
        if (self.comments().length == 0) {
            return '';
        }
        return self.comments()[0].parentUrl();
    });

    self.recentComments = ko.computed(function(){
        var comments = [];
        for (var c in self.comments()) {
            var comment = self.comments()[c];
            if (comment.isVisible()) {
                comments.push(comment);
            }
            if (comments.length == 5) {
                break;
            }
        }
        return comments;
    });


    self.fetch(thread);
    self.fetchDiscussion();

};

CommentListModel.prototype = new BaseComment();

CommentListModel.prototype.onSubmitSuccess = function() {};

CommentListModel.prototype.fetchDiscussion = function() {
    var self = this;
    $.getJSON(
        nodeApiUrl + 'comments/discussion/',
        {
            page: self.page(),
            target: self.id()
        },
        function(response) {
            self.discussion_by_frequency(response.discussion_by_frequency);
            self.discussion_by_recency(response.discussion_by_recency);
            self.discussion(response.discussion_by_recency);
        }
    );
};

CommentListModel.prototype.showRecent = function() {
    var self = this;
    self.discussion(self.discussion_by_recency());
}

CommentListModel.prototype.showFrequent = function() {
    var self = this;
    self.discussion(self.discussion_by_frequency());
}

CommentListModel.prototype.initListeners = function() {
    var self = this;
    $(window).on('beforeunload', function() {
        if (self.editors) {
            return 'Your comments have unsaved changes. Are you sure ' +
                'you want to leave this page?';
        }
    });
};

var timestampUrl = nodeApiUrl + 'comments/timestamps/';
var onOpen = function(host_page, host_name) {
    var request = osfHelpers.putJSON(
        timestampUrl,
        {
            page: host_page,
            rootId: host_name
        }
    );
    request.fail(function(xhr, textStatus, errorThrown) {
        Raven.captureMessage('Could not update comment timestamp', {
            url: timestampUrl,
            textStatus: textStatus,
            errorThrown: errorThrown
        });
    });
};

var init = function(selector, host_page, host_name, mode, userName, canComment, hasChildren, thread_id) {

    new CommentPane(selector, host_page, host_name, mode, {onOpen: onOpen});
    var viewModel = new CommentListModel(userName, host_page, host_name, mode, canComment, hasChildren, thread_id);
    var $elm = $(selector);
    if (!$elm.length) {
        throw('No results found for selector');
    }
    ko.applyBindings(viewModel, $elm[0]);
    viewModel.initListeners();

    return viewModel;
};

module.exports = {
    init: init
};
