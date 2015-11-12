/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var moment = require('moment');
var Raven = require('raven-js');
var koHelpers = require('./koHelpers');
require('knockout.punches');
require('jquery-autosize');
ko.punches.enableAll();

var osfHelpers = require('js/osfHelpers');
var CommentPane = require('js/commentpane');
var markdown = require('js/markdown');
var waterbutler = require('./waterbutler');


// Maximum length for comments, in characters
var FIGSHARE = 'figshare';

var MAXLENGTH = 500;
var MAXLEVEL = {
    'page': 10,
    'pane': 5,
    'widget': 5
};

var TOGGLELEVEL = 2;

var ABUSE_CATEGORIES = {
    spam: 'Spam or advertising',
    hate: 'Hate speech',
    violence: 'Violence or harmful behavior'
};

var FILES = 'files';
var PANE = 'pane';

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

var BaseComment = function() {

    var self = this;
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

    self.level = 0;

    self.displayCount = ko.pureComputed(function() {
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

    self.replyNotEmpty = ko.pureComputed(function() {
        return notEmpty(self.replyContent());
    });
    self.commentButtonText = ko.computed(function() {
        return self.submittingReply() ? 'Commenting' : 'Comment';
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
            $item.find('[data-toggle="tooltip"]').tooltip({container: 'body'});
        }
    });
};

BaseComment.prototype.fetch = function(nodeId, threadId) {
    var self = this;
    var deferred = $.Deferred();
    if (self._loaded) {
        deferred.resolve(self.comments());
    }
    if (threadId !== undefined) {
        return self.getThread(threadId);
    }
    $.getJSON(
        self.$root.nodeApiUrl + 'comments/',
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
            self.configureCommentsVisibility(nodeId);
            self._loaded = true;
        }
    );
    return deferred.promise();
};

BaseComment.prototype.getThread = function(threadId) {
    var self = this;
    var deferred = $.Deferred();
    if (self._loaded) {
        deferred.resolve(self.comments());
    }
    var request = $.getJSON(self.$root.nodeApiUrl + 'comment/' + threadId + '/');
    request.done(function(response){
        self.comments([new CommentModel(response.comment, self, self.$root)]);
        deferred.resolve(self.comments());
        self._loaded = true;
    });
    return deferred.promise();
};

BaseComment.prototype.configureCommentsVisibility = function(nodeId) {
    var self = this;
    for (var c in self.comments()) {
        var comment = self.comments()[c];
        if (self.level > 0 && self.loading() === false) {
            comment.isHidden(self.isHidden());
            if (!self.isHidden() && self.page() === FILES) {
                comment.title(self.title());
            }
            comment.loading(false);
            continue;
        }
        if (comment.page() !== FILES || self.mode === PANE) {
            comment.loading(false);
            continue;
        }
        if (comment.page() === FILES) {
            comment.checkFileExistsAndConfigure(comment.rootId(), nodeId);
        }
    }
};

BaseComment.prototype.checkFileExistsAndConfigure = function(rootId, nodeId) {
    var self = this;
    var url  = waterbutler.buildMetadataUrl(rootId, self.provider(), nodeId, {}); // waterbutler url
    var request = $.ajax({
        method: 'GET',
        url: url,
        beforeSend: osfHelpers.setXHRAuthorization
    });
    request.done(function (resp) {
        if (self.provider() === FIGSHARE) {
            self.title(resp.data.name);
        }
        self.loading(false);
    });
    request.fail(function (xhl) {
        self.isHidden(true);
        self.loading(false);
    });
    return request;
};


BaseComment.prototype.submitReply = function() {
    var self = this;
    var nodeUrl = '/' + self.$root.nodeId() + '/';
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
        self.$root.nodeApiUrl + 'comment/',
        {
            page: self.page(),
            target: self.id(),
            content: self.replyContent(),
        }
    ).done(function(response) {
        self.cancelReply();
        self.replyContent(null);
        var newComment = new CommentModel(response.comment, self, self.$root);
        self.comments.unshift(newComment);
        newComment.loading(false);
        if (!self.hasChildren()) {
            self.hasChildren(true);
        }
        self.replyErrorMessage('');
        self.onSubmitSuccess(response);
        if (self.level >= self.MAXLEVEL) {
            window.location.href = nodeUrl + 'discussions/' + self.id();
        }
    }).fail(function() {
        self.cancelReply();
        self.errorMessage('Could not submit comment');
    });
};

