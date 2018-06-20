var config = {
    apiKey: 'AIzaSyAopB_dSUGin7xEjijI8KlT56VKcMHyBmk',
    authDomain: 'gakunin-rdm.firebaseapp.com',
    databaseURL: 'https://gakunin-rdm.firebaseio.com',
    projectId: 'gakunin-rdm',
    storageBucket: 'gakunin-rdm.appspot.com',
    messagingSenderId: '340702114761'
};
firebase.initializeApp(config);
const messaging = firebase.messaging();
var user = window.contextVars.currentUser;
if (user.id.length > 0 ){
    messaging.requestPermission()
        .then(function() {
        getCurrentToken();
    })
    .catch(function(err) {
        console.log('Unable to get permission to notify.', err);
    });
}

messaging.onTokenRefresh(function() {
    messaging.getToken()
    .then(function(refreshedToken) {
        console.log('Token refreshed.');
        sendTokenToServer(refreshedToken);
    })
    .catch(function(err) {
      console.log('Unable to retrieve refreshed token ', err);
    });
});
messaging.onMessage(function(payload) {
    var notificationInfo = payload.notification;
    var options = {
        body: notificationInfo.body,
        icon: '/static/public/css/images/firebase-logo.png'
    };
    var n = new Notification(notificationInfo.title,options);
    setTimeout(n.close.bind(n), 5000);
});

function getCurrentToken() {
    messaging.getToken()
    .then(function(currentToken) {
    if (currentToken) {
         sendTokenToServer(currentToken);
    } else {
        console.log('No Instance ID token available. Request permission to generate one.');
      }
    })
    .catch(function(err) {
      console.log('An error occurred while retrieving token. ', err);
    });
}
function sendTokenToServer(currentToken) {
    $.post(
        '/api/v1/firebase/usertoken/'+ user.id + '/' + currentToken,
        {},
        function(data){
            if(data.success === 'False'){
                console.log('An error has occured.');
        }
    });
}
