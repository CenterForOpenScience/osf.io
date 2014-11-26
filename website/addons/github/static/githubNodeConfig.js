
/**
 * Module that controls the GitHub node settings. Includes Knockout view-model
 * for syncing data.
 */



;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery',
                'zeroclipboard', 'osfutils', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['folderPicker', 'zeroclipboard'], function() {

            global.GithubNodeConfig  = factory(ko, jQuery, ZeroClipboard);
            $script.done('githubNodeConfig');
        });
    } else {
        global.GithubNodeConfig  = factory(ko, jQuery, ZeroClipboard);
    }
}(this, function(ko, $, FolderPicker, ZeroClipboard) {
    'use strict';
    ko.punches.attributeInterpolationMarkup.enable();
    /**
     * Knockout view model for the Github node settings widget.
     */
    var ViewModel = function(url, submitUrl, selector) {
        var self = this;
        var repoInFiles;
        self.selector = selector;
        // Auth information
        self.nodeHasAuth = ko.observable(false);
        // whether current user is authorizer of the addon
        self.userIsOwner = ko.observable(false);
        // whether current user has an auth token
        self.userHasAuth = ko.observable(false);
        // Currently linked folder, an Object of the form {name: ..., path: ...}
        self.ownerName = ko.observable('');
        self.repos = ko.observableArray([]);
        // Display Repositories in Select menu
        self.displayRepos = ko.observableArray([]);
        self.currentRepoUser = ko.observable();
        self.currentRepoName = ko.observable();
        self.repoFullName = ko.observable();
        self.urls = ko.observable({});
        self.SelectedRepository = ko.observable();
        self.createRepo = ko.observable();
        self.displayMessage = ko.observable();
        self.displayMessageClass = ko.observable();
        self.githubUser = ko.observable();
        self.githubRepo = ko.observable();
        self.githubRepoUser=ko.observable();
              // Flashed messages

        self.loading = ko.observable(false);
        // Whether the initial data has been fetched form the server. Used for
        // error handling.
        self.loadedSettings = ko.observable(false);
        // Whether the contributor emails have been loaded from the server
        self.loadedEmails = ko.observable(false);

        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.ownerName(data.ownerName);
            self.nodeHasAuth(data.nodeHasAuth);
            self.userIsOwner(data.userIsOwner);
            self.userHasAuth(data.userHasAuth);
            self.repos(data.repos);
            self.urls(data.urls);
            self.currentRepoUser(data.repoUser);
            self.currentRepoName(data.repoName);
            self.repoFullName(data.repoUser + ' / ' + data.repoName)
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: url, type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response.result);
                    loadRepos();
                    self.loadedSettings(true);
                },
                error: function(xhr, textStatus, error) {
                    self.changeMessage('Could not retrieve Github settings at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@osf.io">support@osf.io</a>.',
                        'text-warning');
                    Raven.captureMessage('Could not GET Github settings', {
                        url: url,
                        textStatus: textStatus,
                        error: error
                    });
                }
            });
        };

        /**
         * Function that displays list of repositories of authorized user
         */
        function loadRepos() {
            $.getJSON(
                self.urls().repos,
                {},
                function (repos) {
                    if (repos.length == 0)
                    {
                        self.changeMessage("You don't have any repository yet !",'text-danger');
                    }
                    else
                    for (var i = 0; i < repos.length; i++) {
                        self.displayRepos.push(repos[i].user + ' / ' + repos[i].repo);
                    }
                self.SelectedRepository(self.repoFullName());
                });
        }

        self.fetchFromServer();

          /**
         * Whether or not to show the Import Access Token Button
         */
        self.showImport = ko.computed(function() {
            // Invoke the observables to ensure dependency tracking
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            return userHasAuth && !nodeHasAuth && loaded;
        });

        /** Whether or not to show the full settings pane. */
        self.showSettings = ko.computed(function() {
            return self.nodeHasAuth();
        });

          /** Whether or not to show the Create Access Token button */
        self.showTokenCreateButton = ko.computed(function() {
            // Invoke the observables to ensure dependency tracking
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            return !userHasAuth && !nodeHasAuth && loaded;
        });

        /** Change the flashed message. */
        self.changeMessage = function(text, css, timeout) {
            self.displayMessage(text);
            var cssClass = css || 'text-info';
            self.displayMessageClass(cssClass);
            if (timeout) {
                // Reset displayMessage after timeout period
                setTimeout(function() {
                    self.displayMessage('');
                    self.displayMessageClass('text-info');
                }, timeout);
            }
        };


         /**
         * Send DELETE request to deauthorize this node.
         */
        function sendDeauth() {
            return $.ajax({
                url: self.urls().deauthorize,
                type: 'DELETE',
                success: function() {
                    // Update observables
                    self.nodeHasAuth(false);
//                    self.currentDisplay(null);
                    self.changeMessage('Deauthorized Github.', 'text-warning', 3000);
                },
                error: function() {
                    self.changeMessage('Could not deauthorize because of an error. Please try again later.',
                        'text-danger');
                }
            });
        }

        /** Pop up a confirmation to deauthorize Github from this node.
         *  Send DELETE request if confirmed.
         */
        self.deauthorize = function() {
            bootbox.confirm({
                title: 'Deauthorize Github?',
               message: 'Are you sure you want to remove this Github authorization?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return sendDeauth();
                    }
                }
            });
        };

         // Callback for when PUT request to import user access token
        function onImportSuccess(response) {
            var msg = response.message || 'Successfully imported access token from profile.';
            // Update view model based on response
            self.changeMessage(msg, 'text-success', 3000);
            self.updateFromData(response.result);
        }

        function onImportError() {
            self.displayMessage('Error occurred while importing access token.');
            self.displayMessageClass('text-danger');
        }

        /**
         * Send PUT request to import access token from user profile.
         */
        self.importAuth = function() {
            bootbox.confirm({
                title: 'Import Github Access Token?',
                message: 'Are you sure you want to authorize this project with your Github access token?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return $.osf.putJSON(self.urls().importAuth, {})
                            .done(onImportSuccess)
                            .fail(onImportError);
                    }
                }
            });
        };

        self.showSettings = ko.computed(function() {
            return self.nodeHasAuth();
        });

        self.cancel = function(){
            self.SelectedRepository(null);
        }

        /**
         * send create GITHUB request to create a new repository
         */
            self.createRepo = function(){

                bootbox.prompt('Name your new repo', function(repoName)
                {
                    // Return if cancelled
                    if (repoName === null)
                        return;

                    if (repoName === '') {
                        self.displayMessage('Your repo must have a name');
                        return;
                    }

                    $.osf.postJSON(
                        '/api/v1/github/repo/create/',
                        {name: repoName}
                    ).done(function (response) {
                            var repoFullName = response.user + ' / ' + response.repo;
                            self.displayRepos.push(repoFullName);
                        }).fail(function () {
                            self.displayMessage('Could not create repository');
                        });
                })

            }


        var updateUserRepo = function(val){
            var repoParts = val.split('/');
            self.githubUser(repoParts[0].trim());
            self.githubRepo(repoParts[1].trim());
        }

        self.submitSettings = function(val){
            if(self.repoFullName()==self.SelectedRepository()) {
                self.changeMessage('Repository already connected', 'text-danger');
            }
            else {
                updateUserRepo(self.SelectedRepository())
                $.osf.postJSON(
                    self.urls().config,
                    {
                        'github_user': self.githubUser(),
                        'github_repo': self.githubRepo()
                    }
                ).done(function () {
                        self.changeMessage('Settings-updated', 'addon-settings-message text-success', 3000);
                    }).fail(function () {
                        self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
                    }
                );
            self.repoFullName(self.SelectedRepository());
            return false;
            }

        }


    };
    // Public API
    function GithubNodeConfig(selector, url, submitUrl) {
        var self = this;
        self.url = url;
        self.viewModel = new ViewModel(url, submitUrl, selector);
        $.osf.applyBindings(self.viewModel, selector);
        window.bobob = self.viewModel;
    }

    return GithubNodeConfig;
}));
