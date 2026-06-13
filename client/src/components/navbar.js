import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import FontAwesome6 from '@expo/vector-icons/FontAwesome6';
import FontAwesome from '@expo/vector-icons/FontAwesome';
import HomeScreen from '../screens/main/homeScreen';
import AccountScreen from '../screens/main/accountScreen';
import VideoStorageScreen from '../screens/main/videoStorageScreen';
import { navbarStyle } from '../styles/navbarStyles';

const Tab = createBottomTabNavigator();

const Navbar = () => {
  return (
    <Tab.Navigator
      initialRouteName="home"
      screenOptions={{
        tabBarStyle: {
          ...navbarStyle.navbar, // Fixed reference from missing 'styles' to imported 'navbarStyle'
          borderTopWidth: 0, 
          elevation: 0,      
          shadowOpacity: 0,
          backgroundColor: '#ffdce5', 
        },
        tabBarActiveTintColor: '#92d0ff',   
        tabBarInactiveTintColor: '#64748B',
        tabBarShowLabel: false,
        headerShown: false,
      }}
    >
      <Tab.Screen
        name="videoStorage"
        component={VideoStorageScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <FontAwesome6 name="film" size={24} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="home"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <FontAwesome name="home" size={26} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="account"
        component={AccountScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <FontAwesome6 name="user" size={24} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};

export default Navbar;