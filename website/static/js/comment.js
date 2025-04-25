/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var moment = require('moment');
var Raven = require('raven-js');
var linkifyHtml = require('linkifyjs/html');
require('jquery-autosize');

var osfHelpers = require('js/osfHelpers');
var CommentPane = require('js/commentpane');
var markdown = require('js/markdown');
var atMention = require('js/atMention');

// Cached contributor and group member data, to prevent multiple fetches for @mentions
var __contributorCache = null;

var getContributorAndGroupMemberList = function(url, contributors, ret) {
    contributors = contributors || [];
    ret = ret || $.Deferred();
    if (__contributorCache !== null) {
        ret.resolve(__contributorCache);
    } else {
        var request = osfHelpers.ajaxJSON(
            'GET',
            url,
            {'isCors': true});
        request.done(function(response) {
            var activeContributors = response.data.filter(function(item) {
                return item.attributes.active === true;
            });
            contributors = contributors.concat(activeContributors);
            if (response.links.next) {
                return getContributorAndGroupMemberList(response.links.next, contributors, ret);
            }
            var data = contributors.map(function(userData) {
                return {
                    'id': userData.id,
                    'name': userData.attributes.given_name,
                    'fullName': userData.attributes.full_name,
                    'link': userData.links.html
                };
            });
            __contributorCache = data;
            ret.resolve(data);
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error getting contributors and group members', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            ret.reject(xhr, status, error);
        });
    }
    return ret.promise();
};

// Maximum length for comments, in characters
var MAXLENGTH = 1000;
var WARNLENGTH = 5;

var ABUSE_CATEGORIES = {
    spam: 'Spam or advertising',
    hate: 'Hate speech',
    violence: 'Violence or harmful behavior'
};

var FILES = 'files';
var WIKI = 'wiki';

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
    var trimmed = $.trim(value).toLowerCase();
    return !!trimmed && trimmed !== '<br>';
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

var convertMentionHtmlToMarkdown = function(commentContent) {
    var content = commentContent || '';
    var pattern = '<span[^>]*?data-atwho-guid="([a-z\\d]{5})"[^>]*?>((@|\\+)[^<]+)<\/span>';
    var regex = new RegExp(pattern);
    var regexG = new RegExp(pattern, 'g');
    var matches = content.match(regexG);
    if (matches) {
        for (var i = 0; i < matches.length; i++) {
            var match = regex.exec(matches[i]);
            var guid = match[1];
            var mention = match[2];
            var url = osfHelpers.getDomain() + '/' + guid + '/';
            content = content.replace(match[0], '['+ mention + '](' + url + ')');
        }
    }
    // '&#13;&#10;' is the character entity reference for '\r\n'
    // '\r\n' is treated differently and breaks conversion from markdown to html
    content = content.replace(/<span[^>]*?>/g, '')
        .replace(/<\/span>/g, '')
        .replace(/&nbsp;/g, ' ')
        .replace(/<br>/g, '&#13;&#10;');
    return content;
};

var convertMentionMarkdownToHtml = function(commentContent) {
    var content = commentContent ||'';
    var pattern = '\\[(@|\\+)(.*?)\\]\\(htt[ps]{1,2}:\\/\\/[a-z\\d:.]+?\\/([a-z\\d]{5})\\/\\)';
    var regex = new RegExp(pattern);
    var regexG = new RegExp(pattern, 'g');
    var matches = content.match(regexG);
    if (matches) {
        for (var i = 0; i < matches.length; i++) {
            var match = regex.exec(matches[i]);
            var atwho = match[1];
            var guid = match[3];
            var mention = match[2];

            content = content.replace(
                match[0],
                '<span class="atwho-inserted" contenteditable="true" data-atwho-guid="' +
                    guid + '" data-atwho-at-query="' + atwho + '">' +
                    atwho + mention + '</span>'
            );
        }
    }
    return content.replace(/\r\n/g, '<br>');
};

