<div class="modal fade" id="addPointer" tabindex="-1">

    <div class="modal-dialog modal-lg">

        <div class="modal-content">

            <div class="modal-header">
                <h3>Link other OSF projects</h3>
            </div>

            <div class="modal-body">

                <form role='form'>
                    <div class="form-group">
                        <input class="form-control" placeholder="Search projects" data-bind="value:query" />

                        <div class="help-block">
                            <span class="text-danger" data-bind="html: searchWarningMsg"></span>
                        </div>
                    </div>
                    <div>
                      <button class="btn btn-default"
                          data-bind="click:searchAllProjects,
                          text: searchAllProjectsSubmitText(),
                          attr: {disabled: loadingResults()},
                          css: {active: includePublic()}">
                          Search all projects
                      </button>
                      <button class="btn btn-default"
                          data-bind="
                          click: searchMyProjects,
                          text: searchMyProjectsSubmitText(),
                          attr: {disabled: loadingResults()},
                          css: {active: !includePublic()}">
                          Search my projects
                      </button>
                    </div>
                </form>

                <br>
                <div>
                  <ul class="nav nav-tabs">
                    <li id="getLinksNodesTab" class="active"><a data-bind="click: nodeView">Projects</a></li>
                    <li id="getLinksRegistrationsTab"><a data-bind="click: registrationView">Registrations</a></li>
                  </ul>
                </div>
                <br>

                <!-- Choose which to add -->
                <div class="row">

                    <div class="col-md-10">
                        <table class="table add-links table-striped table-condensed table-hover">
                            <caption>
                                <span data-bind="if: (inputType() == 'nodes' && includePublic)" class="modal-subheader">Results: All Projects</span>
                                <span data-bind="if: (inputType() == 'nodes' && !includePublic())" class="modal-subheader">Results: My Projects</span>
                                <span data-bind="if: (inputType() != 'nodes' && includePublic)" class="modal-subheader">Results: All Registrations</span>
                                <span data-bind="if: (inputType() != 'nodes' && !includePublic())" class="modal-subheader">Results: My Registrations</span>
                                <p class="h5 error" data-bind="text:errorMsg"></p>
                            </caption>
                            <tbody data-bind="foreach:{data:results}">
                                <tr>
                                    <td data-label="">
                                        <a data-bind="attr: {class: $root.selected($data) ? 'fa-button btn btn-default': 'fa-button btn btn-success' }, click: $root.selected($data) ? $root.remove.bind($root) : $root.add.bind($root), css: $root.disableButtons()">
                                            <i data-bind="attr: {class: $root.selected($data) ? 'fa-fix-width fa fa-minus': 'fa-fix-width fa fa-plus' }, visible: !$root.processing() || ($root.processing() && !($root.isClicked() == $data.id))"></i>
                                            <i data-bind="visible: $root.processing() && $root.isClicked() == $data.id" class="fa-fix-width fa fa-spinner fa-spin"></i>
                                        </a>
                                        <a target="_blank" data-toggle="tooltip" data-bind="attr: {href: $data.links.html, title: $root.title($data).long}, text: $root.title($data).short, "></a>
                                    </td>
                                    <td data-label="" class="text-center node-dates" data-bind="text:$root.getDates($data)"></td>
                                    <td data-label="" class="text-center" data-bind="text:$root.authorText($data)"></td>
                                </tr>
                            </tbody>
                        </table>
                        <div data-bind='if: loadingResults'>
                            <div class="ball-pulse ball-scale-blue text-center">
                              <div></div>
                              <div></div>
                              <div></div>
                            </div>
                        </div>
                        <div class='help-block'>
                            <div data-bind='if: foundResults'>
                                <ul class="pagination pagination-sm" data-bind="foreach: paginators">
                                    <li data-bind="css: style"><a href="#" data-bind="click: handler, text: text"></a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a class="btn btn-default" data-bind='click:done' data-dismiss="modal">Done</a>
                <div class="help-block">
                    <span class="text-danger" data-bind="html: submitWarningMsg"></span>
                </div>
            </div><!-- end modal-footer -->

        </div><!-- end modal-content -->

    </div><!-- end modal-dialog -->

</div><!-- end modal -->
