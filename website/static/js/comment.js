this.Comment = (function(window, $, ko, bootbox) {

    'use strict';

    var PRIVACY_MAP = {
        'public': 'Public',
        'private': 'Private'
    };

    var relativeDate = function(datetime) {
        return moment.utc(datetime, 'MM/DD/YY HH:mm:ss').fromNow();
    };

    /*
     *
     */
    var BaseComment = function() {

        var self = this;

        self.privacyOptions = Object.keys(PRIVACY_MAP);

        self._loaded = false;
        self.id = ko.observable();

        self.replying = ko.observable(false);
        self.replyContent = ko.observable('');
        self.replyPublic = ko.observable('public');

        self.comments = ko.observableArray();
        self.displayComments = ko.computed(function() {
            return ko.utils.arrayFilter(self.comments(), function(comment) {
                return !comment.isSpam();
            });
        });

    };

    BaseComment.prototype.privacyLabel = function(item) {
        return PRIVACY_MAP[item];
    };

    BaseComment.prototype.showReply = function() {
        this.replying(true);
    };

    BaseComment.prototype.cancelReply = function() {
        this.replyContent('');
        this.replying(false);
    };

    BaseComment.prototype.fetch = function() {
        var self = this;
        var deferred = $.Deferred();
        if (self._loaded) {
            deferred.resolve(self.comments());
        }
        $.getJSON(
            nodeApiUrl + 'comments/',
            {target: self.id()},
            function(response) {
                self.comments(
                    ko.utils.arrayMap(response.comments, function(comment) {
                        return new CommentModel(comment, self, self.$root);
                    })
                );
                deferred.resolve(self.comments());
                self._loaded = true;
            }
        );
        return deferred;
    };

    BaseComment.prototype.submitReply = function() {
        var self = this;
        $.osf.postJSON(
            nodeApiUrl + 'comment/',
            {
                target: self.id(),
                content: self.replyContent(),
                isPublic: self.replyPublic()
            },
            function(response) {
                self.cancelReply();
                self.replyContent(null);
                self.comments.push(new CommentModel(response.comment, self, self.$root));
                if (!self.hasChildren()) {
                    self.hasChildren(true);
                }
                self.onSubmitSuccess(response);
            }
        );
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
        self.dateCreated(relativeDate(data.dateCreated));
        self.dateModified(relativeDate(data.dateModified));

        self.showChildren = ko.observable(false);

        self.hoverContent = ko.observable(false);
        
        self.editing = ko.observable(false);
        self.editVerb = self.modified ? 'edited' : 'posted';

        self.showPrivateIcon = ko.computed(function() {
            return self.isPublic() === 'private';
        });
        self.toggleIcon = ko.computed(function() {
            return self.showChildren() ? 'icon-collapse-alt' : 'icon-expand-alt';
        });
        self.editHighlight = ko.computed(function() {
            return self.canEdit() && self.hoverContent();
        });

    };

    CommentModel.prototype = new BaseComment();

    CommentModel.prototype.edit = function(data) {
        if (this.canEdit()) {
            this._content = this.content();
            this._isPublic = this.isPublic();
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
        this.hoverContent(false);
        this.content(this._content);
        this.isPublic(this._isPublic);
    };

    CommentModel.prototype.submitEdit = function() {
        var self = this;
        $.osf.postJSON(
            nodeApiUrl + 'comment/' + self.id() + '/',
            {
                content: self.content(),
                isPublic: self.isPublic()
            },
            function(response) {
                self.content(response.content);
                self.dateModified(relativeDate(response.dateModified));
                self.editing(false);
                self.$root.editors -= 1;
            }
        ).fail(function() {
            self.cancelEdit();
        });
    };

    CommentModel.prototype.reportSpam = function() {
        var self = this;
        bootbox.confirm('Are you sure you want to report this comment as spam?', function(response) {
            if (response) {
                $.osf.postJSON(
                    nodeApiUrl + 'comment/' + self.id() + '/report/spam/',
                    {isSpam: !self.isSpam()},
                    function(response) {
                        self.isSpam(!self.isSpam());
                    }
                );
            }
        });
    };

    CommentModel.prototype.remove = function() {
        var self = this;
        bootbox.confirm('Are you sure you want to delete this comment?', function(response) {
            if (response) {
                $.ajax({
                    type: 'DELETE',
                    url: nodeApiUrl + 'comment/' + self.id() + '/',
                    success: function(response) {
                        var siblings = self.$parent.comments;
                        siblings.splice(siblings.indexOf(self), 1);
                    }
                });
            }
        });
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

    CommentModel.prototype.onSubmitSuccess = function(response) {
        this.showChildren(true);
    };

    /*
     *
     */
    var CommentListModel = function(userName, canComment, hasChildren) {

        BaseComment.prototype.constructor.call(this);

        this.$root = this;

        this.editors = 0

        this.userName = ko.observable(userName);
        this.canComment = ko.observable(canComment);
        this.hasChildren = ko.observable(hasChildren);
        this.discussion = ko.observableArray();

        this.fetch();
        this.fetchDiscussion();

    };

    CommentListModel.prototype = new BaseComment();

    CommentListModel.prototype.onSubmitSuccess = function() {};

    CommentListModel.prototype.fetchDiscussion = function() {
        var self = this;
        $.getJSON(
            nodeApiUrl + 'comments/discussion/',
            function(response) {
                self.discussion(response.discussion);
            }
        )
    };

    CommentListModel.prototype.discussionToolTips = function(elm) {
        $(elm).tooltip();
    };

    CommentListModel.prototype.initListeners = function() {
        var self = this;
        $(window).on('beforeunload', function() {
            if (self.editors) {
                return 'Your comments have unsaved changes. Are you sure ' +
                    'you want to leave this page?';
            }
        });
    };

    var init = function(selector, userName, canComment, hasChildren) {
        var viewModel = new CommentListModel(userName, canComment, hasChildren);
        var $elm = $(selector);
        if (!$elm.length) {
            throw('No results found for selector');
        }
        ko.applyBindings(viewModel, $elm[0]);
        viewModel.initListeners();
    };

    return {
        init: init
    }

})(window, $, ko, bootbox);
