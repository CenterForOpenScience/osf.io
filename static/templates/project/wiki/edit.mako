<%inherit file="base.mako"/>
<%def name="title()">Edit Wiki</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div class="row">
    <div class="span9">
        <form action="${node_url}wiki/${pageName}/edit/" method="POST">
            <div class="wmd-panel">
                <div id="wmd-button-bar"></div>
                <textarea class="wmd-input" id="wmd-input" name="content">${content}</textarea>
                <input type="submit" value="Save">
            </div>
            <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
        </form>
    </div>
    <div class="span3">
        <div style="width:200px; float:right; margin-left:30px;">
            <div mod-meta='{
                    "tpl": "project/wiki/nav.mako",
                    "replace": true
                }'></div>
            <div mod-meta='{
                    "tpl": "project/wiki/history.mako",
                    "replace": true
                }'></div>
        </div>
    </div>
    <script type="text/javascript" src="/static/pagedown/Markdown.Converter.js"></script>
    <script type="text/javascript" src="/static/pagedown/Markdown.Sanitizer.js"></script>
    <script type="text/javascript" src="/static/pagedown/Markdown.Editor.js"></script>
    <script type="text/javascript">
        (function () {
            var converter1 = Markdown.getSanitizingConverter();
            var editor1 = new Markdown.Editor(converter1);
            editor1.run();
        })();
    </script>
</div>
</%def>
