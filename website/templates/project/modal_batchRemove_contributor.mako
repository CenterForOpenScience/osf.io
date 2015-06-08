<div id="batchRemoveContribs" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Remove contributors from multiple components</h3>
            </div><!-- end modal-header -->

            <div class="modal-body">

                <!-- Whom to add -->

                <div data-bind="if: page() == 'whom'">

                    <!-- Find contributors -->
                    <form class='form' data-bind="submit: startSearch">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="input-group">
                                    <input class='form-control'
                                            data-bind="value:query"/>
                                    <span class="input-group-btn">
                                        <input type="submit" value="Search" class="btn btn-default">
                                    </span>

                                </div>
                            </div>
                        </div>
                        <div class="row search-contributor-links">
                        </div>
                    </form>
                    <hr/>
                    <div class="row">
                        <div class="col-md-6">

                                <table>
                                    <thead>                            <div>
                                <span class="modal-subheader">Contributors</span>
                                    <a data-bind="click:addAll">Add all</a>
                                <br><b >Select Components</b>
                                <div data-bind="foreach:nodes ">
                                <div data-bind="style:{marginLeft: margin}">
                                            <a data-bind="click:$root.selectNodesForSearch, text:title"></a>
                                        </div>
                                </div>
                            </div>
                                </thead>

                                    <tbody data-bind="foreach:{data : contributors, as: 'contributor', afterRender:addTips}"  >
                                        <tr data-bind="if:!($root.selected($data))">
                                            <td style="padding-right: 10px;">
                                                <a
                                                        class="btn btn-default contrib-button btn-mini"
                                                        data-bind="click:$root.add, css:{disabled: $root.contribInProject(contributor)}, tooltip: {title: 'Remove contributor'}"
                                                    >-</a>
                                            </td>
                                            <td>
                                                <!-- height and width are explicitly specified for faster rendering -->
                                                <img data-bind="attr: {src: contributor.gravatar_url}" height=40 width=40 />
                                            </td>
                                            <td >
                                                <a data-bind = "attr: {href: contributor.profile_url}" target="_blank">
                                                    <span data-bind= "text:contributor.fullname"></span>
                                                </a><br>


                                                    <span data-bind="if: contributor.employment">
                                                        <span
                                                            class = 'small'
                                                            data-bind="text: contributor.employment">
                                                        </span><br>
                                                    </span>


                                                    <span data-bind="if: contributor.education">
                                                        <span
                                                            class = 'small'
                                                            data-bind= "text: contributor.education">
                                                        </span><br>
                                                    </span>

                                                    <span class= 'small'
                                                          data-bind= "text: contributor.displayProjectsInCommon">
                                                    </span>

                                                <span
                                                        class='text-muted'
                                                        data-bind="visible: !contributor.registered">(unregistered)</span>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                        </div><!-- ./col-md -->


                        <div class="col-md-6">
                            <table class="table-fixed"  style="padding-top: 10px;">
                                <div>
                                    <span class="modal-subheader">Removing</span>
                                    <a data-bind="click:removeAll">Remove all</a>
                                </div>

                                <tbody data-bind="sortable: {data: selection, as: 'contributor', afterRender: makeAfterRender(), options: {containment: 'parent'}}">
                                    <tr style="padding-top: 10px;">
                                        <td style="padding-right: 10px;">
                                            <a
                                                    class="btn btn-default contrib-button btn-mini"
                                                    data-bind="click:$root.remove, tooltip: {title: 'Keep contributor'}"
                                                >-</a>
                                        </td>
                                        <td>
                                            <img data-bind="attr: {src: contributor.gravatar_url}" />
                                        </td>

                                        <td>
                                            <span   data-bind="text: contributor.fullname"></span>

                                            <span
                                                    class='text-muted'
                                                    data-bind="visible: !contributor.registered">(unregistered)</span>
                                        </td>

                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Component selection page -->
                <div data-bind="if:page()=='which'">

                    <div>
                        Removing contributor(s)
                        <span data-bind="text:addingSummary()"></span>
                        from component
                        <span data-bind="text:title"></span>.
                    </div>

                    <hr />

                    <div style="margin-bottom:10px;">
                        Would you like to remove these contributor(s) from any of
                        the following components?
                    </div>

                    <div class="row">

                        <div data-bind="foreach:selection">
                            <div class="col-md-6" >
                                <b><span data-bind="text:fullname"></span></b>
                                <div>
                                    <a data-bind="click:$root.selectNodesForContrib"> All</a> |
                                    <a data-bind="click:$root.deselectNodesForContrib">None</a>
                                </div>

                                <div data-bind="foreach:$parent.nodes">
                                    <!-- ko if:$root.contribNodes(id,$parent.id) -->
                                     <div data-bind="style:{marginLeft: margin}">
                                            <input type="checkbox" data-bind="checked:$root.nodesToChange, value : $parent.id+ '|'+id" />
                                            <em data-bind="text:title"></em>
                                        </div>
                                        <!-- /ko -->



                                </div>

                            </div>

                        </div>


                        <div class="col-md-6">
                            <div>
                                <a data-bind="click:selectNodes">Select all</a>
                            </div>
                            <div>
                                <a data-bind="click:deselectNodes">De-select all</a>
                            </div>
                        </div>
                    </div>

                </div><!-- end component selection page -->

            </div><!-- end modal-body -->


            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>


                <span data-bind="if:selection().length && page() == 'whom'">
                    <a class="btn btn-success" data-bind="visible:selection().length==0, click:submit">Submit</a>
                    <a class="btn btn-primary" data-bind="visible:selection().length, click:selectWhich">Next</a>
                </span>

                <span data-bind="if: page() == 'which'">
                    <a class="btn btn-primary" data-bind="click:selectWhom">Back</a>
                    <a class="btn btn-success" data-bind="click:submit">Submit</a>
                </span>

            </div><!-- end modal-footer -->

        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

