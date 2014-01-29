<link href="${STATIC_PATH}/css/pygments.css" rel="stylesheet">
<link href="${STATIC_PATH}/css/style.min.css" rel="stylesheet">
<link href="${STATIC_PATH}/css/theme/${css_theme}.css" rel="stylesheet">


<style type="text/css">
    .imgwrap {
        text-align: center;
    }
    .input_area {
        padding: 0.4em;
    }
    div.input_area > div.highlight > pre {
        margin: 0px;
        padding: 0px;
        border: none;
    }
</style>

${ body | n }


<script type="text/javascript">
    (function() {
    if (window.MathJax) {
        // MathJax loaded
        MathJax.Hub.Config({
            tex2jax: {
                inlineMath: [ ['$','$'], ["\\(","\\)"] ],
                displayMath: [ ['$$','$$'], ["\\[","\\]"] ]
            },
            displayAlign: 'left', // Change this to 'center' to center equations.
            "HTML-CSS": {
                styles: {'.MathJax_Display': {"margin": 0}}
            }
        });
        MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
    }
})();
</script>

<script src="${STATIC_PATH}/js/mathjax.js"type="text/javascript"></script>