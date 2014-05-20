<%inherit file="../../project/addon/node_settings.mako" />

<div>
    % if connected:

        <div class="well well-sm">
            Authorized by <a href="${authorized_user_url}">${authorized_user_name}</a>
            on behalf of Dataverse user ${authorized_dataverse_user}
            % if authorized_dataverse_user:
                <a id="dataverseDeauth" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
            % endif
        </div>

        % if authorized:

            % if len(dataverses) != 0:
                <div class="row" style="padding-bottom: 10px">

                    <div class="col-md-6">
                        Dataverse:
                        <select id="dataverseDropDown" class="form-control">
                            <option value="None">---</option>
                            % for i, dv in enumerate(dataverses):
                                <option value=${dataverse_aliases[i]} ${'selected' if dataverse_aliases[i] == dataverse_alias else ''} ${'disabled' if not dv_status[i] else ''}>${dv} ${'(Not Released)' if not dv_status[i] else ''}</option>
                            % endfor
                        </select>
                    </div>

                    <div class="col-md-6">
                        Study:
                        <select id="studyDropDown" class="form-control">
                            <option value="None">---</option>
                            % for i, hdl in enumerate(studies):
                                <option value=${hdl} ${'selected' if hdl == study_hdl else ''}>${study_names[i]}</option>
                            % endfor
                        </select>
                    </div>

                </div>

            % else:
                This Dataverse account does not yet have a Dataverse.
            % endif

        % endif


        % if study_hdl:

            <div style="padding-bottom: 10px">
                This node is linked to
                <a href=${study_url}>${study}</a> on
                <a href=${dataverse_url}>${dataverse}.</a>
            </div>

        % elif len(dataverses) != 0:

            <div>
                This node has not yet been linked to a study.
            </div>

        % endif
    </div>

    % else:
        <div>
            % if user_dataverse_connected:
                <a id="dataverseAuth" class="btn btn-success">Authorize: Link to Dataverse Account</a>
            % elif authorized:
                There was a problem connecting to the Dataverse using your
                credentials. If they have changed, please go to
                <a href="/settings/addons/">user settings</a> and update your account
                information.
            % elif authorized_dataverse_user:
                There was a problem connecting to the Dataverse using the
                credentials for Dataverse user ${authorized_dataverse_user}.
                If they have changed, the Dataverse will not be accessible
                through that account until the information is updated.
            % else:
                In order to access this feature, please go to <a href="/settings/addons/">
                user settings</a> and link your account to a Dataverse account.
            % endif
        </div>

        % if authorized_dataverse_user:
            <div style="padding-top: 10px">
                <a id="dataverseDeauth" class="btn btn-danger">Deauthorize</a>
            </div>
        % endif

    % endif

</div>

<script>

    $("#dataverseDropDown").change(function() {
        var alias = '{"dataverse_alias":"' + $(this).find(":selected").val() + '"}'
        console.log(alias);
        $.ajax({
            url: '${set_dataverse_url}',
            data: alias,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                window.location.reload();
            }
        });
    });

    $("#studyDropDown").change(function() {
        var sn = '{"study_hdl":"' + $(this).find(":selected").val() + '"}'
        $.ajax({
            url: '${set_study_url}',
            data: sn,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                window.location.reload();
            }
        });
    });


    $('#dataverseAuth').on('click', function() {
        $.ajax({
            url: nodeApiUrl + 'dataverse/authorize/',
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                window.location.reload();
            }
        });
    });

    $('#dataverseDeauth').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to unlink this Dataverse account? This will ' +
                    'revoke the ability to view, download, modify, and upload files ' +
                    'to studies on the Dataverse from the OSF. This will not remove your ' +
                    'Dataverse authorization from your <a href="/settings/addons/">user settings</a> ' +
                    'page.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'dataverse/deauthorize/',
                            type: 'DELETE',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            )
        });

</script>

<%def name="submit_btn()">
    % if show_submit:
        ${parent.submit_btn()}
    % endif
</%def>

<%def name="on_submit()">
    % if show_submit:
        ${parent.on_submit()}
    % endif
</%def>