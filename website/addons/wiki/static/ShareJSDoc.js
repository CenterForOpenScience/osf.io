var $ = require('jquery');
require('bootstrap');

var WikiEditor = require('./WikiEditor.js');
var LanguageTools = ace.require('ace/ext/language_tools');

var activeUsers = [];
var collaborative = (typeof WebSocket !== 'undefined' && typeof sharejs !== 'undefined');

var ShareJSDoc = function(selector, url, metadata) {
    var wikiEditor = new WikiEditor(selector, url);
    var viewModel = wikiEditor.viewModel;
    var deleteModal = $('#deleteModal');
    var renameModal = $('#renameModal');
    var permissionsModal = $('#permissionsModal');

    // Initialize Ace and configure settings
    var editor = ace.edit('editor');
    editor.getSession().setMode('ace/mode/markdown');
    editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    editor.getSession().setUseWrapMode(true);   // Wraps text
    editor.renderer.setShowGutter(false);       // Hides line number
    editor.setShowPrintMargin(false);           // Hides print margin
    editor.commands.removeCommand('showSettingsMenu');  // Disable settings menu
    editor.setReadOnly(true); // Read only until initialized
    editor.setOptions({
        enableBasicAutocompletion: [LanguageTools.snippetCompleter],
        enableSnippets: true,
        enableLiveAutocompletion: true
    });

    if (!collaborative) {
        // Populate editor with most recent draft
        viewModel.fetchData().done(function(response) {
            editor.setValue(response.wiki_draft, -1);
            editor.setReadOnly(false);
            if (typeof WebSocket === 'undefined') {
                viewModel.status('unsupported');
            } else {
                viewModel.status('disconnected');
            }
        });
        return;
    }

    // Requirements load order is specific in this case to compensate
    // for older browsers.
    var ReconnectingWebSocket = require('reconnectingWebsocket');
    require('addons/wiki/static/ace.js');

    // Configure connection
    var wsPrefix = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
    var wsUrl = wsPrefix + window.contextVars.wiki.urls.sharejs;
    var socket = new ReconnectingWebSocket(wsUrl);
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);
    var madeConnection = false;
    var allowRefresh = true;
    var refreshTriggered = false;

    function whenReady() {

        // Create a text document if one does not exist
        if (!doc.type) {
            doc.create('text');
        }

        viewModel.fetchData().done(function(response) {
            doc.attachAce(editor);
            if (viewModel.wikisDiffer(viewModel.currentText(), response.wiki_draft)) {
                viewModel.currentText(response.wiki_draft);
            }
            unlockEditor();
            viewModel.status('connected');
            madeConnection = true;
        });

    }

    function unlockEditor() {
        editor.gotoLine(0,0);
        var undoManager = editor.getSession().getUndoManager();
        undoManager.reset();
        editor.getSession().setUndoManager(undoManager);
        editor.setReadOnly(false);
    }

    // Send user metadata
    function register() {
        socket.send(JSON.stringify(metadata));
    }

    function refreshMaybe() {
        if (allowRefresh && refreshTriggered) {
            window.location.reload();
        }
    }

    // Handle our custom messages separately
    var onmessage = socket.onmessage;
    socket.onmessage = function (message) {
        var data = JSON.parse(message.data);
        // Meta type is not built into sharejs; we pass it manually
        switch (data.type) {
            case 'meta':
                // Convert users object into knockout array
                activeUsers = [];
                for (var user in data.users) {
                    var userMeta = data.users[user];
                    userMeta.id = user;
                    activeUsers.push(userMeta);
                }
                viewModel.activeUsers(activeUsers);
                break;
            case 'lock':
                allowRefresh = false;
                editor.setReadOnly(true);
                permissionsModal.modal({
                    backdrop: 'static',
                    keyboard: false
                });
                setTimeout(function() {
                    allowRefresh = true;
                    refreshMaybe();
                }, 3000);
                break;
            case 'unlock':
                refreshTriggered = true;
                refreshMaybe();
                break;
            case 'redirect':
                editor.setReadOnly(true);
                renameModal.modal({
                    backdrop: 'static',
                    keyboard: false
                });
                setTimeout(function() {
                    window.location.replace(data.redirect);
                }, 3000);
                break;
            case 'delete':
                editor.setReadOnly(true);
                deleteModal.on('hide.bs.modal', function() {
                    window.location.replace(data.redirect);
                });
                deleteModal.modal();
                break;
            default:
                onmessage(message);
                break;
        }
    };

    // Update status when reconnecting
    var onclose = socket.onclose;
    socket.onclose = function (event) {
        onclose(event);
        viewModel.status('connecting');
    };

    var onopen = socket.onopen;
    socket.onopen = function(event) {
        onopen(event);
        if (madeConnection) {
            viewModel.status('connected');
        }
    };

    // This will be called on both connect and reconnect
    doc.on('subscribe', register);

    // This will be called when we have a live copy of the server's data.
    doc.whenReady(whenReady);

    // Subscribe to changes
    doc.subscribe();
};

module.exports = ShareJSDoc;