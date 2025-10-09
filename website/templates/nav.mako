<%def name="nav(service_name, service_url, service_support_url)">
<link rel="stylesheet" href='/static/css/nav.css'>
<div class="osf-nav-wrapper" role="navigation">

<nav class="navbar navbar-fixed-top mobile-only">
    <span class="left-logo"><span class="osf-navbar-logo"></span>OSF</span>
    <input type="checkbox" id="toggle-leftnav" class="toggle-nav-input" aria-controls='slideout-nav' hidden/>
    <label for="toggle-leftnav" class="toggle-nav-label mobile-only" aria-label="Toggle navigation menu">
        <i class="fa fa-bars fa-2x"></i>
    </label>
    <!-- Sliding left nav -->
    <aside id="slideout-nav" class="left-pane left-pane-nav slideout mobile-only">
        <nav>
            <ul class='left-pane-ul'>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Home')" href="${domain}">
                        <i class="fa fa-home"></i>
                        Home
                    </a>
                </li>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Search')" href="${domain}search/">
                        <i class="fa fa-search"></i>
                        Search
                    </a>
                </li>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Support')" href="${service_support_url}">
                        <i class="fa fa-headset"></i>
                        Support
                    </a>
                </li>
            </ul>
            <ul class='left-pane-ul'>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Registries')" href="${domain}registries/">
                        <img class="social-icons" src="/static/img/left-nav-icons/registries.svg" title="Registries" alt="Registries icon">
                        Registries
                        <i class="fa fa-chevron-right chevron-right"></i>
                    </a>
                </li>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Preprints')" href="${domain}preprints/">
                        <img class="social-icons" src="/static/img/left-nav-icons/preprints.svg" title="Preprints" alt="Preprints icon">
                        Preprints
                        <i class="fa fa-chevron-right chevron-right"></i>
                    </a>
                </li>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Meetings')" href="${domain}meetings/">
                        <img class="social-icons" src="/static/img/left-nav-icons/meetings.svg" title="Meetings" alt="Meetings icon">
                        Meetings
                    </a>
                </li>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Institutions')" href="${domain}institutions/">
                        <i class="fa fa-university"></i>
                        Institutions
                    </a>
                </li>
            </ul>
            <ul class='left-pane-ul'>
                <li>
                    <a data-bind="click: trackClick.bind($data, 'Donate')" href="https://www.cos.io/support-cos">
                        <i class="fa fa-hand-holding-dollar"></i>
                        Donate
                    </a>
                </li>
            </ul>
        </nav>
    </aside>
</nav>


<!-- Left nav for desktop --->
<nav class="left-pane-nav desktop-only" id="leftnavScope">
    <div>
        <span class="left-logo"><span class="osf-navbar-logo"></span>OSF</span>
    </div>
    <ul class='left-pane-ul'>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Home')" href="${domain}">
                <i class="fa fa-home"></i>
                Home
            </a>
        </li>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Search')" href="${domain}search/">
                <i class="fa fa-search"></i>
                Search
            </a>
        </li>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Support')" href="${service_support_url}">
                <i class="fa fa-headset"></i>
                Support
            </a>
        </li>
    </ul>
    <ul class='left-pane-ul'>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Registries')" href="${domain}registries/">
                <img src="/static/img/left-nav-icons/registries.svg" title="Registries" alt="Registries icon">
                Registries
                <i class="fa fa-chevron-right chevron-right"></i>
            </a>
        </li>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Preprints')" href="${domain}preprints/">
                <img src="/static/img/left-nav-icons/preprints.svg" title="Preprints" alt="Preprints icon">
                Preprints
                <i class="fa fa-chevron-right chevron-right"></i>
            </a>
        </li>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Meetings')" href="${domain}meetings/">
                <img src="/static/img/left-nav-icons/meetings.svg" title="Meetings" alt="Meetings icon">
                Meetings
            </a>
        </li>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Institutions')" href="${domain}institutions/">
                <i class="fa fa-university"></i>
                Institutions
            </a>
        </li>
    </ul>
    <ul class='left-pane-ul'>
        <li>
            <a data-bind="click: trackClick.bind($data, 'Donate')" href="https://www.cos.io/support-cos">
                <i class="fa fa-hand-holding-dollar"></i>
                Donate
            </a>
        </li>
    </ul>
</div>
</%def>
