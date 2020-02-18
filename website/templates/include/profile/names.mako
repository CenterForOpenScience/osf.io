<script id="profileName" type="text/html">

    <form role="form" data-bind="submit: submit">

        <div class="form-group">
            <label>${_("Full name (e.g. Rosalind Elsie Franklin)")}</label>
            ## Maxlength for full names must be 186 - quickfile titles use fullname + 's Quick Files
            <input class="form-control" data-bind="value: full" maxlength="186"/>
            <div data-bind="visible: showMessages, css:'text-danger'">
                <p data-bind="validationMessage: full"></p>
            </div>
        </div>

        <span class="help-block">
            ${_('Your full name, above, is the name that will be displayed in your profile.\
            To control the way your name will appear in citations, you can use the\
            "Auto-fill" button to automatically infer your first name, last\
            name, etc., or edit the fields directly below.')}
        </span>

        <div style="margin-bottom: 10px;">
            <a class="btn btn-primary" data-bind="enabled: hasFirst(), click: autoFill">${_("Auto-fill")}</a>
        </div>

        <div class="form-group">
            <label>${_("Given name (e.g. Rosalind)")}</label>
            <input class="form-control" data-bind="value: given" maxlength="255"/>
        </div>

        <div class="form-group">
            <label>${_("Middle name(s) (e.g. Elsie)")}</label>
            <input class="form-control" data-bind="value: middle" maxlength="255"/>
        </div>

        <div class="form-group">
            <label>${_("Family name (e.g. Franklin)")}</label>
            <input class="form-control" data-bind="value: family" maxlength="255"/>
        </div>

        <div class="form-group">
            <label>${_("Suffix")}</label>
            <input class="form-control" data-bind="value: suffix" maxlength="255"/>
        </div>

        <hr />

        <h4>${_("Citation preview")}</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>${_("Style")}</th>
                    <th class="overflow-block" width="30%">${_("Citation format")}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>APA</td>
                    <td class="overflow-block" width="30%"><span data-bind="text: citeApa"></span></td>
                </tr>
                <tr>
                    <td>MLA</td>
                    <td class="overflow-block" width="30%"><span data-bind="text: citeMla"></span></td>
                </tr>
            </tbody>
        </table>

        <div class="p-t-lg p-b-lg">

            <button
                    type="button"
                    class="btn btn-default"
                    data-bind="click: cancel"
                >${_("Discard changes")}</button>

            <button
                    data-bind="disable: saving(), text: saving() ? '${_("Saving")}' : '${_("Save")}'"
                    type="submit"
                    class="btn btn-success"
                >${_("Save")}</button>

        </div>

        <!-- Flashed Messages -->
        <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
        </div>
    </form>

</script>