var CommentModel = function(data, $parent, $root) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$parent = $parent;
    self.$root = $root;

    // Note: assigns observables: canEdit, content, dateCreated, dateModified
    //       hasChildren, id, isAbuse, isDeleted. Leaves out author.
    $.extend(self, koHelpers.mapJStoKO(data, {exclude: ['author']}));


    self.contentDisplay = ko.observable(markdown.full.render(self.content()));

    // Update contentDisplay with rednered markdown whenever content changes
    self.content.subscribe(function(newContent) {
        self.contentDisplay(markdown.full.render(newContent));
    });

    self.prettyDateCreated = ko.computed(function() {
        return relativeDate(self.dateCreated());
    });
    self.prettyDateModified = ko.pureComputed(function() {
        return 'Modified ' + relativeDate(self.dateModified());
    });

    self.mode = $parent.mode;
    self.MAXLEVEL = MAXLEVEL[self.mode];

    self.level = $parent.level + 1;

    self.loading = ko.observable(true);
    self.showChildren = ko.observable(false);

    self.reporting = ko.observable(false);
    self.deleting = ko.observable(false);
    self.unreporting = ko.observable(false);
    self.undeleting = ko.observable(false);

    self.abuseCategory = ko.observable('spam');
    self.abuseText = ko.observable();

    self.editing = ko.observable(false);

    exclusifyGroup(
        self.editing, self.replying, self.reporting, self.deleting,
        self.unreporting, self.undeleting
    );

    self.isVisible = ko.pureComputed(function() {
        return !self.isDeleted() && !self.isHidden() && !self.isAbuse();
    });

    self.editNotEmpty = ko.pureComputed(function() {
        return notEmpty(self.content());
    });

    self.toggleIcon = ko.computed(function() {
            return self.showChildren() ? 'fa fa-minus' : 'fa fa-plus';
    });
    
    self.canReport = ko.pureComputed(function() {
        return self.$root.canComment() && !self.canEdit();
    });

    self.shouldShow = ko.pureComputed(function() {
        if (!self.isDeleted() && !self.isHidden()) {
            return true;
        }
        if (self.isHidden()) {
            return self.level === 1;
        }
        return self.hasChildren() || self.canEdit();
    });

    self.shouldShowChildren = ko.computed(function() {
        if (self.isHidden()) {
            self.showChildren(false);
            return false;
        }
        return self.level < self.MAXLEVEL;
    });

    self.shouldContinueThread = ko.pureComputed(function() {
        if (self.shouldShowChildren()) { return false;}
        return ((!self.isHidden()) && self.hasChildren());
    });

    self.cleanTitle = ko.pureComputed(function() {
        var cleaned;
        switch(self.page()) {
            case 'wiki':
                cleaned = '(Wiki';
                if (self.title().toLowerCase() !== 'home') {
                    cleaned += ' - ' + self.title();
                }
                break;
            case 'files':
                cleaned = '(Files - ' + self.title();
                break;
            case 'node':
                cleaned = '(Project Overview';
                break;
        }
        cleaned += ')';
        return decodeURIComponent(cleaned);
    });

    self.nodeUrl = '/' + self.$root.nodeId() + '/';

    self.rootUrl = ko.pureComputed(function(){
        var url = 'discussions';
        if (self.page() === 'node') {
            url = url + '/?page=overview';
        } else {
            url = url + '/?page=' + self.page();
        }
        return url;
    });

    self.parentUrl = ko.pureComputed(function(){
        if (self.targetId() === self.rootId()) {
            return '';
        }
        return '/' + self.targetId();
    });

    self.targetUrl = ko.pureComputed(function(){
        if (self.page() === 'node') {
            return self.nodeUrl;
        } else if (self.page() === 'wiki') {
            return self.nodeUrl + self.page() + '/' + self.rootId();
        } else if (self.page() === 'files') {
            return '/' + self.rootId() + '/';
        }
    });

    if ((self.mode === 'pane' &&
        self.level < TOGGLELEVEL) ||
        (self.mode === 'page' &&
        self.level < self.MAXLEVEL)) {
        self.toggle();
    }

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
        self.$root.nodeApiUrl + 'comment/' + self.id() + '/',
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
        self.$root.nodeApiUrl + 'comment/' + self.id() + '/report/',
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
        url: self.$root.nodeApiUrl + 'comment/' + self.id() + '/',
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
        self.$root.nodeApiUrl + 'comment/' + self.id() + '/undelete/',
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
        self.$root.nodeApiUrl + 'comment/' + self.id() + '/unreport/',
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


