/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var Raven = require('raven-js');
var $ = require('jquery');
var m = require('mithril');
var AddProject = require('js/addProjectPlugin');

//console.log(AddProject);
describe('AddProjectPlugin', () => {
    it('should validate if new project name is not empty', () => {
        var project = new AddProject.controller();
        project.newProjectName('Hello');
        project.checkValid();
        assert.ok(project.isValid(), true);
        project.newProjectName('');
        project.checkValid();
        assert.notOk(project.isValid(), false);
    });
    it('should reset states and defaults when reset function runs', () => {
        var project = new AddProject.controller();
        // Change values
        project.newProjectName('Hello there');
        project.viewState('error');
        project.newProjectDesc('Description');
        project.newProjectCategory('thesis');
        // Reset
        project.reset();
        // Assert the return to defaults;
        assert.equal(project.newProjectName(), '');
        assert.equal(project.viewState(), 'form');
        assert.equal(project.newProjectDesc(), '');
        assert.equal(project.newProjectCategory(), 'project');
    });
});