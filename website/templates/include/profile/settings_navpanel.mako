<%page args="current_page=''" />
<!-- The following jquery functions are to fix the bootstrap affix issue
    where having a top offset and a bottom offset can cause conflicts when the page is refreshed.
    In this cause it caused the user settings side navigation bar to stick to the bottom of the page
    when refreshed. The first function checks if the page has been shrunk to the mobile settings or not.
    The second function affixes the element to the top of the screen window and the top of the page footer.--->

<script>

var lastWidth;
$(window).load(function(){
    if($(window).width() > 769){
        lastWidth = $(window).width();
        sticky_element();
    }
});

$(window).resize(function(){
    if($(window).width()!=lastWidth){
        if(lastWidth > 769 && $(window).width() <= 769){
            $(window).scroll(function () {
                $("#usersettingspanel").css('top', '');
            });
        }
        lastWidth = $(window).width();
    }

});

$(window).resize(function(){
    if($(window).width()!=lastWidth){
        if(lastWidth <= 769 && $(window).width() > 769){
            lastWidth = $(window).width();
            sticky_element();
        }
    }

});


function sticky_element(){
    var stickyE   = "#usersettingspanel",
        bottomE   = "#pagefooter";
    if($( stickyE ).length){
        $( stickyE ).each(function(){
            var fromTop = $( this ).offset().top - 60, // number of pixels to the top of element
            // "-60" is the offset from the top of the screen
            fromBottom = $( document ).height()-($( this ).offset().top + $( this ).outerHeight()),
            //number of pixels from the top of the bottom element, adding height to take into account padding/borders
            stopOn = $( document ).height()-( $( bottomE ).offset().top)+($( this ).outerHeight() - $( this ).height());
            if( (fromBottom-stopOn) > 200){
                $( this ).css('width', $( this ).width()).css('top', 105).css('position', '');
                $( this ).affix({
                    offset: {
                        top: fromTop,
                        bottom: stopOn
                    }
                    // position is fixed and at the top, not position relative
                }).on('affix.bs.affix', function(){ $( this ).css('top', 60).css('position', ''); });
            }
            $( window ).trigger('scroll');
        });
    }
};

</script>

<div class="osf-affix profile-affix panel panel-default" id="usersettingspanel">
    <ul class="nav nav-stacked nav-pills">
        <li class="${'active' if current_page == 'profile' else ''}">
            <a href="${ '#' if current_page == 'profile' else web_url_for('user_profile') }">Profile information</a></li>
        <li class="${'active' if current_page == 'account' else ''}">
            <a href="${ '#' if current_page == 'account' else web_url_for('user_account') }">Account settings</a></li>
        <li class="${'active' if current_page == 'addons' else ''}">
            <a href="${ '#' if current_page == 'addons' else  web_url_for('user_addons') }">Configure add-on accounts</a></li>
        <li class="${'active' if current_page == 'notifications' else ''}">
            <a href="${ '#' if current_page == 'notifications' else web_url_for('user_notifications') }">Notifications</a></li>
        <li class="${'active' if current_page == 'dev_apps' else ''}">
            <a href="${ '#' if current_page == 'dev_apps' else web_url_for('oauth_application_list')}">Developer apps</a></li>
        <li class="${'active' if current_page == 'personal_tokens' else ''}">
            <a href="${ '#' if current_page == 'personal_tokens' else web_url_for('personal_access_token_list')}">Personal access tokens</a></li>
    </ul>
</div>


