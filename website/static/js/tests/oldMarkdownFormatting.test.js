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

            var html = '<ol>\n<li>hello</li><li>there</li></ol>';
            assert.equal(rendered, html);
        });
    });
    describe('orderedListChangeSymbols', () => {

        it('returns a numbered list even when the symbols change', () => {
            var text = '1. hello \n 2. there \n * friend';

            var rendered = mdOld.render(text);

            var html = '<ol>\n<li>hello</li><li>there</li><li>friend</li></ol>';
            assert.equal(rendered, html);
        });

    });
    describe('listNoSpace', () => {

        it('returns a paragraph because there is not a blank line before list starts', () => {
            var text = 'This Should Not Render\n1. hello \n 2. there \n * friend';

            var rendered = mdOld.render(text);

            var html = '<p>1. hello 2. there * friend</p>';
            assert.equal(rendered, html);
        });

    });
});
