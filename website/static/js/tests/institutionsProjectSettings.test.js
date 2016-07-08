/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var m = require('mithril');
var InstitutionProjectSettings = require('js/institutionProjectSettings');
var bootbox = require('bootbox');

describe('InstitutionSettings', () => {
    var data = {
        apiV2Prefix: 'http://localhost:8000/v2/',
        node: {
            title: 'Sample Project',
            id: 'abcde',
            urls: {
                api: '/api/v1/project/abcde'
            },
            institutions: [{
                id: 'cos',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'Center For Open Science'
            }, {
                id: 'uoa',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'University of Awesome'
            }]},
        currentUser: {
            fullname: 'John Cena',
            institutions: [{
                id: 'cos',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'Center For Open Science'
            },
                {
                    id: 'bff',
                    logo_path: '/static/img/institutions/cos-shield.png',
                    name: 'Best Friend University'
                }]
        }
    };

    var item = {
        name: 'Sample Institution',
        id: 'abcde'
    };

    var modifyStub;

    beforeEach(() => {
        modifyStub = sinon.stub(viewModel, 'modifyDialog');
    });

    afterEach(() => {
        modifyStub.restore();
    });

    var viewModel = new InstitutionProjectSettings.ViewModel(data);

    viewModel.institutionInAllChildren = function() {
        return false;
    };

    it('user variables set', () => {
        assert.equal(viewModel.userInstitutions, data.currentUser.institutions);
        assert.equal(viewModel.userInstitutionsIds.length, 2);
        assert.equal(viewModel.userInstitutionsIds[0], ['cos']);
        assert.equal(viewModel.userInstitutionsIds[1], ['bff']);
    });

    it('node variables set', () => {
        assert.equal(viewModel.affiliatedInstitutions(), data.node.institutions);
        assert.equal(viewModel.affiliatedInstitutionsIds().length, 2);
        assert.equal(viewModel.affiliatedInstitutionsIds()[0], ['cos']);
        assert.equal(viewModel.affiliatedInstitutionsIds()[1], ['uoa']);
        assert.equal(viewModel.availableInstitutions().length, 1);
        assert.equal(viewModel.availableInstitutions()[0], data.currentUser.institutions[1]);
    });

    it('computed variables set', () => {
        assert.equal(viewModel.affiliatedInstitutions(), data.node.institutions);
        assert.equal(viewModel.affiliatedInstitutionsIds().length, 2);
        assert.equal(viewModel.affiliatedInstitutionsIds()[0], ['cos']);
        assert.equal(viewModel.affiliatedInstitutionsIds()[1], ['uoa']);
    });

    it('shows a dialog if the Node has children', () => {
        viewModel.hasChildren(true);
        viewModel.submitInst(item);
        assert(modifyStub.called);
    });

    it('does not show dialog if the Node has no children', () => {

        viewModel.hasChildren(false);
        viewModel.submitInst(item);
        assert.isFalse(modifyStub.called);
    });


});
