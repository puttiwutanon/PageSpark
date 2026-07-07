/**
 * screens/VideoLesson/VideoLessonScreen.jsx
 * 
 * The landing page for video lessons.
 * Shows a list of all saved lessons fetched from Firestore.
 * From here the user can:
 *   - Tap a lesson to view its episodes → VideoLessonDetailScreen
 *   - Delete a lesson (swipe or press delete)
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  FlatList,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';
import { fetchUserLessons, deleteLesson } from '../../../firebase/lessonFirestore';
import { getAuth } from 'firebase/auth';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(timestamp) {
  if (!timestamp) return '';
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  return date.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getLessonIcon(episodeCount) {
  if (episodeCount >= 3) return 'video';
  if (episodeCount >= 1) return 'play-circle';
  return 'book';
}

// ── Sub-component: single lesson card ──────────────────────────────────────

function LessonCard({ lesson, onPress, onDelete }) {
  const episodeCount = lesson.episodeCount || 0;
  
  return (
    <TouchableOpacity 
      style={cardStyles.card} 
      onPress={() => onPress(lesson)} 
      activeOpacity={0.85}
    >
      <View style={cardStyles.left}>
        <View style={cardStyles.iconBox}>
          <FontAwesome5 name={getLessonIcon(episodeCount)} size={20} color="#fff" />
        </View>
        <View style={cardStyles.info}>
          <AppText style={cardStyles.title} numberOfLines={2}>
            {lesson.title || 'บทเรียนที่ไม่มีชื่อ'}
          </AppText>
          <View style={cardStyles.metaRow}>
            <FontAwesome5 name="play" size={10} color="#888" />
            <AppText style={cardStyles.meta}>
              {episodeCount} ตอน
            </AppText>
            <FontAwesome5 name="calendar-alt" size={10} color="#888" style={{ marginLeft: 12 }} />
            <AppText style={cardStyles.meta}>
              {formatDate(lesson.createdAt)}
            </AppText>
          </View>
        </View>
      </View>

      <TouchableOpacity
        style={cardStyles.deleteBtn}
        onPress={() => onDelete(lesson)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <FontAwesome5 name="trash-alt" size={16} color="#f87171" />
      </TouchableOpacity>
    </TouchableOpacity>
  );
}

// ── Main Screen ──────────────────────────────────────────────────────────────

const VideoLessonScreen = () => {
  const navigation = useNavigation();
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const auth = getAuth();
  const uid = auth.currentUser?.uid;

  const loadLessons = useCallback(async () => {
    if (!uid) {
      setLoading(false);
      return;
    }
    
    try {
      const data = await fetchUserLessons(uid);
      setLessons(data);
    } catch (err) {
      console.error('fetchUserLessons error:', err);
      Alert.alert('ข้อผิดพลาด', 'ไม่สามารถโหลดรายการบทเรียนวิดีโอได้');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [uid]);

  // Reload every time screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadLessons();
    }, [loadLessons]),
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadLessons();
  };

  const handlePressLesson = (lesson) => {
    navigation.navigate('videoLessonDetail', { lesson });
  };

  const handleDelete = (lesson) => {
    Alert.alert(
      'ลบบทเรียน',
      `คุณต้องการลบ "${lesson.title}" และวิดีโอทั้งหมดในบทเรียนนี้ใช่หรือไม่?`,
      [
        { text: 'ยกเลิก', style: 'cancel' },
        {
          text: 'ลบ',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteLesson(lesson.id);
              setLessons((prev) => prev.filter((l) => l.id !== lesson.id));
            } catch (e) {
              Alert.alert('ข้อผิดพลาด', 'ไม่สามารถลบบทเรียนได้');
            }
          },
        },
      ],
    );
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <AppText style={styles.headerTitle}>คลังวิดีโอ</AppText>
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      ) : lessons.length === 0 ? (
        <View style={styles.empty}>
          <FontAwesome5 name="video" size={48} color="#3d3f5a" />
          <AppText style={styles.emptyTitle}>ยังไม่มีวิดีโอ</AppText>
          <AppText style={styles.emptySubtitle}>
            ถ่ายภาพหน้าหนังสือเรียนฟิสิกส์เพื่อให้ AI สร้างวิดีโอบทเรียนให้คุณ
          </AppText>
          <TouchableOpacity
            style={styles.emptyBtn}
            onPress={() => navigation.navigate('home')}
          >
            <FontAwesome5 name="camera" size={16} color="white" />
            <AppText style={styles.emptyBtnText}>ไปถ่ายรูปหน้าเรียน</AppText>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={lessons}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          renderItem={({ item }) => (
            <LessonCard 
              lesson={item} 
              onPress={handlePressLesson} 
              onDelete={handleDelete} 
            />
          )}
          ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        />
      )}
    </SafeAreaView>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    marginTop: '10%',
  },
  headerTitle: {
    fontSize: 26,
    color: '#1e293b',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    padding: 16,
    paddingTop: 8,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 12,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1e293b',
    marginTop: 12,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 22,
  },
  emptyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    marginTop: 8,
  },
  emptyBtnText: {
    color: 'white',
    fontSize: 15,
    fontWeight: '500',
  },
});

const cardStyles = StyleSheet.create({
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    flex: 1,
    gap: 4,
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1e293b',
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  meta: {
    fontSize: 12,
    color: '#94a3b8',
  },
  deleteBtn: {
    padding: 6,
    marginLeft: 8,
  },
});

export default VideoLessonScreen;