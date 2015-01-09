<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki (Edit)</%def>

<div class="wiki">
    <div class="row">
        <div class="col-sm-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
         <div class="col-sm-9">
                 <%include file="wiki/templates/status.mako"/>
            <form action="${urls['web']['edit']}" method="POST">
                <div class="form-group wmd-panel">
                    <div id="wmd-button-bar"></div>
                    <textarea class="form-control wmd-input" rows="25" id="wmd-input" name="content" data-bind="value: wikiText"></textarea>
                </div>
                <div class="pull-right">
                    <!-- clicking "Cancel" overrides unsaved changes check -->
                    % if wiki_created:
                        <a href="${urls['web']['home']}" class="btn btn-default">Cancel</a>
                    % else:
                        <a href="${urls['web']['page']}" class="btn btn-default">Cancel</a>
                    % endif
                    <input type="submit" class="btn btn-primary" value="Save" onclick=$(window).off('beforeunload')>
                </div>
                <p class="help-block">Preview</p>
                <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
            </form>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->


<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script>
    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {urls: {content: '${urls['api']['content']}'}};
</script>
<script src="/static/vendor/pagedown/Markdown.Converter.js"></script>
<script src="/static/vendor/pagedown/Markdown.Sanitizer.js"></script>
<script src="/static/vendor/pagedown/Markdown.Editor.js"></script>
<script src="/static/public/js/wiki-edit-page.js"></script>
</%def>
