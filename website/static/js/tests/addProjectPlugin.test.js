/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var Raven = require('raven-js');
var $ = require('jquery');
var m = require('mithril');
var AddProject = require('js/addProjectPlugin');

// TODO write tests for AddProject
//console.log(AddProject);
describe('AddProjectPlugin', () => {
    it.skip('should validate if new project name is not empty', () => {
        var project = new AddProject.controller();
        project.newProjectName('Hello');
        project.checkValid();
        assert.ok(project.isValid(), true);
        project.newProjectName('');
        project.checkValid();
        assert.notOk(project.isValid(), false);
    });
    it.skip('should reset states and defaults when reset function runs', () => {
        var project = new AddProject.controller();
        // Change values
        project.newProjectName('Hello there');
        project.viewState('error');
        project.newProjectDesc('Description');
        project.newProjectCategory('thesis');
        project.newProjectInheritContribs(true);
        // Reset
        project.reset();
        // Assert the return to defaults;
        assert.equal(project.newProjectName(), '');
        assert.equal(project.viewState(), 'form');
        assert.equal(project.newProjectDesc(), '');
        assert.equal(project.newProjectCategory(), 'project');
        assert.equal(project.project.newProjectInheritContribs(), false);
    });
});
