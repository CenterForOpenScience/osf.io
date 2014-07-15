<ul> <!-- start onboarding -->

                <!-- start #obNewProject -->
                <li id="obNewProject" class="ob-list list-group-item">
                    <div id="obNewProjectBtn" class="ob-reveal-btn ob-unselectable">
                        <h3 class="ob-heading">Create a new project</h3>
                        <img class="ob-expand-icon pull-right" id="obIconNewProject" src="/static/img/plus.png">
                    </div><!-- end .obNewProjectBtn -->

                    <div class="ob-reveal" id="obRevealNewProject">
                        <br> 
                        <%include file="project/new_project_form.mako"/>
                    </div>
                </li> <!-- end #obNewProject" -->

                <!-- start #obRegisterProject -->
                <li id="obRegisterProject" class="ob-list list-group-item"> 
                    <div id="obRegisterProjectBtn" class="ob-unselectable">
                        <h3 class="ob-heading" >Register a project or component</h3>
                        <img class="ob-expand-icon pull-right" id="obIconRegisterProject" src="/static/img/plus.png">
                    </div><!-- end #obInputProject-btn -->

                    <div class="ob-reveal" id="obRevealRegisterProject">
                        <div class="row">
                            <div class="col-md-12" >
                                <h4>1. Select Project</h4>
                                <div style="position:relative;" class="projectSearchRegisterProject">
                                    <img class="ob-clear-button ob-reveal" id="clearInputProjectRegisterProject" src="/static/img/close2.png">
                                    <input class="typeahead" type="text" placeholder="Type to search" id = 'inputProjectRegisterProject'>
                                </div> <!-- end #projectSearchRegisterProject -->
                            </div>
                        </div><!-- end row -->

                        <div class="row">
                            <div class="col-md-12">
                                <h4>2. (Optional) Select a component</h4>
                                <div style="position:relative;" id="projectSearchRegisterProject">
                                    <img class="ob-clear-button ob-reveal" id="clearInputComponentRegisterProject" src="/static/img/close2.png">
                                    <input class="typeahead" type="text" placeholder="Type to search" disabled="disabled" id = 'inputComponentRegisterProject'>
                                </div> <!-- end #projectSearchRegisterProject -->

                                <span class="findBtn btn btn-default pull-right" id="addLinkRegisterProject" disabled="disabled">Go to registration page</span>
                            </div>
                        </div>
                    </div>
                </li> <!-- end #obInputProject" -->

                <!-- start #ob-AddFile -->
                <li class="ob-list list-group-item">
                    <div class="row">
                        <div class="col-md-12">
                            <h3>Add a file to a project</h3>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-12">
                            <h4>1. Drop file (or click below)</h4>
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
                                <div style="position:relative;" class="projectSearchAddFile" >
                                    <img class="ob-clear-button ob-reveal" id="clearInputProjectAddFile" src="/static/img/close2.png">
                                    <input class="typeahead" type="text" placeholder="Type to search"
                                     id='inputProjectAddFile'>
                                </div>
                            </div>
                        </div><!-- end row -->

                        <div class="row">
                            <div class="col-md-12">
                                <h4>3. (optional) Select a component</h4>
                                <div style="position:relative;" class="projectSearchAddFile">
                                    <img class="ob-clear-button ob-reveal" id="clearInputComponentAddFile" src="/static/img/close2.png">         
                                    <input class="typeahead" disabled="disabled" type="text" placeholder="Type to search" id='inputComponentAddFile'>
                                </div>
                                <span class="findBtn btn btn-default pull-right" id="addLinkAddFile" disabled="disabled">Upload</span>
                                <span class="findBtn btn btn-default pull-right" id="fakeAddLinkAddFile" disabled="disabled">Upload</span>
                            </div>
                        </div>
                    </div>
                </li> <!-- end #ob-AddFile" -->

            </ul> <!-- end onboarding -->