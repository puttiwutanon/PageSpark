import React, { useState } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    KeyboardAvoidingView, 
    Platform,
    SafeAreaView,
    ScrollView
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AppText from '../../components/appText';        
import AppTextInput from '../../components/appTextInput';
import { videoStorageScreenStyle } from '../../styles/videoStorageScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';

const VideoStorageScreen = () => {

    const navigation = useNavigation();

  return (
    <SafeAreaView style={videoStorageScreenStyle.videoStorageScreenContainer}>
        <View style={videoStorageScreenStyle.welcomeContainer}>
            <AppText style={videoStorageScreenStyle.welcomeText}>คลังคลิปวิดีโอ</AppText>
                    
                {/* 1. Add this Wrapper View */}
                <View style={videoStorageScreenStyle.videoListWrapper}>

                    
                </View>

        </View>
    </SafeAreaView>
  )
}

export default VideoStorageScreen