<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <div id="shareSearch"></div>
  <style>
    @font-face {
      font-family: yanonekaffeesatz;
      src: url(/static/css/font/share/YanoneKaffeesatz-Regular.ttf);
      font-weight: 400;

    }

    .about-share-header {
      color: lightgrey;
      text-align: center;
      font-family: yanonekaffeesatz;
      -webkit-animation-delay: 0.5s;
    }

    .share-search-input:focus {
      outline: 0 !important;
      box-shadow: none;
      border-bottom-style: solid;
      border-bottom-width: medium;
      border-bottom-color: lightgrey;
      border-bottom-left-radius: 5px;
    }

    .share-search-input {
      background: none;
      border: none;
      box-shadow: none;
      border-bottom: 1px dotted #FFF;
      border-radius: 0;
      padding: 0 0;
      font-size: 20px;
      color: #214762;
      font-weight: 300;
      border-bottom-style: solid;
      border-bottom-width: medium;
      border-bottom-color: lightgrey;
      border-bottom-left-radius: 5px;
    }

    .stats-expand:hover {
      background: -webkit-gradient(linear, 50% 0%, 50% 100%, color-stop(0%, #fff), color-stop(100%, #f9f9f9));
      background: -moz-linear-gradient(top, #fff, #f9f9f9);
      background: -webkit-linear-gradient(top, #fff, #f9f9f9);
      background: linear-gradient(to bottom, #fff, #f9f9f9);
      color: #333;
      text-decoration: none;
      border-color: #c0c0c0
  }

    ## .stats-expand:before {
    ##     content: "";
    ##     position: absolute;
    ##     bottom: -1px;
    ##     left: -1px;
    ##     right: -1px;
    ##     height: 1.462rem;
    ##     -moz-box-shadow: 0 -10px 10px -7px #c8c8c8;
    ##     -webkit-box-shadow: 0 -10px 10px -7px #c8c8c8;
    ##     box-shadow: 0 -10px 10px -7px #c8c8c8
    ## }

    .stats-expand {
      -moz-box-sizing: border-box;
      -webkit-box-sizing: border-box;
      box-sizing: border-box;
      display: block;
      position: relative;
      width: 100%;
      height: 19px;
      margin-bottom: 0px;
      background-color: inherit;
      text-align: center;
      color: #777;
      border: 1px solid transparent;
      ## border-top-color: #e4e4e4
    }
  </style>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
