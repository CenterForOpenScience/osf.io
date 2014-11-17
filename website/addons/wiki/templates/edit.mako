<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki (Edit)</%def>

<style type="text/css" media="screen">
    #editor {
        position: relative;
        height: 300px;
        border: solid;
        border-width: 1px;
    }
</style>

<div class="wiki">
    <div class="row">
        <div class="col-sm-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
        <div class="col-sm-9">
            <%include file="wiki/templates/status.mako"/>
            <div class="form-group wmd-panel">
                <p><em>Changes will be stored but not published until you click "Save Version."</em></p>
                <div id="wmd-button-bar"></div>
                <div id="editor" class="wmd-input"
                     data-bind="ace: wikiText">Loading. . .</div>
            </div>
            <div class="pull-right">
                <!-- clicking "Cancel" overrides unsaved changes check -->
                % if wiki_created:
                    <a href="${urls['web']['home']}" class="btn btn-default">Return</a>
                % else:
                    <a href="${urls['web']['page']}" class="btn btn-default">Return</a>
                % endif
                <button id="revert-button" class="btn btn-primary"
                        data-bind="click: revertChanges, enable: changed">Revert to Last Save</button>
                <input type="submit" class="btn btn-success" value="Save Version"
                       data-bind="enable: changed,
                                  click: function() {updateChanged('${urls['web']['edit']}')}"
                       onclick=$(window).off('beforeunload')>
            </div>
            <p class="help-block">Preview</p>
            <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->

<script src="/static/vendor/bower_components/ace-builds/src-noconflict/ace.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Converter.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Sanitizer.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Editor.js"></script>

<!-- Necessary for ShareJS communication -->
<script src="http://localhost:7007/text.js"></script>
<script src="http://localhost:7007/share.uncompressed.js"></script>
<script src="/static/addons/wiki/ace.js"></script>

<script>

    var url = '${urls['api']['content']}';

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
    var doc = sjs.get('docs', '${share_uuid}');

    // Handle our custom messages separately
    var som = socket.onmessage;
    socket.onmessage = function(message) {
        var data = JSON.parse(message.data);
        if (data.type === 'meta') {
            var userList = "";
            for (var key in data.users) {
                userList += "|" + data.users[key].name;
            }
            console.log('got message', userList);
        } else {
            som(message);
        }
    };

    // This will be called on both connect and reconnect
    doc.on('subscribe', function() {

        // Send user metadata
        socket.send(JSON.stringify({
            registration: true,
            docId: '${share_uuid}',
            userId: '${user_id}',
            userName: '${user_full_name}',
            userUrl: '${user_url}'
        }));

    });

    // This will be called when we have a live copy of the server's data.
    doc.whenReady(function() {

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

    $script('/static/addons/wiki/WikiEditor.js', function() {
        WikiEditor('.wiki', url)
    });

</script>
