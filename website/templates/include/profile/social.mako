<script id="profileSocial" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit">

            <label>Your websites</label>
            <div data-bind="sortable: {
                        data: profileWebsites,
                        options: {
                            handle: '.sort-handle',
                            containment: '#containDrag'
                        }
                    }">

                <div>
                    <div class="sort-handle">
                        <i title="Click to remove" class="btn text-danger pull-right  fa fa-times fa" data-bind="click: $parent.removeWebsite"></i>
                        <div class="input-group" >
                            <span class="input-group-addon"><i title="Drag to reorder"  class="fa fa-bars"></i></span>
                            <input class="form-control" data-bind="value: $parent.profileWebsites()[$index()]" placeholder="http://yourwebsite.com"/>
                        </div>
                    </div>
                    <div class="form-group" data-bind="visible: $index() != ($parent.profileWebsites().length - 1)">
                    </div>
                </div>
            </div>

            <div class="p-t-sm p-b-sm">
                <a class="btn btn-default" data-bind="click: addWebsiteInput">
                    Add website
                </a>
            </div>

            <div class="form-group">
                <label>ORCID</label>
                <div class="input-group">
                <span class="input-group-addon">http://orcid.org/</span>
                <input class="form-control" data-bind="value: orcid" placeholder="xxxx-xxxx-xxxx-xxxx"/>
                </div>
            </div>

            <div class="form-group">
                <label>ResearcherID</label>
                <div class="input-group">
                <span class="input-group-addon">http://researcherid.com/rid/</span>
                <input class="form-control" data-bind="value: researcherId" placeholder="x-xxxx-xxxx" />
                </div>
            </div>

            <div class="form-group">
                <label>Twitter</label>
                <div class="input-group">
                <span class="input-group-addon">@</span>
                <input class="form-control" data-bind="value: twitter" placeholder="twitterhandle"/>
                </div>
            </div>

            <div class="form-group">
                <label>GitHub</label>
                <div class="input-group">
                    <span class="input-group-addon">https://github.com/</span>
                    <input class="form-control" data-bind="value: github" placeholder="username"/>
                    <span class="input-group-btn" data-bind="if: github.hasAddon()">
                        <button
                                class="btn btn-primary"
                                data-bind="click: github.importAddon"
                                >Import</button>
                     </span>
                </div>
            </div>

            <div class="form-group">
                <label>LinkedIn</label>
                <div class="input-group">
                <span class="input-group-addon">https://www.linkedin.com/</span>
                <input class="form-control" data-bind="value: linkedIn" placeholder="in/userID, profile/view?id=profileID, or pub/pubID"/>
                </div>
            </div>

            <div class="form-group">
                <label>ImpactStory</label>
                <div class="input-group">
                <span class="input-group-addon">https://impactstory.org/</span>
                <input class="form-control" data-bind="value: impactStory" placeholder="profileID"/>
                </div>
            </div>

            <div class="form-group">
                <label>Google Scholar</label>
                <div class="input-group">
                <span class="input-group-addon">http://scholar.google.com/citations?user=</span>
                <input class="form-control" data-bind="value: scholar" placeholder="profileID"/>
                </div>
            </div>

            <div class="p-t-lg p-b-lg">

                <button
                        type="button"
                        class="btn btn-default"
                        data-bind="click: cancel"
                    >Discard changes</button>

                <button
                        type="submit"
                        class="btn btn-success"
                    >Save</button>

            </div>

            <!-- Flashed Messages -->
            <div class="help-block">
                <p data-bind="html: message, attr.class: messageClass"></p>
            </div>

        </form>

    </div>

    <div data-bind="if: mode() === 'view'">

        <table class="table" data-bind="if: hasValues()">
            <tbody>
                <tr data-bind="if: hasProfileWebsites()">
                    <td data-bind="visible: profileWebsites().length > 1">Personal websites</td>
                    <td data-bind="visible: profileWebsites().length === 1">Personal website</td>
                    <td data-bind="foreach: profileWebsites"><a target="_blank" data-bind="attr.href: $data">{{ $data }}</a></br></td>
                </tr>
            </tbody>

            <tbody data-bind="foreach: values">
                <tr data-bind="if: value">
                    <td>{{ label }}</td>
                    <td><a target="_blank" data-bind="attr.href: value">{{ text }}</a></td>
                </tr>
            </tbody>
        </table>

        <div data-bind="ifnot: hasValues()">
            <div class="well well-sm">Not provided</div>
        </div>

        <div data-bind="if: editAllowed">
            <a class="btn btn-primary" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
