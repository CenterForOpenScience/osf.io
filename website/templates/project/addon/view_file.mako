<%inherit file="../project_base.mako"/>
<%def name="title()">${file_name}</%def>

<<<<<<< HEAD
% if user['can_comment'] or node['has_comments']:
    <%include file="../../include/comment_pane_template.mako"/>
    <%include file="../../include/comment_template.mako"/>
% endif
=======
    <div>
        <h2>
            ${file_name | h}
            % if file_revision:
                <small>&nbsp;${file_revision | h}</small>
            % endif
        </h2>
        <hr />
    </div>
>>>>>>> f06b14bf9b01c7a00a6f36a13eee129f9344998e

<div id="file-container" class="row">

    <div class="col-md-8">
        ${self.file_contents()}
    </div>

    <div class="col-md-4">
        ${self.file_versions()}
    </div>

</div>


<%def name="file_contents()">


    <div id="fileRendered" class="mfr mfr-file">
        % if rendered is not None:
            ${rendered}
        % else:
            <img src="/static/img/loading.gif">
        % endif
    </div>

</%def>

<%def name="file_versions()"></%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % if rendered is None:
        <script type="text/javascript">
            window.contextVars = window.contextVars || {};
            window.contextVars.renderURL = '${render_url}';
        </script>
        <script src=${"/static/public/js/view-file-page.js" | webpack_asset}></script>
    % endif
</%def>
