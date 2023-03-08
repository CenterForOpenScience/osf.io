<%inherit file="base.mako"/>
<%def name="title()">${_("Import Project")}</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="content()">
    <div>
        <div class="modal-dialog row">
            <div class="col-xs-12">
                <div class="page-header">
                    <h3>
                        ${_("Importing...")}
                    </h3>
                </div>
            </div>
            <div class="col-xs-12" style="text-align: center;">
                <div id="loading"></div>
                <div class="progress-state-node" style="display: none;">${_("Preparing node settings...")}</div>
                <div class="progress-state-folders" style="display: none;">${_("Preparing folders...")}</div>
                <div class="progress-state-files" style="display: none;">${_("Preparing files...")}</div>
                <div class="progress-state-finished" style="display: none;">${_("Finished.")}</div>
            </div>
            <div class="col-xs-12" style="padding-top: 2em; color: #555;">
                <div id="progress-error" class="text-danger" style="display: none;">
                    <div style="font-weight: bold;">
                        ${_("An error occurred during the import process:")}
                    </div>
                    <div class="error-content"></div>
                </div>
            </div>
        </div>
    </div>
</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        const logPrefix = '[metadata]';
        const REFRESH_INTERVAL = 500;
        var errorCount = 0;

        function refresh() {
            $.ajax({
                url: '/api/v1/metadata/packages/tasks/${task_id}',
                type: 'GET',
                dataType: 'json',
                xhrFields:{withCredentials: true},
            }).done(function (data) {
                console.log(logPrefix, 'loaded: ', data);
                errorCount = 0;
                if (data.state === 'SUCCESS') {
                    window.location.href = data.info.node_url;
                }
                if (data.state === 'FAILURE') {
                    $('#loading').empty();
                    $('#loading').append($('<i>').attr('class', 'fa fa-exclamation-triangle fa-3x fa-fw'));
                    if (data.error) {
                        $('#progress-error .error-content').text(data.error);
                        $('#progress-error').show();
                    }
                    return;
                }
                if (data.state === 'provisioning node') {
                    $('.progress-state-node').show();
                    $('.progress-state-folders').hide();
                    $('.progress-state-files').hide();
                    $('.progress-state-finished').hide();
                } else if (data.state === 'preparing folders') {
                    $('.progress-state-node').hide();
                    $('.progress-state-folders').show();
                    $('.progress-state-files').hide();
                    $('.progress-state-finished').hide();
                } else if (data.state === 'preparing files') {
                    $('.progress-state-node').hide();
                    $('.progress-state-folders').hide();
                    $('.progress-state-files').show();
                    $('.progress-state-finished').hide();
                } else if (data.state === 'finished') {
                    $('.progress-state-node').hide();
                    $('.progress-state-folders').hide();
                    $('.progress-state-files').hide();
                    $('.progress-state-finished').show();
                }
                $('#progress-debug').text(JSON.stringify(data));
                setTimeout(refresh, REFRESH_INTERVAL);
            }).fail(function(xhr, status, error) {
                console.error(logPrefix, error);
                errorCount ++;
                setTimeout(refresh, REFRESH_INTERVAL * errorCount);
            });
        }

        $(document).ready(function() {
            $('#loading').append($('<i>').attr('class', 'fa fa-spinner fa-pulse fa-3x fa-fw'));
            setTimeout(refresh, REFRESH_INTERVAL);
        });
    </script>
</%def>
