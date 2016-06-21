/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var comment = require('js/comment');
var convertMentionHtmlToMarkdown = comment.convertMentionHtmlToMarkdown;
var convertMentionMarkdownToHtml = comment.convertMentionMarkdownToHtml;

describe('@Mentions', () => {
    var atMentionHTML = 'Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="@">@Test User</span>';
    var atMentionMarkdown = 'Hello, [@Test User](/12345/)';
    var plusMentionHTML = 'Hello, <span class="atwho-inserted" contenteditable="false" data-atwho-guid="12345" data-atwho-at-query="+">+Test User</span>';
    var plusMentionMarkdown = 'Hello, [+Test User](/12345/)';
    var returnHTML = 'Test.<br>';
    var returnMarkdown = 'Test.&#13;&#10;';
    var returnMarkdown2 = 'Test.\r\n';


    describe('convertMentionHtmlToMarkdown', () => {
        it('convert <br> to &#13;&#10;', () => {
            var converted = convertMentionHtmlToMarkdown(returnHTML);
            assert.equal(converted, returnMarkdown);
        });
        it('convert @ mention to markdown link', () => {
            var converted = convertMentionHtmlToMarkdown(atMentionHTML);
            assert.equal(converted, atMentionMarkdown);
        });
        it('convert + mention to markdown link', () => {
            var converted = convertMentionHtmlToMarkdown(plusMentionHTML);
            assert.equal(converted, plusMentionMarkdown);
        });
    });
    describe('convertMentionMarkdownToHtml', () => {
            it('convert \\r\\n; to <br>', () => {
                var converted = convertMentionMarkdownToHtml(returnMarkdown2);
                assert.equal(converted, returnHTML);
            });
            it('convert @ mention markdown link to span', () => {
                var converted = convertMentionMarkdownToHtml(atMentionMarkdown);
                assert.equal(converted, atMentionHTML);
            });
            it('convert + mention markdown link to span', () => {
                var converted = convertMentionMarkdownToHtml(plusMentionMarkdown);
                assert.equal(converted, plusMentionHTML);
            });
    });

});
