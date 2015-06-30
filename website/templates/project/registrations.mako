<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<ul id="registrationsTabs" class="nav nav-tabs" role="tablist">
  <li role="presentation" class="active">
    <a id="registrationsControl" aria-controls="registrations" href="#registrations">Registrations</a>
  </li>
  <li role="presentation">
    <a id="draftsControl" aria-controls="drafts" href="#drafts">Draft Registrations</a>
  </li>
  <li role="presentation">
    <a id="editDraftsControl" class="disabled" aria-controls="editDrafts" href="#editDrafts">Edit Draft</a>
  </li>   
</ul>
<div class="tab-content registrations-view">
  <div role="tabpanel" class="tab-pane active" id="registrations">
    <div class="row" style="min-height: 150px">
      <h2> Registrations </h2>
      <div class="col-md-9">
        % if node["registration_count"]:
        <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_registrations/",
            "replace": true,
            "kwargs": {"sortable": false, "pluralized_node_type": "registrations"}
            }'></div>
    ## Uncomment to disable registering Components
    ##% elif node['node_type'] != 'project':
    ##      %if user['is_admin_parent']:
    ##          To register this component, you must <a href="${parent_node['url']}registrations"><b>register its parent project</b></a> (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %else:
    ##          There have been no registrations of the parent project (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %endif
        % else:
        <p>
          There have been no completed registrations of this ${node['node_type']}.
          For a list of the most viewed and most recent public registrations on the
          Open Science Framework, click <a href="/explore/activity/#newPublicRegistrations">here</a>,
          or you start a new draft registration from the "Draft Registrations" tab.
        </p>
        % endif
        %if parent_node['exists'] and user['is_admin_parent']:
        <br />
        <br />
        To register the entire project "${parent_node['title']}" instead, click <a href="${parent_node['registrations_url']}">here.</a>
        %endif         
      </div>
    </div>
  </div>
  <div role="tabpanel" class="tab-pane" id="drafts">
    <div id="draftRegistrationScope" class="row" style="min-height: 150px">
      <h2> Draft Registrations </h2>
      <div class="col-md-9">
      <div>
        % if 'admin' in user['permissions'] and not disk_saving_mode:
        <a data-bind="css: {disabled: loading}" id="registerNode" class="btn btn-default" type="button">
          <i class="fa fa-plus"></i>
          New Draft Registration
        </a>
        % endif
      </div>    
      <br />
      <div class="scripted" data-bind="foreach: drafts">
        <li class="project list-group-item list-group-item-node">
          <h4 class="list-group-item-heading">          
            <div class="progress progress-bar-md">
              <div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100"
               data-bind="attr.aria-completion: completion,
                          style: {width: completion + '%'}">
                <span class="sr-only"></span>
              </div>
            </div>
            <p data-bind="text: schema.title"></p>
            <p>initiated by <span data-bind="text: initiator.fullname"></span>
            <p>started about <span data-bind="text: $root.formattedDate(initiated)"></span></p>
            <p>last updated about <span data-bind="text: $root.formattedDate(updated)"></span></p>
            <p>
              <button class="btn btn-success"
                      data-bind="click: $root.editDraft"><i class="fa fa-pencil"></i>Edit</button>
              <button class="btn btn-danger"
                      data-bind="click: $root.deleteDraft"><i class="fa fa-times"></i>Delete</button>
            </p>
          </h4>
        </li>
      </div>
    </div>
    </div>
  </div>  
  <div role="tabpanel" class="tab-pane" id="editDrafts">
    <div class="row">
      <h2> Edit Draft Registration </h2>
      <div class="col-md-12">
        <%include file="project/registration_editor.mako"/>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/project-registrations-page.js" | webpack_asset}> </script>
</%def>
<script type="text/html" id="preRegisterMessageTemplate">
  <div
  <!-- if not a top-level Node -->
  <div data-bind="if: parentUrl">
    You are about to register the 
    <span data-bind="text: category"></span>  
    <b data-bind="text: title"></b> 
    including all components and data within it. This will <b>not</b> register its parent, 
    <b data-bind="text: parentTitle"></b>. If you want to register the parent, please go 
    <a data-bind="attr.href: parentUrl">here.</a>
    After selecting OK, you will next select a registration form.
  </div>
  <!-- if root Node -->
  <div data-bind="ifnot: parentUrl">
    You are about to register <b data-bind="text: title"></b>
    including all components and data within it. Registration creates a permanent, 
    time-stamped, uneditable version of the project. If you would prefer to register 
    only one particular component, please navigate to that component and then initiate registration. 
  </div>
  <br />
  <div class="form-group">
    <label>Please select a registration schema to continue:</label>
    <br />
    <div data-bind="foreach: schemas">
      <div class="panel-group" id="accordion" role="tablist" aria-multiselectable="true">
        <div class="panel panel-default">
          <div class="panel-heading" role="tab" data-bind="attr.id: id">            
            <h3 class="panel-title">
              <div class="row">
                <div class="col-md-9">
                  <span role="button" data-toggle="collapse" data-parent="#accordion" aria-expanded="true"
                     data-bind="text: name,
                                attr.aria-controls: id + '-collapse',
                                attr.href: id + '-collapse'">
                  </span>
                </div>
                <div class="col-md-1">
                  <button data-bind="click: $root.launchEditor.bind($root, null, $data)" class="btn btn-primary">Use</button>
                </div>
              </div>
            </h3>
          </div>
          <div class="panel-collapse collapse in p-md" role="tabpanel" data-bind="attr.id: id + '-collapse', 
                                                                             attr.aria-labelledby: id">
            <h4> Fulfills: </h4>
            <div class="btn-group" data-bind="foreach: schema.fulfills">
              <!-- TODO badges?; definitely improve UI here -->
              <span data-bind="text: $data"></span>
            </div>
            <hr />
            <h4> Description: </h4>
            <p data-bind="html: schema.description"></p>
            <!--
            <div data-bind="foreach: {data: schema.pages, as: 'page'}">
              <h4 data-bind="text: page.title"></h4>
              <ul data-bind="foreach: {data: page.questions, as: 'question'}">
                <li data-bind="question.nav"></li>
              </ul>
            </div>
            -->
          </div>
        </div>
      </div>
    </div>
  </div>
  <hr />
  <div class="form-group" style="text-align: right">
    <button class="btn btn-default" data-bind="click: cancel">Cancel</button>
  </div>
</script>
