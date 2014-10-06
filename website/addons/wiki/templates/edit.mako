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
                <div id="editor" class="wmd-input"
                     data-bind="ace: wikiText">Loading. . .</div>
            </div>
            <div class="pull-right">
                <!-- clicking "Cancel" overrides unsaved changes check -->
                % if wiki_created:
                    <a href="${node['url']}wiki/home/" class="btn btn-default">Return</a>
                % else:
                    <a href="${node['url']}wiki/${pageName}/" class="btn btn-default">Return</a>
                % endif
                <button id="revert-button" class="btn btn-primary"
                        data-bind="click: revertChanges, enable: changed">Revert to Last Save</button>
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

    var url = '${node['api_url']}wiki/${pageName}/content/';

    var setDoc = function(docName) {

        sharejs.open(docName, "text", 'http://localhost:7007/channel', function(error, newDoc) {

            if (doc != null) {
                doc.close();
                doc.detach_ace();
            }

            doc = newDoc;

            if (error) {
                console.error(error);
                return;
            }

            // Initializes editor
            doc.attach_ace(editor);
            editor.setReadOnly(false);

            // If no share data is loaded, fetch most recent wiki from osf
            // TODO: Only works sometimes, likely based on order of execution
            if (newDoc.version === 0) {
                $.ajax({
                    type: 'GET',
                    url: url,
                    dataType: 'json',
                    success: function (response) {
                        editor.setValue(response.wiki_content);
                    },
                    error: function (xhr, textStatus, error) {
                        console.error(textStatus);
                        console.error(error);
                        bootbox.alert('Could not get wiki content.');
                    }
                });
            }
        });
    };

    var doc = null;
    var langTools = ace.require("ace/ext/language_tools");
    var editor = ace.edit("editor");
    editor.getSession().setMode("ace/mode/markdown");
    editor.setReadOnly(true); // Read only until initialized

    setDoc('${share_uuid}');

    // Settings
    editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
    editor.getSession().setUseWrapMode(true);   // Wraps text
    editor.renderer.setShowGutter(false);       // Hides line number
    editor.setShowPrintMargin(false);           // Hides print margin

    $script('/static/addons/wiki/WikiEditor.js', function() {
        WikiEditor('.wiki', url)
    });

</script>
