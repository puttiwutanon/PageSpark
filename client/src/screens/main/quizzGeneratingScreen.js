import React, { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, SafeAreaView } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import { quizzScreenStyle } from '../../styles/quizzScreenStyle';
import AppText from '../../components/appText';        
import axios from 'axios';

const QuizzGeneratingScreen = () => {
  return (
    <SafeAreaView style={quizzScreenStyle.quizzScreenContainer}>
        <View style={quizzScreenStyle.welcomeContainer}>
            <AppText style={quizzScreenStyle.welcomeText}>เลือกเนื้อหา</AppText>
                    
                {/* 1. Add this Wrapper View */}
                <View style={quizzScreenStyle.quizzGenerator}>

                </View>

        </View>
    </SafeAreaView>
  )
}

export default QuizzGeneratingScreen