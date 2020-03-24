<%inherit file="base.mako"/>

<%def name="title()">
    %if waffle.switch_is_active(features.OSF_PREREGISTRATION):
        ${_("GakuNin RDM Preregistration")}
    %else:
        ${_("GakuNin RDM Prereg Challenge")}
    %endif
</%def>
<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <link rel="stylesheet" href="/static/css/registration_landing.css">
</%def>

<%def name="javascript_bottom()">
    ${ parent.javascript_bottom() }
    <script src=${"/static/public/js/reg-landing-page.js" | webpack_asset}></script>
</%def>

<%def name="newPrereg(size='')">
<div id="newPrereg${size}" class="prereg-new-prereg p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p class="reg-landing-page-text-left">${_("Please provide a title for your project:")}</p>
  <input type="text" class="new-project-title form-control" placeholder="Title">
  <button type="submit" id="newProject${size}" class="btn btn-primary pull-right m-t-md">${_("Continue")}</button>
</div>
</%def>

<%def name="existingDraft(size='')">
<div id="existingDraft${size}" class="prereg-existing-prereg p-md osf-box box-round clearfix m-b-lg" style="display:none; width: 100%;">
  <p class="reg-landing-page-text-left">${_("Go to an existing preregistration:")}</p>
    <input id="regDraftSearch${size}" class="form-control"></input>
    <div class="p-xs"><a href="#" class="regDraftButton btn btn-primary m-t-sm disabled pull-right">${_("Preregister")}</a></div>
</div>
</%def>

<%def name="existingProject(size='')">
<% size = size or '' %>
<div id="existingProject${size}" class="prereg-existing-project p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p class="reg-landing-page-text-left">${_("Preregister an existing project:")}</p>
  <input id="projectSearch${size}" class="form-control" ></input>
  <div class="p-xs"><a href="#" class="projectRegButton btn btn-primary disabled m-t-sm pull-right">${_("Preregister")}</a></div>
</div>
</%def>

<%def name="content()">
<div class="prereg-container">
    <h1 class="m-t-xl m-b-lg text-center">
        %if waffle.switch_is_active(features.OSF_PREREGISTRATION):
            <img class="reg-landing-page-logo" src="/static/img/registries/osf-prereg-red.png" alt="preregistration_logo">
        %else:
            <img class="reg-landing-page-logo" src="/static/img/registries/osf-prereg-challenge-black.png" alt="preregistration_logo">
        %endif
    </h1>
    %if waffle.switch_is_active(features.OSF_PREREGISTRATION):
        ${_("<p>Improve your research with <a %(cosPreregUrl)s>preregistration</a>. By writing out specific details such as data collection methods, analysis plans, and rules for data exclusion, you can make important decisions early on and have a clear record of these choices. This can help reduce biases that occur once the data are in front of you.</p>") % dict(cosPreregUrl="target='_blank' href='http://www.cos.io/prereg/'") | n}
        ${_("<p>Use <a %(osfRegistriesUrl)s>OSF Registries</a> to discover previously registered work.</p>") % dict(osfRegistriesUrl="target='_blank' href='https://osf.io/registries/'") | n}
    %else:
        ${_("<p><strong> Articles must be published by an <a %(preregMoreInfoUrl)s>approved</a> journal by December 31, 2018, to be eligible for a prize. Please use this this helpful workflow to preregister, even if you are not seeking a prize. </strong></p>") % dict(preregMoreInfoUrl="target='_blank' href='http://cos.io/our-services/prereg-more-information/'") | n}
        ${_("<p> Improve your research with preregistration. The process of creating a <a %(cosPreregUrl)s> preregistration</a> is beneficial to both the scientific field and to you, the scientist. By writing out detailed data collection methods, analysis plans, and rules for excluding or missing data, you can make important decisions that affect your workflow earlier, without the biases that occur once the data are in front of you.</p>") % dict(cosPreregUrl="href='http://www.cos.io/prereg'")}
    %endif
    <div class="col-md-12 visible-xs">
      %if is_logged_in:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPreregXS">${_("Start a new preregistration")}</div>
        <div class="prereg-button-content-xs">
          ${newPrereg('XS')}
        </div>
      </div>
      %else:
      <a href="${domain}login/?campaign=prereg">
          <div class="reg-landing-page-button-xs reg-landing-page-button m-b-md p-md osf-box-lt p-md box-round">${_("Preregister")}</div>
      </a>
      %endif
      %if has_draft_registrations:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingDraftXS">${_("Continue working on an existing draft preregistration")}</div>
        <div class="prereg-button-content-xs">
          ${existingDraft('XS')}
        </div>
      </div>
      %endif
      %if has_projects:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProjectXS">${_("Preregister a project you already have on the GakuNin RDM")}
        </div>
        <div class="reg-button-content-xs">
          ${existingProject('XS')}
        </div>
      </div>
      %endif
    </div>
    <div class="row hidden-xs">
      <%
          if has_draft_registrations and has_projects:
              # all three buttons
              num_cols = 3
          elif has_draft_registrations or has_projects:
              # two buttons
              num_cols = 2
          else:
              # one button
              num_cols = 1
      %>
      <table class="reg-landing-page-button-row">
        <tbody>
          <tr>
            %if is_logged_in:
            <div>
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPrereg">${_("Start a new preregistration")}</div>
            </td>
            %else:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <a href="${domain}login/?campaign=prereg">
                <div class="reg-landing-page-button m-b-md p-md osf-box-lt p-md box-round">${_("Preregister")}</div>
              </a>
            </td>
            %endif
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingDraft">${_("Continue working on an existing draft preregistration")}</div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProject">${_("Preregister a project you already have on the GakuNin RDM")}</div>
            </td>
            %endif
          </tr>
          <tr>
            ## Always displayed
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${newPrereg()}
              </div>
            </td>
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${existingDraft()}
              </div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${existingProject()}
              </div>
            </td>
            %endif
          </tr>
        </tbody>
      </table>
    </div>
</div>
<%include file="components/autocomplete.mako"/>
<script type="text/javascript">
  window.contextVars = window.contextVars || {};
  window.contextVars.campaign = ${campaign_short | sjson};
</script>
</%def>
