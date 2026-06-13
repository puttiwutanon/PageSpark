import React, { useState } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    KeyboardAvoidingView, 
    Platform,
    SafeAreaView
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AppText from '../../components/appText';        
import AppTextInput from '../../components/appTextInput';
import { homeScreenStyle } from '../../styles/homeScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';

const VideoStorageScreen = () => {

    const navigation = useNavigation();

  return (
    <SafeAreaView style={homeScreenStyle.homeContainer}>
        <View style={homeScreenStyle.welcomeContainer}>
            <AppText style={homeScreenStyle.welcomeText}>คลังคลิปวิดีโอ</AppText>
        </View>
    </SafeAreaView>
  )
}

export default VideoStorageScreen