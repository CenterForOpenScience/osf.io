/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var m = require('mithril');
var InstitutionProjectSettings = require('js/institutionProjectSettings');
var bootbox = require('bootbox');

var expectedTitle = 'Sample Project';

    window.contextVars = $.extend(true, {}, window.contextVars, {
        node: {
            title: expectedTitle
            },
            institutions: [{
                id: 'cos',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'Center For Open Science'
            }, {
                id: 'uoa',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'University of Awesome'
            }]
        },
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
});

describe('InstitutionSettings', () => {
    var data = {
        apiV2Prefix: 'http://localhost:8000/v2/'
    };
    var item = {
        name: 'Sample Institution'
    };

    var modifyStub;
    var modifyInstStub;
    var bootboxStub;

    var viewModel = new InstitutionProjectSettings.ViewModel(data);

    it('user variables set', (done) => {
        assert.equal(viewModel.userInstitutions, window.contextVars.currentUser.institutions);
        assert.equal(viewModel.userInstitutionsIds().length, 2);
        assert.equal(viewModel.userInstitutionsIds()[0], ['cos']);
        assert.equal(viewModel.userInstitutionsIds()[1], ['bff']);
        done();
    });

    it('node variables set', (done) => {
        assert.equal(viewModel.affiliatedInstitutions(), window.contextVars.node.institutions);
        assert.equal(viewModel.affiliatedInstitutionsIds.length, 2);
        assert.equal(viewModel.affiliatedInstitutionsIds[0], ['cos']);
        assert.equal(viewModel.affiliatedInstitutionsIds[1], ['uoa']);
        assert.equal(viewModel.availableInstitutions().length, 1);
        assert.equal(viewModel.availableInstitutions()[0], window.contextVars.currentUser.institutions[1]);
        done();
    });

    it('computed variables set', (done) => {
        assert.equal(viewModel.affiliatedInstitutions(), window.contextVars.node.institutions);
        assert.equal(viewModel.affiliatedInstitutionsIds.length, 2);
        assert.equal(viewModel.affiliatedInstitutionsIds[0], ['cos']);
        assert.equal(viewModel.affiliatedInstitutionsIds[1], ['uoa']);
        done();
    });

    it('shows a dialog if the Node has children', (done) => {
        modifyStub = sinon.stub(viewModel, 'modifyChildrenDialog');
        viewModel.hasChildren(true);
        viewModel.submitInst({});
        assert(modifyStub.called);
        modifyStub.restore();
        done();
    });

    it('does not show dialog if the Node has no children', (done) => {
        modifyStub = sinon.stub(viewModel, 'modifyChildrenDialog');
        viewModel.hasChildren(false);
        viewModel.submitInst({});
        assert.isFalse(modifyStub.called);
        modifyStub.restore();
        done();
    });


});
