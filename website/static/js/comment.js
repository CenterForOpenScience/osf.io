this.Comment = (function($, ko, bootbox) {

    'use strict';

    var PRIVACY_MAP = {
        true: 'Public',
        false: 'Private'
    };

    /*
     *
     */
    var BaseComment = function() {

        var self = this;

        self.privacyOptions= Object.keys(PRIVACY_MAP);

        self.replying = ko.observable(false);
        self.replyContent = ko.observable('');
        self.replyPublic = ko.observable(true);

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
        this.replying(false);
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
                self.comments.push(new CommentModel(response.comment, self));
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

    /*
     *
     */
    var CommentModel = function(data, $parent) {

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
        self.canStartEdit= ko.computed(function() {
            return self.canEdit && !self.editing();
        });

        self.publicIcon = ko.computed(function() {
            return self.isPublic() ? 'icon-unlock-alt' : 'icon-lock';
        });

    };

    CommentModel.prototype = new BaseComment();

    CommentModel.prototype.fetch = function() {
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
                        return new CommentModel(comment, self);
                    })
                );
                deferred.resolve(self.comments());
                self._loaded = true;
            }
        );
        return deferred;
    };

    CommentModel.prototype.edit = function() {
        this._content = this.content();
        this._isPublic = this.isPublic();
        this.editing(true);
    };

    CommentModel.prototype.cancelEdit = function() {
        this.editing(false);
        this.content(this._content);
        this.isPublic(this._isPublic);
    };

    CommentModel.prototype.submitEdit = function() {
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

    CommentModel.prototype.reportSpam = function() {
        var self = this;
        $.postJSON(
            nodeApiUrl + 'comment/' + this.id + '/report/spam/',
            {isSpam: !self.isSpam()},
            function(response) {
                self.isSpam(!self.isSpam());
            }
        )
    };

    CommentModel.prototype.remove = function() {
        var self = this;
        bootbox.confirm('Are you sure you want to delete this comment?', function(response) {
            if (response) {
                $.ajax({
                    type: 'DELETE',
                    url: nodeApiUrl + 'comment/' + this.id + '/',
                    success: function(response) {
                        var siblings = self.$parent.comments;
                        siblings.splice(siblings.indexOf(self), 1);
                    }
                });
            }
        });
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
    var CommentListModel = function(canComment) {
        BaseComment.prototype.constructor.call(this);
        this.canComment = canComment;
        this.fetch();
    };

    CommentListModel.prototype = new BaseComment();

    CommentListModel.prototype.fetch = function() {
        var self = this;
        var deferred = $.Deferred();
        $.getJSON(
            nodeApiUrl + 'comments/',
            function(response) {
                self.comments(
                    ko.utils.arrayMap(response.comments, function(comment) {
                        return new CommentModel(comment, self);
                    })
                );
                deferred.resolve(self.comments());
            }
        );
        return deferred;
    };

    CommentListModel.prototype.onSubmitSuccess = function() {};

    var init = function(selector, canComment) {
        var viewModel = new CommentListModel(canComment);
        var $elm = $(selector);
        if (!$elm.length) {
            throw('No results found for selector');
        }
        ko.applyBindings(viewModel, $elm[0]);
    };

    return {
        init: init
    }

})($, ko, bootbox);
