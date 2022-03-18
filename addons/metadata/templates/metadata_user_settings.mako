<!-- Authorization -->
<div id='${addon_short_name}Scope' class='addon-settings addon-generic scripted'
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        <span data-bind="text: properName"></span>
    </h4>

    <div class="addon-auth-table" id="${addon_short_name}-header">
        <div class="input-group">
            <span class="input-group-addon">e-Rad Researcher Number</span>
            <input class="form-control" data-bind="textInput: eRadResearcherNumber" name="erad_researcher_number" ${'disabled' if disabled else ''} />
        </div>
        <div style="text-align: right; margin: 2px;">
            <!-- Save Button -->
            <button data-bind="click: save, enable: eRadResearcherNumberChanged" class="btn btn-success">${_("Save")}</button>
        </div>
    </div>
</div>