var BaseComment = function() {

    var self = this;
    self.abuseOptions = Object.keys(ABUSE_CATEGORIES);

    self._loaded = false;
    self.id = ko.observable();
    self.page = ko.observable('node'); // Default

    self.errorMessage = ko.observable();
    self.editErrorMessage = ko.observable();
    self.replyErrorMessage = ko.observable();

    self.replying = ko.observable(false);
    self.replyContent = ko.observable('');

    self.urlForNext = ko.observable();

    self.saveContent = ko.pureComputed(function() {
        return convertMentionHtmlToMarkdown(self.replyContent());
    });

    self.submittingReply = ko.observable(false);

    self.comments = ko.observableArray();

    self.loadingComments = ko.observable(true);

    self.underMaxLength = ko.observable(true);

    self.currentCount = ko.observable(0);

    self.counter = ko.pureComputed(function(){
        return self.currentCount() + '/' + MAXLENGTH;
    });

    self.counterColor = ko.pureComputed(function(){
        return self.currentCount() >  MAXLENGTH - WARNLENGTH ? 'alert-danger' : 'label-default';
    });

    self.replyNotEmpty = ko.pureComputed(function() {
        return notEmpty(self.replyContent());
    });

    self.commentButtonText = ko.computed(function() {
        return self.submittingReply() ? 'Commenting' : 'Comment';
    });

    self.validateReply = ko.pureComputed(function() {
        return self.replyNotEmpty() && self.underMaxLength();
    });

};

