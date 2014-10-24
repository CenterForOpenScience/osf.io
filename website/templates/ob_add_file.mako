<!-- start #ob-AddFile -->
<li class="ob-list list-group-item">
    <div class="row">
        <div class="col-md-12">
            <h3>Upload a file</h3>
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            <h4>1. Drop file (or click below)</h4>
            <div id="obDropzoneError" class="ob-reveal"></div>
            <div id="obDropzone" class="ob-dropzone-box pull-left"></div>
            <div id="obDropzoneSelected" class="ob-dropzone-box ob-reveal pull-left">
                <img id="uploadIcon" src="//:0">
                <div id="obDropzoneFilename"></div>
                <progress class="ob-reveal" id="uploadProgress" max="100" value="0"></progress>
                <img class="ob-clear-button" id="clearDropzone" src="/static/img/close2.png">
            </div>
        </div>
    </div><!-- end row -->

    <div id="obDropzoneReveal">
        <div class="row">
            <div class="col-md-12">
                <h4> 2. Select a project</h4>
                <div class="ob-search" class="projectSearchAddFile" >
                    <img class="ob-clear-button ob-reveal" id="clearInputProjectAddFile" src="/static/img/close2.png">
                    <input class="typeahead" type="text" placeholder="Type to search"
                     id='inputProjectAddFile'>
                </div>
            </div>
        </div><!-- end row -->

        <div class="row">
            <div class="col-md-12">
                <h4>3. Select a component (optional)</h4>
                <div class="ob-search" class="projectSearchAddFile">
                    <img class="ob-clear-button ob-reveal" id="clearInputComponentAddFile" src="/static/img/close2.png">
                    <input class="typeahead" disabled="disabled" type="text" placeholder="First select a project" id='inputComponentAddFile'>
                </div>
                <span class="findBtn btn btn-primary pull-right" id="addLinkAddFile" disabled="disabled">Upload</span>
                <span class="findBtn btn btn-primary pull-right" id="fakeAddLinkAddFile" disabled="disabled">Upload</span>
            </div>
        </div>
    </div>
</li> <!-- end #ob-AddFile" -->
