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
            title: {
                api: expectedTitle
            },
            institutions: [{
                id: 'cos',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'Center For Open Science'
            }]
        },
        currentUser: {
            fullname: 'John Cena',
            institutions: [{
                id: 'cos',
                logo_path: '/static/img/institutions/cos-shield.png',
                name: 'Center For Open Science'
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

    before(() => {
        modifyInstStub = sinon.stub(viewModel, '_modifyInst');
        bootboxStub = sinon.stub(bootbox, 'dialog');
    });
    after(() => {
        viewModel.modifyChildrenDialog.restore();
    });

    it('shows a dialog if the Node has children', () => {
        modifyStub = sinon.stub(viewModel, 'modifyChildrenDialog');
        viewModel.hasChildren(true);
        viewModel.submitInst({});
        assert(modifyStub.called);
        viewModel._modifyInst.restore();
    });
    it('modifyChildrenDialog shows an add message if adding an institution', () => {
        viewModel.isAddInstitution(true);
        viewModel.modifyChildrenDialog();
        var opts = bootboxStub.args[0];
        assert(opts.title === expectedTitle);
    });
});
