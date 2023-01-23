<script id="profileSocial" type="text/html">

    <link rel="stylesheet" href='/static/css/pages/profile-page.css'>
    <link rel="stylesheet" href="/static/vendor/bower_components/academicons/css/academicons.css"/>

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
                            <input type="url" class="form-control" data-bind="value: $parent.profileWebsites()[$index()]" placeholder="http://yourwebsite.com"/  aria-label="personal website input" >
                        </div>
                    </div>
                    <div class="form-group" data-bind="visible: $index() != ($parent.profileWebsites().length - 1)">
                    </div>
                </div>
            </div>
            <div data-bind="ifnot: hasValidWebsites" class="text-danger">Please enter a valid website</div>
            <div class="p-t-sm p-b-sm">
                <a class="btn btn-default" data-bind="click: addWebsiteInput">
                    Add website
                </a>
            </div>

            <div class="form-group">
                <label>ORCID</label>
                <div class="input-group">
                <span class="input-group-addon">http://orcid.org/</span>
                <input class="form-control" data-bind="value: orcid" placeholder="xxxx-xxxx-xxxx-xxxx" aria-label="ORCID input" />
                </div>
            </div>

            <div class="form-group">
                <label>ResearcherID</label>
                <div class="input-group">
                <span class="input-group-addon">http://researcherid.com/rid/</span>
                <input class="form-control" data-bind="value: researcherId" placeholder="x-xxxx-xxxx" aria-label="ResearcherID username input" />
                </div>
            </div>

            <div class="form-group">
                <label>Twitter</label>
                <div class="input-group">
                <span class="input-group-addon">@</span>
                <input class="form-control" data-bind="value: twitter" placeholder="twitterhandle" aria-label="Twitter username input" />
                </div>
            </div>

            <div class="form-group">
                <label>GitHub</label>
                <div class="input-group">
                    <span class="input-group-addon">https://github.com/</span>
                    <input class="form-control" data-bind="value: github" placeholder="username" aria-label="github username input" />
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
                <input class="form-control" data-bind="value: linkedIn" placeholder="in/userID, profile/view?id=profileID, or pub/pubID" aria-label="LinkedIn input" />
                </div>
            </div>

            <div class="form-group">
                <label>ImpactStory</label>
                <div class="input-group">
                <span class="input-group-addon">https://impactstory.org/u/</span>
                <input class="form-control" data-bind="value: impactStory" placeholder="profileID" aria-label="ImpactStory input" />
                </div>
            </div>

            <div class="form-group">
                <label>Google Scholar</label>
                <div class="input-group">
                <span class="input-group-addon">http://scholar.google.com/citations?user=</span>
                <input class="form-control" data-bind="value: scholar" placeholder="profileID" aria-label="Google Scholar information input" />
                </div>
            </div>

            <div class="form-group">
                <label>ResearchGate</label>
                <div class="input-group">
                <span class="input-group-addon">https://researchgate.net/profile/</span>
                <input class="form-control" data-bind="value: researchGate" placeholder="profileID" aria-label="ResearchGate information input" />
                </div>
            </div>

            <div class="form-group">
                <label>Academia</label>
                <div class="input-group">
                <span class="input-group-addon">https://</span>
                <input class="form-control" data-bind="value: academiaInstitution" placeholder="institution" size="5"/>
                <span class="input-group-addon">.academia.edu/</span>
                <input class="form-control" data-bind="value: academiaProfileID" placeholder="profileID" aria-label="Academia information input" />
                </div>
            </div>

            <div class="form-group">
                <label>Baidu Scholar</label>
                <div class="input-group">
                <span class="input-group-addon">http://xueshu.baidu.com/scholarID/</span>
                <input class="form-control" data-bind="value: baiduScholar" placeholder="profileID" aria-label="Baidu Scholar id input" />
                </div>
            </div>

            <div class="form-group">
                <label>SSRN</label>
                <div class="input-group">
                <span class="input-group-addon">http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=</span>
                <input class="form-control" data-bind="value: ssrn" placeholder="profileID" aria-label="ssrn information input" />
                </div>
            </div>

            <div class="p-t-lg p-b-lg">

                <button
                        type="button"
                        class="btn btn-default"
                        data-bind="click: cancel"
                    >Discard changes</button>

                <button
                        data-bind="disable: saving(), text: saving() ? 'Saving' : 'Save'"
                        type="submit"
                        class="btn btn-success"
                    >Save</button>
            </div>

            <!-- Flashed Messages -->
            <div class="help-block flashed-message">
                <p data-bind="html: message, attr: {class: messageClass}"></p>
            </div>


        </form>

    </div>

    <div data-bind="if: mode() === 'view'">
        <table class="table social-links" data-bind="if: hasValues()">
            <tbody>
                <tr data-bind="if: hasProfileWebsites()">
                    <td><span><i class='fa fa-globe fa-2x'/></span></td>
                    <td data-bind="visible: profileWebsites().length > 1">Personal websites</td>
                    <td data-bind="visible: profileWebsites().length === 1">Personal website</td>
                    <td data-bind="foreach: profileWebsites"><a rel="nofollow" data-bind="attr: {href: $data}, text: $data"></a><br></td>
                </tr>
            </tbody>

            <tbody data-bind="foreach: values">
                <tr data-bind="if: value">
                    <td><a target="_blank" ="" data-bind="attr: {href: value, 'aria-label': 'Link to user ' + label}"><span data-bind="html: iconName(label)"></span></a></td>
                    <td><span data-bind="text: label"></span></td>
                    <td><a target="_blank" data-bind="attr: {href: value}, text: text"></a></td>
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
<script>
iconName = function(name) {
    var nameToHtml = {
        "ORCID": "<i class='ai ai-orcid-square ai-2x' />",
        "ResearcherID": "<img src='http://tguillerme.github.io/images/logo-RID.png' class='icon-image'>",
        "Twitter": "<i class='fa fa-twitter-square fa-2x' />",
        "GitHub": "<i class='fa fa-github-square fa-2x' />",
        "LinkedIn": "<i class='fa fa-linkedin-square fa-2x' />",
        "ImpactStory": "<i class='ai ai-impactstory-square ai-2x' />",
        "Google Scholar": "<i class='ai ai-google-scholar-square ai-2x' />",
        "ResearchGate": "<i class='ai ai-researchgate-square ai-2x' />",
        "Academia": "<i class='ai ai-academia-square ai-2x' />",
        "Baidu Scholar": "<img src='http://www.baidu.com/favicon.ico' class='icon-image'>",
        "SSRN": "<img src='https://www.google.com/s2/favicons?domain=http://www.ssrn.com/' class='icon-image'>"
    };
    return nameToHtml[name];
}
</script>
