import React, { useState, useRef } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    StyleSheet, 
    Alert, 
    SafeAreaView, 
    ActivityIndicator,
    ScrollView,
    Image,
    Dimensions,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { useNavigation } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import { cameraScreenStyle } from '../../styles/cameraScreenStyles';
import AppText from '../../components/appText';        
import axios from 'axios';
import { useAuth } from '../../context/authContext';

const { width } = Dimensions.get('window');

const CameraScreen = () => {
    const navigation = useNavigation();
    const [permission, requestPermission] = useCameraPermissions();
    const cameraRef = useRef(null);
    const [isLoading, setIsLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState('');
    const [selectedImages, setSelectedImages] = useState([]);
    const [processingAll, setProcessingAll] = useState(false);

    const { user } = useAuth();

    // Your ngrok URL - make sure this is correct
    const API_BASE_URL = 'https://pagespark-api-663555450350.asia-southeast1.run.app';

    // ── Camera Permissions ────────────────────────────────────────────────────

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

    // ── Take Picture (adds to selection) ────────────────────────────────────

    const takePicture = async () => {
        if (cameraRef.current) {
            try {
                const photo = await cameraRef.current.takePictureAsync();
                setSelectedImages(prev => [...prev, {
                    uri: photo.uri,
                    fileName: `photo_${Date.now()}.jpg`,
                    type: 'image/jpeg',
                }]);
                Alert.alert('✅ รูปถ่ายแล้ว', `มี ${selectedImages.length + 1} รูปที่เลือก`);
            } catch (error) {
                console.error('Error taking picture:', error);
                Alert.alert('Error', 'Failed to take picture. Please try again.');
            }
        }
    };

    // ── Pick Multiple Images from Gallery ────────────────────────────────────

    const pickMultipleImages = async () => {
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsMultipleSelection: true,
            quality: 1,
            selectionLimit: 10,
        });

        if (!result.canceled) {
            const newImages = result.assets.map(asset => ({
                uri: asset.uri,
                fileName: asset.fileName || `gallery_${Date.now()}.jpg`,
                type: 'image/jpeg',
            }));
            setSelectedImages(prev => [...prev, ...newImages]);
            Alert.alert('✅ เลือกรูปแล้ว', `เลือกไป ${newImages.length} รูป (รวม ${selectedImages.length + newImages.length} รูป)`);
        }
    };

    // ── Pick PDF Document ────────────────────────────────────────────────────

    const pickPdf = async () => {
        const result = await DocumentPicker.getDocumentAsync({
            type: 'application/pdf',
            copyToCacheDirectory: true,
        });

        if (!result.canceled && result.assets && result.assets[0]) {
            setSelectedImages(prev => [...prev, {
                uri: result.assets[0].uri,
                fileName: result.assets[0].name || 'document.pdf',
                type: 'application/pdf',
            }]);
            Alert.alert('✅ เลือก PDF แล้ว', `มี ${selectedImages.length + 1} ไฟล์ที่เลือก`);
        }
    };

    // ── Remove image from selection ─────────────────────────────────────────

    const removeImage = (index) => {
        setSelectedImages(prev => prev.filter((_, i) => i !== index));
    };

    // ── Clear all selected images ───────────────────────────────────────────

    const clearAllImages = () => {
        setSelectedImages([]);
    };

    // ── Upload single image to backend (uses your existing upload function) ──

    const uploadSingleImage = async (image, index, total) => {
        setUploadProgress(`📤 ไฟล์ ${index + 1}/${total}: ${image.fileName}`);

        const formData = new FormData();
        formData.append('file', {
            uri: image.uri,
            name: image.fileName,
            type: image.type,
        });
        
        const uid = user?.uid || user?.email || 'anonymous';
        formData.append('uid', uid);
        formData.append('lesson_id', `lesson_${Date.now()}_${index}`);

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
                    setUploadProgress(`⏫ ${image.fileName} ${percent}%`);
                },
            }
        );

        return response.data;
    };

    // ── Process all selected images ─────────────────────────────────────────

    const processAllImages = async () => {
        if (selectedImages.length === 0) {
            Alert.alert('⚠️ ไม่มีรูป', 'กรุณาเลือกรูปหรือถ่ายรูปก่อน');
            return;
        }

        setProcessingAll(true);
        setUploadProgress(`📤 กำลังประมวลผล ${selectedImages.length} ไฟล์...`);

        const results = [];
        const errors = [];

        for (let i = 0; i < selectedImages.length; i++) {
            const image = selectedImages[i];
            
            try {
                const data = await uploadSingleImage(image, i, selectedImages.length);
                results.push({
                    file: image.fileName,
                    success: true,
                    data: data,
                });
                setUploadProgress(`✅ ไฟล์ ${i + 1}/${selectedImages.length} สำเร็จ!`);
            } catch (error) {
                console.error(`❌ Failed for ${image.fileName}:`, error.message);
                let errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
                errors.push({
                    file: image.fileName,
                    error: errorMessage,
                });
                setUploadProgress(`❌ ไฟล์ ${i + 1}/${selectedImages.length} ล้มเหลว`);
            }

            // Add delay between uploads to avoid rate limiting
            if (i < selectedImages.length - 1) {
                setUploadProgress(`⏳ รอ 5 วินาทีก่อนไฟล์ถัดไป...`);
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }

        setProcessingAll(false);
        setUploadProgress('');

        // ── Show results ──────────────────────────────────────────────────────

        const successCount = results.length;
        const errorCount = errors.length;

        if (successCount === 0 && errorCount === 0) {
            Alert.alert('⚠️ ไม่มีผลลัพธ์', 'ไม่สามารถประมวลผลไฟล์ใดๆ ได้');
            return;
        }

        let message = `📊 ประมวลผลเสร็จสิ้น\n\n✅ สำเร็จ: ${successCount} ไฟล์\n❌ ล้มเหลว: ${errorCount} ไฟล์\n\n`;
        
        if (results.length > 0) {
            message += '✅ ไฟล์ที่สำเร็จ:\n';
            results.forEach((r, idx) => {
                const episodeCount = r.data?.expected_episodes || 0;
                message += `  ${idx + 1}. ${r.file} (${episodeCount} ตอน)\n`;
            });
        }

        if (errors.length > 0) {
            message += '\n❌ ไฟล์ที่ล้มเหลว:\n';
            errors.forEach((e, idx) => {
                const shortError = e.error.length > 50 ? e.error.substring(0, 50) + '...' : e.error;
                message += `  ${idx + 1}. ${e.file}: ${shortError}\n`;
            });
        }

        Alert.alert(
            '🎬 เสร็จสิ้น!',
            message,
            [
                { 
                    text: 'ดูวิดีโอที่สร้าง', 
                    onPress: () => {
                        navigation.navigate('videoLesson');
                        if (successCount > 0) {
                            setSelectedImages([]);
                        }
                    } 
                },
                { 
                    text: 'OK', 
                    onPress: () => {
                        if (errorCount === 0) {
                            setSelectedImages([]);
                        } else {
                            // Keep only failed images for retry
                            const successfulFiles = new Set(results.map(r => r.file));
                            setSelectedImages(prev => prev.filter(img => !successfulFiles.has(img.fileName)));
                        }
                    } 
                },
                ...(errorCount > 0 ? [{
                    text: 'ลองใหม่เฉพาะที่ล้มเหลว',
                    onPress: () => {
                        const failedFiles = new Set(errors.map(e => e.file));
                        setSelectedImages(prev => prev.filter(img => failedFiles.has(img.fileName)));
                        setTimeout(() => processAllImages(), 500);
                    }
                }] : [])
            ]
        );
    };

    // ── Render selected images preview ──────────────────────────────────────

    const renderSelectedImages = () => {
        if (selectedImages.length === 0) return null;

        return (
            <View style={styles.selectedContainer}>
                <View style={styles.selectedHeader}>
                    <AppText style={styles.selectedTitle}>
                        📷 เลือก {selectedImages.length} ไฟล์
                    </AppText>
                    <TouchableOpacity onPress={clearAllImages} style={styles.clearBtn}>
                        <FontAwesome5 name="trash" size={14} color="#ef4444" />
                        <AppText style={styles.clearText}>ล้างทั้งหมด</AppText>
                    </TouchableOpacity>
                </View>

                <ScrollView 
                    horizontal 
                    showsHorizontalScrollIndicator={false}
                    style={styles.thumbnailScroll}
                    contentContainerStyle={styles.thumbnailContainer}
                >
                    {selectedImages.map((item, index) => (
                        <View key={index} style={styles.thumbnailWrapper}>
                            {item.type === 'application/pdf' ? (
                                <View style={[styles.thumbnail, styles.pdfThumbnail]}>
                                    <FontAwesome5 name="file-pdf" size={30} color="#ef4444" />
                                </View>
                            ) : (
                                <Image source={{ uri: item.uri }} style={styles.thumbnail} />
                            )}
                            <TouchableOpacity 
                                style={styles.removeBtn}
                                onPress={() => removeImage(index)}
                            >
                                <FontAwesome5 name="times" size={12} color="#fff" />
                            </TouchableOpacity>
                            <AppText style={styles.thumbnailLabel} numberOfLines={1}>
                                {item.fileName?.substring(0, 15) || `ไฟล์ ${index + 1}`}
                            </AppText>
                        </View>
                    ))}
                </ScrollView>

                <TouchableOpacity 
                    style={styles.processBtn}
                    onPress={processAllImages}
                    disabled={processingAll}
                >
                    {processingAll ? (
                        <ActivityIndicator size="small" color="#fff" />
                    ) : (
                        <>
                            <FontAwesome5 name="play" size={16} color="#fff" />
                            <AppText style={styles.processBtnText}>
                                ประมวลผล {selectedImages.length} ไฟล์
                            </AppText>
                        </>
                    )}
                </TouchableOpacity>
            </View>
        );
    };

    // ── Render ──────────────────────────────────────────────────────────────────

    return (
        <SafeAreaView style={cameraScreenStyle.container}>
            {/* Loading Overlay */}
            {(isLoading || processingAll) && (
                <View style={styles.loadingOverlay}>
                    <View style={styles.loadingCard}>
                        <ActivityIndicator size="large" color="#FFD700" />
                        <AppText style={styles.loadingText}>{uploadProgress}</AppText>
                        <AppText style={styles.loadingSubText}>
                            {processingAll 
                                ? `กำลังประมวลผล ${selectedImages.length} ไฟล์...`
                                : 'Please wait, this may take a few minutes...'}
                        </AppText>
                    </View>
                </View>
            )}

            {/* Top Bar */}
            <View style={cameraScreenStyle.header}>
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <FontAwesome5 name="arrow-left" size={24} color="#F8FAFC" />
                </TouchableOpacity>
                <AppText style={cameraScreenStyle.headerTitle}>สแกนบทเรียน</AppText>
                <View style={{ width: 24 }} />
            </View>

            {/* Camera Viewport */}
            <View style={cameraScreenStyle.cameraContainer}>
                <CameraView style={cameraScreenStyle.camera} facing="back" ref={cameraRef} />
            </View>

            {/* Selected Images Preview */}
            {renderSelectedImages()}

            {/* Bottom Controls */}
            <View style={cameraScreenStyle.controlsContainer}>
                {/* Pick Multiple Images Button */}
                <TouchableOpacity 
                    style={cameraScreenStyle.iconButton} 
                    onPress={pickMultipleImages} 
                    disabled={isLoading || processingAll}
                >
                    <FontAwesome5 name="images" size={28} color="#fff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือกรูป</AppText>
                </TouchableOpacity>

                {/* Shutter Button (Take Picture) */}
                <TouchableOpacity 
                    style={cameraScreenStyle.shutterButton} 
                    onPress={takePicture} 
                    disabled={isLoading || processingAll}
                >
                    <View style={cameraScreenStyle.shutterInner} />
                </TouchableOpacity>

                {/* Pick PDF Button */}
                <TouchableOpacity 
                    style={cameraScreenStyle.iconButton} 
                    onPress={pickPdf} 
                    disabled={isLoading || processingAll}
                >
                    <FontAwesome5 name="file-pdf" size={28} color="#fff" />
                    <AppText style={cameraScreenStyle.iconText}>เลือก PDF</AppText>
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
};

// ── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    loadingOverlay: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
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
    selectedContainer: {
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        paddingVertical: 10,
        paddingHorizontal: 12,
        borderTopWidth: 1,
        borderTopColor: 'rgba(255,255,255,0.1)',
        position: 'absolute',
        bottom: 130,
        width: '100%',
    },
    selectedHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    selectedTitle: {
        color: '#FFFFFF',
        fontSize: 14,
        fontWeight: '600',
    },
    clearBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        padding: 4,
    },
    clearText: {
        color: '#ef4444',
        fontSize: 12,
    },
    thumbnailScroll: {
        flexGrow: 0,
    },
    thumbnailContainer: {
        gap: 8,
        paddingVertical: 4,
    },
    thumbnailWrapper: {
        alignItems: 'center',
        position: 'relative',
    },
    thumbnail: {
        width: 60,
        height: 60,
        borderRadius: 8,
        backgroundColor: '#2d2d4a',
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.1)',
    },
    pdfThumbnail: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    removeBtn: {
        position: 'absolute',
        top: -4,
        right: -4,
        backgroundColor: '#ef4444',
        width: 20,
        height: 20,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#fff',
    },
    thumbnailLabel: {
        color: '#94A3B8',
        fontSize: 9,
        marginTop: 2,
        maxWidth: 60,
        textAlign: 'center',
    },
    processBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: '#FFD700',
        paddingVertical: 10,
        paddingHorizontal: 16,
        borderRadius: 10,
        marginTop: 8,
    },
    processBtnText: {
        color: '#1C1C2E',
        fontSize: 14,
        fontWeight: '600',
    },
});

export default CameraScreen;