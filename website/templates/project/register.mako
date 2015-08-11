<%inherit file="project/project_base.mako"/>
<%def name="title()">Register ${node['title']}</%def>

<legend class="text-center">Register</legend>

% if node.get('registered_schema'):
  <div id="registrationMetaDataScope" class="container scripted">
    <div class="row">
      <div class="span8 col-md-2 columns eight large-8">        
        <ul class="nav nav-stacked list-group" data-bind="foreach: {data: metaSchema.schema.pages, as: 'page'}">
          <li class="re-navbar">
            <a class="registration-editor-page" id="top-nav" style="text-align: left; font-weight:bold;" data-bind="text: title, attr.href: '#' + page.id">
            </a>
            <span class="btn-group-vertical" role="group">
              <ul class="list-group" data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                <span data-bind="with: page.questions[qid]">
                  <li class="registration-editor-question list-group-item">
                    <a data-bind="text: nav, attr.href: '#' + qid"></a>
                  </li>
                </span>
              </ul>
            </span>
          </li>
        </ul>
      </div>
      <div class="span8 col-md-9 columns eight large-8" style="padding-left: 30px">
        <div data-bind="foreach: {data: metaSchema.schema.pages, as: 'page'}">
          <h3 data-bind="attr.id: page.id, text: page.title"></h3>
          <div class="row">
            <div data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
              <div class="row" data-bind="with: $parent.questions[qid]">
                <h4 data-bind="attr.id: qid, text: title"></h4>
                <small><em data-bind="text: description"></em></small>
                <div class="col-md-12 well" data-bind="text: $root.schemaData[qid].value"></div>
              </div>
            </div>              
          </div>
        </div>
      </div>
    </div>
  </div>  
% else:
    <script type="text/javascript">
      window.location.href = '${node.url}' + 'registrations/';
    </script>
% endif

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % if node.get('registered_schema'):
      <script src="${'/static/public/js/register-page.js' | webpack_asset}"></script>
    % endif
</%def>
