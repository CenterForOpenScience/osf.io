<%inherit file="project/addon/page.mako" />
<html>
    Viewing Bucket: <b>${bucket}</b>
    <script type="text/javascript">
        var gridData = ${grid},
        can_io = ${int(user['can_edit'])},
        can_dl = 1
    </script>

                <div class="container" style="position: relative;">
                <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="s3FormUpload">click here</a>) to upload files</h3>
                <div id="fallback"></div>
                <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
                    <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
                </div>
            </div>


    <div id="grid">
    	<div id="s3Crumbs"></div>
		<div id="s3Grid"/></div>
	</div>
</html>
