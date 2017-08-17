
var user;
var merchant;
var arrayNoneCheck = ["account-validated", "reset-password", "welcome", "register", "login", "forget_password"];
var checkUser = true;
var getUrlParameter = function getUrlParameter(sParam) {
  var sPageURL = decodeURIComponent(window.location.search.substring(1)),
    sURLVariables = sPageURL.split('&'),
    sParameterName,
    i;

  for (i = 0; i < sURLVariables.length; i++) {
    sParameterName = sURLVariables[i].split('=');

    if (sParameterName[0] === sParam) {
        return sParameterName[1] === undefined ? true : sParameterName[1];
      }
  }
};
arrayNoneCheck.forEach(function(entry) {
  if (window.location.href.indexOf(entry) > -1){
    checkUser = false;
  }
});

if (checkUser){
  if (localStorage.getItem('user_global')){

  } else {
    $(location).attr('href', welcomePageUrl);
  } 
}

$(document).ready(function(){
// Check user permission
(function(){
  if (checkUser){
    if (localStorage.getItem('user_global')){
      try {
        user = JSON.parse(Base64.decode(localStorage.getItem('user_global')));
        if (user.is_staff){
          // Refresh user data
          $('#loading-overlay').css('visibility', 'visible');
          $.ajax({
            type: "GET",
            url: '/api/users/' + localStorage.getItem('id_user') + '/',
            beforeSend: function(request) {
              request.setRequestHeader("Authorization", 'Token ' + localStorage.getItem('token'));
            },
            dataType: "json",
            success: function (data) {
              $('#loading-overlay').css('visibility', 'hidden');
              user = data;
              console.log(user);
              $("#name_store").html(user.username);
              localStorage.setItem('user_global', Base64.encode(JSON.stringify(data)));
              try {
                UserFromLib(user);
              } catch(e) {
                // console.log(e);
              }
            },
            error: function(jqXHR, text, error){
              alert('Error, can not get information.');
            }
          });

          // Refresh merchant data
          $.ajax({
            type: "GET",
            url: '/api/merchants/me/',
            beforeSend: function(request) {
              request.setRequestHeader("Authorization", 'Token ' + localStorage.getItem('token'));
            },
            dataType: "json",
            success: function (data) {  
              merchant = data.results[0];
              console.log(merchant);
              localStorage.setItem('merchant_global', Base64.encode(JSON.stringify(merchant)));
              try {
                MerchantFromLib(merchant);
                if (merchant.status == 0) $('#merchant-lead-open-store-banner').remove();
              } catch(e) {
                // console.log(e);
              }
            },
            error: function(jqXHR, text, error){
              alert('Error, can not get information.');
            }
          });          
        } else {
          alert("You are not a staff");
          $(location).attr('href', welcomePageUrl);
        }
      }
      catch(err) {
        console.log('Catch Error By LVNTruong + HoangTN: ')
        console.log(err);
        $(location).attr('href', welcomePageUrl);
      }
    } else {
      $(location).attr('href', welcomePageUrl);
    } 
  }
})();

});