/////////////////////
// Project JS      //
/////////////////////

$(document).ready(function() {


    $("#humanStyles").change(function(){

        if($(this).val()==="OSFURL")
        {
            $(".rendered-citation").text(absoluteUrl);
        }

        else{
            $.ajax({
                type: "GET",
                url: nodeApiUrl + 'citation/human/' +$(this).val(),
                success: function(response){
                    $(".rendered-citation").text(response.output);
                    return false;
                }
            })
            return false;
        }
    })

//        var $citationFormMachineSelect = $("#machineStyles");

    $("#machineStyles").change(function(){
        window.location.href =nodeApiUrl + 'citation/machine/' + $(this).val() ;
        return false;
    })
})

