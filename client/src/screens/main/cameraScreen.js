import React, { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, SafeAreaView } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import { cameraScreenStyle } from '../../styles/cameraScreenStyles';
import AppText from '../../components/appText';        
import axios from 'axios';
import AppTextInput from '../../components/appTextInput';

const CameraScreen = () => {
    const navigation = useNavigation();
    const [permission, requestPermission] = useCameraPermissions();
    const cameraRef = useRef(null);

    // 1. Handle Camera Permissions
    if (!permission) {
        return <View style={cameraScreenStyle.container} />; // Loading state
    }
    if (!permission.granted) {
        return (
            <View style={cameraScreenStyle.container}>
                <AppText style={cameraScreenStyle.text}>PageSpark ต้องการเข้าถึงกล้องของคุณ</AppText>
                <TouchableOpacity style={cameraScreenStyle.primaryButton} onPress={requestPermission}>
                    <AppText style={cameraScreenStyle.buttonText}>อนุญาตการเข้าถึงกล้อง</AppText>
                </TouchableOpacity>
            </View>
        );
    }

    // 2. Function: Take a Picture
    const takePicture = async () => {
        if (cameraRef.current) {
            const photo = await cameraRef.current.takePictureAsync();
            // Call your new function right here!
            await uploadImageToBackend(photo.uri); 
        }
    };

    // 3. Function: Pick an Image from Gallery
    const pickImage = async () => {
        let result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: true,
            quality: 1,
            base64: true,
        });

        if (!result.canceled) {
            console.log("Image selected from gallery!");
            // TODO: Send result.assets[0] to Backend
            await uploadImageToBackend(result.assets[0].uri);
        }
    };

    // 4. Function: Pick a PDF Document
    const pickPdf = async () => {
        let result = await DocumentPicker.getDocumentAsync({
            type: 'application/pdf',
            copyToCacheDirectory: true,
        });

        if (!result.canceled) {
            console.log("PDF selected!");
            // TODO: Send result.assets[0] to Backend
        }
    };

    // 5. Function: Upload Image to Backend
    const uploadImageToBackend = async (imageUri) => {
        const formData = new FormData();
        formData.append('file', {
            uri: imageUri,
            name: 'photo.jpg',
            type: 'image/jpeg',
        });

        try {
            const response = await axios.post('http://192.168.1.149:8000/api/ingest', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            console.log("Success:", response.data);
        } catch (error) {
            console.error("Axios upload failed:", error.response?.data || error.message);
        }
    };

    return (
        <SafeAreaView style={cameraScreenStyle.container}>
            {/* Top Bar */}
            <View style={cameraScreenStyle.header}>
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <FontAwesome5 name="arrow-left" size={24} color="#F8FAFC" />
                </TouchableOpacity>
                <AppText style={cameraScreenStyle.headerTitle}>สแกนบทเรียน</AppText>
                <View style={{ width: 24 }} /> {/* Spacer for alignment */}
            </View>

            {/* Camera Viewport */}
            <View style={cameraScreenStyle.cameraContainer}>
                <CameraView style={cameraScreenStyle.camera} facing="back" ref={cameraRef} />
            </View>

            {/* Bottom Controls */}
            <View style={cameraScreenStyle.controlsContainer}>
                {/* Pick Image Button */}
                <TouchableOpacity style={cameraScreenStyle.iconButton} onPress={pickImage}>
                    <FontAwesome5 name="image" size={28} color="#92d0ff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือกรูป</AppText>
                </TouchableOpacity>

                {/* Shutter Button (Take Picture) */}
                <TouchableOpacity style={cameraScreenStyle.shutterButton} onPress={takePicture}>
                    <View style={cameraScreenStyle.shutterInner} />
                </TouchableOpacity>

                {/* Pick PDF Button */}
                <TouchableOpacity style={cameraScreenStyle.iconButton} onPress={pickPdf}>
                    <FontAwesome5 name="file-pdf" size={28} color="#92d0ff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือก PDF</AppText>
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
};

export default CameraScreen;