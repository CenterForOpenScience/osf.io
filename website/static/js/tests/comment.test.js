'use strict';
var assert = require('chai').assert;

var comment = require('js/comment');
var BaseComment = comment.BaseComment;
var CommentModel = comment.CommentModel;

describe('@Mentions', () => {

    describe('convertHtmlToMarkdown', () => {
        describe('BaseComment', () => {
            it('convert <br> to &#13;&#10;', () => {
                var comment = new BaseComment();
                comment.replyContent('Test.<br>');
                assert.equal(comment.saveContent(), 'Test.&#13;&#10;');
            });
            it('convert @ mention to markdown link', () => {
                var comment = new BaseComment();
                comment.replyContent('Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="@">@Test User</span>');
                assert.equal(comment.saveContent(), 'Hello, [@Test User](/12345/)');
            });
            it('convert + mention to markdown link', () => {
                var comment = new BaseComment();
                comment.replyContent('Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="+">+Test User</span>');
                assert.equal(comment.saveContent(), 'Hello, [+Test User](/12345/)');
            });
        });
        describe('CommentModel', () => {
            it('convert <br> to &#13;&#10;', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Test.<br>');
                assert.equal(comment.editedContent(), 'Test.&#13;&#10;');
            });
            it('convert @ mention to markdown link', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="@">@Test User</span>');
                assert.equal(comment.editedContent(), 'Hello, [@Test User](/12345/)');
            });
            it('convert + mention to markdown link', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="+">+Test User</span>');
                assert.equal(comment.editedContent(), 'Hello, [+Test User](/12345/)');
            });
        });
    });
    describe('convertMarkdownToHtml', () => {
        describe('CommentModel', () => {
            it('convert \\r\\n; to <br>', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Test.\r\n');
                assert.equal(comment.editableContent(), 'Test.<br>');
            });
            it('convert @ mention markdown link to span', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Hello, [@Test User](/12345/)');
                assert.equal(comment.editableContent(), 'Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="@">@Test User</span>');
            });
            it('convert + mention markdown link to span', () => {
                var $parent = {};
                var $root = {
                    author: 'George Ant',
                    nodeId: function() {
                        return '56789';
                    }
                };
                var data = {
                    id: 4,
                    attributes: {}
                };
                var comment = new CommentModel(data, $parent, $root);
                comment.content('Hello, [+Test User](/12345/)');
                assert.equal(comment.editableContent(), 'Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="+">+Test User</span>');
            });
        });
    });

});
