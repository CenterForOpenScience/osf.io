<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}" class="container-fluid">
    <div class="row">
        <h4 class="addon-title">Mendeley</h4>
    </div>

    <div class="row">
        <div class="form-group">
            <label>User</label>
            <select class="form-control" data-bind="foreach: accounts, value: selectedAccountId">
                    <option data-bind="text: display_name, value: id"></option>
            </select>
        </div>
        <div class="form-group">
            <label>Folder</label>
            <select class="form-control" data-bind="foreach: citationLists, value: selectedCitationList">
                    <option data-bind="text: name, value: provider_list_id"></option>
            </select>
        </div>
        <div>
            <a class="btn btn-primary" data-bind="click: save">Save</a>
            <span data-bind="text: message"></span>
        </div>
    </div>


</form>
