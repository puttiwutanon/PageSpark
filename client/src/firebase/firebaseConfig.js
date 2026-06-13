// Import the functions you need from the SDKs you need
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, initializeAuth, getReactNativePersistence  } from "firebase/auth";
import { getFirestore } from 'firebase/firestore';
import { createAsyncStorage } from '@react-native-async-storage/async-storage';
const appStorage = createAsyncStorage("app");
const persistence = getReactNativePersistence(appStorage);
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB8LwCqPINW8OUKGlXN6ZThYc0KTZZHXMs",
  authDomain: "pagespark-39612.firebaseapp.com",
  projectId: "pagespark-39612",
  storageBucket: "pagespark-39612.firebasestorage.app",
  messagingSenderId: "774539129021",
  appId: "1:774539129021:web:89dda3fc9b2dd878dac7d4",
  measurementId: "G-6XYP0CRZVV"
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const db = getFirestore(app); // Re-added missing db initialization

let auth;
try {
  auth = getAuth(app);
} catch (error) {
  auth = initializeAuth(app, {
    persistence: getReactNativePersistence(AsyncStorage)
  });
}

export { app, auth, db };