
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
var $osf = require('osfHelpers');

ko.punches.enableAll();
/**
    * Knockout view model for the Google Drive node settings widget.
    */
    var ViewModel = function(url, selector, folderPicker) {
        var self = this;
        self.url = url;
        self.nodeHasAuth = ko.observable(false);
        self.userHasAuth = ko.observable(false);
        // whether current user is authorizer of the addon
        self.userIsOwner = ko.observable(false);

        //Api key required for Google picker
        self.access_token = ko.observable();

        self.owner = ko.observable();
        self.ownerName = ko.observable();
        self.urls = ko.observable();
        self.folder = ko.observable({name: null, path: null});
        self.loadedFolders = ko.observable(false);
        self.loading = ko.observable(false);

        //Folderpicker specific
        self.folderPicker =  folderPicker;
        self.selected = ko.observable(null);
        self.selectedName = ko.observable("No folder selected yet !");
        self.showFileTypes = ko.observable(false);
        var setOwner;

        self.loadedSettings = ko.observable(false);
        self.selectedFileTypeOption = ko.observable('');

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        // Get data from the config GET endpoint
        function onFetchSuccess(response) {
            // Update view model
            self.nodeHasAuth(response.result.nodeHasAuth);
            self.userHasAuth(response.result.userHasAuth);
            self.userIsOwner(response.result.userIsOwner);
            self.urls(response.result.urls);
            self.ownerName(response.result.ownerName);
            self.owner(response.result.urls.owner);
            self.access_token (response.result.access_token);
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
                self.selected({name: 'Google Drive' + item.data.path.path, path: item.data.path, id: item.data.id});
                self.selectedName(self.selected().name);
                return false; // Prevent event propagation
        }


        /** Calling Google Drive API & arranging data as
         * required for treebeard Hgrid
         */

        self.changeFolder = function() {
            //Get folder & files using drive service
//            $.getJSON(
//                self.urls().get_folders,
//                {
//                    'folder-id': 'root'
//                },
//                function (response) {
//                    console.log(response);
//                    var result = response.result; //all Folders
//                    if (result != null) {
//                        var roots = []
//                        var path='';
//                        for (var f = 0; f < result.length; f++) {
//
//                            if(result[f].parents.length>0 && result[f].parents[0].isRoot == false) //Non root folders
//                            {
//                                var g = 0;
//                                // Finding parent of f
//                                for(g=0; g<result.length;g++)
//                                {
//                                    if (result[f].parents[0].id == result[g].id) // parent found
//                                    {
//                                        //Setup f
//                                        result[f].name = result[f].title;
//                                        result[f].kind = 'item';
//
//
//                                        //setup parent
//                                        result[g].name = result[g].title;
//                                        result[g].kind = 'folder';
//
//
//                                        // Adding f as a child to parent g
//                                        if(result[g].children == null)
//                                            result[g].children = [result[f]];
//                                        else
//                                            result[g].children.push(result[f]);
//
//                                        break;
//                                    }
//                                }
//                            }
//                        }
//                    }
//
//                    // All folders should have subfolders by now
//
//                    function assignPath(folder){
//                        folder.path = folder.path + '/' + folder.name;
//                        if(folder.children != null)
//                        {
//                            for (var c = 0; c < folder.children.length; c++) {
//                                folder.children[c].path = folder.path;
//                                folder.children[c] = assignPath(folder.children[c]);
//
//                            }
//                        }
//
//                        return folder;
//                    }
//
//
//                    // Adding to treebeard Hgrid
//                    for (var f = 0; f < result.length; f++) {
//                        if(result[f].parents.length > 0 && result[f].parents[0].isRoot == true) // check for root folders
//                        {
//
//                            result[f].name = result[f].title;
//                            if(result[f].children != null)
//                                result[f].kind = 'folder';
//                            else
//                                result[f].kind = 'item';
//                            result[f].path = '/';
//                            result[f]=assignPath(result[f]);
//                            roots.push(result[f]);
//                        }
//                    }
//                    console.log(result);
//                    var files = [
//                        {
//                            id: 'root',
//                            name:'Google Drive',
//                            kind: 'folder',
//                            children: roots
//                        }
//                    ]



                    $(self.folderPicker).folderpicker({
                        onPickFolder: onPickFolder,
                        filesData: self.urls().get_folders,
                        // Lazy-load each folder's contents
                        // Each row stores its url for fetching the folders it contains

                        resolveLazyloadUrl : function(item){
                             return item.data.urls.get_folders;
                        },
                        ajaxOptions: {
                            error: function (xhr, textStatus, error) {
                                self.loading(false);
                                self.changeMessage('Could not connect to Google Drive at this time. ' +
                                    'Please try again later.', 'text-warning');
                                Raven.captureMessage('Could not GET get Google Drive contents.', {
                                    textStatus: textStatus,
                                    error: error
                                });
                            }
                        },
                        folderPickerOnload: function () {
                        }
                    });
//
//                }
//            );

//            $.getScript('https://apis.google.com/js/api.js?onload=onApiLoad', function () {
//
//                gapi.load('picker', {'callback': onPickerApiLoad });
//
//                function onPickerApiLoad() {
//
//
//                    var docsView = new google.picker.DocsView().
//                        setIncludeFolders(true).
//                        setSelectFolderEnabled(true).
//                        setOwnedByMe(setOwner);
//
//                    var picker = new google.picker.PickerBuilder().
//                        addView(docsView).
////                        addView(google.picker.ViewId.FOLDERS).
//                        setOAuthToken(self.access_token()).
////                        setDeveloperKey(self.api_key()).
//                        enableFeature(google.picker.Feature.MULTISELECT_ENABLED).
//                        setCallback(pickerCallback).
//                        build();
//                    picker.setVisible(true);
//                }
//
//                // callback for picker API
//                function pickerCallback(data) {
//                    var url = 'nothing';
//                    if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
//                        var doc = data[google.picker.Response.DOCUMENTS][0];
//                        var id = doc[google.picker.Document.ID];
//                        self.selectedName(doc[google.picker.Document.NAME]);
//
//                        //Get folder & files using drive service
//                        $.getJSON(
//                            self.urls().get_folders,
//                            {
//                                'folder-id': id
//                            },
//                            function (response) {
//                                console.log(response);
//                                var result = response.result;
//                                if (result != null) {
//                                    var Items = []
//                                    for (var child = 0; child < result.length; child++) {
//                                        Items.push({
//                                            name: result[child].title,
//                                            id: result[child].id,
//                                            kind: "item"
//                                        })
//                                    }
//                                }
//
//                                var files = [
//                                    {
//                                        id: id,
//                                        name: self.selectedName(),
//                                        kind: 'folder',
//                                        children: Items
//                                    }
//                                ]
//
//                                $(self.folderPicker).folderpicker({
//                                    onPickFolder: onPickFolder,
//                                    filesData: files,
//                                    ajaxOptions: {
//                                        error: function (xhr, textStatus, error) {
//                                            self.loading(false);
//                                            self.changeMessage('Could not connect to Google Drive at this time. ' +
//                                                'Please try again later.', 'text-warning');
//                                            Raven.captureMessage('Could not GET get Google Drive contents.', {
//                                                textStatus: textStatus,
//                                                error: error
//                                            });
//                                        }
//                                    },
//                                    folderPickerOnload: function () {
//                                        // TODO
//                                    }
//                                });
//
//                            }
//                        );
//                    }
//
//
//                }
//            });
        }



        self.showFolders = ko.computed(function(){
            return self.nodeHasAuth();
        })

        self.selectedFolderName = ko.computed(function() {
        var userIsOwner = self.userIsOwner();
        var selected = self.selected();
        return (userIsOwner && selected) ? selected.name : '';
        });


        function onSubmitSuccess(response) {
        self.changeMessage('Successfully linked "' + self.selected().name +
            '". Go to the <a href="' +
            self.urls().files + '">Files page</a> to view your files.',
            'text-success', 5000);
        // Update folder in ViewModel
        self.folder(response.result.folder);
        self.urls(response.result.urls);
        }

        function onSubmitError() {
            self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
        }

        /**
            * Send a PUT request to change the linked Dropbox folder.
            */
        self.submitSettings = function() {
            $osf.putJSON(self.urls().config, ko.toJS(self))
                .done(onSubmitSuccess)
                .fail(onSubmitError);
        };


    };

    function GdriveNodeConfig(selector, url, folderPicker) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url, selector, folderPicker);
        $.osf.applyBindings(self.viewModel, selector);
    }

    module.exports= GdriveNodeConfig;
