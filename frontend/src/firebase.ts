// frontend/src/firebase.ts
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getFunctions } from 'firebase/functions';  // If needed for cloud funcs

const firebaseConfig = {
  apiKey: "AIzaSyAzdlb6LA3GvS1_bJ8sUBeuEM3KJGBzBSs",
  authDomain: "nova-c4819.firebaseapp.com",
  projectId: "nova-c4819",
  storageBucket: "nova-c4819.firebasestorage.app",
  messagingSenderId: "208491483739",
  appId: "1:208491483739:web:32d697c50f5e9d6f75257e",
  measurementId: "G-VYXD6Q910E"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const functions = getFunctions(app);  // Optional
export default app;
