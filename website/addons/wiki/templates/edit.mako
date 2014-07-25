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
                <div class="pull-right">
                    <!-- clicking "Cancel" overrides unsaved changes check -->
                    <a href="${node['url']}wiki/${pageName}/" class="btn btn-default" onclick=$(window).off('beforeunload')>Cancel</a>
                    <input type="submit" class="btn btn-primary" value="Save">
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

    <script src="/static/vendor/pagedown/Markdown.Converter.js"></script>
    <script src="/static/vendor/pagedown/Markdown.Sanitizer.js"></script>
    <script src="/static/vendor/pagedown/Markdown.Editor.js"></script>

    <script>
        $(window).on('beforeunload', function() {
          return 'There are unsaved changes to your wiki.';
        });
    </script>

    <script>
        var converter1 = Markdown.getSanitizingConverter();
        var editor1 = new Markdown.Editor(converter1);
        editor1.run();
    </script>
</%def>
