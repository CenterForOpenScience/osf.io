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
        <div class="col-md-9">
            <form action="${node['url']}wiki/${pageName}/edit/" method="POST">
                <div class="form-group wmd-panel">
                    <div id="wmd-button-bar"></div>
                    <div id="editor" data-bind="ace: wikiText, value: wikiText">Loading. . . </div>
                    <!-- use an invisible text area to perform actual form submission -->
                    <textarea id="wmd-input" name="content" data-bind="value: wikiText" style="display: none;"></textarea>
                </div>
                <div class="pull-right">
                    <!-- clicking "Cancel" overrides unsaved changes check -->
                    <a href="${node['url']}wiki/${pageName}/" class="btn btn-default">Cancel</a>
                    <input type="submit" class="btn btn-primary" value="Save"  data-bind="enable: changed" onclick=$(window).off('beforeunload')>
                </div>
                <p class="help-block">Preview</p>
                <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
            </form>
        </div>
        <div class="col-md-3">
            <div>
                <%include file="wiki/templates/nav.mako" />
                <%include file="wiki/templates/history.mako" />
            </div>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->

<%def name="javascript_bottom()">

    <script src="/static/vendor/bower_components/ace-builds/src/ace.js"></script>
    <script src="/static/vendor/pagedown/Markdown.Converter.js"></script>
    <script src="/static/vendor/pagedown/Markdown.Sanitizer.js"></script>
    <script src="/static/vendor/pagedown/Markdown.Editor.js"></script>

    <script>

        var langTools = ace.require("ace/ext/language_tools");
        var editor = ace.edit("editor");
        editor.getSession().setMode("ace/mode/markdown");
        editor.setReadOnly(true);

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
</%def>
