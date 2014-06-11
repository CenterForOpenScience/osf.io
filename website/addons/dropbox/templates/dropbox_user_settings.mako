## Template for the "Dropbox" section in the "Configure Add-ons" panel

<h4 class="addon-title">Dropbox</h4>

<div id='dropboxAddonScope' class='addon-settings scripted'>

    <!-- Delete Access Token Button -->
    <div data-bind="if: userHasAuth() && loaded()">
        <button data-bind='click: deleteKey' class="btn btn-danger">
            Delete Access Token
        </button>

        <div class="scrolling-table">
            <table class="table table-hover">
                <thead>Authorized Projects:</thead>
                <tbody data-bind="foreach: nodes">
                    <tr>
                        <td>
                            <a data-bind="attr: { href: url, title: title }, text: title"></a>
                        </td>
                        <td>
                            <a data-bind="click: removeNodeAuth" class="text-danger pull-right">Deauthorize</a>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Create Access Token Button -->
    <div data-bind="if: !userHasAuth() && loaded()">
        <a data-bind="attr: {href: urls().create}" class="btn btn-primary">Create Access Token</a>
    </div>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>


<script>
    $script(['/static/addons/dropbox/dropboxUserConfig.js'], function() {
        // Endpoint for dropbox user settings
        var url = '/api/v1/settings/dropbox/';
        // Start up the Dropbox Config manager
        var dropbox = new DropboxUserConfig('#dropboxAddonScope', url);
    });
</script>

