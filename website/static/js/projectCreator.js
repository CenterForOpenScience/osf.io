/**
* A KO component for the project creation form.
*/
'use strict';

var $ = require('jquery');
require('select2');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('osf-helpers');

var CREATE_URL = '/api/v1/project/new/';

/*
    * ViewModel for the project creation form.
    *
    * Template: osf-project-creat-form in component/dashboard_templates.mako
    *
    * Params:
    *  - data: Data to populate the template selection input
    */
function ProjectCreatorViewModel(params) {
    var self = this;
    self.params = params || {};
    self.minSearchLength = 2;
    self.title = ko.observable('');
    self.description = ko.observable();
    self.errorMessage = ko.observable('');

    self.hasFocus = params.hasFocus;

    self.submitForm = function () {
        if (self.title().trim() === '') {
            self.errorMessage('This field is required.');
        } else {
            self.createProject();
        }
    };

    self.createProject = function() {
        $osf.postJSON(
            CREATE_URL,
            self.serialize()
        ).done(
            self.createSuccess
        ).fail(
            self.createFailure
        );
    };

    self.createSuccess = function(data) {
        window.location = data.projectUrl;
    };

    self.createFailure = function() {
        $osf.growl('Could not create a new project.', 'Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');

    };

    self.serialize = function() {
        return {
            title: self.title(),
            description: self.description(),
            template: $('#templates').val()
        };
    };
    /**
        * Query the current users projects from a local cache
        *
        * @method ownProjects
        * @param {String} q a string query
        * @return {Array} A filtered array of strings
        */
    self.ownProjects = function(q) {
        if (q === '') {
            return self.templates;
        }
        return self.templates.filter(function(item) {
            return item.text.toLowerCase().indexOf(q.toLowerCase()) !== -1;
        });
    };

    self.query = function(query) {
        if (query.term.length > self.minSearchLength) {
            self.fetchNodes(query.term, query.callback);
            return;
        }
        query.callback({
            results: [{
                text: 'Your Projects',
                children: self.ownProjects(query.term)
            }]
        });
    };

    /**
        * Fetch Nodes from the search api and concat. them with the current users projects
        *
        * @method fetchNodes
        * @param {String} q A string query
        * @param {Function} cb A callback to call with the list of projects
        * @return null
        */
    self.fetchNodes = function(q, cb) {
        $osf.postJSON(
            '/api/v1/search/node/',
            {
                includePublic: true,
                query: q,
            }
        ).done(function(data) {
            var results = [];
            var local = self.ownProjects(q);
            var fetched = self.loadNodes(data.nodes);

            // Filter against local projects so that duplicates are not shown
            fetched = fetched.filter(function(element) {
                for (var i = 0; i < local.length; i++) {
                    if (element.id === local[i].id) {
                        return false;
                    }
                }
                return true;
            });

            if (fetched.length > 0) {
                results.push({
                    text: 'Other Projects',
                    children: fetched
                });
            }

            if (local.length > 0) {
                results.push({
                    text: 'Your Projects',
                    children: local
                });
            }

            cb({results: results});
        }).fail(function() {
            //Silently error by just returning your projects
            cb({
                results: [{
                    text: 'Your Projects',
                    children: self.ownProjects(q)
                }]
            });
        });
    };

    self.loadNodes = function(nodes) {
        return ko.utils.arrayMap(nodes, function(node) {
            return {
                'id': node.id,
                'text': node.title
            };
        });
    };

    self.templates = self.loadNodes(params.data);
    $('#templates').select2({
        allowClear: true,
        placeholder: 'Select a project to use as a template',
        query: self.query
    });
}

ko.components.register('osf-project-create-form', {
    viewModel: ProjectCreatorViewModel,
    template: {element: 'osf-project-create-form'}
});
