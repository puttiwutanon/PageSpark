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

const QuizzScreen = () => {
    const navigation = useNavigation();

  return (
    <SafeAreaView style={quizzScreenStyle.quizzScreenContainer}>
        <View style={quizzScreenStyle.welcomeContainer}>
            <AppText style={quizzScreenStyle.welcomeText}>แบบทดสอบ</AppText>
                    
                {/* 1. Add this Wrapper View */}
                <TouchableOpacity style={quizzScreenStyle.quizzGeneratorButton} onPress={() => navigation.navigate('quizzGenerator')}>
                    <AppText style={{ fontSize: 18, color: 'white', margin: 8}}>สร้างแบบทดสอบ</AppText>
                    <FontAwesome5 name="book" size={24} color="white" />
                </TouchableOpacity>

        </View>
    </SafeAreaView>
  )
}

export default QuizzScreen