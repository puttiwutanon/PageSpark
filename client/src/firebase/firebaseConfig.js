// Import the functions you need from the SDKs you need
import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  initializeAuth,
  getReactNativePersistence
} from "firebase/auth";

import AsyncStorage from "@react-native-async-storage/async-storage";
import { getFirestore } from "firebase/firestore";
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

const app = !getApps().length
  ? initializeApp(firebaseConfig)
  : getApp();

const db = getFirestore(app);

let auth;

try {
  auth = initializeAuth(app, {
    persistence: getReactNativePersistence(AsyncStorage),
  });
} catch {
  auth = getAuth(app);
}

export { app, auth, db };