var $ = require('jquery');

var WikiEditor = require('./WikiEditor.js');
var LanguageTools = ace.require('ace/ext/language_tools');

var activeUsers = [];
var collaborative = (typeof WebSocket !== 'undefined' && typeof sharejs !== 'undefined');

var ShareJSDoc = function(url, metadata, viewText, editor) {
    var self = this;
    self.editor = editor;
    var wikiEditor = new WikiEditor(url, viewText, self.editor);
    self.wikiEditor = wikiEditor;

    var viewModel = wikiEditor.viewModel;
    var ctx = window.contextVars.wiki;
    var deleteModal = $('#deleteModal');
    var renameModal = $('#renameModal');
    var permissionsModal = $('#permissionsModal');

    // Initialize Ace and configure settings
    self.editor.getSession().setMode('ace/mode/markdown');
    self.editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    self.editor.getSession().setUseWrapMode(true);   // Wraps text
    self.editor.renderer.setShowGutter(false);       // Hides line number
    self.editor.setShowPrintMargin(false);           // Hides print margin
    self.editor.commands.removeCommand('showSettingsMenu');  // Disable settings menu
    self.editor.setReadOnly(true); // Read only until initialized
    self.editor.setOptions({
        enableBasicAutocompletion: [LanguageTools.snippetCompleter],
        enableSnippets: true,
        enableLiveAutocompletion: true
    });

    if (!collaborative) {
        // Populate editor with most recent draft
        viewModel.fetchData().done(function(response) {
            self.editor.setValue(response.wiki_draft, -1);
            self.editor.setReadOnly(false);
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
    var wsUrl = wsPrefix + ctx.urls.sharejs;
    var socket = new ReconnectingWebSocket(wsUrl);
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);
    var madeConnection = false;
    var allowRefresh = true;
    var refreshTriggered = false;
    var canEdit = true;

    function whenReady() {

        // Create a text document if one does not exist
        if (!doc.type) {
            doc.create('text');
        }

        viewModel.fetchData().done(function(response) {
            doc.attachAce(self.editor);
            if (viewModel.wikisDiffer(viewModel.currentText(), response.wiki_draft)) {
                viewModel.currentText(response.wiki_draft);
            }
            unlockEditor();
            viewModel.status('connected');
            madeConnection = true;
        });

    }

    function unlockEditor() {
        self.editor.gotoLine(0,0);
        var undoManager = self.editor.getSession().getUndoManager();
        undoManager.reset();
        self.editor.getSession().setUndoManager(undoManager);
        self.editor.setReadOnly(false);
    }

    // Send user metadata
    function register() {
        socket.send(JSON.stringify(metadata));
    }

    function refreshMaybe() {
        if (allowRefresh && refreshTriggered) {
            if (canEdit) {
                window.location.reload();
            } else {
                window.location.replace(ctx.urls.page);
            }
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
                self.editor.setReadOnly(true);
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
                canEdit = data.contributors.indexOf(metadata.userId) > -1;
                refreshTriggered = true;
                refreshMaybe();
                break;
            case 'redirect':
                self.editor.setReadOnly(true);
                renameModal.modal({
                    backdrop: 'static',
                    keyboard: false
                });
                setTimeout(function() {
                    window.location.replace(data.redirect);
                }, 3000);
                break;
            case 'delete':
                if (ctx.triggeredDelete) {
                    break;
                }
                self.editor.setReadOnly(true);
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