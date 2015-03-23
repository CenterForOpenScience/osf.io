/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var ko = require('knockout');

var comment = require('js/comment');

sinon.assert.expose(assert, {prefix: ''});

console.log(comment);

describe('comment', () => {
    describe('ViewModels', () => {

        describe('CommentModel', () => {
            var vm;
            var parent = {
                comment: "Not great.",
                overarching: ko.observable(10),
                indesc: ko.observable(42)
            };
            var data = {
                thursday: "Before Friday",
                object2: {
                    offer: "Greatly appreciated",
                    other: 5
                },
                more: "The other day"
            };

            beforeEach(() => {
                //vm = new comment.ViewModel();
                //parent = comment.BaseComment();
            });

            it('comment good', () => {
                assert.isTrue(true);
            });

            it('Insert knockout into parent', () => {
                comment.mapJS(data, parent);
                assert.isEqual(data[object2][other], parent[object2][other]());
            })
        });
    });
});
