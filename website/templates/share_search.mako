<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <div id="shareSearch"></div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>

<script type="text/x-mathjax-config">
   MathJax.Hub.Config({
       tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']], processEscapes: true}
    });
</script>

<script type="text/javascript"
    src="/static/vendor/bower_components/MathJax/unpacked/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>

</%def>

