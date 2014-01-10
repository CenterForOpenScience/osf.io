<%inherit file="project/addon/page.mako" />

<%def name="page()">
<html>
    Viewing Bucket: <b>${bucket}</b>

    <script type="text/javascript">
        var gridData = ${grid}
    </script>

    <div id="grid">
    	<div id="s3Crumbs"></div>
		<div id="s3Grid"/></div>
	</div>
<b>
${grid}
</b>



</html>
</%def>
