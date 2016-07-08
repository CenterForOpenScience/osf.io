<script id="profileName" type="text/html">

    <form role="form" data-bind="submit: submit">

        <div class="form-group">
            <label>Full name (e.g. Rosalind Elsie Franklin)</label>
            <input class="form-control" data-bind="value: full" />
            <div data-bind="visible: showMessages, css:'text-danger'">
                <p data-bind="validationMessage: full"></p>
            </div>
        </div>

        <span class="help-block">
            Your full name, above, is the name that will be displayed in your profile.
            To control the way your name will appear in citations, you can use the
            "Auto-fill" button to automatically infer your first name, last
            name, etc., or edit the fields directly below.
        </span>

        <div style="margin-bottom: 10px;">
            <a class="btn btn-primary" data-bind="enabled: hasFirst(), click: impute">Auto-fill</a>
        </div>

        <div class="form-group">
            <label>Given name (e.g. Rosalind)</label>
            <input class="form-control" data-bind="value: given" />
        </div>

        <div class="form-group">
            <label>Middle name(s) (e.g. Elsie)</label>
            <input class="form-control" data-bind="value: middle" />
        </div>

        <div class="form-group">
            <label>Family name (e.g. Franklin)</label>
            <input class="form-control" data-bind="value: family" />
        </div>

        <div class="form-group">
            <label>Suffix</label>
            <input class="form-control" data-bind="value: suffix" />
        </div>

        <hr />

        <h4>Citation preview</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Style</th>
                    <th class="overflow-block" width="30%">Citation format</th>
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
                >Discard changes</button>

            <button
                    data-bind="disable: saving(), text: saving() ? 'Saving' : 'Save'"
                    type="submit"
                    class="btn btn-success"
                >Save</button>

        </div>

        <!-- Flashed Messages -->
        <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
        </div>
    </form>

</script>
