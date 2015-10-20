<%inherit file="project/project_base.mako"/>

<%def name="title()">Register ${node['title']}</%def>

<%def name="content()">
    <div class="col-md-12" id="draftRegistrationScope">
        <h2>Previewing Draft Registration of ${node['title']}:</h2>
        <br/>
        <div class="span8 col-lg-12 columns twelve large-12" style="padding-left: 30px">
            <div data-bind="foreach: {data: draft.schema().pages, as: 'page'}">
                <h3 data-bind="attr.id: page.id, text: page.title"></h3>
                <div data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                    <span data-bind="with: $parent.questions[qid]">
                        <h4 data-bind="attr.id: qid, text: title"></h4>
                        <!-- ko if: value -->
                        <span data-bind="text: value"></span>
                        <!-- /ko -->
                    </span>
                </div>
            </div>
        </div>

        <a type="button" class="btn btn-default pull-left" href="${draft['urls']['edit']}">Continue editing</a>

        <span data-bind="if: draft.metaSchema.name === 'Prereg Challenge'" >
          <a type="button" class="btn btn-success pull-right" data-bind="click: submitForReview">Submit to the Pre-Registration Challenge</a>
          <button id="register-submit" type="button" class="btn btn-primary pull-right" data-toggle="tooltip" data-placement="top" title="Not eligible for the Pre-Registration Challenge" data-bind="click: registerDraft">Register without review</button>
        </span>

        <span data-bind="ifnot: draft.metaSchema.name === 'Prereg Challenge'">
            <button id="register-submit" type="button" class="btn btn-primary pull-right" data-bind="click: registerDraft">Register immediately</button>
            <button id="register-submit" type="button" class="btn btn-primary pull-right" data-bind="click: submitForReview, visible: draft.requiresApproval"">Submit for review</button>
         </span>
</%def>

<%def name="javascript_bottom()">

    <script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.draft = ${draft | sjson, n};
  </script>
  <script src=${"/static/public/js/register-page.js" | webpack_asset}></script>
</%def>
