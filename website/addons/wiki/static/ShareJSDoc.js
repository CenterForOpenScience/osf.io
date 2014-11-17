var activeUsers = [];

var ShareJSDoc = function(viewModel, url, registration) {

    // Initialize Ace and configure settings
    var editor = ace.edit("editor");
    editor.getSession().setMode("ace/mode/markdown");
    editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    editor.getSession().setUseWrapMode(true);   // Wraps text
    editor.renderer.setShowGutter(false);       // Hides line number
    editor.setShowPrintMargin(false);           // Hides print margin
    editor.setReadOnly(true); // Read only until initialized

    var socket = new WebSocket('ws://localhost:7007');
    var sjs = new sharejs.Connection(socket);
    var doc = sjs.get('docs', registration.docId);

    // Handle our custom messages separately
    var som = socket.onmessage;
    socket.onmessage = function (message) {
        var data = JSON.parse(message.data);
        if (data.type === 'meta') {
            activeUsers = [];
            for (var user in data.users) {
                var userMeta = data.users[user];
                userMeta.id = user;
                activeUsers.push(userMeta);
            }
            //            activeUsers = data.users;
            viewModel.activeUsers(activeUsers);
            console.log('Active users', activeUsers);
        } else {
            som(message);
        }
    };

    // This will be called on both connect and reconnect
    doc.on('subscribe', function () {

        // Send user metadata
        socket.send(JSON.stringify(registration));

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

    window.editor = editor;
    window.doc = doc;

};