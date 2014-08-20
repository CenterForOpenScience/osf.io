;
(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.ProjectCreator = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function ProjectCreatorViewModel(url) {
        var self = this;
        self.minSearchLength = 2;
        self.url = url;

        self.title = ko.observable('').extend({
            required: true,
            maxLength: 200
        });
        self.description = ko.observable();
        self.templates = [];

        self.createProject = function() {
            $.osf.postJSON(self.url, self.serialize(), self.createSuccess, self.createFailure);
        };

        self.createSuccess = function(data) {
            window.location = data.projectUrl;
        };

        self.createFailure = function() {
            bootbox.alert('Could not create a new project. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
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
            $.osf.postJSON('/api/v1/search/node/', {
                    includePublic: true,
                    query: q
                },
                function(data) {
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

                    cb({
                        results: results
                    });
                },
                function() {
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

        function fetchSuccess(ret) {
            self.templates = self.loadNodes(ret.nodes);

            $('#templates').select2({
                allowClear: true,
                placeholder: 'Select a Project to Use as a Template',
                query: self.query
            });
        }

        function fetchFailed() {
            bootbox.alert('Could not retrieve dashboard nodes at this time. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
        }

        $.ajax({
            type: 'GET',
            url: '/api/v1/dashboard/get_nodes/',
            dataType: 'json',
            success: fetchSuccess,
            error: fetchFailed
        });

    }

    function ProjectCreator(selector, url) {
        var viewModel = new ProjectCreatorViewModel(url);
        // Uncomment for debugging
        //window.viewModel = viewModel;
        $.osf.applyBindings(viewModel, selector);
    }

    return ProjectCreator;
}));
