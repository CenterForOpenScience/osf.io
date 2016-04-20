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

var caret = require('Caret.js');
var atWho = require('At.js');

// preventing unexpected contenteditable behavior
var onPaste = function(e){
    e.preventDefault();
    var pasteText = e.originalEvent.clipboardData.getData('text/plain');
    document.execCommand('insertHTML', false, pasteText);
};

// remove br if no text
var onlyElementBr = function() {
    if (this.innerText.trim() === '') {
        this.innerHTML = '';
    }
};

// make sure br is always the lastChild of contenteditable so return works properly
var lastElementBr = function(){
    if (!this.lastChild || this.lastChild.nodeName.toLowerCase() !== 'br') {
        this.appendChild(document.createElement('br'));
    }
};

// ensure that return inserts a <br> in all browsers
var onReturn = function (e) {
    var docExec = false;
    var range;

    // Gecko
    try {
        docExec = document.execCommand('insertBrOnReturn', false, true);
    }
    catch (error) {
        // IE throws an error if it does not recognize the command...
    }

    if (docExec) {
        return true;
    }
    // Standard
    else if (window.getSelection) {
        e.preventDefault();

        var selection = window.getSelection(),
            br = document.createElement('br');
        range = selection.getRangeAt(0);

        range.deleteContents();
        range.insertNode(br);
        range.setStartAfter(br);
        range.setEndAfter(br);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);

        return false;
    }
    // IE (http://wadmiraal.net/lore/2012/06/14/contenteditable-ie-hack-the-new-line/)
    else if ($.browser.msie) {
        e.preventDefault();

        range = document.selection.createRange();

        range.pasteHTML('<BR>');

        // Move the caret after the BR
        range.moveStart('character', 1);

        return false;
    }
    return true;
};

// At.js
var callbacks = {
    beforeInsert: function(value, $li) {
        var data = $li.data('item-data');
        var model = ko.dataFor(this.$inputor[0]);
        if (model.replyMentions().indexOf(data.id) === -1) {
            model.replyMentions().push(data.id);
        }
        this.query.el.attr('data-atwho-guid', '' + data.id);
        return value;
    },
    highlighter: function(li, query) {
        var regexp;
        if (!query) {
            return li;
        }
        regexp = new RegExp('>\\s*([\\w\\s]*?)(' + query.replace('+', '\\+') + ')([\\w\\s]*)\\s*<', 'ig');
        return li.replace(regexp, function(str, $1, $2, $3) {
            return '> ' + $1 + '<strong>' + $2 + '</strong>' + $3 + ' <';
        });
    },
    matcher: function(flag, subtext, should_startWithSpace, acceptSpaceBar) {
        acceptSpaceBar = true;
        var _a, _y, match, regexp, space;
        flag = flag.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, '\\$&');
        if (should_startWithSpace) {
            flag = '(?:^|\\s)' + flag;
        }
        _a = decodeURI('%C3%80');
        _y = decodeURI('%C3%BF');
        space = acceptSpaceBar ? '\ ' : '';
        regexp = new RegExp(flag + '([A-Za-z' + _a + '-' + _y + '0-9_' + space + '\'\.\+\-]*)$|' + flag + '([^\\x00-\\xff]*)$', 'gi');
        match = regexp.exec(subtext.replace(/\s/g, ' '));
        if (match) {
            return match[2] || match[1];
        } else {
            return null;
        }
    }
};

var headerTemplate = '<div class="atwho-header">Contributors<small>&nbsp;↑&nbsp;↓&nbsp;</small></div>';
var displayTemplate = '<li>${fullName}</li>';

var at_config = {
    at: '@',
    headerTpl: headerTemplate,
    insertTpl: '@${fullName}',
    displayTpl: displayTemplate,
    searchKey: 'fullName',
    limit: 6,
    callbacks: callbacks
};

var plus_config = {
    at: '+',
    headerTpl: headerTemplate,
    insertTpl: '+${fullName}',
    displayTpl: displayTemplate,
    searchKey: 'fullName',
    limit: 6,
    callbacks: callbacks
};

var input = $('.atwho-input');
var nodeId = window.nodeId;

var getContributorList = function(input, nodeId) {
    var url = osfHelpers.apiV2Url('nodes/' + nodeId + '/contributors/', {});
    var request = osfHelpers.ajaxJSON(
        'GET',
        url,
        {'isCors': true});
    request.done(function(response) {
        var activeContributors = response.data.filter(function(item) {
            return item.embeds.users.data.attributes.active === true;
        });
        var data = activeContributors.map(function(item) {
            return {
                'id': item.id,
                'name': item.embeds.users.data.attributes.given_name,
                'fullName': item.embeds.users.data.attributes.full_name,
                'link': item.embeds.users.data.links.html
            };
        });
        // for any input areas that currently exist on page
        input.atwho('load','@', data).atwho('load', '+', data).atwho('run');
        // for future input areas so that data doesn't need to be reloaded
        at_config.data = data;
        plus_config.data = data;
    });
    request.fail(function(xhr, status, error) {
        Raven.captureMessage('Error getting contributors', {
            url: url,
            status: status,
            error: error
        });
    });
    return request;
};

