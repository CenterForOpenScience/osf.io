<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div>
        <h4 class="addon-title">Mendeley</h4>
    </div>

    <div>
        <select class="form-control" data-bind="foreach: accounts, value: selectedAccountId">
                <option data-bind="text: display_name, value: id"></option>
        </select>
        <select class="form-control" data-bind="foreach: citationLists, value: selectedCitationList">
                <option data-bind="text: name, value: provider_list_id"></option>
        </select>
    </div>

    <a class="btn btn-primary" data-bind="click: save">Save</a>
</form>
