<%inherit file="../project_base.mako"/>
<%def name="title()">${file_name}</%def>

<div id="file-container" class="row">

    <div class="col-md-8">
        ${self.file_contents()}
    </div>

    <div class="col-md-4">
        ${self.file_versions()}
    </div>

</div>


<%def name="file_contents()">

    <section>
        <div class="page-header overflow">
            <h2>
                ${file_name | h}
                % if file_revision:
                    <small>&nbsp;${file_revision | h}</small>
                % endif
            </h2>
        </div>
    </section>

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
        <script src="/static/public/js/view-file-page.js"></script>
    % endif
</%def>
