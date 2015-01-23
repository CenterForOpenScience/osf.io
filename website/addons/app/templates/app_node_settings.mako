<!-- TODO -->
<h4 class="addon-title">
    Application
</h4>


<div id="appScope" class="scripted">
    <!-- Uncomment for debugging. Shows pretty printed ViewModel data -->
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->

    <h4>Custom Routes</h4>
    <table class="table">
        <thead>
            <tr>
                <th>Query</th>
                <th>Route</th>
            </tr>
        </thead>
        <tbody data-bind="foreach: customRoutes">
            <tr>
                <td>{{query}}</td>
                <td>
                    <a data-bind="attr: { href: url}">{{url}}</a>
                </td>
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

    <div class="row" id="sortingBlock" data-bind="visible: isSortable">
      <div class="col-md-12">
        <h4>Default Sorting</h4>
        <input id="sorts"></input>
        <button class="btn btn-md btn-success" data-bind="click: setDefaultSearch">Submit</button>
      </div>
    </div>

</div>
