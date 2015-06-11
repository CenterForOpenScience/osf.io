/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ZeroClipboard = require('zeroclipboard');
var AddonNodeConfigVM = require('js/addonNodeConfig')._AddonNodeConfigViewModel;
var testUtils = require('./folderPickerTestUtils.js');

var makeEmailList = function(n) {
    var ret = [];
    for (var i = 0; i < n; i++){
        ret.push(faker.internet.email());
    }
    return ret;
};

describe('AddonNodeConfig', () => {
    describe('AddonFolderPickerViewModel', () => {
        var settingsUrl = '/api/v1/12345/addon/config/';
        var onPickFolderSpy = sinon.spy();
        var decodeFolderSpy = sinon.spy();
        var opts = {
            onPickFolder: onPickFolderSpy,
            decodeFolder: decodeFolderSpy
        };
        var vm = new AddonNodeConfigVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker', opts);
        
        describe('#constructor', () => {
            it('applies overrides from the opts param if supplied', () => {
                vm.treebeardOptions.onPickFolder();
                assert.calledOnce(opts.onPickFolder);
                vm.treebeardOptions.decodeFolder();
                assert.calledOnce(opts.decodeFolder);
            });
        });
    });
});
