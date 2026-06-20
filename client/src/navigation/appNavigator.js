import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

// Import Firebase auth and your config
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../firebase/firebaseConfig'; // Adjust path if needed

import LoginScreen from '../screens/auth/loginScreen';
import SignUpScreen from '../screens/auth/signupScreen';
import Navbar from '../components/navbar'; 
import CameraScreen from '../screens/main/cameraScreen';

const Stack = createNativeStackNavigator();

const AppNavigator = () => {
const [user, setUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      // 1. Update the user state
      setUser(currentUser);
      
      // 2. Once the listener fires, we are done loading.
      // Even if currentUser is null, we now know for sure 
      // that the user is actually logged out.
      setIsAuthLoading(false); 
    });

    return () => unsubscribe();
  }, []);

  if (isAuthLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="rgba(128, 128, 128, 0.27)" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {user ? (
          // ✅ User is logged in: Only show Main App screens
          <>
            <Stack.Screen name="MainApp" component={Navbar} />
            <Stack.Screen name="camera" component={CameraScreen} />
          </>
        ) : (
          // ❌ No user: Only show Authentication screens
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="SignUp" component={SignUpScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;