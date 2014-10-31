<script id="profileName" type="text/html">

    <form role="form" data-bind="submit: submit">

        <div class="form-group">
            <label>Full Name (e.g. Rosalind Elsie Franklin)</label>
            <input class="form-control" data-bind="value: full" />
        </div>

        <span class="help-block">
            Your full name, above, is the name that will be displayed in your profile.
            To control the way your name will appear in citations, you can use the
            "Auto-fill" button to automatically infer your first name, last
            name, etc., or edit the fields directly below.
        </span>

        <div style="margin-bottom: 10px;">
            <a class="btn btn-default" data-bind="enabled: hasFirst(), click: impute">Auto-fill</a>
        </div>

        <div class="form-group">
            <label>Given Name (e.g. Rosalind)</label>
            <input class="form-control" data-bind="value: given" />
        </div>

        <div class="form-group">
            <label>Middle Name(s) (e.g. Elsie)</label>
            <input class="form-control" data-bind="value: middle" />
        </div>

        <div class="form-group">
            <label>Family Name (e.g. Franklin)</label>
            <input class="form-control" data-bind="value: family" />
        </div>

        <div class="form-group">
            <label>Suffix</label>
            <input class="form-control" data-bind="value: suffix" />
        </div>

        <hr />

        <h4>Citation Preview</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Style</th>
                    <th class="overflow-block" width="30%">Citation Format</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>APA</td>
                    <td class="overflow-block" width="30%">{{ citeApa }}</td>
                </tr>
                <tr>
                    <td>MLA</td>
                    <td class="overflow-block" width="30%">{{ citeMla }}</td>
                </tr>
            </tbody>
        </table>

        <div class="padded">

            <button
                    class="btn btn-default"
                    data-bind="click: cancel"
                >Cancel</button>

            <button
                    type="submit"
                    class="btn btn-primary"
                >Submit</button>

        </div>

        <!-- Flashed Messages -->
        <div class="help-block">
            <p data-bind="html: message, attr.class: messageClass"></p>
        </div>

    </form>

</script>