getContributorList(input, nodeId);
input.atwho(at_config).atwho(plus_config).bind('paste', onPaste).on('focusin keyup', lastElementBr).on('focusout', onlyElementBr).keydown(function(e) {
    if(e.which === 13 && !e.isDefaultPrevented()) {
        onReturn(e);
    }
});

// Maximum length for comments, in characters
var MAXLENGTH = 500;

var ABUSE_CATEGORIES = {
    spam: 'Spam or advertising',
    hate: 'Hate speech',
    violence: 'Violence or harmful behavior'
};

var FILES = 'files';

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
    if (value === '<br>')  {
        return false;
    }
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

    self.errorMessage = ko.observable();
    self.editErrorMessage = ko.observable();
    self.replyErrorMessage = ko.observable();

    self.replying = ko.observable(false);
    self.replyContent = ko.observable('');
    self.replyMentions = ko.observableArray([]);

    self.saveContent = ko.computed(function() {
        var content = self.replyContent();
        if (!content) {
            content = '';
        }
        var regex = /<span.*?data-atwho-guid="([a-z\d]{5})".*?>((@|\+)[\w\s]+)<\/span>/;
        var matches = content.match(/<span.*?data-atwho-guid="([a-z\d]{5})".*?>((@|\+)[\w\s]+)<\/span>/g);
        if (matches) {
            for (var i = 0; i < matches.length; i++) {
                var match = regex.exec(matches[i]);
                var guid = match[1];
                var mention = match[2];
                var url = '/' + guid + '/';
                content = content.replace(match[0], '['+ mention + '](' + url + ')');

                if (guid && self.replyMentions.indexOf(guid) === -1) {
                    self.replyMentions.push(guid);
                }
            }
        }
        return content.replace(/<br>/g, '&#13;&#10;');

    });

    self.submittingReply = ko.observable(false);

    self.comments = ko.observableArray();

    self.underMaxLength = ko.observable(true);

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
    if (self.comments().length === 0) {
        var urlParams = osfHelpers.urlParams();
        var query = 'embed=user';
        if (urlParams.view_only && !window.contextVars.node.isPublic) {
            query += '&view_only=' + urlParams.view_only;
        }
        if (self.id() !== undefined) {
            query += '&filter[target]=' + self.id();
        }
        var url = osfHelpers.apiV2Url(self.$root.nodeType + '/' + window.contextVars.node.id + '/comments/', {query: query});
        self.fetchNext(url, []);
    }
};

/* Go through the paginated API response to fetch all comments for the specified target */
BaseComment.prototype.fetchNext = function(url, comments) {
    var self = this;
    var request = osfHelpers.ajaxJSON(
        'GET',
        url,
        {'isCors': true});
    request.done(function(response) {
        comments = response.data;
        if (self._loaded !== true) {
            self._loaded = true;
        }
        comments.forEach(function(comment) {
            self.comments.push(
                new CommentModel(comment, self, self.$root)
            );
        });
        self.configureCommentsVisibility();
        if (response.links.next !== null) {
            self.fetchNext(response.links.next, comments);
        } else {
            self.loadingComments(false);
        }
    }).fail(function () {
        self.loadingComments(false);
    });
};

BaseComment.prototype.setUnreadCommentCount = function() {
    var self = this;
    var url;
    if (self.page() === FILES) {
        url = osfHelpers.apiV2Url('files/' + self.$root.fileId + '/', {query: 'related_counts=True'});
    } else {
        url = osfHelpers.apiV2Url(self.$root.nodeType + '/' + window.contextVars.node.id + '/', {query: 'related_counts=True'});
    }
    var request = osfHelpers.ajaxJSON(
        'GET',
        url,
        {'isCors': true});
    request.done(function(response) {
        if (self.page() === FILES) {
            self.unreadComments(response.data.relationships.comments.links.related.meta.unread);
        } else {
            self.unreadComments(response.data.relationships.comments.links.related.meta.unread.node);
        }
    });
    return request;
};


BaseComment.prototype.configureCommentsVisibility = function() {
    var self = this;
    for (var c in self.comments()) {
        var comment = self.comments()[c];
        comment.loading(false);
    }
};

