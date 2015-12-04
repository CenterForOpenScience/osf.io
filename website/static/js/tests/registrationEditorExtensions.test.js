/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var Raven = require('raven-js');
var $ = require('jquery');
var RegistrationEditor = require('js/registrationEditorExtensions');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});


describe('RegistrationEditor.osfUploader', () => {
    var itemIsOsfstorage = {
        data: {
            provider: 'osfstorage',
            name: 'name',
            permissions: {
                edit: true,
                view: true
            },
            open: true,
            load: true
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

    // variables to test the filePicker
    // var element = {
    //     id: 'testId'
    // };

    // var valueAccessor = "";
    // var allBindings = "";
    // var bindingContext = "";

    describe('limitContents', () => {
        it('says provider is osfstorage and can edit', () => {
            RegistrationEditor.limitContents(itemIsOsfstorage);
            assert.isTrue(itemIsOsfstorage.data.permissions.edit);
        });
        it('says provider is osfstorage and can view', () => {
            RegistrationEditor.limitContents(itemIsOsfstorage);
            assert.isTrue(itemIsOsfstorage.data.permissions.view);
        });
        it('says provider is not osfstorage and cannot edit', () => {
            RegistrationEditor.limitContents(itemIsNotOsfstorage);
            assert.isFalse(itemIsNotOsfstorage.data.permissions.edit);
        });
        it('says provider is not osfstorage and cannot view', () => {
            RegistrationEditor.limitContents(itemIsNotOsfstorage);
            assert.isFalse(itemIsNotOsfstorage.data.permissions.view);
        });
    });

    // TODO
    // describe('filePicker', () => {
    //     var vm;

    //     beforeEach(() => {
    //         vm = new RegistrationEditor.Uploader();
    //     });

    //     it('sets dropzone id to element id passed to handler', () => {
    //         RegistrationEditor.filePicker(element, valueAccessor, allBindings, vm, bindingContext);
    //         assert.isTrue(true);
    //     });
    // });    

});
