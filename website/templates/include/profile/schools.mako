<script id="profileSchools" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit">

            <div data-bind="foreach: contents">

                <div class="well well-sm">
                    Position {{ $index() + 1 }}
                    <a
                            class="text-danger pull-right"
                            data-bind="click: $parent.removeContent,
                                       visible: $parent.canRemove"
                        >Remove</a>
                </div>

                <div class="form-group">
                    <label>Institution</label>
                    <input class="form-control" data-bind="value: institution" />
                </div>

                <div class="form-group">
                    <label>Department</label>
                    <input class="form-control" data-bind="value: department" />
                </div>

                <div class="form-group">
                    <label>Degree</label>
                    <input class="form-control" data-bind="value: degree" />
                </div>

                <div class="form-group">
                    <label>Start Date</label>
                    <input class="form-control" data-bind="value: start" />
                </div>

                <div class="form-group">
                    <label>End Date</label>
                    <input class="form-control" data-bind="value: end" />
                </div>

                <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

            </div>

            <div>
                <a class="btn btn-default" data-bind="click: addContent">
                    Add another
                </a>
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
                        data-bind="enable: isValid"
                    >Submit</button>

            </div>

            <!-- Flashed Messages -->
            <div class="help-block">
                <p data-bind="html: message, attr.class: messageClass"></p>
            </div>

        </form>

    </div>

    <div data-bind="if: mode() === 'view'">

        <div data-bind="ifnot: contents().length">
            <div class="well well-sm">Not provided</div>
        </div>

        <div data-bind="if: contents().length">

            <table class="table">

                <thead>
                    <tr>
                        <th>Institution</th>
                        <th>Department</th>
                        <th>Degree</th>
                        <th>Start Date</th>
                        <th>End Date</th>
                    </tr>
                </thead>

                <tbody data-bind="foreach: contents">

                    <tr>

                        <td>{{ institution }}</td>
                        <td>{{ department }}</td>
                        <td>{{ degree }}</td>
                        <td>{{ start }}</td>
                        <td>{{ end }}</td>

                    </tr>

                </tbody>

            </table>

        </div>


        <div data-bind="if: editable">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
