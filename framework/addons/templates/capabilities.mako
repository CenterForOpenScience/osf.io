<h3>${full_name} Add-on Capabilities</h3>

<table class="table table-bordered">

    <thead>
        <tr>
            <th>Function</th>
            <th>Status</th>
            <th>Detail</th>
        </tr>
    </thead>

    <tbody>
        % for cap in caps:
            <tr class="${cap['class']}">
                <td>${cap['function']}</td>
                <td>${cap['status']}</td>
                <td>${cap['detail']}</td>
            </tr>
        % endfor
    </tbody>

</table>
