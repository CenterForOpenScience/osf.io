/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var OauthAddonNodeConfigVM = require('js/oauthAddonNodeConfig.js')._OauthAddonNodeConfigViewModel;
var testUtils = require('./folderPickerTestUtils.js');

var makeEmailList = function(n) {
    var ret = [];
    for (var i = 0; i < n; i++){
        ret.push(faker.internet.email());
    }
    return ret;
};

describe('OauthAddonNodeConfig', () => {
    describe('OauthAddonFolderPickerViewModel', () => {
        var settingsUrl = '/api/v1/12345/addon/config/';
        var onPickFolderSpy = sinon.spy();
        var connectAccountSpy = sinon.spy();
        var opts = {
            onPickFolder: onPickFolderSpy,
        };
        var vm = new OauthAddonNodeConfigVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker', opts);
        
        describe('#constructor', () => {
            it('applies overrides from the opts param if supplied', () => {
                vm.treebeardOptions.onPickFolder();
                assert.calledOnce(opts.onPickFolder);
            });
        });
    });
});
