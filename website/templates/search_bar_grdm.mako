
<div class="osf-search" data-bind="fadeVisible: showSearch" style="display: none">
    <div class="container">
        <div class="row">
            <div class="col-md-7">
                <form class="input-group" data-bind="submit: submit">
                    <input id="searchPageFullBar" style="background-color: white;" name="search-placeholder" type="text" class="osf-search-input form-control" placeholder="${_('GakuNin RDM Search')}" data-bind="value: query, hasFocus: true">
                    <label id="searchBarLabel" class="search-label-placeholder" for="search-placeholder">${_("GakuNin RDM Search")}</label>
                    <span class="input-group-btn">
                        <button type=button class="btn osf-search-btn" data-bind="click: submit"><i class="fa fa-circle-arrow-right fa-lg"></i></button>
                        <button type=button class="btn osf-search-btn" data-toggle="modal" data-target="#search-help-modal"><i class="fa fa-question fa-lg"></i></button>
                        <button type="button" class="btn osf-search-btn" data-bind="visible: showClose, click : toggleSearch"><i class="fa fa-times fa-lg"></i></button>
                    </span>

                </form>
            </div>
            <div class="col-md-5">
                <form class="osf-treebeard-minimal">
                    <div style="display: flex; flex-wrap: nowrap; justify-content: flex-end; align-items: center;" class="tb-td tb-col-1">
                        <div style="margin-right: 5px;">${_("sort by")}</div>
                        <select id="sortPullDownMenu" style="margin-left: 5px; width: auto;" class="form-control" data-bind="options: sortOrderSettings, optionsText: 'text', optionsValue: 'value', value: sortOrder"></select>
                        <div style="margin-left: 15px; margin-right: 5px;">${_("per page")}</div>
                        <select id="resultsPerPagePullDownMenu" style="width: auto;" class="form-control" data-bind="options: resultsPerPageSettings, optionsText: 'text', optionsValue: 'value', value: resultsPerPage"></select>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
<%include file="search_bar_help_modal.mako" />
