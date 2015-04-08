
var FileViewFangorn = function(params) {

    var fangornConfig = function(ctrl) {
        return function(elem, isInitialized) {
            if (!isInitialized) {
                new FileViewTreebeard({data: ctrl.data, divId: elem.id, onload: ctrl.onload});
            }
        };
    };
    return {
        controller: function() {
            this.data = params.data;
            this.onload = params.onload;
        },
        view: function(ctrl) {
            return m('div#fileViewFangorn', {config: fangornConfig(ctrl)});
        }
    };
};
var FileDrawer = function(params) {
    return {
        controller: function(){
            this.visible = m.prop(false);
            this.fileViewFangorn = new FileViewFangorn({
                data: params.data,
                onload: function() {
                    this.visible(true);
                }
            });
        },
        view: function(ctrl) {
            return (
                m('.osf-panel-header', {style: {display: ctrl.visible() ? 'block': 'none'}}, [
                    ctrl.fileViewFangorn.view(this.fileViewFangorn.controller())
                ])
            );
        }
    };
};


// page module
$.ajax({...}).done(function(data) {
    m.module($('#fileDrawer')[0], new FileDrawer({data: data}));
});

