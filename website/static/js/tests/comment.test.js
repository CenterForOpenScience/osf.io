/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var faker = require('faker');

var ko = require('knockout');

var comment = require('js/comment');

sinon.assert.expose(assert, {prefix: ''});

console.log(comment);
var nodeApiUrl;

describe('comment', () => {
    describe('ViewModels', () => {

        describe('CommentModel', () => {
            var vm;
            var userid = "4r3al";
            var userName = faker.name.firstName();
            var canComment = true;
            var hasChildren = false;
            var endpoints = [
                {url: "comments/", response: ""},
                {url: "comment/", response: ""},
                {url: "comment/" + userid + "/", response: ""},
                {url: 'comment/' + userid + '/report/', response: ""},
                {url: 'comment/' + userid + '/undelete/', response: ""},
                {url: 'comment/' + userid + '/unreport/', response: ""},
                {url: 'comments/discussion/', response: ""},
                {url: 'comments/timestamps/', response: faker.date.recent(1)}
            ];
            nodeApiUrl = utils.createServer(sinon, endpoints);
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
                vm = comment.init('#commentPane', userid, userName, canComment, hasChildren);
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
