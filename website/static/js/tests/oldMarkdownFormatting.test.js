/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var mdOld = require('js/markdown').old;


// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('oldMarkdown', () => {

    describe('orderedList', () => {

        it('returns a numbered list', () => {
            var text = '1. hello\n2. there';

            var rendered = mdOld.render(text);

            var html = '<ol>\n<li>hello</li>\n<li>there</li>\n</ol>\n';
            assert.equal(rendered, html);
        });
    });
    describe('orderedListChangeSymbols', () => {

        it('returns a numbered list even when the symbols change', () => {
            var text = '1. hello \n 2. there \n * friend';

            var rendered = mdOld.render(text);

            var html = '<ol>\n<li>hello</li>\n<li>there</li>\n<li>friend</li>\n</ol>\n';
            assert.equal(rendered, html);
        });

    });
    describe('listNoSpace', () => {

        it('returns a paragraph because there is not a blank line before list starts', () => {
            var text = 'Not a list but a paragraph\n1. hello\n2. there\n* friend';

            var rendered = mdOld.render(text);

            var html = '<p>Not a list but a paragraph\n1. hello\n2. there\n* friend</p>\n';
            assert.equal(rendered, html);
        });

    });
});