CommentModel.prototype.toggle = function () {
    this.fetch();
    this.showChildren(!this.showChildren());
};

CommentModel.prototype.onSubmitSuccess = function() {
    this.showChildren(true);
};


var CommentListModel = function(options) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$root = self;
    self.MAXLENGTH = MAXLENGTH;

    self.mode = options.mode;
    self.MAXLEVEL = MAXLEVEL[self.mode];

    self.editors = 0;
    self.userName = ko.observable(options.userName);
    self.canComment = ko.observable(options.canComment);
    self.hasChildren = ko.observable(options.hasChildren);

    self.page(options.hostPage);
    self.id = ko.observable(options.hostName);
    self.rootId = ko.observable(options.hostName);
    self.nodeId = ko.observable(options.nodeId);
    self.nodeApiUrl = options.nodeApiUrl;

    self.commented = ko.pureComputed(function(){
        return self.comments().length > 0;
    });
    self.rootUrl = ko.pureComputed(function(){
        if (self.comments().length === 0) {
            return '';
        }
        return self.comments()[0].rootUrl();
    });

    self.parentUrl = ko.pureComputed(function() {
        if (self.comments().length === 0) {
            return '';
        }
        return self.comments()[0].parentUrl();
    });

    self.recentComments = ko.pureComputed(function(){
        var comments = [];
        for (var c in self.comments()) {
            var comment = self.comments()[c];
            if (comment.isVisible()) {
                comments.push(comment);
            }
            if (comments.length === 5) {
                break;
            }
        }
        return comments;
    });

    self.fetch(options.nodeId, options.threadId);

};

CommentListModel.prototype = new BaseComment();

CommentListModel.prototype.onSubmitSuccess = function() {};

CommentListModel.prototype.initListeners = function() {
    var self = this;
    $(window).on('beforeunload', function() {
        if (self.editors) {
            return 'Your comments have unsaved changes. Are you sure ' +
                'you want to leave this page?';
        }
    });
};

var onOpen = function(hostPage, hostName, nodeApiUrl) {
    var timestampUrl = nodeApiUrl + 'comments/timestamps/';
    var request = osfHelpers.putJSON(
        timestampUrl,
        {
            page: hostPage,
            rootId: hostName
        }
    );    
    request.fail(function(xhr, textStatus, errorThrown) {
        Raven.captureMessage('Could not update comment timestamp', {
            url: nodeApiUrl + 'comments/timestamps/',
            textStatus: textStatus,
            errorThrown: errorThrown
        });
    });
    return request;
};

/* options example: {
 *      nodeId: Node._id,
 *      nodeApiUrl: Node.api_url,
 *      hostPage: 'node',
 *      hostName: Node._id,
 *      mode: 'page',
 *      userName: User.fullname,
 *      canComment: User.canComment,
 *      hasChildren: Node.hasChildren,
 *      threadId: undefined }
 */
var init = function(selector, options) {
    new CommentPane(selector, options.mode, {
        onOpen: function(){
            return onOpen(options.hostPage, options.hostName, options.nodeApiUrl);
        }
    });
    var viewModel = new CommentListModel(options);
    var $elm = $(selector);
    if (!$elm.length) {
        throw('No results found for selector');
    }
    osfHelpers.applyBindings(viewModel, selector);
    viewModel.initListeners();

    return viewModel;
};

module.exports = {
    init: init
};
