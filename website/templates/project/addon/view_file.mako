<%inherit file="../../base.mako"/>
<%def name="title()">${file_name}</%def>

<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<%def name="file_contents()"></%def>

    <div id="file-container" class="row">

        <div class="col-md-8">
            ${self.file_contents()}
        </div>

        <div class="col-md-4">
            ${self.file_versions()}
        </div>

</%def>

<%def name="file_contents()">

    <div id="file-container" class="row">

        <section>
            <div class="page-header overflow">
                <h1>${file_name}</h1>
            </div>
        </section>

        <div id="fileRendered" class="mfr mfr-file">
            % if rendered is not None:
                ${rendered}
            % else:
                <img src="/static/img/loading.gif">
            % endif
        </div>

    </div>

</%def>

<%def name="file_versions()"></%def>

<%def name="javascript()">
    % if rendered is None:
        <script type="text/javascript">
            $(document).ready(function() {
                FileRenderer.start('${render_url}', '#fileRendered');
            });
        </script>
    % endif
</%def>
