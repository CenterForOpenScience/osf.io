<!-- TODO -->
<h4 class="addon-title">
    Application <small>${application_url}</small>
</h4>


<div id="appScope" class="scripted">
    <!-- Uncomment for debugging. Shows pretty printed ViewModel data -->
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->

    <h4>Custom Routes</h4>
    <table class="table">
        <thead>
            <tr>
                <th>Route</th>
                <th>Query</th>
            </tr>
        </thead>
        <tbody data-bind="foreach: customRoutes">
            <tr>
                <td>
                    <a data-bind="attr: { href: url}">{{url}}</a>
                </td>
                <td>{{query}}</td>
            </tr>
        </tbody>
    </table>
    <form class="form-inline" role="form">
        <input class="form-control" type="text" data-bind="value: customUrl" placeholder="Url">
        <input class="form-control" type="text" data-bind="value: customQuery" placeholder="Query">
        <button class="btn btn-success" data-bind="click: createCustomRoute">Create</button>
    </form>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message"></p>
    </div>

</div>

<script>
    $script('/static/addons/app/appNodeConfig.js', function() {
        AppNodeConfig('#appScope', '${'/api/v1/%s/app/q/' % node['id']}');
    });
</script>
