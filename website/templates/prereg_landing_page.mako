<%inherit file="base.mako"/>

<%def name="title()">OSF Prereg Challenge</%def>

<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <link rel="stylesheet" href="/static/css/prereg.css">
</%def>

<%def name="javascript_bottom()">
    ${ parent.javascript_bottom() }
    <script src=${"/static/public/js/prereg-landing-page.js" | webpack_asset}></script>
</%def>

<%def name="content()">
<div class="prereg-container">
    <h1 class="m-t-xl m-b-lg text-center">Welcome to the Preregistration Challenge!</h1>
    <p>The process of <a href="http://www.cos.io/prereg">pre-registering </a> your plans is beneficial to both the scientific field and to you, the scientist. By writing out detailed data collection methods, analysis plans, and rules for excluding or missing data, you can make important decisions that affect your workflow earlier, without the biases that occur once the data are in front of you.</p>
    <p class="m-t-lg f-w-lg">Ready for the Challenge?</p>
    <p>
        <ol>
            <li>Specify all your study and analysis decisions prior to investigating your data</li>
            <li>Publish your study in an eligible journal</li>
            <li>Receive $1,000</li>
        </ol>
    </p>
    <div class="row prereg-button-row m-v-lg">
        <%
            if has_draft_registrations and has_projects:
                # all three buttons
                option_columns = 4
                options_offset = 0
            elif has_draft_registrations or has_projects:
                # two buttons
                option_columns = 5
                options_offset = 1
            else:
                # one button
                option_columns = 6
                options_offset = 3
        %>
        ## Always displayed
        <div class="col-sm-${ option_columns } col-sm-offset-${ options_offset }">
            <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPrereg">Start a new preregistration</div>
            <div id="newPrereg" class="p-md osf-box box-round clearfix m-b-lg" style="display:none">
              <p>Please provide a title for your project: </p>
              <input type="text" id="newProjectTitle" class="form-control" placeholder="Title">
              <button type="submit" id="newProject" class="btn btn-primary pull-right m-t-md">Continue <i class="fa fa-angle-right"></i></button>
            </div>
        </div>
        %if has_draft_registrations:
        <div class="col-sm-${ option_columns }">
            <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingPrereg">Continue working on an existing preregistration</div>
            <div id="existingPrereg" class="p-md osf-box box-round clearfix m-b-lg" style="display:none">
              <p>Go to an existing preregistration:</p>
                <form>
                  <osf-draft-registrations-search
                     params="data: '/api/v1/prereg/draft_registrations/',
                             submitText: 'Edit draft'">
                    </osf-draft-registrations-search>
                </form>
            </div>
        </div>
        %endif
        %if has_projects:
        <div class="col-sm-${ option_columns }">
            <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProject">Preregister a project you already have on the OSF</div>
            <div id="existingProject" class="p-md osf-box box-round clearfix m-b-lg" style="display:none">
                <p>Preregister an existing project:</p>
                <osf-project-search
                    params="data: nodes,
                            onSubmit: function(selected) { window.location = selected.urls.register; },
                            enableComponents: false,
                            submitText: 'Preregister'">
                </osf-project-search>
            </div>
        </div>
        %endif
    </div>
</div>
<%include file="components/dashboard_templates.mako"/>
<%include file="components/autocomplete.mako"/>
</%def>
