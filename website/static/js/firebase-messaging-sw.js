importScripts('https://www.gstatic.com/firebasejs/4.8.0/firebase.js');
firebase.initializeApp({
  'messagingSenderId': '340702114761'
});
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function(payload) {
  // Customize notification here
  const notificationTitle = 'RDM Announcements';
  const notificationOptions = {
    body: 'Background Message body.',
    icon: '/static/public/css/images/firebase-logo.png'
  };

  return self.registration.showNotification(notificationTitle,
      notificationOptions);
});

