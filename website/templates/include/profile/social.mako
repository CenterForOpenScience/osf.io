<script id="profileSocial" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit">

            <div class="form-group">
                <label>Personal Site</label>
                <input class="form-control" data-bind="value: personal" />
            </div>

            <div class="form-group">
                <label>ORCID</label>
                <input class="form-control" data-bind="value: orcid" />
            </div>

            <div class="form-group">
                <label>ResearcherID</label>
                <input class="form-control" data-bind="value: researcherId" />
            </div>

            <div class="form-group">
                <label>Twitter</label>
                <input class="form-control" data-bind="value: twitter" />
            </div>

            <div class="form-group">
                <label>Google Scholar</label>
                <input class="form-control" data-bind="value: scholar" />
            </div>

            <div class="form-group">
                <label>LinkedIn</label>
                <input class="form-control" data-bind="value: linkedIn" />
            </div>

            <div class="form-group">
                <label>GitHub</label>
                <div data-bind="css: {'input-group': github.hasAddon()}">
                    <input class="form-control" data-bind="value: github" />
                    <span
                            class="input-group-btn"
                            data-bind="if: github.hasAddon()"
                        >
                        <button
                                class="btn btn-default"
                                data-bind="click: github.importAddon"
                            >Import</button>
                    </span>
                </div>
            </div>

            <div class="padded">

                <button
                        type="submit"
                        class="btn btn-default"
                        data-bind="visible: viewable, click: cancel"
                    >Cancel</button>

                <button
                        type="submit"
                        class="btn btn-primary"
                        data-bind="enable: enableSubmit"
                    >Submit</button>

            </div>

            <!-- Flashed Messages -->
            <div class="help-block">
                <p data-bind="html: message, attr.class: messageClass"></p>
            </div>

        </form>

    </div>

    <div data-bind="if: mode() === 'view'">

        <table class="table" data-bind="if: hasValues()">
            <tbody data-bind="foreach: values">
                <tr data-bind="if: value">
                    <td>{{ label }}</td>
                    <td><a target="_blank" data-bind="attr.href: value">{{ text }}</a></td>
                </tr>
            </tbody>
        </table>

        <div data-bind="ifnot: hasValues()">
            <div class="well well-sm">Not provided</div>
        </div>

        <div data-bind="if: editable">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
