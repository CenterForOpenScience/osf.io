<%inherit file="base.mako"/>
<%def name="title()">${file_name}</%def>

<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div id="file-container" class="row">

    <div class="col-md-8">
      	<section>
          	<div class="page-header overflow">
              	<h1>${file_name} (current)</h1>
          	</div>
      	</section>
      	<div>
      		${rendered}
      	</div>
    </div>

</div>

</%def>
