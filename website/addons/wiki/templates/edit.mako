<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki (Edit)</%def>

<div class="wiki">
    <div class="row">
        <div class="col-md-9">
            <form action="${node['url']}wiki/${pageName}/edit/" method="POST">
                <div class="form-group wmd-panel">
                    <div id="wmd-button-bar"></div>
                    <textarea class="form-control wmd-input" rows="25" id="wmd-input" name="content">${wiki_content}</textarea>
                </div>
                <input type="submit" class="btn btn-primary pull-right" value="Save">
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
    <script>
        $script('/static/vendor/pagedown/Markdown.Converter.js','markdown-converter');
        $script('/static/vendor/pagedown/Markdown.Sanitizer.js','markdown-sanitizer');
        $script('/static/vendor/pagedown/Markdown.Editor.js','markdown-editor');
        $script.ready(['markdown-converter'], function(){
            $script.ready(['markdown-sanitizer'], function() {
                $script.ready(['markdown-editor'], function() {
                    var converter1 = Markdown.getSanitizingConverter();
                    var editor1 = new Markdown.Editor(converter1);
                    editor1.run();
                });
            });
        });
     </script>
</%def>
