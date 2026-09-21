import React, { useState, useRef, useEffect } from 'react';
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
    Animated,
    Easing,
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
import { saveQuizToFirestore } from '../../firebase/quizFirestore'; // adjust path if your firebase folder lives elsewhere

const { width } = Dimensions.get('window');

// ── Pipeline stages ─────────────────────────────────────────────────────────
// These mirror the backend logs 1:1 so the user sees exactly which step the
// server is on:
//   main.py          → 📁 Saved uploaded file / 🔍 Step 1 / 📝 Step 2 / 📊 Step 3 / 🎬 Step 4
//   manim_engine.py  → 🔒 validate / 🎬 Running manim command / ✅ Audio generated
//   video_engine.py  → 🎬 Combining video and audio
//   manim_engine.py  → 📤 Uploading final video to Cloudinary
//
// `secs` is the *estimated* duration of each stage. The backend returns one
// single response at the very end (no streaming), so these weights are what
// drive the bar between "request sent" and "response received". Tune them if
// your real render times differ — bigger number = that stage holds longer.
const PIPELINE_STAGES = [
    {
        key: 'upload',
        icon: 'cloud-upload-alt',
        th: 'กำลังอัปโหลดไฟล์ไปยังเซิร์ฟเวอร์',
        en: 'Uploading file to server',
        secs: 8,
    },
    {
        key: 'prescan',
        icon: 'search',
        th: 'ขั้นที่ 1: กำลังนับจำนวนโจทย์ในหน้านี้',
        en: 'Step 1: Pre-scanning for question count',
        secs: 10,
    },
    {
        key: 'lesson',
        icon: 'pen-fancy',
        th: 'ขั้นที่ 2: กำลังสร้างบทเรียนด้วย AI',
        en: 'Step 2: Generating lesson JSON (Gemini)',
        secs: 40,
    },
    {
        key: 'quiz',
        icon: 'question-circle',
        th: 'ขั้นที่ 2.5: กำลังสร้างแบบทดสอบทบทวน 10 ข้อ',
        en: 'Step 2.5: Generating 10-question review quiz',
        secs: 20,
    },
    {
        key: 'episodes',
        icon: 'layer-group',
        th: 'ขั้นที่ 3: กำลังตรวจสอบจำนวนตอน',
        en: 'Step 3: Enforcing episode count',
        secs: 5,
    },
    {
        key: 'validate',
        icon: 'shield-alt',
        th: 'กำลังตรวจสอบและแก้ไขโค้ด Manim',
        en: 'Validating & auto-fixing Manim code',
        secs: 15,
    },
    {
        key: 'render',
        icon: 'film',
        th: 'ขั้นที่ 4: กำลังเรนเดอร์วิดีโอ Manim',
        en: 'Step 4: Rendering Manim animation',
        secs: 70,
    },
    {
        key: 'audio',
        icon: 'volume-up',
        th: 'กำลังสร้างเสียงบรรยาย (TTS)',
        en: 'Generating voiceover audio',
        secs: 20,
    },
    {
        key: 'combine',
        icon: 'object-group',
        th: 'กำลังรวมวิดีโอกับเสียงบรรยาย',
        en: 'Combining video + audio',
        secs: 18,
    },
    {
        key: 'cloud',
        icon: 'cloud',
        th: 'กำลังอัปโหลดวิดีโอขึ้นคลาวด์',
        en: 'Uploading final video to Cloudinary',
        secs: 15,
    },
];

const TOTAL_PIPELINE_SECS = PIPELINE_STAGES.reduce((sum, s) => sum + s.secs, 0);
const LAST_STAGE_INDEX = PIPELINE_STAGES.length - 1;

