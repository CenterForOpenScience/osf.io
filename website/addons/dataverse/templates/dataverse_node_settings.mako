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

            % if len(dataverses) > 0:

                % for j, s in enumerate(studies):
                    % if j == int(study_number):
                        <option value=${j} selected>${s}</option>
                    % else:
                        <option value=${j}>${s}</option>
                    % endif
                % endfor

            % else:

                <option value=${0}>---</option>

            % endif

        </select>
        <div>
            DV: ${dataverse_number} : ${study_number}
        </div>
    % else:

        Please go to account settings and connect to a dataverse.

    % endif
</div>

<script>
    $("#dataverseDropDown").change(function() {
        var dn = '{"dataverse_number":"' + $(this).find(":selected").val() +
                '", "study_number":"0"}'
        $.ajax({
            url: nodeApiUrl + 'dataverse/set/',
            data: dn,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json'
        })
        location.reload(true)
        var show_studies = $(this).find(":selected").val();
        console.log(dn);
    });

    $("#studyDropDown").change(function() {
        var sn = '{"study_number":"' + $(this).find(":selected").val() + '"}'
        $.ajax({
            url: nodeApiUrl + 'dataverse/set/',
            data: sn,
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json'
        })
        location.reload(true)
        var show_studies = $(this).find(":selected").val();
        console.log("the value you selected: " + show_studies);
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