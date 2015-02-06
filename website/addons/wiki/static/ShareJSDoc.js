var ReconnectingWebSocket = require('reconnectingWebsocket');
var LanguageTools = ace.require('ace/ext/language_tools');
require('addons/wiki/static/ace.js');

var activeUsers = [];
var collaborative = (typeof WebSocket !== 'undefined' && typeof sharejs !== 'undefined');

var ShareJSDoc = function(viewModel, url, metadata) {
    // Initialize Ace and configure settings
    var editor = ace.edit("editor");
    editor.getSession().setMode("ace/mode/markdown");
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
        viewModel.fetchData(function(response) {
            editor.setValue(response.wiki_draft, -1);
            editor.setReadOnly(false);
            if (typeof WebSocket === 'undefined') {
                viewModel.status('noWebSocket');
            } else {
                viewModel.status('disconnected');
            }
        });
        return;
    }



    // Configure connection
    var wsPrefix = (window.location.protocol == 'https:') ? 'wss://' : 'ws://';
    var wsUrl = wsPrefix + window.contextVars.wiki.urls.sharejs;
    var socket = new ReconnectingWebSocket(wsUrl);
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);
    var madeConnection = false;

    function whenReady() {

        // Create a text document if one does not exist
        if (!doc.type) {
            doc.create('text');
        }

        viewModel.fetchData(function(response) {
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

    // Handle our custom messages separately
    var onmessage = socket.onmessage;
    socket.onmessage = function (message) {
        var data = JSON.parse(message.data);
        // Meta type is not built into sharejs; we pass it manually
        if (data.type === 'meta') {
            // Convert users object into knockout array
            activeUsers = [];
            for (var user in data.users) {
                var userMeta = data.users[user];
                userMeta.id = user;
                activeUsers.push(userMeta);
            }
            viewModel.activeUsers(activeUsers);
        } else if (data.type === 'lock') {
            editor.setReadOnly(true);
            $('#permissions-modal').modal({
                backdrop: 'static',
                keyboard: false
            });
        } else if (data.type === 'unlock') {
            // TODO: Wait a certain number of seconds so they can read it?
            window.location.reload();
        } else if (data.type === 'redirect') {
            editor.setReadOnly(true);
            $('#rename-modal').modal({
                backdrop: 'static',
                keyboard: false
            });
            setTimeout(function() {
                window.location.replace(data.redirect);
            }, 3000);
        } else if (data.type === 'delete') {
            editor.setReadOnly(true);
            var deleteModal = $('#delete-modal');
            deleteModal.on('hide.bs.modal', function() {
                window.location.replace(data.redirect);
            });
            deleteModal.modal();
        } else {
            onmessage(message);
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