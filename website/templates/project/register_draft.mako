<%inherit file="project/project_base.mako"/>

<%def name="title()">Register ${node['title']}</%def>

<div id="draftRegistrationScope">
    <div class="row">
        <div class="col-md-12">
            <h3>Register</h3>
        </div>
    </div>
    <hr>
    <div class="row">
      <div class="col-lg-12 large-12" style="padding-left: 30px">
         <div data-bind="foreach: {data: draft.pages, as: 'page'}">
           <h3 data-bind="attr: {id: page.id}, text: page.title"></h3>
             <div data-bind="foreach: {data: page.questions, as: 'question'}">
               <p>
                 <strong data-bind="attr: {id: question.id}, text: question.title"></strong>:
                 <span data-bind="previewQuestion: $root.editor.context(question, $root.editor)"></span>
               </p>
             </div>
            </div>
        </div>
    </div>
    <div class="row-md-12 scripted">
        <span data-bind="ifnot: draft.isPendingApproval">
          <a type="button" class="btn btn-default pull-left" href="${draft['urls']['edit']}">Continue editing</a>

          <button id="register-submit" type="button" class="btn btn-success pull-right"
                  style="margin-left: 5px;"
                  data-bind="visible: draft.requiresApproval,
                             click: draft.submitForReview.bind(draft),
                             enable: editor.canSubmit">
            Submit for review
          </button>
        </span>
        <span data-bind="if: draft.isPendingApproval">
          <a type="button" class="btn btn-default pull-left" href="${web_url_for('node_registrations', pid=node['id'], tab='drafts')}"> Back </a>
        </span>

        <span data-bind="if: draft.metaSchema.name === 'Prereg Challenge'">
          <button id="register-submit" type="button" class="btn btn-primary pull-right" data-toggle="tooltip" data-placement="top" title="Not eligible for the Pre-Registration Challenge" data-bind="click: draft.registerWithoutReview.bind(draft)">Register without review</button>
        </span>

        <button id="register-submit" type="button" class="btn btn-success pull-right"
                style="margin-left: 5px;"
                data-bind="visible: !draft.requiresApproval(), click: draft.beforeRegister.bind(draft, null)">
          Register
        </button>
    </div>
</div>

<%include file="project/registration_utils.mako" />
<%include file="project/registration_editor_extensions.mako" />

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.draft = ${draft | sjson, n};
  </script>
  <script src=${"/static/public/js/register-page.js" | webpack_asset}></script>
</%def>
