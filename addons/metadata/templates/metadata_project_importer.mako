<%inherit file="base.mako"/>
<%def name="title()">${_("Import Project")}</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="content()">
    <div class="modal-dialog row">
        <div class="col-xs-12">
            <div class="page-header">
                <h3>${_("Import Project")}</h3>
            </div>
        </div>
        <div class="col-xs-12">
            ${_("Source URL:")}
            <div style="font-weight: bold;">
                ${url}
            </div>
        </div>
        <div class="col-xs-12" style="padding-top: 2em;">
            ${_("Project Title")}
            <input id='title' placeholder='${_("Enter the title of the imported project")}' type="text" class="form-control" value="${default_title}">
        </div>
        <div class="col-xs-12" style="padding-top: 1em;">
            <div class="pull-right">
                <button id="create-project" class="btn btn-success btn-success-high-contrast f-w-xl">
                    ${_("Create")}
                </button>
            </div>
        </div>
    </div>
</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        const logPrefix = '[metadata]';

        $(document).ready(function() {
            $('#create-project').on(
                'click',
                function() {
                    const settings = {
                        url: '${url}',
                        title: $('#title').val(),
                    };
                    $.ajax({
                        url: '/api/v1/metadata/packages/projects/',
                        type: 'PUT',
                        contentType: 'application/json',
                        data: JSON.stringify(settings),
                        dataType: 'json',
                        xhrFields:{withCredentials: true},
                    }).done(function (data) {
                        console.log(logPrefix, 'loaded: ', data);
                        window.location.href = data.progress_url;
                    }).fail(function(xhr, status, error) {
                        console.error(logPrefix, error);
                    });
                }
            );
        });
    </script>
</%def>
