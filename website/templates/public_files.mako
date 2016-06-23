<%inherit file="base.mako"/>
<%def name="title()"> ${node['ownerName']}'s Public Files</%def>

<%def name="og_description()">
    Hosted on the Open Science Framework


</%def>

## To change the postion of alert on project pages, override alert()
<%def name="alert()"> </%def>

<%def name="content()">
<div class="page-header  visible-xs">
</div>
    <h2 class="text-center"> ${node['ownerName']}'s Public Files</h2>

<div id="treeGrid">
	<div class="spinner-loading-wrapper">
		<div class="logo-spin logo-lg"></div>
		<p class="m-t-sm fg-load-message"> Loading files...  </p>
	</div>
</div>
<style>
.container {
    width: 100% !important;
}

</style>





</%def>

<%def name="javascript_bottom()">

<script src="/static/vendor/citeproc-js/xmldom.js"></script>
<script src="/static/vendor/citeproc-js/citeproc.js"></script>

<script>

    ## $script(['/static/addons/badges/badge-awarder.js'], function() {
    ##     attachDropDown('${'{}badges/json/'.format(user_api_url)}');
    ## });

    window.contextVars = $.extend(true, {}, window.contextVars, {
         nodeId : ${ node['id'] |sjson, n },
         userApiUrl : ${ user_api_url | sjson, n },
         nodeApiUrl : ${ node['api_url'] | sjson, n },
         isPublicFilesCol : ${node['isPublicFilesCol']  | sjson, n },
     });


</script>
<script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']], processEscapes: true},
        // Don't automatically typeset the whole page. Must explicitly use MathJax.Hub.Typeset
        skipStartupTypeset: true
    });
</script>
<script type="text/javascript"
    src="/static/vendor/bower_components/MathJax/unpacked/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>
<script src=${"/static/public/js/publicfiles-page.js" | webpack_asset}></script>



<script src=${"/static/public/js/project-base-page.js" | webpack_asset}> </script>
</%def>