BaseComment.prototype.handleEditableUpdate = function(element) {
    var self = this;
    var $element = $(element);
    var charLimit = $element.attr('maxlength');
    var inputTextLength = $element[0].innerText.length || 0;
    var showLength = inputTextLength === 1 ? 1 : inputTextLength - 1;
    // + 1 to account for the <br> that is added to the end of the contenteditable content
    // <br> is necessary for the return key to function properly
    var underOrEqualMaxLength = inputTextLength <= parseInt(charLimit) + 1 || charLimit == undefined;  // jshint ignore: line
    self.currentCount(showLength);
    self.underMaxLength(underOrEqualMaxLength);
    self.errorMessage(underOrEqualMaxLength ? '' : 'Exceeds character limit. Please reduce to ' + charLimit + ' characters or less.');
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
    this.errorMessage('');
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

BaseComment.prototype.fetch = function() {
    var self = this;
    var setUnread = self.getTargetType() !== 'comments' && !osfHelpers.urlParams().view_only && self.author.id !== '';
    if (self.comments().length === 0) {
        var urlParams = osfHelpers.urlParams();
        var query = 'embed=user';
        if (!osfHelpers.urlParams().view_only && setUnread) {
            query += '&related_counts=True';
        }
        if (urlParams.view_only && !window.contextVars.node.isPublic) {
            query += '&view_only=' + urlParams.view_only;
        }
        if (self.id() !== undefined) {
            query += '&filter[target]=' + self.id();
        }
        query += '&page[size]=30';
        var url = osfHelpers.apiV2Url(self.$root.nodeType + '/' + window.contextVars.node.id + '/comments/', {query: query});
        self.fetchNext(url, [], setUnread);
    }
};

/* Go get the next specified page of the API response, and add to the comments list */
BaseComment.prototype.fetchNext = function(url, comments, setUnread) {
    var self = this;
    var request = osfHelpers.ajaxJSON(
        'GET',
        url,
        {'isCors': true});
    self.loadingComments(true);
    request.done(function(response) {
        comments = response.data;
        if (self._loaded !== true) {
            self._loaded = true;
        }
        if (setUnread && response.links.meta.unread) {
            self.$root.unreadComments(response.links.meta.unread);
            setUnread = false;
        }
        if (response.links.meta.comment_count) {
            self.$root.totalComments(response.links.meta.comment_count);
        }
        comments.forEach(function(comment) {
            self.comments.push(
                new CommentModel(comment, self, self.$root)
            );
        });
        self.configureCommentsVisibility();
        self.urlForNext(response.links.next);
    }).always(function () {
        self.loadingComments(false);
    });
};

BaseComment.prototype.getMoreComments = function() {
    var self = this;
    var nextUrl = self.urlForNext();
    var comments = self.comments();
    var setUnread = self.getTargetType() !== 'comments' && !osfHelpers.urlParams().view_only && self.author.id !== '';

    if (self.urlForNext() && !self.loadingComments()) {
        self.fetchNext(nextUrl, comments, setUnread);
    }
};

BaseComment.prototype.configureCommentsVisibility = function() {
    var self = this;
    for (var c in self.comments()) {
        var comment = self.comments()[c];
        comment.loading(false);
    }
};

BaseComment.prototype.getTargetType = function() {
    var self = this;
    if (self.id() === window.contextVars.node.id) {
        return 'nodes';
    } else if (self.id() === self.$root.rootId() && self.page() === FILES) {
        return 'files';
    } else if (self.id() === self.$root.rootId() && self.page() === WIKI) {
        return 'wiki';
    } else {
        return 'comments';
    }
};

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
    var url = osfHelpers.apiV2Url(self.$root.nodeType + '/' + window.contextVars.node.id + '/comments/', {});
    var request = osfHelpers.ajaxJSON(
        'POST',
        url,
        {
            'isCors': true,
            'data': {
                'data': {
                    'type': 'comments',
                    'attributes': {
                        'content': self.saveContent(),
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': self.getTargetType(),
                                'id': self.id() === window.contextVars.node.id ? window.contextVars.node.id : self.id()
                            }
                        }
                    }
                }
            }
        });
    request.done(function(response) {
        self.cancelReply();
        self.replyContent(null);
        var newComment = new CommentModel(response.data, self, self.$root);
        newComment.loading(false);
        self.comments.unshift(newComment);
        if (!self.hasChildren()) {
            self.hasChildren(true);
        }
        self.replyErrorMessage('');
        self.errorMessage('');
        self.onSubmitSuccess(response);
    });
    request.fail(function(xhr, status, error) {
        self.cancelReply();
        self.errorMessage('Could not submit comment');
        Raven.captureMessage('Error creating comment', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
};

var CommentModel = function(data, $parent, $root) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$parent = $parent;
    self.$root = $root;

    self.id = ko.observable(data.id);
    self.content = ko.observable(data.attributes.content || '');
    self.page = ko.observable(data.attributes.page);
    self.dateCreated = ko.observable(data.attributes.date_created);
    self.dateModified = ko.observable(data.attributes.date_modified);
    self.isDeleted = ko.observable(data.attributes.deleted);
    self.modified = ko.observable(data.attributes.modified);
    self.isAbuse = ko.observable(data.attributes.is_abuse);
    self.canEdit = ko.observable(data.attributes.can_edit);
    self.hasChildren = ko.observable(data.attributes.has_children);
    self.hasReport = ko.observable(data.attributes.has_report);
    self.isHam = ko.observable(data.attributes.is_ham);

    self.isDeletedAbuse = ko.pureComputed(function() {
        return self.isDeleted() && self.isAbuse();
    });
    self.isDeletedNotAbuse = ko.pureComputed(function() {
        return self.isDeleted() && !self.isAbuse();
    });
    self.isAbuseNotDeleted = ko.pureComputed(function() {
        return !self.isDeleted() && self.isAbuse();
    });

    if ('embeds' in data && 'user' in data.embeds && 'data' in data.embeds.user) {
        var userData = data.embeds.user.data;
        self.author = {
            'id': userData.id,
            'urls': {'profile': userData.links.html},
            'fullname': userData.attributes.full_name,
            'profileImageUrl': userData.links.profile_image
        };
    } else if ('embeds' in data && 'user' in data.embeds && 'errors' in data.embeds.user) {
        var errors = data.embeds.user.errors;
        for (var e in data.embeds.user.errors) {
            if ('meta' in errors[e] && 'full_name' in errors[e].meta) {
                self.author = {
                    'id': null,
                    'urls': {'profile': ''},
                    'fullname': errors[e].meta.full_name,
                    'profileImageUrl': ''
                };
                break;
            }
        }
    } else {
        self.author = self.$root.author;
    }

    self.editableContent = ko.pureComputed(function() {
        return convertMentionMarkdownToHtml(self.content());
    });

    self.editedContent = ko.pureComputed(function() {
        return convertMentionHtmlToMarkdown(self.content());
    });

    var linkifyOpts = { target: function (href, type) { return type === 'url' ? '_top' : null; } };
    self.contentDisplay = ko.observable(linkifyHtml(markdown.full.render(self.content()), linkifyOpts));

    // Update contentDisplay with rendered markdown whenever content changes
    self.content.subscribe(function(newContent) {
        self.contentDisplay(linkifyHtml(markdown.full.render(newContent), linkifyOpts));
    });

    self.prettyDateCreated = ko.computed(function() {
        return relativeDate(self.dateCreated());
    });
    self.prettyDateModified = ko.pureComputed(function() {
        return 'Modified ' + relativeDate(self.dateModified());
    });

    self.loading = ko.observable(true);
    self.showChildren = ko.observable(false);

    self.reporting = ko.observable(false);
    self.deleting = ko.observable(false);

    self.abuseCategory = ko.observable('spam');
    self.abuseText = ko.observable('');

    self.editing = ko.observable(false);

    exclusifyGroup(
        self.editing, self.replying, self.reporting, self.deleting
    );

    self.isVisible = ko.pureComputed(function() {
        return !self.isDeleted() && !self.isAbuse();
    });

    self.editNotEmpty = ko.pureComputed(function() {
        return notEmpty(self.content());
    });

    self.validateEdit = ko.pureComputed(function() {
        return self.editNotEmpty() && self.underMaxLength();
    });

    self.toggleIcon = ko.computed(function() {
        return self.showChildren() ? 'fa fa-minus' : 'fa fa-plus';
    });

    self.canReport = ko.pureComputed(function() {
        return self.$root.canComment() && !self.canEdit();
    });

    self.nodeUrl = '/' + self.$root.nodeId() + '/';

};

CommentModel.prototype = new BaseComment();

CommentModel.prototype.edit = function() {
    if (this.canEdit()) {
        this._content = this.content();
        this.content(this.editableContent());
        this.editing(true);
        this.$root.editors += 1;
    }
};

CommentModel.prototype.autosizeText = function(elm) {
    var self = this;
    var $elm = $(elm);
    $elm.find('textarea').autosize().focus();
    initAtMention(self.$root.nodeId(), $elm.find(self.$root.inputSelector));
};

CommentModel.prototype.cancelEdit = function() {
    this.editing(false);
    this.$root.editors -= 1;
    this.editErrorMessage('');
    this.errorMessage('');
    this.content(this._content);
};

CommentModel.prototype.submitEdit = function(data, event) {
    var self = this;
    var $tips = $(event.target)
        .closest('.comment-container')
        .find('[data-toggle="tooltip"]');
    if (!self.content()) {
        self.editErrorMessage('Please enter a comment');
        return;
    }
    var url = osfHelpers.apiV2Url('comments/' + self.id() + '/', {});
    var request = osfHelpers.ajaxJSON(
        'PUT',
        url,
        {
            'isCors': true,
            'data': {
                'data': {
                    'id': self.id(),
                    'type': 'comments',
                    'attributes': {
                        'content': self.editedContent(),
                        'deleted': false
                    }
                }
            }
        });
    request.done(function(response) {
        self.content(response.data.attributes.content);
        self.dateModified(response.data.attributes.date_modified);
        self.editing(false);
        self.modified(true);
        self.editErrorMessage('');
        self.errorMessage('');
        self.$root.editors -= 1;
        // Refresh tooltip on date modified, if present
        $tips.tooltip('destroy').tooltip();
    });
    request.fail(function(xhr, status, error) {
        self.cancelEdit();
        self.errorMessage('Could not submit comment');
        Raven.captureMessage('Error editing comment', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
    return request;
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
    var url = osfHelpers.apiV2Url('comments/' + self.id() + '/reports/', {});
    var request = osfHelpers.ajaxJSON(
        'POST',
        url,
        {
            'isCors': true,
            'data': {
                'data': {
                    'type': 'comment_reports',
                    'attributes': {
                        'category': self.abuseCategory(),
                        'message': self.abuseText() || ''
                    }
                }
            }
        });
    request.done(function() {
        self.isAbuse(true);
        self.reporting(false);
        self.hasReport(true);
    });
    request.fail(function(xhr, status, error) {
        self.errorMessage('Could not report abuse.');
        Raven.captureMessage('Error reporting abuse', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
    return request;
};

CommentModel.prototype.startDelete = function() {
    this.deleting(true);
};

CommentModel.prototype.submitDelete = function() {
    var self = this;
    var url = osfHelpers.apiV2Url('comments/' + self.id() + '/', {});
    var request = osfHelpers.ajaxJSON(
        'DELETE',
        url,
        {'isCors': true}
    );
    request.done(function() {
        self.isDeleted(true);
        self.deleting(false);
    });
    request.fail(function(xhr, status, error) {
        self.deleting(false);
        Raven.captureMessage('Error deleting comment', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
    return request;
};

CommentModel.prototype.cancelDelete = function() {
    this.deleting(false);
};

CommentModel.prototype.submitUndelete = function() {
    var self = this;
    var url = osfHelpers.apiV2Url('comments/' + self.id() + '/', {});
    var request = osfHelpers.ajaxJSON(
        'PUT',
        url,
        {
            'isCors': true,
            'data': {
                'data': {
                    'id': self.id(),
                    'type': 'comments',
                    'attributes': {
                        'content': self.content(),
                        'deleted': false
                    }
                }
            }
        });
    request.done(function() {
        self.isDeleted(false);
    });
    request.fail(function(xhr, status, error) {
        Raven.captureMessage('Error undeleting comment', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });

    });
    return request;
};


CommentModel.prototype.submitUnreportAbuse = function() {
    var self = this;
    var url = osfHelpers.apiV2Url('comments/' + self.id() + '/reports/' + window.contextVars.currentUser.id + '/', {});
    var request = osfHelpers.ajaxJSON(
        'DELETE',
        url,
        {'isCors': true}
    );
    request.done(function() {
        self.isAbuse(false);
    });
    request.fail(function(xhr, status, error) {
        Raven.captureMessage('Error unreporting comment', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });

    });
    return request;
};


CommentModel.prototype.toggle = function (data, event) {
    // Fetch comments when toggling open
    if (!this.showChildren()) {
        this.fetch();
    }
    this.showChildren(!this.showChildren());
};

CommentModel.prototype.onSubmitSuccess = function() {
    this.showChildren(true);
};

/*
    *
    */
var CommentListModel = function(options) {

    BaseComment.prototype.constructor.call(this);

    var self = this;

    self.$root = self;
    self.MAXLENGTH = MAXLENGTH;

    self.inputSelector = options.inputSelector;
    self.editors = 0;
    self.nodeId = ko.observable(options.nodeId);
    self.nodeApiUrl = options.nodeApiUrl;
    self.nodeType = options.isRegistration ? 'registrations' : 'nodes';
    self.page(options.page);
    self.pageTitle = options.pageTitle;
    self.id = ko.observable(options.rootId);
    self.rootId = ko.observable(options.rootId);
    self.fileId = options.fileId || '';
    self.canComment = ko.observable(options.canComment);
    self.hasChildren = ko.observable(options.hasChildren);
    self.author = options.currentUser;

    self.togglePane = options.togglePane;

    self.unreadComments = ko.observable(0);
    self.displayCount = ko.pureComputed(function() {
        if (self.unreadComments() !== 0) {
            return self.unreadComments().toString();
        } else {
            return ' ';
        }
    });

    self.totalComments = ko.observable(0);
    self.hasComments = ko.pureComputed(function() {
        if (self.totalComments() !== 0) {
            return true;
        } else {
            return false;
        }
    });

    /* Removes number of unread comments from tab when comments pane is opened  */
    self.removeCount = function() {
        self.unreadComments(0);
    };

    osfHelpers.onScrollToBottom(document.getElementById('comments_window'), self.getMoreComments.bind(self));

    self.fetch(options.nodeId);
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

var onOpen = function(page, rootId, nodeApiUrl, currentUserId) {
    if (osfHelpers.urlParams().view_only || !currentUserId) {
        return null;
    }
    var timestampUrl = nodeApiUrl + 'comments/timestamps/';
    var request = osfHelpers.putJSON(
        timestampUrl,
        {
            page: page,
            rootId: rootId
        }
    );
    request.fail(function(xhr, textStatus, errorThrown) {
        Raven.captureMessage('Could not update comment timestamp', {
            extra: {
                url: timestampUrl,
                textStatus: textStatus,
                errorThrown: errorThrown
            }
        });
    });
    return request;
};


function initAtMention(nodeId, selectorOrElem) {
    var url = osfHelpers.apiV2Url('nodes/' + nodeId + '/contributors_and_group_members/', {
        query: {
            'page[size]': 50,
            'fields[users]': 'given_name,full_name,active',
        }
    });
    return getContributorAndGroupMemberList(url)
        .then(function(contributors) {
            atMention(selectorOrElem, contributors);
        });
}

/* options example: {
 *      nodeId: Node._id,
 *      nodeApiUrl: Node.api_url,
 *      isRegistration: Node.is_registration,
 *      page: 'node',
 *      rootId: Node._id,
 *      fileId: StoredFileNode._id,
 *      canComment: User.canComment,
 *      currentUser: window.contextVars.currentUser,
 *      pageTitle: Node.title
 * }
 */
var init = function(commentLinkSelector, commentPaneSelector, options) {
    // TODO: Don't hardcode selector here; pass argument in page module
    initAtMention(options.nodeId, options.inputSelector);
    var cp = new CommentPane(commentPaneSelector, {
        onOpen: function(){
            return onOpen(options.page, options.rootId, options.nodeApiUrl, options.currentUser.id);
        }
    });
    options.togglePane = cp.toggle;
    var viewModel = new CommentListModel(options);
    osfHelpers.applyBindings(viewModel, commentLinkSelector);
    osfHelpers.applyBindings(viewModel, commentPaneSelector);
    viewModel.initListeners();

    return viewModel;
};

module.exports = {
    init: init,
    convertMentionHtmlToMarkdown: convertMentionHtmlToMarkdown,
    convertMentionMarkdownToHtml: convertMentionMarkdownToHtml
};
