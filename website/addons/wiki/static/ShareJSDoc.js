var activeUsers = [];

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

    // Configure connection
    var wsUrl = 'ws://' + metadata.sharejsHost + ':' + metadata.sharejsPort;
    var socket = new ReconnectingWebSocket(wsUrl);
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);

    function whenReady() {

        // Create a text document if one does not exist
        if (!doc.type) {
            doc.create('text');
            viewModel.fetchData(function(response) {
                doc.attachAce(editor);
                editor.setValue(response.wiki_content, -1);
                editor.setReadOnly(false);
            });
        } else {
            doc.attachAce(editor);
            editor.gotoLine(0,0);
            editor.setReadOnly(false);
        }

    }

    // Send user metadata
    function register() {
        socket.send(JSON.stringify(metadata));
    }

    // Inform client of new published version
    $('#wiki-form').submit(function() {
        socket.send(JSON.stringify({
            publish: true,
            docId: metadata.docId,
            content: viewModel.currentText()
        }));
    });

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
        } else if (data.type === 'updatePublished') {
            console.log('content', data.content);
            viewModel.publishedText(data.content);
        } else if (data.type === 'lock') {
            editor.setReadOnly(true);
            $('#refresh-modal').modal({
                backdrop: 'static',
                keyboard: false
            });
        } else if (data.type === 'unlock') {
            // TODO: Wait a certain number of seconds so they can read it?
            location.reload();
        } else {
            onmessage(message);
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