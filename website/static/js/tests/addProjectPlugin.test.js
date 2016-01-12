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
    it('should load project categories from api server', () => {
        var project = new AddProject.controller();
        var promise = project.loadCategories();
        promise.then(function(){
            assert.ok(project.categoryList.length > 0);
            console.log(project.categoryList);
        });
    });
});