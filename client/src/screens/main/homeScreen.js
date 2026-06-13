import React, { useState } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    KeyboardAvoidingView, 
    Platform 
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AppText from '../../components/appText';        
import AppTextInput from '../../components/appTextInput';

const HomeScreen = () => {
  return (
    <View>
      <Text>HomeScreen</Text>
    </View>
  )
}

export default HomeScreen