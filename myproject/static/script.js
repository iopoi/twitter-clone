
$(document).ready(function(){
    $("#adduser_button").click(
        function(){
            var msg = {username: $("#adduser_username").val(),
                       email: $("#adduser_email").val(),
                       password: $("#adduser_password").val()};
            $.post("http://130.245.168.104/adduser", JSON.stringify(msg))
            .done(
                function(data){
                    var data_json = JSON.parse(data)
                    $("ol").append("<li>output: "+data_json+"</li>")
                }
            );
        }
    );

});


