## This page is rendered as a standalone template, outside of `OsfWebRenderer` defaults
<%page expression_filter="h"/>

<h3>${full_name} Add-on Terms</h3>

<table class="table table-bordered table-addon-terms">

    <thead>
        <tr>
            <th>Function</th>
            <th>Status</th>
        </tr>
    </thead>

    <tbody>
        % for cap in caps['capabilities']:
            <tr class="${cap['class']}">
                <td>${cap['function']}</td>
                <td>${cap['detail']}</td>
            </tr>
        % endfor
    </tbody>

</table>

<ul>
    % for term in caps['terms']:
        <li>${term}</li>
    % endfor
</ul>
