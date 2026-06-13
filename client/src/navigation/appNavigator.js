import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import LoginScreen from '../screens/auth/loginScreen';
import SignUpScreen from '../screens/auth/signupScreen';
import Navbar from '../components/navbar'; 
import CameraScreen from '../screens/main/cameraScreen';

const Stack = createNativeStackNavigator();

const AppNavigator = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator 
        initialRouteName="Login"
        screenOptions={{
          headerShown: false,
        }}
      >
        {/* Authentication Flow */}
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="SignUp" component={SignUpScreen} />
        
        {/* Main Application Flow */}
        {/* Replacing HomeScreen with Navbar connects your home, video storage, and account tabs */}
        <Stack.Screen name="MainApp" component={Navbar} />
        <Stack.Screen name="camera" component={CameraScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;