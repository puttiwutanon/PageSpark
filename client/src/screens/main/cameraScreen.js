import React, { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, SafeAreaView, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import { cameraScreenStyle } from '../../styles/cameraScreenStyles';
import AppText from '../../components/appText';        
import axios from 'axios';
import AppTextInput from '../../components/appTextInput';
import { useAuth } from '../../context/authContext';

const CameraScreen = () => {
    const navigation = useNavigation();
    const [permission, requestPermission] = useCameraPermissions();
    const cameraRef = useRef(null);
    const [isLoading, setIsLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState('');

    const { user } = useAuth();

    // Your ngrok URL - make sure this is correct
    const API_BASE_URL = 'https://pamphlet-manmade-abridge.ngrok-free.dev';

    // 1. Handle Camera Permissions
    if (!permission) {
        return <View style={cameraScreenStyle.container} />;
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
            try {
                const photo = await cameraRef.current.takePictureAsync();
                await uploadImageToBackend(photo.uri, 'photo.jpg');
            } catch (error) {
                console.error('Error taking picture:', error);
                Alert.alert('Error', 'Failed to take picture. Please try again.');
            }
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
            await uploadImageToBackend(result.assets[0].uri, result.assets[0].fileName || 'gallery_photo.jpg');
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
            // For PDF, you might want to use a different endpoint or handle differently
            // For now, we'll treat it like an image upload
            if (result.assets && result.assets[0]) {
                await uploadImageToBackend(result.assets[0].uri, result.assets[0].name || 'document.pdf');
            }
        }
    };

    // 5. Function: Upload Image to Backend (UPDATED to use /api/generate-video)

    // ... permission checks remain the same ...

    const uploadImageToBackend = async (imageUri, fileName) => {
        setIsLoading(true);
        setUploadProgress('📤 Uploading image...');

        const formData = new FormData();
        formData.append('file', {
            uri: imageUri,
            name: fileName || 'photo.jpg',
            type: fileName?.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg',
        });
        
        // ✅ Use actual user ID from auth
        const uid = user?.uid || user?.email || 'anonymous';
        formData.append('uid', uid);
        formData.append('lesson_id', `lesson_${Date.now()}`);

        try {
            setUploadProgress('📝 Generating lesson and rendering video...');
            
            const response = await axios.post(
                `${API_BASE_URL}/api/generate-video`, 
                formData, 
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: 300000,
                    onUploadProgress: (progressEvent) => {
                        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setUploadProgress(`⏫ Uploading: ${percent}%`);
                    },
                }
            );

            console.log("✅ Success:", response.data);
            setUploadProgress('✅ Processing complete!');
            
            const result = response.data;
            
            let message = `✅ Processed ${result.expected_episodes || 0} episode(s)\n`;
            
            if (result.render_results) {
                const successCount = result.render_results.filter(r => r.status === 'success').length;
                message += `📹 ${successCount}/${result.render_results.length} videos rendered\n`;
                
                result.render_results.forEach((r) => {
                    if (r.status === 'success' && r.video_url) {
                        message += `\n🎬 Episode ${r.episode_number}: Video uploaded successfully!`;
                    }
                });
            }
            
            Alert.alert(
                '🎬 Success!', 
                message,
                [
                    { text: 'View Videos', onPress: () => navigation.navigate('VideoList') },
                    { text: 'OK', onPress: () => navigation.goBack() },
                ]
            );
            
            return response.data;

        } catch (error) {
            console.error("❌ Upload failed:", error.response?.data || error.message);
            
            let errorMessage = 'Failed to process image. Please try again.';
            if (error.response?.data?.detail) {
                errorMessage = error.response.data.detail;
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            Alert.alert('❌ Error', errorMessage);
            throw error;
            
        } finally {
            setIsLoading(false);
            setUploadProgress('');
        }
    };

    // 6. Function: Upload Image with Summary Only (if you still want the old behavior)
    const uploadSummaryOnly = async (imageUri, fileName) => {
        setIsLoading(true);
        setUploadProgress('📤 Uploading image...');

        const formData = new FormData();
        formData.append('file', {
            uri: imageUri,
            name: fileName || 'photo.jpg',
            type: 'image/jpeg',
        });

        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/ingest?render=false`, // Explicitly no render
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: 60000,
                }
            );

            console.log("✅ Summary only:", response.data);
            Alert.alert(
                '📝 Summary Generated',
                'Summary only mode. To generate videos, use the "Generate Video" button.',
                [{ text: 'OK' }]
            );
            
            return response.data;

        } catch (error) {
            console.error("❌ Summary failed:", error.response?.data || error.message);
            Alert.alert('❌ Error', 'Failed to generate summary. Please try again.');
            throw error;
            
        } finally {
            setIsLoading(false);
            setUploadProgress('');
        }
    };

    return (
        <SafeAreaView style={cameraScreenStyle.container}>
            {/* Loading Overlay */}
            {isLoading && (
                <View style={styles.loadingOverlay}>
                    <View style={styles.loadingCard}>
                        <ActivityIndicator size="large" color="#FFD700" />
                        <AppText style={styles.loadingText}>{uploadProgress}</AppText>
                        <AppText style={styles.loadingSubText}>Please wait, this may take a few minutes...</AppText>
                    </View>
                </View>
            )}

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
                <TouchableOpacity style={cameraScreenStyle.iconButton} onPress={pickImage} disabled={isLoading}>
                    <FontAwesome5 name="image" size={28} color="#fff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือกรูป</AppText>
                </TouchableOpacity>

                {/* Shutter Button (Take Picture) */}
                <TouchableOpacity style={cameraScreenStyle.shutterButton} onPress={takePicture} disabled={isLoading}>
                    <View style={cameraScreenStyle.shutterInner} />
                </TouchableOpacity>

                {/* Pick PDF Button */}
                <TouchableOpacity style={cameraScreenStyle.iconButton} onPress={pickPdf} disabled={isLoading}>
                    <FontAwesome5 name="file-pdf" size={28} color="#fff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือก PDF</AppText>
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
};

// Styles for loading overlay
const styles = StyleSheet.create({
    loadingOverlay: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 999,
    },
    loadingCard: {
        backgroundColor: '#1C1C2E',
        padding: 30,
        borderRadius: 16,
        alignItems: 'center',
        width: '80%',
        borderWidth: 1,
        borderColor: '#FFD700',
    },
    loadingText: {
        color: '#FFFFFF',
        fontSize: 18,
        marginTop: 16,
        fontFamily: 'TH Sarabun New',
        textAlign: 'center',
    },
    loadingSubText: {
        color: '#94A3B8',
        fontSize: 14,
        marginTop: 8,
        fontFamily: 'TH Sarabun New',
        textAlign: 'center',
    },
});

export default CameraScreen;