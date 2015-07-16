/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var Raven = require('raven-js');
var $ = require('jquery');
var RegistrationEditor = require('js/registrationEditorExtensions');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});


describe('RegistrationEditor.osfUploader', () => {
    var returnTrue = function() {
        return true;
    };

    var returnFalse = function() {
        return false;
    };

    var itemIsOsfstorage = {
        data: {
            provider: 'osfstorage',
            name: 'name',
            permissions: {
                edit: true,
                view: true
            }
        }
    };

    var itemIsNotOsfstorage = {
        data: {
            provider: 'anything',
            name: 'name',
            permissions: {
                edit: true,
                view: true
            },
            open: true,
            load: true,
            css: ''
        }
    };

    describe('limitOsfStorage', () => {
        it('says provider is osfstorage', () => {
            RegistrationEditor.limitOsfStorage(itemIsOsfstorage);
            assert.isTrue(itemIsOsfstorage.data.permissions.edit);
        });
        it('says provider is not osfstorage', () => {
            RegistrationEditor.limitOsfStorage(itemIsNotOsfstorage);
            assert.isFalse(itemIsNotOsfstorage.data.permissions.edit);
        });
    });

});