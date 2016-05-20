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
                        <span>Position <span data-bind="text: $index() + 1"></span></span>
                        <span data-bind="visible: $parent.contentsLength() > 1">
                            [ drag to reorder ]
                        </span>
                        <a
                                class="text-danger pull-right"
                                data-bind="click: $parent.removeContent.bind($parent)"
                                >Remove</a>
                    </div>

                    <div class="form-group">
                        <label>Institution</label>
                        <input class="form-control" data-bind="value: institution" 
                            placeholder="Required" />
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
                        <label>Start date</label>
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
                        <label>End date</label>
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
                <a class="btn btn-default" data-bind="click: addContent">
                    Add another
                </a>
            </div>

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

    </div>

    <div data-bind="if: mode() === 'view'">

        <div data-bind="ifnot: contents().length">
            <div class="well well-sm">Not provided</div>
        </div>

        <div class="row" data-bind="if: contents().length">
            <div data-bind="foreach: contents">
                <div class="col-xs-12">
                    <!-- ko if: expandable() -->
                        <div class="panel panel-default">
                            <div class="panel-heading card-heading" data-bind="click: toggle(), attr: {id: 'schoolHeading' + $index(), href: '#schoolCard' + $index()}" role="button" data-toggle="collapse" aria-controls="card" aria-expanded="false">
                                <div class="header-content">
                                    <h5 class="institution" data-bind="text: institution"></h5>
                                    <span data-bind="if: startYear()" class="subheading">
                                        <span data-bind="text: startMonth"></span> <span data-bind="text: startYear"></span> - <span data-bind="text: endView"></span>
                                    </span>
                                </div>
                                <span data-bind="attr: {class: expanded() ? 'fa toggle-icon fa-angle-down' : 'fa toggle-icon fa-angle-up'}"></span>
                            </div>
                            <div data-bind="attr: {id: 'schoolCard' + $index(), 'aria-labelledby': 'schoolHeading' + $index()}" class="panel-collapse collapse">
                                <div class="panel-body">
                                    <span data-bind="if: department().length"><h5>Department:</h5> <span data-bind="text: department"></span></span>
                                    <span data-bind="if: degree().length"><h5>Degree:</h5> <span data-bind="text: degree"></span></span>
                                    <span data-bind="if: startYear()"><h5>Dates:</h5>
                                        <span data-bind="text: startMonth"></span> <span data-bind="text: startYear"></span> - <span data-bind="text: endView"></span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    <!-- /ko -->
                    <!-- ko ifnot: expandable() -->
                        <div class="panel panel-default">
                            <div class="panel-heading no-bottom-border">
                                <div>
                                    <h5 data-bind="text: institution"></h5>
                                </div>
                            </div>
                        </div>
                    <!-- /ko -->
                </div>
            </div>

        </div>


        <div data-bind="if: editable">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
