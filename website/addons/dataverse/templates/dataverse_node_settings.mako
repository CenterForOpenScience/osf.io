<%inherit file="project/addon/node_settings.mako" />

<div>
    % if connected:

        <select id="dataverseDropDown">
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
        <div>
            DV: ${dataverse_number} : ${study_hdl}

        </div>

        %for file in files:
            <div>${file}</div>
        %endfor

    % else:

        You must have a dataverse account to use this feature.

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