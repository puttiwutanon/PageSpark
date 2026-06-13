import { createUserWithEmailAndPassword, GoogleAuthProvider, sendEmailVerification, sendPasswordResetEmail, signInWithPopup, updatePassword, signInWithEmailAndPassword, signOut, onAuthStateChanged } from "firebase/auth";
import { auth } from "./firebaseConfig";

export const doCreateUserWithEmailAndPassword = async(email, password)=>{
    return createUserWithEmailAndPassword(auth, email, password)
}

export const doSignOut = () => {
    return signOut(auth);
}

export const doPasswordReset = (email) => {
    return sendPasswordResetEmail(auth, email);
}

export const doPasswordChange = (password) => {
    return updatePassword(auth, password);
}

export const doSignInWithEmailAndPassword = (email, password) => {
  return signInWithEmailAndPassword(auth, email, password);
};

export const doOnAuthStateChanged = (callback) => {
    return onAuthStateChanged(auth, callback);
};