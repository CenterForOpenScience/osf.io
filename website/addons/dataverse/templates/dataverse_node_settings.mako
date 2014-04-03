<%inherit file="../../project/addon/node_settings.mako" />

<div>
    % if connected:

        % if authorized:
            <div style="padding-bottom: 10px">

                % if len(dataverses) != 0:
                    Dataverse:
                    <select id="dataverseDropDown" class="form-control">
                        % for i, dv in enumerate(dataverses):
                            % if i == dataverse_number:
                                <option value=${i} selected>${dv}</option>
                            % else:
                                <option value=${i}>${dv}</option>
                            % endif
                        % endfor
                    </select>

                    <br>

                    Study:
                    <select id="studyDropDown" class="form-control">
                        <option value="None">---</option>
                        % if len(dataverses) > 0:
                            % for i, hdl in enumerate(studies):
                                % if hdl == study_hdl:
                                    <option value=${hdl} selected>${study_names[i]}</option>
                                % else:
                                    <option value=${hdl}>${study_names[i]}</option>
                                % endif
                            % endfor
                        % endif
                    </select>

                % else:
                    This Dataverse account does not yet have a Dataverse.
                % endif

            </div>

        % endif

        <div>
            % if study_hdl:
                This node is linked to
                <a href=${study_url}>${study}</a> on
                <a href=${dataverse_url}>${dataverse}.</a>
            % elif len(dataverses) != 0:
                This node has not yet been linked to a study.
            % endif
        </div>

        <div style="padding-bottom: 10px">
            Authorized by OSF user
            <a href="${authorized_user_url}" target="_blank">
                ${authorized_user_name}
            </a>
            on behalf of Dataverse user ${authorized_dataverse_user}
        </div>

    % else:
        <div>
            % if user_dataverse_connected:
                <a id="dataverseAuth" class="btn btn-success">Authorize: Link to Dataverse Account</a>
            % elif authorized:
                There was a problem connecting to the Dataverse using your
                credentials. If they have changed, please go to
                <a href="/settings/">user settings</a> and update your account
                information.
            % elif authorized_dataverse_user:
                There was a problem connecting to the Dataverse using the
                credentials for Dataverse user ${authorized_dataverse_user}.
                If they have changed, the Dataverse will not be accessible
                through that account until the information is updated.
            % else:
                In order to access this feature, please go to <a href="/settings/">
                user settings</a> and link your account to a Dataverse account.
            % endif
        </div>

    % endif

    % if authorized_dataverse_user:
        <div style="padding-top: 10px">
            <a id="dataverseDeauth" class="btn btn-danger">Unauthorize</a>
        </div>
    % endif

</div>

<script>

    $("#dataverseDropDown").change(function() {
        var dn = '{"dataverse_number":' + $(this).find(":selected").val() + '}'
        $.ajax({
            url: nodeApiUrl + 'dataverse/set/',
            data: dn,
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
            url: nodeApiUrl + 'dataverse/set/study/',
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
                    'Dataverse authorization from your <a href="/settings/">user settings</a> ' +
                    'page.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'dataverse/unauthorize/',
                            type: 'POST',
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