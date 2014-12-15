///**
// * Module that controls the Google Drive node settings. Includes Knockout view-model
// * for syncing data.
// */
//;(function (global, factory) {
//    if (typeof define === 'function' && define.amd) {
//        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
//    } else {
//        global.GdriveNodeConfig  = factory(ko, jQuery);
//    }
//}(this, function(ko, $) {
//    // Enable knockout punches
//    ko.punches.enableAll();

/**
* Module that controls the Dropbox node settings. Includes Knockout view-model
* for syncing data, and HGrid-folderpicker for selecting a folder.
*/
'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var FolderPicker = require('folderpicker');
var ZeroClipboard = require('zeroclipboard');
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
var $osf = require('osf-helpers');

ko.punches.enableAll();
/**
    * Knockout view model for the Google Drive node settings widget.
    */
    var ViewModel = function(url, selector, folderPicker) {
        var self = this;
        self.url = url;
        self.nodeHasAuth = ko.observable(false);
        self.userHasAuth = ko.observable(false);

        //Api key required for Google picker
        self.api_key = ko.observable();
        var access_token;

        self.owner = ko.observable();
        self.ownerName = ko.observable();
        self.urls = ko.observable();

        //Folderpicker specific
        self.folderPicker =  folderPicker;
        self.selected = ko.observable(null);
        self.selectedName = ko.observable();

        self.loadedSettings = ko.observable(false);

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        // Get data from the config GET endpoint
        function onFetchSuccess(response) {
            // Update view model
            self.nodeHasAuth(response.result.nodeHasAuth);
            self.userHasAuth(response.result.userHasAuth);
            self.urls(response.result.urls);
            self.ownerName(response.result.ownerName);
            self.owner(response.result.urls.owner);
            self.api_key(response.result.api_key);
            access_token = response.result.access_token;
            self.loadedSettings(true);
        }
        function onFetchError(xhr, textstatus, error) {
            self.message('Could not fetch settings.');
        }
        function fetch() {
            $.ajax({url: self.url, type: 'GET', dataType: 'json',
                    success: onFetchSuccess,
                    error: onFetchError
            });
        }

        fetch();
         /** Change the flashed status message */
        self.changeMessage = function(text, css, timeout) {
            self.message(text);
            var cssClass = css || 'text-info';
            self.messageClass(cssClass);
            if (timeout) {
                // Reset message after timeout period
                setTimeout(function() {
                    self.message('');
                    self.messageClass('text-info');
                }, timeout);
            }
        };

        /** Whether or not to show the Create Access Token button */
        self.showTokenCreateButton = ko.computed(function() {
            // Invoke the observables to ensure dependency tracking
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            return !userHasAuth && !nodeHasAuth && loaded;
        });

        self.createAuth = function(){

                    $.osf.postJSON(
                    self.urls().create
                    ).success(function(response){
                        window.location.href = response.url;
                        self.changeMessage('Successfully authorized Google Drive account', 'text-primary');
                    }).fail(function(){
                        self.changeMessage('Could not authorize at this moment', 'text-danger');
                    });
        };



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

        // Callback for when PUT request to import user access token
        function onImportSuccess(response) {
            var msg = response.message || 'Successfully imported access token from profile.';
            self.changeMessage(msg, 'text-success', 3000);
            window.location.reload();
        }

        function onImportError() {
            self.message('Error occurred while importing access token.');
            self.messageClass('text-danger');
        }

        /**
         * Send PUT request to import access token from user profile.
         */
        self.importAuth = function() {
            bootbox.confirm({
                title: 'Import Google Drive Access Token?',
                message: 'Are you sure you want to authorize this project with your Google Drive access token?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return $.osf.putJSON(self.urls().importAuth, {})
                            .done(onImportSuccess)
                            .fail(onImportError);
                    }
                }
            });
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
                    self.changeMessage('Deauthorized Google Drive.', 'text-warning', 3000);
                },
                error: function() {
                    self.changeMessage('Could not deauthorize Google Drive because of an error. Please try again later.',
                        'text-danger');
                }
            });
        }

        /** Pop up a confirmation to deauthorize Dropbox from this node.
         *  Send DELETE request if confirmed.
         */
        self.deauthorize = function() {
            bootbox.confirm({
                title: 'Deauthorize Google Drive?',
                message: 'Are you sure you want to remove this Google Drive authorization?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return sendDeauth();
                    }
                }
            });
        };


        /** Callback for chooseFolder action.
        *   Just changes the ViewModel's self.selected observable to the selected
        *   folder.
        */
        function onPickFolder(evt, item) {
                evt.preventDefault();
                self.selected({name: 'Drive' + item.data.path, path: item.data.path});
                return false; // Prevent event propagation
        }


        /** Calls Google picker API & selects a folder
         * to replace existing folder
         */
        self.changeFolder = function() {

            var setOwner;


            $.getScript('https://apis.google.com/js/api.js?onload=onApiLoad', function () {

                gapi.load('picker', {'callback': onPickerApiLoad });

                function onPickerApiLoad() {

                    var docsView = new google.picker.DocsView().
                        setIncludeFolders(true).
                        setSelectFolderEnabled(true).
                        setOwnedByMe(setOwner);

                    var picker = new google.picker.PickerBuilder().
                        addView(docsView).
//                        addView(google.picker.ViewId.FOLDERS).
                        setOAuthToken(access_token).
                        setDeveloperKey(self.api_key()).
                        enableFeature(google.picker.Feature.MULTISELECT_ENABLED).
                        setCallback(pickerCallback).
                        build();
                    picker.setVisible(true);
                }

                // callback for picker API
                function pickerCallback(data) {
                    var url = 'nothing';
                    if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
                        var doc = data[google.picker.Response.DOCUMENTS][0];
                        var id = doc[google.picker.Document.ID];
                        self.selectedName(doc[google.picker.Document.NAME]);
                        console.log(id);
                        console.log(name);

                        //Get folder & files using drive service
                        $.getJSON(
                            self.urls().get_folders,
                            {
                                'folder-id': id
                            },
                            function (response) {
                                console.log(response);
                                var result = response.result;
                                if (result != null) {
                                    var Items = []
                                    for (var child = 0; child < result.length; child++) {
                                        Items.push({
                                            name: result[child].title,
                                            id: result[child].id,
                                            kind: "item"
                                        })
                                    }
                                }
                                console.log(Items);


                                var files = [
                                    {
                                        id: id,
                                        name: self.selectedName(),
                                        kind: 'folder',
                                        children: Items
                                    }
                                ]

                                $(self.folderPicker).folderpicker({
                                    onPickFolder : onPickFolder,
                                    filesData : files,
                                    ajaxOptions: {
                                        error: function(xhr, textStatus, error) {
                                            self.loading(false);
                                            self.changeMessage('Could not connect to Dropbox at this time. ' +
                                                                'Please try again later.', 'text-warning');
                                            Raven.captureMessage('Could not GET get Dropbox contents.', {
                                                textStatus: textStatus,
                                                error: error
                                            });
                                        }
                                    },
                                    folderPickerOnload: function() {
                                    // TODO
                }
                                });
                                // Treebeard options
                                var options = {
                                    divID: "myGdriveGrid",
                                    filesData: files,     // Array variable to be passed in
                                    rowHeight: 35,
                                    paginate: false,
                                    showPaginate: false,
                                    uploads: false,
                                    columnTitles: function () {
                                        return [
                                            {
                                                title: "ID",
                                                width: "10%",
                                                sortType: "text",
                                                sort: false
                                            },
                                            {
                                                title: "Name",
                                                width: "60%",
                                                sortType: "text",
                                                sort: true
                                            },
                                            {
                                                title: "Kind",
                                                width: "15%",
                                                sortType: "text",
                                                sort: false
                                            }
                                        ]
                                    },
                                    resolveRows: function (item) {
                                        return [
                                            {
                                                data: "id",
                                                filter: false
                                            },
                                            {
                                                data: "name",
                                                filter: true,
                                                folderIcons: true
                                            },
                                            {
                                                data: "kind",
                                                filter: false
                                            }
                                        ]
                                    },
                                    allowMove: false
                                }

                            }
                        );
                    }


                }
            });
        }


        self.showFolders = ko.observable(true);


    };

    function GdriveNodeConfig(selector, url, folderPicker) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url, selector, folderPicker);
        $.osf.applyBindings(self.viewModel, selector);
    }

    module.exports= GdriveNodeConfig;
