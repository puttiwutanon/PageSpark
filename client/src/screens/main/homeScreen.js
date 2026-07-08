import React, { useState, useCallback } from 'react';
import { 
    View, 
    TouchableOpacity, 
    SafeAreaView,
    FlatList,
    ActivityIndicator,
    ScrollView,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import AppText from '../../components/appText';        
import { homeScreenStyle } from '../../styles/homeScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import { getAuth } from 'firebase/auth';
import { fetchUserLessons } from '../../firebase/lessonFirestore';
import { fetchAllQuizzes } from '../../firebase/quizFirestore';

const HomeScreen = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(true);
  const [recentItems, setRecentItems] = useState([]);
  const auth = getAuth();
  const uid = auth.currentUser?.uid;

  // ── Load recent activity ──────────────────────────────────────────────────

  const loadRecentActivity = useCallback(async () => {
    if (!uid) {
      setLoading(false);
      return;
    }

    try {
      // Fetch lessons and quizzes
      const lessons = await fetchUserLessons(uid);
      const quizzes = await fetchAllQuizzes();

      // Format items with timestamps
      const lessonItems = lessons.map(lesson => ({
        id: lesson.id,
        type: 'lesson',
        title: lesson.title || 'บทเรียน',
        subtitle: `${lesson.episodeCount || 0} ตอน`,
        icon: 'video',
        color: '#818cf8',
        timestamp: lesson.createdAt || new Date(),
        onPress: () => navigation.navigate('videoLessonDetail', { lesson }),
      }));

      const quizItems = quizzes.map(quiz => ({
        id: quiz.id,
        type: 'quiz',
        title: quiz.title || 'แบบทดสอบ',
        subtitle: `${quiz.questions?.length || 0} ข้อ`,
        icon: 'clipboard-list',
        color: '#a78bfa',
        timestamp: quiz.createdAt || new Date(),
        onPress: () => navigation.navigate('quizzPlay', { quiz }),
      }));

      // Combine and sort by date (newest first)
      const allItems = [...lessonItems, ...quizItems];
      allItems.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

      // Take only the 5 most recent
      setRecentItems(allItems.slice(0, 5));
    } catch (error) {
      console.error('Error loading recent activity:', error);
    } finally {
      setLoading(false);
    }
  }, [uid, navigation]);

  // Reload when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadRecentActivity();
    }, [loadRecentActivity])
  );

  // ── Format date ──────────────────────────────────────────────────────────

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // If less than 24 hours, show relative time
    if (diff < 24 * 60 * 60 * 1000) {
      const hours = Math.floor(diff / (60 * 60 * 1000));
      if (hours < 1) {
        const minutes = Math.floor(diff / (60 * 1000));
        return minutes < 1 ? 'เมื่อสักครู่' : `${minutes} นาทีที่แล้ว`;
      }
      return `${hours} ชั่วโมงที่แล้ว`;
    }
    
    return date.toLocaleDateString('th-TH', { 
      day: 'numeric', 
      month: 'short',
    });
  };

  // ── Render recent item ──────────────────────────────────────────────────

  const renderRecentItem = ({ item }) => (
    <TouchableOpacity 
      style={homeScreenStyle.recentItem} 
      onPress={item.onPress}
      activeOpacity={0.7}
    >
      <View style={[homeScreenStyle.recentIcon, { backgroundColor: `${item.color}20` }]}>
        <FontAwesome5 name={item.icon} size={18} color={item.color} />
      </View>
      <View style={homeScreenStyle.recentInfo}>
        <AppText style={homeScreenStyle.recentTitle} numberOfLines={1}>
          {item.title}
        </AppText>
        <AppText style={homeScreenStyle.recentSubtitle}>
          {item.subtitle}
        </AppText>
      </View>
      <View style={homeScreenStyle.recentRight}>
        <AppText style={homeScreenStyle.recentTime}>
          {formatDate(item.timestamp)}
        </AppText>
        <FontAwesome5 name="chevron-right" size={12} color="#64748b" />
      </View>
    </TouchableOpacity>
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={homeScreenStyle.homeContainer}>
      <View style={homeScreenStyle.welcomeContainer}>
        <AppText style={homeScreenStyle.welcomeText}>ยินดีต้อนรับสู่ PageSpark👋</AppText>
        <AppText style={homeScreenStyle.subText}>เลือกสิ่งที่คุณต้องการ</AppText>
      </View>

      <View style={homeScreenStyle.routeToFunctionContainer}>
        <TouchableOpacity style={homeScreenStyle.routeToFunction} onPress={() => navigation.navigate('camera')}>
          <AppText style={{ fontSize: 16, color: 'white' }}>สรุปบทเรียน</AppText>
          <FontAwesome5 name="chalkboard-teacher" size={24} color="white" />
        </TouchableOpacity>

        <TouchableOpacity style={homeScreenStyle.routeToFunction} onPress={() => navigation.navigate('quizz')}>
          <AppText style={{ fontSize: 16, color: 'white' }}>ทำแบบทดสอบ</AppText>
          <FontAwesome5 name="book" size={24} color="white" />
        </TouchableOpacity>
      </View>

      <View style={homeScreenStyle.recentActivityContainer}>
        <View style={homeScreenStyle.recentActivityHeader}>
          <AppText style={homeScreenStyle.recentHeaderTitle}>กิจกรรมล่าสุด</AppText>
          <TouchableOpacity onPress={() => navigation.navigate('videoLesson')}>
            <AppText style={homeScreenStyle.seeAllText}>ดูทั้งหมด</AppText>
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={homeScreenStyle.recentLoading}>
            <ActivityIndicator size="small" color="#818cf8" />
          </View>
        ) : recentItems.length === 0 ? (
          <View style={homeScreenStyle.recentEmpty}>
            <FontAwesome5 name="inbox" size={28} color="#4a4a6a" />
            <AppText style={homeScreenStyle.recentEmptyText}>
              ยังไม่มีกิจกรรมล่าสุด
            </AppText>
            <AppText style={homeScreenStyle.recentEmptySubtext}>
              สร้างวิดีโอหรือแบบทดสอบเพื่อเริ่มต้น
            </AppText>
          </View>
        ) : (
          <FlatList
            data={recentItems}
            renderItem={renderRecentItem}
            keyExtractor={(item) => `${item.type}_${item.id}`}
            contentContainerStyle={homeScreenStyle.recentList}
            showsVerticalScrollIndicator={false}
          />
        )}
      </View>
    </SafeAreaView>
  );
};

export default HomeScreen;