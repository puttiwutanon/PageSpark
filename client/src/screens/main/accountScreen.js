import React, { useState, useCallback } from 'react';
import { 
    View, 
    TouchableOpacity, 
    SafeAreaView,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import AppText from '../../components/appText';        
import { accountScreenStyle } from '../../styles/accountScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import FontAwesome from '@expo/vector-icons/FontAwesome';
import { PieChart } from "react-native-gifted-charts";
import { signOut } from 'firebase/auth';
import { auth } from '../../firebase/firebaseConfig';
import { getAuth } from 'firebase/auth';
import { fetchAllQuizzes } from '../../firebase/quizFirestore';
import { fetchUserLessons } from '../../firebase/lessonFirestore';

const AccountScreen = () => {
    const navigation = useNavigation();
    const [loading, setLoading] = useState(true);
    const [quizStats, setQuizStats] = useState({
        totalCorrect: 0,
        totalQuestions: 0,
        percentage: 0,
        totalQuizzes: 0,
        attemptedQuizzes: 0,
    });
    const [videoStats, setVideoStats] = useState({
        totalVideos: 0,
        totalLessons: 0,
    });

    const authInstance = getAuth();
    const uid = authInstance.currentUser?.uid;

    // ── Load stats ──────────────────────────────────────────────────────────────

    const loadStats = useCallback(async () => {
        if (!uid) {
            setLoading(false);
            return;
        }

        try {
            // ── Fetch quizzes ──────────────────────────────────────────────────
            const quizzes = await fetchAllQuizzes();
            
            let totalCorrect = 0;
            let totalQuestions = 0;
            let totalQuizzes = quizzes.length;
            let attemptedQuizzes = 0;

            // Count questions from all quizzes (even if not attempted yet)
            quizzes.forEach(quiz => {
                const questionCount = quiz.questions?.length || 0;
                totalQuestions += questionCount;
                
                // Check if this quiz has been attempted (has results)
                if (quiz.results && quiz.results.length > 0) {
                    attemptedQuizzes++;
                    quiz.results.forEach(result => {
                        if (result.isCorrect) {
                            totalCorrect++;
                        }
                    });
                }
            });

            const percentage = totalQuestions > 0 
                ? Math.round((totalCorrect / totalQuestions) * 100) 
                : 0;

            setQuizStats({
                totalCorrect,
                totalQuestions,
                percentage,
                totalQuizzes,
                attemptedQuizzes,
            });

            // ── Fetch videos ──────────────────────────────────────────────────
            const lessons = await fetchUserLessons(uid);
            let totalVideos = 0;
            
            lessons.forEach(lesson => {
                totalVideos += lesson.episodeCount || 0;
            });

            setVideoStats({
                totalVideos,
                totalLessons: lessons.length,
            });

        } catch (error) {
            console.error('Error loading stats:', error);
        } finally {
            setLoading(false);
        }
    }, [uid]);

    // Reload when screen comes into focus
    useFocusEffect(
        useCallback(() => {
            loadStats();
        }, [loadStats])
    );

    // ── Pie chart data ──────────────────────────────────────────────────────

    const pieData = quizStats.totalQuestions > 0 
        ? [
            { 
                value: quizStats.percentage, 
                color: '#818cf8', 
                text: `${quizStats.percentage}%` 
            },
            { 
                value: 100 - quizStats.percentage, 
                color: '#2d2d4a' 
            }
        ]
        : [
            { value: 0, color: '#2d2d4a' },
            { value: 100, color: '#2d2d4a' }
        ];

    // ── Handle logout ──────────────────────────────────────────────────────────

    const handleLogout = async () => {
        try {
            await signOut(auth);
            navigation.replace('Login');
        } catch (error) {
            console.error("Firebase Signout Error:", error.message);
            Alert.alert(
                "เกิดข้อผิดพลาด",
                "ไม่สามารถออกจากระบบได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง",
                [{ text: "ตกลง" }]
            );
        }
    };

    // ── Render ──────────────────────────────────────────────────────────────────

    return (
        <SafeAreaView style={accountScreenStyle.profileContainer}>
            <View style={accountScreenStyle.profileHeader}>
                <FontAwesome5 name="user-alt" size={100} color="#334155" />
                <AppText style={accountScreenStyle.welcomeText}>USER PROFILE</AppText>
            </View>

            <View style={{ width: '90%', alignItems: 'center', marginTop: '5%', backgroundColor: 'rgba(128, 128, 128, 0.27)', padding: 20, borderRadius: 16 }}>
                
                {loading ? (
                    <ActivityIndicator size="large" color="#818cf8" style={{ marginVertical: 40 }} />
                ) : (
                    <>
                        <View style={{ alignItems: 'center', marginVertical: 2 }}>
                            <AppText style={{ fontSize: 18, marginBottom: 15, color: '#FFF' }}>
                                สถิติการทำแบบทดสอบหลังเรียน
                            </AppText>
                            
                            <PieChart
                                data={pieData}
                                donut
                                radius={90}
                                innerRadius={60}
                                innerCircleColor={'#0F172A'}
                                centerLabelComponent={() => {
                                    return (
                                        <View style={{ justifyContent: 'center', alignItems: 'center' }}>
                                            <AppText style={{ fontSize: 22, color: 'white', fontWeight: 'bold' }}>
                                                {quizStats.totalQuestions > 0 ? `${quizStats.percentage}%` : '0%'}
                                            </AppText>
                                            <AppText style={{ fontSize: 12, color: '#64748B' }}>
                                                ถูกต้องเฉลี่ย
                                            </AppText>
                                            {quizStats.attemptedQuizzes > 0 ? (
                                                <AppText style={{ fontSize: 10, color: '#4a4a6a', marginTop: 2 }}>
                                                    ทำไปแล้ว {quizStats.attemptedQuizzes} ชุด
                                                </AppText>
                                            ) : (
                                                <AppText style={{ fontSize: 10, color: '#4a4a6a', marginTop: 2 }}>
                                                    ยังไม่ได้ทำ
                                                </AppText>
                                            )}
                                        </View>
                                    );
                                }}
                            />
                        </View>

                        <View style={accountScreenStyle.accountInfoContainer}>
                            <View style={accountScreenStyle.routeToFunction}>
                                <FontAwesome5 name="clipboard-list" size={18} color="#FFFFFF" />
                                <AppText style={{ fontSize: 12, color: '#FFFFFF', textAlign: 'center', marginTop: 4 }}>
                                    แบบทดสอบที่สร้าง
                                </AppText>
                                <AppText style={{ fontSize: 20, color: '#FFFFFF', fontWeight: 'bold' }}>
                                    {quizStats.totalQuizzes}
                                </AppText>
                                <AppText style={{ fontSize: 11, color: '#64748B' }}>
                                    {quizStats.totalQuestions} ข้อ
                                </AppText>
                                {quizStats.attemptedQuizzes > 0 && (
                                    <AppText style={{ fontSize: 10, color: '#4a7a4a' }}>
                                        ✅ ทำแล้ว {quizStats.attemptedQuizzes} ชุด
                                    </AppText>
                                )}
                            </View>

                            <View style={accountScreenStyle.routeToFunction}>
                                <FontAwesome5 name="video" size={18} color="#FFFFFF" />
                                <AppText style={{ fontSize: 12, color: '#FFFFFF', textAlign: 'center', marginTop: 4 }}>
                                    คลิปวิดีโอที่สร้าง
                                </AppText>
                                <AppText style={{ fontSize: 20, color: '#FFFFFF', fontWeight: 'bold' }}>
                                    {videoStats.totalVideos}
                                </AppText>
                                <AppText style={{ fontSize: 11, color: '#64748B' }}>
                                    {videoStats.totalLessons} บทเรียน
                                </AppText>
                            </View>
                        </View>
                    </>
                )}
            </View>

            <View style={accountScreenStyle.logoutContainer}>
                <TouchableOpacity style={accountScreenStyle.logoutButton} onPress={handleLogout}>
                    <FontAwesome name="sign-out" size={24} color="white" />
                    <AppText style={{ fontSize: 16, color: 'white' }}>ออกจากระบบ</AppText>
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
};

export default AccountScreen;