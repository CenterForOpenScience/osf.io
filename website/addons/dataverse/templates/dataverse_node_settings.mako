<%inherit file="project/addon/node_settings.mako" />

<div>
    % if connected:

        % if authorized:
            <div style="padding-bottom: 10px">
                <select id="dataverseDropDown" >
                    % for i, dv in enumerate(dataverses):
                        % if i == int(dataverse_number):
                            <option value=${i} selected>${dv}</option>
                        % else:
                            <option value=${i}>${dv}</option>
                        % endif
                    % endfor
                </select>

                <select id="studyDropDown">

                    <option value="None">---</option>

                    % if len(dataverses) > 0:
                        % for i, s in enumerate(studies):
                            % if s == study_hdl:
                                <option value=${s} selected>${study_names[i]}</option>
                            % else:
                                <option value=${s}>${study_names[i]}</option>
                            % endif
                        % endfor
                    % endif

                </select>

            </div>

        % endif

        <div>
            % if study_hdl != "None":
                This node is linked to the Dataverse study ${study} on ${dataverse}.
            % else:
                This node has not yet been linked to a study.
            % endif
        </div>

        <div style="padding-bottom: 10px">
            Authorized by OSF user
            <a href="${domain}/${authorized_user_id}" target="_blank">
                ${authorized_user_name}
            </a>
            on behalf of Dataverse user ${authorized_dataverse_user}
        </div>

##        %for file in files:
##            <div>${file}</div>
##        %endfor

    % else:

        <a id="dataverseAuth" class="btn btn-success">Authorize</a>

    % endif

    % if authorized:
        <a id="dataverseDeauth" class="btn btn-danger" style="padding-top: 10px">Unauthorize</a>
    % endif

</div>

<script>

    $("#dataverseDropDown").change(function() {
        var dn = '{"dataverse_number":"' + $(this).find(":selected").val() +
                '", "study_hdl":"None"}'
        $.ajax({
            url: nodeApiUrl + 'dataverse/set/',
            data: dn,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            async: false
        });
        location.reload(true);
    });

    $("#studyDropDown").change(function() {
        var sn = '{"study_hdl":"' + $(this).find(":selected").val() + '"}'
        $.ajax({
            url: nodeApiUrl + 'dataverse/set/',
            data: sn,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            async: false
        });
        location.reload(true);
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
                'Are you sure you want to detach your Dataverse access key? This will ' +
                    'revoke the ability to modify and upload files to the Harvard Dataverse. If ' +
                    'the associated repo is private, this will also disable viewing ' +
                    'and downloading files from Dataverse. This will not remove your ' +
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