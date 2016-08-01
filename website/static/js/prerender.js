window.activeAjaxCount = 0;

function isAllXhrComplete(){
    window.activeAjaxCount--;
    if (window.activeAjaxCount === 0){
        $('meta[name=prerender-status-code]').attr('content', '200');
        window.prerenderReady = true;
    }

}

(function(open) {
    XMLHttpRequest.prototype.open = function(method, url, async, user, pass) {
        this.addEventListener('load', isAllXhrComplete);
        open.call(this, method, url, async, user, pass);
    };
})(XMLHttpRequest.prototype.open);


(function(send) {
    XMLHttpRequest.prototype.send = function (data) {
        window.activeAjaxCount++;
        send.call(this, data);
    };
})(XMLHttpRequest.prototype.send);
