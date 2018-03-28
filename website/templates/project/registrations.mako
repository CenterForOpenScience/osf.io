<%inherit file="project/project_base.mako"/>
<%namespace name="render_nodes" file="util/render_nodes.mako" />
<%def name="title()">${node['title']} Registrations</%def>
<div id="registrationsListScope">
<ul id="registrationsTabs" class="nav nav-tabs" role="tablist">
  <li role="presentation" class="active">
    <a id="registrationsControl" aria-controls="registrations" href="#registrations">Registrations</a>
  </li>
  % if 'admin' in user['permissions'] and node['has_draft_registrations']:
  <li role="presentation" data-bind="visible: hasDrafts">
      <a id="draftsControl" aria-controls="drafts" href="#drafts">Draft Registrations</a>
  </li>
  % endif
</ul>
<div class="tab-content registrations-view">
  <div role="tabpanel" class="tab-pane active" id="registrations">
    <div class="row" style="min-height: 150px; padding-top:20px;">
      <div class="col-xs-9 col-sm-8">
        % if node["registrations"]:
          ${render_nodes.render_nodes(nodes=node['registrations'], sortable=False, user=user, pluralized_node_type='registrations', show_path=False, include_js=True)}
    ## Uncomment to disable registering Components
    ##% elif node['node_type'] != 'project':
    ##      %if user['is_admin_parent']:
    ##          To register this component, you must <a href="${parent_node['url']}registrations"><b>register its parent project</b></a> (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %else:
    ##          There have been no registrations of the parent project (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %endif
        % else:
          % if 'admin' in user['permissions']:
            <p>There have been no completed registrations of this project.
            You can start a new registration by clicking the “New registration” button, and you have the option of saving as a draft registration before submission.</p>
          % else:
            <p>There have been no completed registrations of this project.
            Only project administrators can initiate registrations.</p>
          % endif
          <p>For a list of the most viewed and most recent public registrations on the Open Science Framework, click <a href="/explore/activity/#newPublicRegistrations">here</a>.</p>
        % endif
        %if parent_node['exists'] and user['is_admin_parent']:
        <br />
        <br />
        To register the entire project "${parent_node['title']}" instead, click <a href="${parent_node['registrations_url']}">here.</a>
        %endif
      </div>
      % if 'admin' in user['permissions'] and not disk_saving_mode:
      <div class="col-xs-3 col-sm-4">
        <a id="registerNode" class="btn btn-success disabled" type="button">
          Loading ...
        </a>
      </div>
      % endif
    </div>
  </div>
  <div role="tabpanel" class="tab-pane" id="drafts">
    <div id="draftRegistrationsScope" class="row scripted" style="min-height: 150px;padding-top:20px;">
      <div data-bind="visible: loadingDrafts" class="spinner-loading-wrapper">
        <div class="ball-scale ball-scale-blue">
          <div></div>
        </div>
      </div>
      <form id="newDraftRegistrationForm" method="POST" style="display:none">
        <!-- ko if: selectedSchema() -->
        <input type="hidden" name="schema_name" data-bind="value: selectedSchema().name">
        <input type="hidden" name="schema_version" data-bind="value: selectedSchema().version">
        <!-- /ko -->
      </form>
      <div>
        <div class="col-md-9">
          <div class="scripted" data-bind="foreach: drafts">
            <li class="project list-group-item list-group-item-node">
              <h4 data-bind="text: schema().title" ></h4>
              <h4 class="list-group-item-heading">
                <div data-bind="visible: hasRequiredQuestions" class="progress progress-bar-md">
                  <div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100"
                       data-bind="attr: {'aria-completion': completion},
                                  style: {width: completion() + '%'}">
                    <span class="sr-only"></span>
                  </div>
                </div>
                <small>
                <p>Initiated by: <span data-bind="text: initiator.fullname"></span>
                <p>Started: <span data-bind="text: initiated"></span></p>
                <p>Last updated: <span data-bind="text: updated"></span></p>
                <span data-bind="if: requiresApproval">
                    <div data-bind="if: isPendingApproval">
                        <div class="draft-status-badge bg-warning"> Pending Review</div>
                    </div>
                    <div data-bind="if: userHasUnseenComment">
                        <div class="draft-status-badge bg-warning"> Unseen Comments</div>
                    </div>
                </span>
                </small>
                <div class="row">
                  <div class="col-md-10">
                    <a class="btn btn-info"
                       data-bind="visible: !isPendingApproval,
                                  click: $root.editDraft">
                      <i style="margin-right: 5px;" class="fa fa-pencil"></i>Edit
                    </a>
                    <a class="btn btn-info"
                       data-bind="visible: isPendingApproval,
                                  click: $root.previewDraft">
                      <i style="margin-right: 5px;" class="fa fa-pencil"></i>Preview
                    </a>
                    <button class="btn btn-danger"
                            data-bind="click: $root.deleteDraft.bind($root)">
                      <i style="margin-right: 5px;" class="fa fa-times"></i>Delete
                    </button>
                  </div>
                  <div class="col-md-1">
                    <!-- TODO(samchrisinger): pin down behavior here
                    <span data-bind="if: requiresApproval">
                      <button id="register-submit" type="button" class="btn btn-primary pull-right" data-toggle="tooltip" data-placement="top" title="Not eligible for the Pre-Registration Challenge" data-bind="click: registerWithoutReview">Register without review</button>
                    </span>
                    -->
                    <span data-bind="ifnot: requiresApproval">
                     <a class="btn btn-success" data-bind="attr: {href: urls.register_page}">Register</a>
                    </span>
                  </div>
                </div>
              </h4>
            </li>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</div>
<script type="text/html" id="createDraftRegistrationModal">
    <p>Registration creates a frozen version of the project that can never be edited or deleted but can be withdrawn. Your original project remains editable but will now have the registration linked to it. Things to know about registration:</p>
    <ul>
        <li>Ensure your project is in the state you wish to freeze before registering.</li>
        <li>Consider turning links into forks.</li>
        <li>Registrations can have embargo periods for up to four years. If you choose an embargo period, the registration will automatically become public when the embargo expires.</li>
        <li>Withdrawing a registration removes the contents of the registrations but will leave behind a log showing when the registration was created and withdrawn.</li>
    </ul>

    <p>Continue your registration by selecting a registration form:</p>
    <span data-bind="foreach: schemas">
    <div class="radio">
        <label>
          <input type="radio" name="selectedDraftSchema"
                 data-bind="attr: {value: id}, checked: $root.selectedSchemaId" />
          <span data-bind="text: schema.title"></span>
          <!-- ko if: schema.description -->
          <i data-bind="tooltip: {title: schema.description}" class="fa fa-info-circle"> </i>
          <!-- /ko -->
        </label>
    </div>
    </span>
</script>
<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script>
        window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
            pageMeta: {
                title: 'Registrations',
                public: true,
            },
        });
    </script>

    <script src=${"/static/public/js/project-registrations-page.js" | webpack_asset}> </script>
</%def>

<%include file="project/registration_preview.mako" />
<%include file="project/registration_utils.mako" />
