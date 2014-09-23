<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki (Edit)</%def>

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
        <div class="col-md-3">
            <%include file="wiki/templates/nav.mako" />
            <%include file="wiki/templates/toc.mako" />
        </div>
        <div class="col-md-9">
            <%include file="wiki/templates/status.mako"/>
            <div class="form-group wmd-panel">
                <p><em>Changes will be stored but not published until you click "Save Version."</em></p>
                <div id="wmd-button-bar"></div>
                <div id="editor" class="wmd-input" data-bind="ace: wikiText, value: wikiText">
                    Loading. . .
                </div>
            </div>
            <div class="pull-right">
                <a href="${node['url']}wiki/${pageName}/" class="btn btn-default">Return</a>
                <button id="revert-button" class="btn btn-primary" data-bind="click: revertChanges, enable: changed">Revert to Last Save</button>
                <input type="submit" class="btn btn-success" value="Save Version"
                       data-bind="enable: changed,
                                  click: function() {updateChanged('${node['url']}wiki/${pageName}/edit/')}"
                       onclick=$(window).off('beforeunload')>
            </div>
            <p class="help-block">Preview</p>
            <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
        </div>

    </div><!-- end row -->
</div><!-- end wiki -->

<script src="/static/vendor/bower_components/ace-builds/src/ace.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Converter.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Sanitizer.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Editor.js"></script>

<!-- Necessary for ShareJS communication -->
<script src="http://localhost:7007/channel/bcsocket.js"></script>
<script src="http://localhost:7007/share/share.js"></script>
<script src="http://localhost:7007/share/ace.js"></script>

<script>

    var doc = null;
    var editor;

    // ShareJS supports multiple document backends per server based on key/
    // value stores. It is possible to expose the document name to switch between
    // different documents, like in a wiki.
    var setDoc = function(docName) {

        editor.setReadOnly(true);

        // TODO: No security from users accessing sharejs from JS console
        sharejs.open(docName, "text", 'http://localhost:7007/channel', function(error, newDoc) {

            // If no share data is loaded, retrieve most recent wiki from osf
            // TODO: If we rename a wiki to a deleted wiki, we get old content
            if (newDoc.version === 0) {
                $("#revert-button").click()
            }

            if (doc != null) {
                doc.close();
                doc.detach_ace();
            }

            doc = newDoc;

            if (error) {
                console.error(error);
                return;
            }
            doc.attach_ace(editor);

            editor.setReadOnly(false);
        });
    };

    var langTools = ace.require("ace/ext/language_tools");
    var editor = ace.edit("editor");
    editor.getSession().setMode("ace/mode/markdown");

    setDoc('${node['id']}-${pageName}');

    // Settings
    editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    editor.getSession().setUseWrapMode(true);   // Wraps text
    editor.renderer.setShowGutter(false);       // Hides line number
    editor.setShowPrintMargin(false);           // Hides print margin

</script>

<script>

    $script('/static/addons/wiki/WikiEditor.js', function() {
        WikiEditor('.wiki', '${node['api_url']}wiki/content/${pageName}/')
    });

</script>
