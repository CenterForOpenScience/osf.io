<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
    <script type="text/javascript" src="/static/vendor/bower_components/MathJax/unpacked/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script> 
    <div id="shareSearch"></div>
</%def>


<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
