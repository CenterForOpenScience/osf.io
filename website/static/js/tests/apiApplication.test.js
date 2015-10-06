/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

var testUtils = require('./utils');

var apiApp = require('js/apiApplication.js');

describe('apiApplicationsInternals', () => {
    describe('ApplicationData', () => {
        var vmd;
        // Sample data returned by an API call
        var sampleData = {
            attributes: {
                client_id: '0123456789abcdef0123456789abcdef',
                client_secret: 'abcdefghij0123456789abcdefghij0123456789',
                owner: '14abc',
                name: 'Of course it has a name',
                description: 'Always nice to have this',
                date_created: '2015-07-21T16:28:28.037000',
                home_url: 'http://tumblr.com',
                callback_url: 'http://goodwill.org'
            },
            links: {
                self: 'http://localhost:8000/v2/users/14abc/applications/0123456789abcdef0123456789abcdef/',
                html: 'http://localhost:5000/settings/applications/0123456789abcdef0123456789abcdef/'
            },
            type: 'applications'
        };

        beforeEach(() => {
            vmd = new apiApp._ApplicationData(sampleData);
        });
        // TODO: Test data populates and test serializer serializes
        // TODO: Test that changing to incorrect data makes us fail validation

        it('loads data into the specified fields', () => {
            var attributes = sampleData.attributes;
            assert.equal(attributes.name, vmd.name());
            assert.equal(attributes.description, vmd.description());
            assert.equal(attributes.home_url, vmd.homeUrl());
            assert.equal(attributes.callback_url, vmd.callbackUrl());

            assert.equal(attributes.owner, vmd.owner);
            assert.equal(attributes.client_id, vmd.clientId);
            assert.equal(attributes.client_secret, vmd.clientSecret());

            // TODO: May change when links field changes
            assert.equal(sampleData.links.html, vmd.webDetailUrl);
            assert.equal(sampleData.links.self, vmd.apiDetailUrl);
        });

        it('is invalid when missing required field', () => {
            vmd.name('');
            assert.isFalse(vmd.isValid());
        });

        it.skip('is invalid when field not a url', () => {
            // FIXME: URL validator not working as intended
            vmd.callbackUrl('notaurl');
            assert.isFalse(vmd.isValid());
        });

    });
});