var getTargetType = function(self) {
    if (self.id() === window.contextVars.node.id) {
        return 'nodes';
    } else if (self.id() === self.$root.rootId() && self.page() === FILES) {
        return 'files';
    } else{
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
                        'new_mentions': self.replyMentions()
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': getTargetType(self),
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
        self.replyMentions([]);
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
        self.replyMentions([]);
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

    if (window.contextVars.node.anonymous) {
        self.author = {
            'id': null,
            'url': '',
            'fullname': 'A User',
            'gravatarUrl': ''
        };
    } else if ('embeds' in data && 'user' in data.embeds) {
        var userData = data.embeds.user.data;
        self.author = {
            'id': userData.id,
            'url': userData.links.html,
            'fullname': userData.attributes.full_name,
            'gravatarUrl': userData.links.profile_image
        };
    } else {
        self.author = self.$root.author;
    }

    self.editableContent = ko.computed(function() {
        var content = self.content();
        if (!content) {
            content = '';
        }
        var regex = /\[(@|\+)(.*?)\]\(\/([a-z\d]{5})\/\)/;
        var matches = content.match(/\[(@|\+)(.*?)\]\(\/([a-z\d]{5})\/\)/g);
        if (matches) {
            for (var i = 0; i < matches.length; i++) {
                var match = regex.exec(matches[i]);
                var atwho = match[1];
                var guid = match[3];
                var mention = match[2];

                content = content.replace(match[0], '<span class="atwho-inserted" contenteditable="false" data-atwho-guid="'+ guid + '" data-atwho-at-query="' + atwho + '">' + atwho + mention + '</span>');
            }
        }
        return content.replace(/\x0D\x0A/g, '<br>');
    });

    self.editedContent = ko.computed(function() {
        var content = self.content();
        if (!content) {
            content = '';
        }
        var regex = /<span.*?data-atwho-guid="([a-z\d]{5})".*?>((@|\+)[\w\s]+)<\/span>/;
        var matches = content.match(/<span.*?data-atwho-guid="([a-z\d]{5})".*?>((@|\+)[\w\s]+)<\/span>/g);
        if (matches) {
            for (var i = 0; i < matches.length; i++) {
                var match = regex.exec(matches[i]);
                var guid = match[1];
                var mention = match[2];
                var url = '/' + guid + '/';
                content = content.replace(match[0], '['+ mention + '](' + url + ')');

                if (guid && self.replyMentions.indexOf(guid) === -1) {
                    self.replyMentions.push(guid);
                }
            }
        }
        return content.replace(/<br>/g, '&#13;&#10;');
    });

    self.contentDisplay = ko.observable(markdown.full.render(self.content()));

    // Update contentDisplay with rendered markdown whenever content changes
    self.content.subscribe(function(newContent) {
        self.contentDisplay(markdown.full.render(newContent));
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

    self.shouldShow = ko.pureComputed(function() {
        return !self.isDeleted() || self.hasChildren() || self.canEdit();
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
    $(elm).find('textarea').autosize().focus();
    $(elm).find('.atwho-input').atwho(at_config).atwho(plus_config).bind('paste', onPaste).on('focusin', lastElementBr).on('focusout', onlyElementBr).keydown(function(e) {
        if(e.which === 13 && !e.isDefaultPrevented()) {
            onReturn(e);
        }
    });
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
                        'new_mentions': self.replyMentions(),
                        'deleted': false
                    }
                }
            }
        });
    request.done(function(response) {
        self.content(response.data.attributes.content);
        self.dateModified(response.data.attributes.date_modified);
        self.replyMentions([]);
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
        self.replyMentions([]);
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

    self.editors = 0;
    self.nodeId = ko.observable(options.nodeId);
    self.nodeApiUrl = options.nodeApiUrl;
    self.nodeType = options.isRegistration ? 'registrations' : 'nodes';
    self.page(options.page);
    self.id = ko.observable(options.rootId);
    self.rootId = ko.observable(options.rootId);
    self.fileId = options.fileId || '';
    self.canComment = ko.observable(options.canComment);
    self.hasChildren = ko.observable(options.hasChildren);
    self.author = options.currentUser;
    self.loadingComments = ko.observable(true);

    self.togglePane = options.togglePane;

    self.unreadComments = ko.observable(0);
    if (!osfHelpers.urlParams().view_only) {
        self.setUnreadCommentCount();
    }

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

var onOpen = function(page, rootId, nodeApiUrl) {
    if (osfHelpers.urlParams().view_only){
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

/* options example: {
 *      nodeId: Node._id,
 *      nodeApiUrl: Node.api_url,
 *      isRegistration: Node.is_registration,
 *      page: 'node',
 *      rootId: Node._id,
 *      fileId: StoredFileNode._id,
 *      canComment: User.canComment,
 *      hasChildren: Node.hasChildren,
 *      currentUser: {
 *          id: User._id,
 *          url: User.url,
 *          fullname: User.fullname,
 *          gravatarUrl: User.profile_image_url
 *      }
 * }
 */
var init = function(commentLinkSelector, commentPaneSelector, options) {
    var cp = new CommentPane(commentPaneSelector, {
        onOpen: function(){
            return onOpen(options.page, options.rootId, options.nodeApiUrl);
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
    init: init
};
