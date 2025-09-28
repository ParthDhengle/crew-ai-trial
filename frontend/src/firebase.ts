// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAzdlb6LA3GvS1_bJ8sUBeuEM3KJGBzBSs",
  authDomain: "nova-c4819.firebaseapp.com",
  projectId: "nova-c4819",
  storageBucket: "nova-c4819.firebasestorage.app",
  messagingSenderId: "208491483739",
  appId: "1:208491483739:web:32d697c50f5e9d6f75257e",
  measurementId: "G-VYXD6Q910E"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
console.log('Firebase initialized')
const analytics = getAnalytics(app);