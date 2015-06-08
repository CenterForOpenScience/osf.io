var $ = require('jquery');
var m = require('mithril');

var collaborative = (typeof WebSocket !== 'undefined' && typeof sharejs !== 'undefined');

var ShareJSDoc = function(shareWSUrl, metadata, editor, observables) {
    var self = this;
    self.editor = editor;
    self.activeUsers = observables.activeUsers;

    var ctx = window.contextVars.file;

    // Initialize Ace and configure settings
    self.editor.getSession().setMode('ace/mode/markdown');
    self.editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    self.editor.getSession().setUseWrapMode(true);   // Wraps text
    self.editor.renderer.setShowGutter(false);       // Hides line number
    self.editor.setShowPrintMargin(false);           // Hides print margin
    self.editor.commands.removeCommand('showSettingsMenu');  // Disable settings menu
    self.editor.setReadOnly(true); // Read only until initialized
    self.editor.setOptions({
        enableBasicAutocompletion: false,
        enableSnippets: false,
        enableLiveAutocompletion: false
    });

    self.collaborative = collaborative;
    self.observables = observables;


    // Requirements load order is specific in this case to compensate
    // for older browsers.
    var ReconnectingWebSocket = require('reconnectingWebsocket');
    require('addons/wiki/static/ace.js');

    // Configure connection
    var wsPrefix = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
    var wsUrl = wsPrefix + shareWSUrl;
    var socket = new ReconnectingWebSocket(wsUrl);
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);
    var madeConnection = false;
    var allowRefresh = true;
    var refreshTriggered = false;
    var canEdit = true;

    function whenReady() {
        if (!collaborative) {
            if (typeof WebSocket === 'undefined') {
                self.observables.status('unsupported');
            } else {
                self.observables.status('disconnected');
            }
            return;
        }

        // Create a text document if one does not exist
        if (!doc.type) {
            var x = self.editor.getValue();
            doc.create('text');
            doc.attachAce(self.editor);
            self.editor.setValue(x);
        } else {
            doc.attachAce(self.editor);
        }

        unlockEditor();
        self.observables.status('connected');
        madeConnection = true;

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
                self.activeUsers(Object.keys(data.users).filter(function(key) {
                    return key !== self.observables.userId;
                }).map(function(key) {
                    data.users[key].id = key;
                    return data.users[key];
                }));
                m.redraw();
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
            default:
                onmessage(message);
                break;
        }
    };

    // Update status when reconnecting
    var onclose = socket.onclose;
    socket.onclose = function (event) {
        onclose(event);
        self.observables.status('connecting');
    };

    var onopen = socket.onopen;
    socket.onopen = function(event) {
        onopen(event);
        if (madeConnection) {
            self.observables.status('connected');
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
