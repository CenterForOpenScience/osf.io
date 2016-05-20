<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <script type="text/javascript" src="/static/vendor/bower_componenets/MathJax/unpacked/MathJax.js?configi=TeX-AMS-MML_HTMLorMML"></script>
  <script type='text/javascript'>
    window.MathJax.Hub.Config({
      tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']]}
    });
  </script>  
  <div id="shareSearch"></div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
