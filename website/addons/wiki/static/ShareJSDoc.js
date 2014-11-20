var activeUsers = [];

var ShareJSDoc = function(viewModel, url, metadata) {

    // Initialize Ace and configure settings
    var editor = ace.edit("editor");
    editor.getSession().setMode("ace/mode/markdown");
    editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    editor.getSession().setUseWrapMode(true);   // Wraps text
    editor.renderer.setShowGutter(false);       // Hides line number
    editor.setShowPrintMargin(false);           // Hides print margin
    editor.setReadOnly(true); // Read only until initialized

    var socket = new ReconnectingWebSocket('ws://localhost:7007');
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', metadata.docId);

    sjs.on('disconnected', function() {
        // TODO: Inform user of disconnect
        console.log('disconnected');
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
        } else {
            onmessage(message);
        }
    };

    // This will be called on both connect and reconnect
    doc.on('subscribe', function () {

        // Send user metadata
        socket.send(JSON.stringify(metadata));

    });

    // This will be called when we have a live copy of the server's data.
    doc.whenReady(function () {

        // Create a text document if one does not exist
        if (!doc.type) {
            doc.create('text');
            $.ajax({
                type: 'GET',
                url: url,
                dataType: 'json',
                success: function (response) {
                    doc.attachAce(editor);
                    editor.setValue(response.wiki_content);
                    editor.setReadOnly(false);
                },
                error: function (xhr, textStatus, error) {
                    console.error(textStatus);
                    console.error(error);
                    bootbox.alert('Could not get wiki content.');
                }
            });
        } else {
            doc.attachAce(editor);
            editor.setReadOnly(false);
        }

    });

    // Subscribe to changes
    doc.subscribe();

    // TODO: Debug variables. Remove before going to production!
    window.sjs = sjs;
    window.doc = doc;
    window.editor = editor;
    window.socket = socket;

};