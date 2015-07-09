<script id="profileSchools" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit, validationOptions: {insertMessages: false, messagesOnModified: false}">

            <div data-bind="sortable: {
                    data: contents,
                    options: {
                        handle: '.sort-handle',
                        containment: '#containDrag',
                        tolerance: 'pointer'
                    }
                }">

                <div>

                    <div class="well well-sm sort-handle">
                        <span>Position {{ $index() + 1 }}</span>
                        <span data-bind="visible: $parent.hasMultiple()">
                            [ drag to reorder ]
                        </span>
                        <a
                                class="text-danger pull-right"
                                data-bind="click: $parent.removeContent"
                            >Remove</a>
                    </div>

                    <div class="form-group">
                        <label>Institution</label>
                       <input class="form-control" data-bind="value: institution"
                            placeholder="Required"/>
                         <div data-bind="visible: $parent.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: institution"></p>
                        </div>
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
                        <div class="row">
                            <div class ="col-md-3">
                                <select class="form-control" data-bind="options: months,
                                         optionsCaption: '-- Month --',
                                         value: startMonth">
                                </select>
                            </div>
                            <div class="col-md-3">
                                <input class="form-control" placeholder="Year" data-bind="value: startYear" />
                            </div>
                        </div>
                    </div>

                    <div class="form-group" data-bind="ifnot: ongoing">
                        <label>End Date</label>
                            <div class="row">
                                <div class ="col-md-3">
                                    <select class="form-control" data-bind="options: months,
                                         optionsCaption: '-- Month --',
                                         value: endMonth">
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <input class="form-control" placeholder="Year" data-bind="value: endYear" />
                                </div>
                            </div>
                    </div>


                    <div class="form-group">
                        <label>Ongoing</label>
                        <input type="checkbox" data-bind="checked: ongoing, click: clearEnd"/>
                    </div>

                    <div data-bind="visible: $parent.showMessages, css:'text-danger'">
                        <p data-bind="validationMessage: start"></p>
                        <p data-bind="validationMessage: end"></p>
                        <p data-bind="validationMessage: startYear"></p>
                        <p data-bind="validationMessage: endYear"></p>
                    </div>

                    <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                </div>

            </div>

            <div>
                <a class="btn btn-default" data-bind="disable, click: addContent">
                    Add another
                </a>
            </div>

            <div class="p-t-lg p-b-lg">

                <button
                        type="button"
                        class="btn btn-default"
                        data-bind="click: cancel"
                    >Cancel</button>

                <button
                        type="submit"
                        class="btn btn-success"
                    >Save</button>

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
                        <th>Start&nbsp;Date</th>
                        <th>End&nbsp;Date</th>
                    </tr>
                </thead>

                <tbody data-bind="foreach: contents">

                    <tr>

                        <td>{{ institution }}</td>
                        <td>{{ department }}</td>
                        <td>{{ degree }}</td>
                        <td>{{ startMonth }} {{ startYear }}</td>
                        <td>{{ endView }}</td>

                    </tr>

                </tbody>

            </table>

        </div>


        <div data-bind="if: editable">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
