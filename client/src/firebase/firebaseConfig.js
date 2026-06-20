import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  initializeAuth,
  getReactNativePersistence,
  browserLocalPersistence
} from "firebase/auth";
import { Platform } from 'react-native';
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyB8LwCqPINW8OUKGlXN6ZThYc0KTZZHXMs",
  authDomain: "pagespark-39612.firebaseapp.com",
  projectId: "pagespark-39612",
  storageBucket: "pagespark-39612.firebasestorage.app",
  messagingSenderId: "774539129021",
  appId: "1:774539129021:web:89dda3fc9b2dd878dac7d4",
  measurementId: "G-6XYP0CRZVV"
};

let app, auth, db;

// Check if this is the very first boot
if (!getApps().length) {
  // 1. Initialize the App
  app = initializeApp(firebaseConfig);
  
  // 2. Safely initialize Auth with custom persistence
  auth = initializeAuth(app, {
    persistence: Platform.OS === 'web' 
      ? browserLocalPersistence 
      : getReactNativePersistence(AsyncStorage),
  });
  console.log("✅ First boot: App and Auth (with persistence) initialized!");
} else {
  // If it's a hot reload, just grab the already running instances
  app = getApp();
  auth = getAuth(app);
  console.log("🔥 Hot Reload: Recovered existing App and Auth.");
}

db = getFirestore(app);

export { app, auth, db };