const CameraScreen = () => {
    const navigation = useNavigation();
    const [permission, requestPermission] = useCameraPermissions();
    const cameraRef = useRef(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedImages, setSelectedImages] = useState([]);
    const [processingAll, setProcessingAll] = useState(false);

    // ── Pipeline status state ───────────────────────────────────────────────
    const [stageIndex, setStageIndex] = useState(0);
    const [stageDetail, setStageDetail] = useState('');      // e.g. "72%" while uploading
    const [overallPercent, setOverallPercent] = useState(0);
    const [elapsed, setElapsed] = useState(0);
    const [fileIndex, setFileIndex] = useState(0);
    const [fileTotal, setFileTotal] = useState(0);
    const [currentFileName, setCurrentFileName] = useState('');
    const [stageError, setStageError] = useState(null);

    // refs used by the ticker (so the interval always reads fresh values)
    const tickRef = useRef(null);
    const uploadDoneAtRef = useRef(null);   // ms timestamp when upload hit 100%
    const startedAtRef = useRef(null);      // ms timestamp when this file started
    const uploadPercentRef = useRef(0);
    const frozenRef = useRef(false);        // true once the server replied

    const barAnim = useRef(new Animated.Value(0)).current;
    const pulseAnim = useRef(new Animated.Value(0.4)).current;

    const { user } = useAuth();

    // Your ngrok URL - make sure this is correct
    const API_BASE_URL = 'https://pagespark-api-663555450350.asia-southeast1.run.app';

    // ── Animate the bar whenever overallPercent changes ─────────────────────

    useEffect(() => {
        Animated.timing(barAnim, {
            toValue: overallPercent,
            duration: 300,
            easing: Easing.out(Easing.quad),
            useNativeDriver: false,
        }).start();
    }, [overallPercent]);

    // ── Pulse animation for the active stage dot ────────────────────────────

    useEffect(() => {
        if (!processingAll) return;
        const loop = Animated.loop(
            Animated.sequence([
                Animated.timing(pulseAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
                Animated.timing(pulseAnim, { toValue: 0.4, duration: 700, useNativeDriver: true }),
            ])
        );
        loop.start();
        return () => loop.stop();
    }, [processingAll]);

    // ── Cleanup ticker on unmount ───────────────────────────────────────────

    useEffect(() => {
        return () => stopTicker();
    }, []);

    // ── Ticker: drives stage progression while the server works ─────────────

    const stopTicker = () => {
        if (tickRef.current) {
            clearInterval(tickRef.current);
            tickRef.current = null;
        }
    };

    const startTicker = () => {
        stopTicker();
        startedAtRef.current = Date.now();
        uploadDoneAtRef.current = null;
        uploadPercentRef.current = 0;
        frozenRef.current = false;
        setStageIndex(0);
        setStageDetail('0%');
        setOverallPercent(0);
        setElapsed(0);
        setStageError(null);
        barAnim.setValue(0);

        tickRef.current = setInterval(() => {
            if (frozenRef.current) return;

            const now = Date.now();
            setElapsed(Math.floor((now - startedAtRef.current) / 1000));

            // Stage 0 (upload) is driven by REAL axios upload progress.
            if (uploadDoneAtRef.current === null) {
                const up = uploadPercentRef.current;
                setStageIndex(0);
                setStageDetail(`${up}%`);
                const done = (up / 100) * PIPELINE_STAGES[0].secs;
                setOverallPercent(Math.min(97, (done / TOTAL_PIPELINE_SECS) * 100));
                return;
            }

            // After upload: walk the remaining stages using their estimates.
            const sinceUpload = (now - uploadDoneAtRef.current) / 1000;
            let acc = 0;
            let idx = LAST_STAGE_INDEX;
            for (let i = 1; i < PIPELINE_STAGES.length; i++) {
                if (sinceUpload < acc + PIPELINE_STAGES[i].secs) {
                    idx = i;
                    break;
                }
                acc += PIPELINE_STAGES[i].secs;
            }

            setStageIndex(idx);

            // If we've blown past the estimate, hold on the last stage and
            // show the extra waiting time instead of lying with 100%.
            const totalEstimateAfterUpload = TOTAL_PIPELINE_SECS - PIPELINE_STAGES[0].secs;
            if (sinceUpload > totalEstimateAfterUpload) {
                setStageDetail('ใช้เวลานานกว่าปกติ กรุณารอสักครู่...');
            } else {
                setStageDetail('');
            }

            const doneSecs = PIPELINE_STAGES[0].secs + Math.min(sinceUpload, totalEstimateAfterUpload);
            setOverallPercent(Math.min(97, (doneSecs / TOTAL_PIPELINE_SECS) * 100));
        }, 250);
    };

    const finishTicker = (ok = true) => {
        frozenRef.current = true;
        stopTicker();
        if (ok) {
            setStageIndex(LAST_STAGE_INDEX);
            setStageDetail('');
            setOverallPercent(100);
        }
    };

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

    // ── Save an AI-generated quiz to Firestore ──────────────────────────────
    // Runs right after /api/generate-video returns a quiz (Step 2.5 on the
    // backend). Wrapped so a Firestore failure never breaks the pipeline —
    // the quiz can still be played immediately even if the save fails, it
    // just won't show up later in QuizzScreen's list.

    const saveGeneratedQuiz = async (quizQuestions, questionTitles, fileName) => {
        if (!quizQuestions || quizQuestions.length === 0) return null;

        const topicNames = (questionTitles && questionTitles.length > 0)
            ? questionTitles
            : [`สแกนจาก: ${fileName}`];

        // Mirror saveQuizToFirestore's own title logic so the title shown
        // here (for the immediate "do it now" play) matches the title that
        // ends up in Firestore / QuizzScreen's list.
        const title = topicNames.length === 1
            ? topicNames[0]
            : `${topicNames[0]} +${topicNames.length - 1} หัวข้อ`;

        try {
            const quizId = await saveQuizToFirestore(
                ['image_scan'],          // topics — this quiz didn't come from the topic picker
                quizQuestions.length,     // questionsPerTopic (kept for schema compatibility)
                quizQuestions,
                topicNames,
            );
            return { id: quizId, title, saved: true };
        } catch (error) {
            console.error('❌ Failed to save quiz to Firestore:', error.message);
            return { id: `local_${Date.now()}`, title, saved: false };
        }
    };

    // ── Upload single image to backend ──────────────────────────────────────

    const uploadSingleImage = async (image, index, total) => {
        setFileIndex(index + 1);
        setFileTotal(total);
        setCurrentFileName(image.fileName);

        startTicker();

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
                timeout: 600000,
                onUploadProgress: (progressEvent) => {
                    if (!progressEvent.total) return;
                    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    uploadPercentRef.current = percent;
                    // Upload finished → hand control over to the stage estimator
                    if (percent >= 100 && uploadDoneAtRef.current === null) {
                        uploadDoneAtRef.current = Date.now();
                    }
                },
            }
        );

        finishTicker(true);
        return response.data;
    };

    // ── Process all selected images ─────────────────────────────────────────

    const processAllImages = async () => {
        if (selectedImages.length === 0) {
            Alert.alert('⚠️ ไม่มีรูป', 'กรุณาเลือกรูปหรือถ่ายรูปก่อน');
            return;
        }

        setProcessingAll(true);
        setFileTotal(selectedImages.length);

        const results = [];
        const errors = [];

        for (let i = 0; i < selectedImages.length; i++) {
            const image = selectedImages[i];
            
            try {
                const data = await uploadSingleImage(image, i, selectedImages.length);

                // Save the quiz to Firestore right away so it shows up in
                // QuizzScreen's list, independent of whether the video
                // (Step 4, the fragile part) succeeds or fails.
                let quizSaveInfo = null;
                if (data?.quiz_available && data?.quiz?.length > 0) {
                    quizSaveInfo = await saveGeneratedQuiz(data.quiz, data.question_titles, image.fileName);
                }

                results.push({
                    file: image.fileName,
                    success: true,
                    data: data,
                    quiz: data?.quiz_available ? data.quiz : null,
                    quizCount: data?.quiz_question_count || 0,
                    quizId: quizSaveInfo?.id || null,
                    quizTitle: quizSaveInfo?.title || null,
                    quizSaved: quizSaveInfo?.saved || false,
                });
                // let the user see the 100% state for a beat
                await new Promise(resolve => setTimeout(resolve, 800));
            } catch (error) {
                console.error(`❌ Failed for ${image.fileName}:`, error.message);
                let errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
                errors.push({
                    file: image.fileName,
                    error: errorMessage,
                });
                frozenRef.current = true;
                stopTicker();
                setStageError(errorMessage);
                await new Promise(resolve => setTimeout(resolve, 1500));
            }

            // Add delay between uploads to avoid rate limiting
            if (i < selectedImages.length - 1) {
                frozenRef.current = true;
                stopTicker();
                setStageError(null);
                for (let s = 5; s > 0; s--) {
                    setStageDetail(`⏳ รอ ${s} วินาทีก่อนไฟล์ถัดไป...`);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }
        }

        stopTicker();
        setProcessingAll(false);
        setOverallPercent(0);
        setStageDetail('');
        setStageError(null);

        // ── Show results ──────────────────────────────────────────────────────

        const successCount = results.length;
        const errorCount = errors.length;

        if (successCount === 0 && errorCount === 0) {
            Alert.alert('⚠️ ไม่มีผลลัพธ์', 'ไม่สามารถประมวลผลไฟล์ใดๆ ได้');
            return;
        }

        // The quiz step runs right after lesson-JSON generation (before the
        // fragile Manim render), so it's the thing most likely to have
        // actually succeeded even when video rendering itself failed.
        // Grab the first successful result that has a usable quiz.
        const resultWithQuiz = results.find(r => r.quiz && r.quiz.length > 0);
        const primaryQuiz = resultWithQuiz
            ? {
                  id: resultWithQuiz.quizId || `local_${Date.now()}`,
                  title: resultWithQuiz.quizTitle || `แบบทดสอบทบทวน: ${resultWithQuiz.file}`,
                  totalQuestions: resultWithQuiz.quiz.length,
                  questions: resultWithQuiz.quiz,
                  createdAt: new Date(),
              }
            : null;

        let message = `📊 ประมวลผลเสร็จสิ้น\n\n✅ สำเร็จ: ${successCount} ไฟล์\n❌ ล้มเหลว: ${errorCount} ไฟล์\n\n`;
        
        if (results.length > 0) {
            message += '✅ ไฟล์ที่สำเร็จ:\n';
            results.forEach((r, idx) => {
                const episodeCount = r.data?.expected_episodes || 0;
                const quizNote = r.quizCount > 0
                    ? `, แบบทดสอบ ${r.quizCount} ข้อ${r.quizSaved ? '' : ' (บันทึกไม่สำเร็จ)'}`
                    : '';
                message += `  ${idx + 1}. ${r.file} (${episodeCount} ตอน${quizNote})\n`;
            });
        }

        if (errors.length > 0) {
            message += '\n❌ ไฟล์ที่ล้มเหลว:\n';
            errors.forEach((e, idx) => {
                const shortError = e.error.length > 50 ? e.error.substring(0, 50) + '...' : e.error;
                message += `  ${idx + 1}. ${e.file}: ${shortError}\n`;
            });
        }

        if (!primaryQuiz && successCount > 0) {
            message += '\nℹ️ ไม่สามารถสร้างแบบทดสอบได้ในครั้งนี้';
        } else if (primaryQuiz && !resultWithQuiz.quizSaved) {
            message += '\nℹ️ ทำแบบทดสอบได้ทันที แต่บันทึกลง Firestore ไม่สำเร็จ (จะไม่ปรากฏในรายการภายหลัง)';
        }

        Alert.alert(
            '🎬 เสร็จสิ้น!',
            message,
            [
                // Quiz first — it runs earlier in the pipeline than the video
                // render, so it's the most likely thing to actually exist.
                ...(primaryQuiz ? [{
                    text: `📝 ทำแบบทดสอบ (${primaryQuiz.totalQuestions} ข้อ)`,
                    onPress: () => {
                        navigation.navigate('quizzPlay', { quiz: primaryQuiz });
                        if (successCount > 0) {
                            setSelectedImages([]);
                        }
                    }
                }] : []),
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

    // ── Format elapsed time as m:ss ─────────────────────────────────────────

    const formatElapsed = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${m}:${sec.toString().padStart(2, '0')}`;
    };

    // ── Render the pipeline status panel ────────────────────────────────────

    const renderStatusPanel = () => {
        const barWidth = barAnim.interpolate({
            inputRange: [0, 100],
            outputRange: ['0%', '100%'],
            extrapolate: 'clamp',
        });

        const activeStage = PIPELINE_STAGES[stageIndex];

        return (
            <View style={styles.loadingOverlay}>
                <View style={styles.statusCard}>

                    {/* Header: which file out of how many */}
                    <View style={styles.statusHeader}>
                        <AppText style={styles.statusTitle}>
                            {stageError ? '❌ เกิดข้อผิดพลาด' : '🎬 กำลังสร้างวิดีโอ'}
                        </AppText>
                        {fileTotal > 1 && (
                            <AppText style={styles.statusFileCount}>
                                ไฟล์ {fileIndex}/{fileTotal}
                            </AppText>
                        )}
                    </View>

                    {currentFileName ? (
                        <AppText style={styles.statusFileName} numberOfLines={1}>
                            {currentFileName}
                        </AppText>
                    ) : null}

                    {/* Progress bar */}
                    <View style={styles.barTrack}>
                        <Animated.View
                            style={[
                                styles.barFill,
                                { width: barWidth },
                                stageError && styles.barFillError,
                            ]}
                        />
                    </View>

                    <View style={styles.barMetaRow}>
                        <AppText style={styles.barPercent}>
                            {Math.round(overallPercent)}%
                        </AppText>
                        <AppText style={styles.barElapsed}>
                            ⏱ {formatElapsed(elapsed)}
                        </AppText>
                    </View>

                    {/* Current stage headline */}
                    {!stageError && activeStage && (
                        <View style={styles.currentStageBox}>
                            <FontAwesome5 name={activeStage.icon} size={16} color="#FFD700" />
                            <View style={{ flex: 1 }}>
                                <AppText style={styles.currentStageTh}>
                                    {activeStage.th} {stageDetail ? `(${stageDetail})` : ''}
                                </AppText>
                                <AppText style={styles.currentStageEn}>{activeStage.en}</AppText>
                            </View>
                        </View>
                    )}

                    {stageError && (
                        <View style={styles.errorBox}>
                            <AppText style={styles.errorText} numberOfLines={4}>
                                {stageError}
                            </AppText>
                        </View>
                    )}

                    {/* Full stage checklist */}
                    <ScrollView style={styles.stageList} showsVerticalScrollIndicator={false}>
                        {PIPELINE_STAGES.map((stage, i) => {
                            const isDone = i < stageIndex || (overallPercent >= 100 && !stageError);
                            const isActive = i === stageIndex && !stageError && overallPercent < 100;
                            const isPending = i > stageIndex;

                            return (
                                <View key={stage.key} style={styles.stageRow}>
                                    <View style={styles.stageIconWrap}>
                                        {isDone ? (
                                            <FontAwesome5 name="check-circle" size={14} color="#22c55e" solid />
                                        ) : isActive ? (
                                            <Animated.View style={{ opacity: pulseAnim }}>
                                                <FontAwesome5 name="dot-circle" size={14} color="#FFD700" solid />
                                            </Animated.View>
                                        ) : (
                                            <FontAwesome5 name="circle" size={14} color="#475569" />
                                        )}
                                    </View>
                                    <AppText
                                        style={[
                                            styles.stageLabel,
                                            isDone && styles.stageLabelDone,
                                            isActive && styles.stageLabelActive,
                                            isPending && styles.stageLabelPending,
                                        ]}
                                        numberOfLines={1}
                                    >
                                        {stage.th}
                                    </AppText>
                                </View>
                            );
                        })}
                    </ScrollView>

                    <AppText style={styles.statusFooter}>
                        อย่าปิดแอประหว่างการประมวลผล
                    </AppText>
                </View>
            </View>
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
                        <ActivityIndicator size="small" color="#1C1C2E" />
                    ) : (
                        <>
                            <FontAwesome5 name="play" size={16} color="#1C1C2E" />
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
            {/* Pipeline status overlay */}
            {(isLoading || processingAll) && renderStatusPanel()}

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
        backgroundColor: 'rgba(0, 0, 0, 0.88)',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 999,
        paddingHorizontal: 20,
    },

    // ── Status card ──────────────────────────────────────────────────────────
    statusCard: {
        backgroundColor: '#1C1C2E',
        padding: 20,
        borderRadius: 16,
        width: '100%',
        maxWidth: 420,
        borderWidth: 1,
        borderColor: '#FFD700',
    },
    statusHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    statusTitle: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '700',
    },
    statusFileCount: {
        color: '#FFD700',
        fontSize: 13,
        fontWeight: '600',
    },
    statusFileName: {
        color: '#94A3B8',
        fontSize: 12,
        marginTop: 2,
        marginBottom: 12,
    },

    // ── Progress bar ─────────────────────────────────────────────────────────
    barTrack: {
        height: 10,
        borderRadius: 5,
        backgroundColor: '#2d2d4a',
        overflow: 'hidden',
        marginTop: 6,
    },
    barFill: {
        height: '100%',
        borderRadius: 5,
        backgroundColor: '#FFD700',
    },
    barFillError: {
        backgroundColor: '#ef4444',
    },
    barMetaRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 6,
        marginBottom: 12,
    },
    barPercent: {
        color: '#FFD700',
        fontSize: 13,
        fontWeight: '700',
    },
    barElapsed: {
        color: '#94A3B8',
        fontSize: 12,
    },

    // ── Current stage headline ───────────────────────────────────────────────
    currentStageBox: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        backgroundColor: 'rgba(255, 215, 0, 0.08)',
        borderRadius: 10,
        padding: 12,
        borderWidth: 1,
        borderColor: 'rgba(255, 215, 0, 0.25)',
    },
    currentStageTh: {
        color: '#FFFFFF',
        fontSize: 15,
        fontWeight: '600',
    },
    currentStageEn: {
        color: '#94A3B8',
        fontSize: 11,
        marginTop: 2,
    },

    // ── Error box ────────────────────────────────────────────────────────────
    errorBox: {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderRadius: 10,
        padding: 12,
        borderWidth: 1,
        borderColor: 'rgba(239, 68, 68, 0.35)',
    },
    errorText: {
        color: '#fca5a5',
        fontSize: 13,
    },

    // ── Stage checklist ──────────────────────────────────────────────────────
    stageList: {
        marginTop: 14,
        maxHeight: 200,
    },
    stageRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        paddingVertical: 5,
    },
    stageIconWrap: {
        width: 18,
        alignItems: 'center',
    },
    stageLabel: {
        fontSize: 13,
        flex: 1,
    },
    stageLabelDone: {
        color: '#22c55e',
    },
    stageLabelActive: {
        color: '#FFD700',
        fontWeight: '700',
    },
    stageLabelPending: {
        color: '#475569',
    },
    statusFooter: {
        color: '#64748B',
        fontSize: 11,
        textAlign: 'center',
        marginTop: 12,
    },

    // ── Selected images ──────────────────────────────────────────────────────
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