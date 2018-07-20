<div id="addContributors" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content scripted">
            <div class="modal-header">
                <a href="#" class='close' data-bind="click: clear" data-dismiss="modal">&times;</a>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">

                <!-- Whom to add -->
                <div data-bind="if: page() == 'whom'">
                    <!-- Find contributors -->
                    <form class='form' data-bind="submit: startSearch">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="input-group m-b-sm">
                                    <input class='form-control'
                                            data-bind="value:query"
                                            placeholder='Search by name or user profile information' autofocus/>
                                    <span class="input-group-btn">
                                        <input type="submit" value="Search" class="btn btn-default">
                                    </span>
                                </div>
                                <div class="row search-contributor-links">
                                    <div class="col-md-12">
                                        <div style='margin-left: 5px'>
                                            <!-- ko if:parentId -->
                                                <a class="f-w-lg" data-bind="click: startSearchParent, text:'Import contributors from ' + parentTitle"></a>
                                            <!-- /ko -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    <hr />
                    </form>


                    <!-- Choose which to add -->
                    <div class="row">

                        <div class="col-md-4">
                            <div>
                                <span class="modal-subheader">Results</span>
                                <a data-bind="visible: addAllVisible, click:addAll">Add all</a>
                            </div>
                            <!-- ko if: notification -->
                            <div data-bind="html: notification().message, css: 'alert alert-' + notification().level"></div>
                            <!-- /ko -->
                            <!-- ko if: doneSearching -->
                            <table class="table-condensed table-hover">
                                <thead data-bind="visible: foundResults">
                                </thead>
                                <tbody data-bind="foreach:{data:results, as: 'contributor', afterRender:addTips}">
                                    <tr data-bind="if:!($root.selected($data))">
                                        <td class="p-r-sm osf-icon-td" >
                                            <a
                                                    class="btn btn-success contrib-button btn-mini"
                                                    data-bind="visible: !contributor.added,
                                                               click:$root.add.bind($root),
                                                               tooltip: {title: 'Add contributor'}"
                                                ><i class="fa fa-plus"></i></a>
                                            <div data-bind="visible: contributor.added,
                                                            tooltip: {title: 'Already added'}"
                                                ><div
                                                    class="btn btn-default contrib-button btn-mini disabled"
                                                    ><i class="fa fa-check"></i></div></div>
                                        </td>
                                        <td>
                                            <!-- height and width are explicitly specified for faster rendering -->
                                            <img data-bind="attr: {src: contributor.profile_image_url}" height=35 width=35 />
                                        </td>
                                        <td width="75%" >
                                            <a  data-bind="attr: {href: contributor.profile_url}" target="_blank">
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

                                                <span>
                                                    <span class= 'small'
                                                      data-bind= "text: contributor.displayProjectsInCommon">
                                                    </span><br>
                                                </span>
                                                <span data-bind="visible: contributor.social.personal">
                                                    <a data-bind="attr: {href: contributor.social.personal}" data-toggle="tooltip" title="Personal Website"  target="_blank">
                                                        <i class="fa fa-globe social-icons fa-lg"></i>
                                                    </a>
                                                </span>

                                                <span data-bind="visible: contributor.social.twitter">
                                                    <a data-bind="attr: {href: contributor.social.twitter}" data-toggle="tooltip" title="Twitter" target="_blank">
                                                        <i class="fa fa-twitter social-icons fa-lg"></i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.github">
                                                    <a data-bind="attr: {href: contributor.social.github}" data-toggle="tooltip" title="Github" target="_blank">
                                                        <i class="fa fa-github-alt social-icons fa-lg"></i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.linkedIn" >
                                                    <a data-bind="attr: {href: contributor.social.linkedIn}" data-toggle="tooltip" title="LinkedIn" target="_blank">
                                                        <i class="fa fa-linkedin social-icons fa-lg"></i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.scholar">
                                                    <a data-bind="attr: {href: contributor.social.scholar}" data-toggle="tooltip" title="Google Scholar" target="_blank">
                                                        <img class="social-icons fa-lg" src="/static/img/googlescholar.png">
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.impactStory">
                                                    <a data-bind="attr: {href: contributor.social.impactStory}" data-toggle="tooltip" title="ImpactStory" target="_blank">
                                                        <i class="fa fa-info-circle social-icons fa-lg"></i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.orcid">
                                                    <a data-bind="attr: {href: contributor.social.orcid}" data-toggle="tooltip" title="ORCiD" target="_blank">
                                                        <i class="fa social-icons fa-lg">iD</i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.researcherId">
                                                    <a data-bind="attr: {href: contributor.social.researcherId}" data-toggle="tooltip" title="ResearcherID" target="_blank">
                                                        <i class="fa social-icons fa-lg">R</i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.researchGate">
                                                    <a data-bind="attr: {href: contributor.social.researchGate}" data-toggle="tooltip" title="ResearchGate" target="_blank">
                                                        <img class="social-icons p-b-xs" src="/static/img/researchgate.jpg"></i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.academiaInstitution + social.academiaProfileID">
                                                    <a data-bind="attr: {href: contributor.social.academiaInstitution + social.academiaProfileID}" data-toggle="tooltip" title="Academia" target="_blank">
                                                        <i class="fa social-icons fa-lg">A</i>
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.baiduScholar">
                                                    <a data-bind="attr: {href: contributor.social.baiduScholar}" data-toggle="tooltip" title="Baidu Scholar" target="_blank">
                                                        <img class="social-icons fa-lg" src="/static/img/baiduscholar.png">
                                                    </a>
                                                </span>
                                                <span data-bind="visible: contributor.social.ssrn">
                                                    <a data-bind="attr: {href: contributor.social.ssrn}" data-toggle="tooltip" title="SSRN" target="_blank">
                                                        <img class="social-icons fa-lg" src="/static/img/SSRN.png">
                                                    </a>
                                                </span>
                                            <span
                                                    class='text-muted'
                                                    data-bind="visible: !contributor.registered">(unregistered)</span>
                                        </td>

                                    </tr>


                                </tbody>
                            </table>
                            <!-- /ko -->
                            <!-- Link to add non-registered contributor -->
                            <div class='help-block'>
                                <div data-bind='if: foundResults'>
                                    <ul class="pagination pagination-sm" data-bind="foreach: paginators">
                                        <li data-bind="css: style"><a href="#" data-bind="click: handler, text: text"></a></li>
                                    </ul>
                                    <p>
                                        <div data-bind='ifnot: emailSearch'>
                                            <a href="#" data-bind="click:gotoInvite">Add <strong><em data-bind="text: query"></em></strong> as an unregistered contributor</a>.
                                        </div>
                                    </p>
                                </div>
                                <div data-bind="if: showLoading">
                                    <p class="text-muted">Searching contributors...</p>
                                </div>
                                <div data-bind="if: noResults">
                                    <div data-bind='if: emailSearch'>
                                      No results found. Try a more specific search.
                                    </div>
                                    <div data-bind='ifnot: emailSearch'>
                                      No results found. Try a more specific search
                                    </div>
                                    <div data-bind="ifnot: emailSearch"> or
                                        <a href="#" data-bind="click:gotoInvite">add <strong><em data-bind="text: query"></em></strong> as an unregistered contributor</a>.
                                    </div>
                                </div>
                                <div data-bind="if: emailSearch">
                                    <p>It looks like you are trying to search by email address. Please try your search again using your collaborator's name. You will be able to add users without OSF accounts as unregistered contributors.</p>
                                </div>
                            </div>
                        </div><!-- ./col-md -->

                        <div class="col-md-8">
                            <div>
                                <span class="modal-subheader">Adding</span>
                                <a data-bind="visible: removeAllVisible, click:removeAll">Remove all</a>
                            </div>

                            <!-- TODO: Duplication here: Put this in a KO template -->
                            <table class="table-condensed table-hover">
                                <thead class="keep-all" data-bind="visible: selection().length">
                                    <th width="10%"></th>
                                    <th width="10%"></th>
                                    <th width="30%">Name</th>
                                    <th>
                                        Bibliographic Contributor
                                        <i class="fa fa-question-circle visibility-info"
                                           data-toggle="popover"
                                           data-title="Bibliographic Contributor Information"
                                           data-container="body"
                                           data-placement="right"
                                           data-html="true">
                                        </i>
                                    <th>
                                        Permissions
                                        <i class="fa fa-question-circle permission-info"
                                                data-toggle="popover"
                                                data-title="Permission Information"
                                                data-container="#addContributors"
                                                data-html="true"
                                            ></i>
                                    </th>
                                </thead>
                                <tbody data-bind="foreach:{data:selection, as: 'contributor', afterRender:makeAfterRender()}">
                                    <tr>
                                        <td class="p-r-sm" class="osf-icon-td">
                                            <a
                                                    class="btn btn-default contrib-button btn-mini"
                                                    data-bind="click:$root.remove.bind($root), tooltip: {title: 'Remove contributor'}"
                                                ><i class="fa fa-minus"></i></a>
                                        </td>
                                        <td>
                                            <!-- height and width are explicitly specified for faster rendering -->
                                            <img data-bind="attr: {src: contributor.profile_image_url || '/static/img/unreg_profile_image.png'}" height=35 width=35 />
                                        </td>

                                        <td>
                                            <span   data-bind="text: contributor.fullname"></span>

                                            <span
                                                    class='text-muted'
                                                    data-bind="visible: !contributor.registered">(unregistered)</span>
                                        </td>
                                        <td>
                                            <input
                                                type="checkbox" class="biblio visible-filter"
                                                data-bind="checked: contributor.visible"
                                            />
                                        </td>

                                        <td>
                                            <select class="form-control input-sm" data-bind="
                                                options: $root.permissionList,
                                                value: permission,
                                                optionsText: 'text'">
                                            </select>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                    </div>
                </div>
                <!-- Component selection page -->
                <div data-bind="visible:page()=='which'">

                    <div>
                        Adding contributor(s)
                        <span data-bind="text:addingSummary()"></span>
                        to <span data-bind="text:title"></span>.
                    </div>

                    <hr />

                    <div style="margin-bottom:10px;">
                        You can also add the contributor(s) to any components on which you are an admin.
                    </div>

                    <div>
                        Select:&nbsp;
                        <a class="text-bigger" data-bind="click:selectAllNodes">Select all</a>
                        &nbsp;|&nbsp;
                        <a class="text-bigger" data-bind="click:selectNoNodes">Select none</a>
                    </div>
                    <div class="tb-row-titles">
                        <div style="width: 100%" data-tb-th-col="0" class="tb-th">
                            <span class="m-r-sm"></span>
                        </div>
                    </div>
                    <div class="osf-treebeard">
                        <div id="addContributorsTreebeard">
                            <div class="spinner-loading-wrapper">
                                <div class="ball-scale ball-scale-blue">
                                    <div></div>
                                </div>
                                <p class="m-t-sm fg-load-message"> Loading projects and components...  </p>
                            </div>
                        </div>
                    </div>

                </div><!-- end component selection page -->

                <!-- Invite user page -->
                <div data-bind='if:page() === "invite"'>
                    <form class='form'>
                        <div class="form-group">
                            <label for="inviteUserName">Full Name</label>
                            <input type="text" class='form-control' id="inviteName"
                                placeholder="Full name" data-bind='value: inviteName, valueUpdate: "input"'/>
                        </div>
                        <div class="form-group">
                            <label for="inviteUserEmail">Email</label>
                            <input type="email" class='form-control' id="inviteUserEmail"
                                    placeholder="Email" data-bind='value: inviteEmail' autofocus/>
                        </div>
                         <div class="help-block">
                            <p>We will notify the user that they have been added to your project.</p>
                            <p class='text-danger' data-bind='text: inviteError'></p>
                        </div>
                    </form>
                </div><!-- end invite user page -->

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>

                <span data-bind="if: page() === 'invite'">
                    <button class="btn btn-primary" data-bind='click:selectWhom'>Back</button>
                    <button class='btn btn-success'
                         data-bind='click: postInvite, enable:canSubmit'
                                    type="submit">Add</button>
                </span>

                <span data-bind="if:selection().length && page() == 'whom'">
                    <a class="btn btn-success" data-bind="visible:!hasChildren(), click:submit">Add</a>
                    <a class="btn btn-primary" data-bind="visible: hasChildren(), click:selectWhich">Next</a>
                </span>

                <span data-bind="if: page() == 'which'">
                    <a class="btn btn-primary" data-bind="click:selectWhom">Back</a>
                    <a class="btn btn-success" data-bind="click:submit">Add</a>
                </span>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
