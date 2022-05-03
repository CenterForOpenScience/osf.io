<script id="profileJobs" type="text/html">

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
                        <span>${_("Position")} <span data-bind="text: $index() + 1"></span></span>
                        <span data-bind="visible: $parent.contentsLength() > 1">
                            [ drag to reorder ]
                        </span>
                        <a
                                class="text-danger pull-right"
                                data-bind="click: $parent.removeContent.bind($parent)"
                                >${_("Remove")}</a>
                        <a
                                style="margin-right: 15px"
                                class="btn-link pull-right"
                                data-bind="click: $parent.setContentFromIdP.bind($parent)"
                                >${_("Read IdP Profile")}</a>
                    </div>

                    <div class="form-row row">
                        <div class="form-group col-md-6">
                            <label>${_("Affiliation")} <span style="color: red">*</span></label>
                            <input class="form-control" data-bind="value: institution_ja"
                                placeholder="${_('Required')}"/>
                            <div data-bind="visible: $parent.showMessages, css:'text-danger'">
                                <p data-bind="validationMessage: institution_ja"></p>
                            </div>
                        </div>
                        <div class="form-group col-md-6">
                            <label>${_("Department / Institute")}</label>
                            <input class="form-control" data-bind="value: department_ja" />
                        </div>
                    </div>

                    <div class="form-row row">
                        <div class="form-group col-md-6">
                            <label>${_("Affiliation (English)")} <span style="color: red">*</span></label>
                            <input class="form-control" data-bind="value: institution"
                                placeholder="${_('Required')}"/>
                            <div data-bind="visible: $parent.showMessages, css:'text-danger'">
                                <p data-bind="validationMessage: institution"></p>
                            </div>
                        </div>
                        <div class="form-group col-md-6">
                            <label>${_("Department / Institute (English)")}</label>
                            <input class="form-control" data-bind="value: department" />
                        </div>
                    </div>

                    <div class="form-group">
                        <label>${_("Job title")}</label>
                        <input class="form-control" data-bind="value: title" />
                    </div>

                    <div class="form-group">
                        <label>${_("Start date")}</label>
                        <div class="row">
                            <div class ="col-md-3">
                                <select class="form-control" data-bind="options: months,
                                         optionsCaption: '${_("-- Month --")}',
                                         value: startMonth">
                                </select>
                            </div>
                            <div class="col-md-3">
                                <input class="form-control" placeholder="${_('Year')}" data-bind="value: startYear" />
                            </div>
                        </div>
                    </div>

                    <div class="form-group" data-bind="ifnot: ongoing">
                        <label>${_("End date")}</label>
                            <div class="row">
                                <div class ="col-md-3">
                                    <select class="form-control" data-bind="options: months,
                                         optionsCaption: '${_("-- Month --")}',
                                         value: endMonth">
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <input class="form-control" placeholder="${_('Year')}" data-bind="value: endYear" />
                                </div>
                            </div>
                    </div>


                    <div class="form-group">
                        <label>${_("Ongoing")}</label>
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
                    ${_("Add another Employment")}
                </a>
            </div>

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

    </div>

    <div data-bind="if: mode() === 'view'">

        <div data-bind="ifnot: contents().length">
            <div class="well well-sm">${_("Not provided")}</div>
        </div>

        <div class="row" data-bind="if: contents().length">

            <div data-bind="foreach: contents">
                <div class="col-xs-12">
                    <!-- ko if: expandable() -->
                        <div class="panel panel-default">
                            <div class="panel-heading card-heading" data-bind="click: toggle(), attr: {id: 'jobHeading' + $index(), href: '#jobCard' + $index()}" role="button" data-toggle="collapse" aria-controls="card" aria-expanded="false">
                                <div class="header-content break-word">
                                    <h5 class="institution" data-bind="text: institution"></h5>
                                    <span data-bind="if: startYear()" class="subheading">
                                        ${_('<span data-bind="text: startMonth"></span> <span data-bind="text: startYear"></span>') | n} - <span data-bind="text: endView"></span>
                                    </span>
                                </div>
                                <span data-bind="attr: {class: expanded() ? 'fa toggle-icon fa-angle-down' : 'fa toggle-icon fa-angle-up'}"></span>
                            </div>
                            <div data-bind="attr: {id: 'jobCard' + $index(), 'aria-labelledby': 'jobHeading' + $index()}" class="panel-collapse collapse">
                                <div class="panel-body card-body">
                                    <span data-bind="if: department().length"><h5>${_("Department / Institute:")}</h5> <span data-bind="text: department"></span></span>
                                    <span data-bind="if: title().length"><h5>${_("Title:")}</h5> <span data-bind="text: title"></span></span>
                                    <span data-bind="if: startYear()"><h5>${_("Dates:")}</h5>
                                        ${_('<span data-bind="text: startMonth"></span> <span data-bind="text: startYear"></span>') | n} - <span data-bind="text: endView"></span>
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
