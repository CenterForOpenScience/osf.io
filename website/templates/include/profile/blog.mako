<script id="profileBlog" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit">

            <div class="form-group">
                <label>Theme</label>
                <div class="input-group">
                    <select class='form-control' data-bind="value: theme">
                        <option value="casper">Casper</option>
                        <option value="openwriter">Openwriter</option>
                        <option value="perfetta">Perfetta</option>
                    </select>
                </div>
            </div>

            <div class="form-group">
                <label>Blog Name</label>
                <input class="form-control" data-bind="value: title" placeholder="My Blog"/>
            </div>

            <div class="form-group">
                <label>Blog Description</label>
                <input class="form-control" data-bind="value: description" placeholder="My Blog Description"/>
            </div>

            <div class="form-group">
                <label>Blog Cover Photo</label>

            </div>

            <div class="padded">

                <button
                        type="button"
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

        <div data-bind="if: editAllowed">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
