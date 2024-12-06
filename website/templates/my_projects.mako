<%inherit file="base.mako"/>
<%def name="title()">${_("My Projects")}</%def>

<%def name="container_class()">container-xxl</%def>

<%def name="content()">
% if disk_saving_mode:
    <div class="alert alert-info alert-flat">${_("<strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the GakuNin RDM undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>") | n}
% endif


  <div id="dashboard" class="dashboard clearfix" >
    <div class="ball-scale ball-scale-blue text-center m-v-xl"><div></div></div>
  </div>

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/my-projects.css">
    <link rel="stylesheet" href="/static/css/pages/dashboard-page.css">
</%def>

<%def name="javascript_bottom()">
<script src=${"/static/public/js/dashboard-page.js" | webpack_asset}></script>

<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        storageRegions: ${ storage_regions | sjson, n },
        storageFlagIsActive: ${ storage_flag_is_active | sjson, n },
        canCreateProject: ${ can_create_project | sjson, n}
    });
</script>
</%def>
