// context/AuthContext.js
import React, { createContext, useState, useEffect, useContext } from 'react';
import { 
  doCreateUserWithEmailAndPassword,
  doSignInWithEmailAndPassword,
  doSignOut,
  doPasswordReset,
  doPasswordChange,
  doOnAuthStateChanged
} from '../firebase/auth';
import { auth } from '../firebase/firebaseConfig';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = doOnAuthStateChanged((user) => {
      if (user) {
        // User is signed in
        setUser({
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL,
          emailVerified: user.emailVerified,
        });
        setError(null);
      } else {
        // User is signed out
        setUser(null);
      }
      setLoading(false);
    });

    // Cleanup subscription on unmount
    return () => unsubscribe();
  }, []);

  // Sign Up
  const signUp = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const userCredential = await doCreateUserWithEmailAndPassword(email, password);
      setUser({
        uid: userCredential.user.uid,
        email: userCredential.user.email,
      });
      return userCredential;
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Sign In
  const signIn = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const userCredential = await doSignInWithEmailAndPassword(email, password);
      setUser({
        uid: userCredential.user.uid,
        email: userCredential.user.email,
        displayName: userCredential.user.displayName,
        photoURL: userCredential.user.photoURL,
      });
      return userCredential;
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Sign Out
  const signOut = async () => {
    setLoading(true);
    try {
      await doSignOut();
      setUser(null);
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Reset Password
  const resetPassword = async (email) => {
    try {
      await doPasswordReset(email);
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  // Change Password
  const changePassword = async (newPassword) => {
    try {
      await doPasswordChange(newPassword);
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  // Get current user
  const getCurrentUser = () => {
    return auth.currentUser;
  };

  // Get ID Token (useful for authenticated API calls)
  const getIdToken = async () => {
    const currentUser = auth.currentUser;
    if (currentUser) {
      return await currentUser.getIdToken();
    }
    return null;
  };

  const value = {
    user,
    loading,
    error,
    signUp,
    signIn,
    signOut,
    resetPassword,
    changePassword,
    getCurrentUser,
    getIdToken,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};