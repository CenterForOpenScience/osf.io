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
        name: 'Sample Institution'
    };

    var modifyStub;
    var modifyInstStub;
    var bootboxStub;

    var viewModel = new InstitutionProjectSettings.ViewModel(data);

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
        modifyStub = sinon.stub(viewModel, 'modifyChildrenDialog');
        viewModel.hasChildren(true);
        viewModel.submitInst({});
        assert(modifyStub.called);
        modifyStub.restore();
    });

    it('does not show dialog if the Node has no children', () => {
        modifyStub = sinon.stub(viewModel, 'modifyChildrenDialog');
        viewModel.hasChildren(false);
        viewModel.submitInst({});
        assert.isFalse(modifyStub.called);
        modifyStub.restore();
    });


});
