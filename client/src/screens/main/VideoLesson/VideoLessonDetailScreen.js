/**
 * screens/VideoLesson/VideoLessonDetailScreen.jsx
 * 
 * Shows all episodes for a lesson as a simple list.
 * Tap an episode → navigate to VideoPlayerScreen.
 * Clean, simple, and works without any video rendering issues.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  FlatList,
  ActivityIndicator,
  Alert,
  Dimensions,
  StatusBar,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';
import { fetchLessonVideos } from '../../../firebase/lessonFirestore';

const { width } = Dimensions.get('window');

// ── Episode Card ────────────────────────────────────────────────────────────

function EpisodeCard({ episode, episodeNumber, onPress }) {
  const duration = episode.videoDuration || 0;
  const durationMinutes = Math.floor(duration / 60);
  const durationSeconds = Math.floor(duration % 60);
  const durationStr = durationMinutes > 0 
    ? `${durationMinutes}:${durationSeconds.toString().padStart(2, '0')}`
    : `${durationSeconds}s`;

  return (
    <TouchableOpacity 
      style={cardStyles.card} 
      onPress={() => onPress(episode)}
      activeOpacity={0.7}
    >
      <View style={cardStyles.left}>
        <View style={cardStyles.numberBadge}>
          <AppText style={cardStyles.numberText}>{episodeNumber}</AppText>
        </View>
        <View style={cardStyles.info}>
          <AppText style={cardStyles.title} numberOfLines={2}>
            {episode.title || `ตอนที่ ${episodeNumber}`}
          </AppText>
          <View style={cardStyles.metaRow}>
            <FontAwesome5 name="clock" size={10} color="#94a3b8" />
            <AppText style={cardStyles.meta}>{durationStr}</AppText>
            {episode.questionTitle && (
              <>
                <FontAwesome5 name="question-circle" size={10} color="#94a3b8" style={{ marginLeft: 12 }} />
                <AppText style={cardStyles.meta} numberOfLines={1}>
                  {episode.questionTitle}
                </AppText>
              </>
            )}
          </View>
        </View>
      </View>
      <FontAwesome5 name="chevron-right" size={16} color="#cbd5e1" />
    </TouchableOpacity>
  );
}

// ── Main Screen ──────────────────────────────────────────────────────────────

const VideoLessonDetailScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { lesson } = route.params;
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const flatListRef = useRef(null);

  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    try {
      const data = await fetchLessonVideos(lesson.id);
      setVideos(data);
    } catch (err) {
      console.error('fetchLessonVideos error:', err);
      Alert.alert('ข้อผิดพลาด', 'ไม่สามารถโหลดวิดีโอในบทเรียนนี้ได้');
    } finally {
      setLoading(false);
    }
  };

  const handlePressEpisode = (episode) => {
    // Navigate to video player with all episodes
    navigation.navigate('videoPlayer', {
      allEpisodes: videos,
      initialIndex: videos.findIndex(v => v.id === episode.id),
    });
  };

  const totalDuration = videos.reduce((sum, v) => sum + (v.videoDuration || 0), 0);
  const totalMinutes = Math.floor(totalDuration / 60);
  const totalSeconds = Math.floor(totalDuration % 60);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity 
          onPress={() => navigation.goBack()} 
          style={styles.backBtn}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <FontAwesome5 name="arrow-left" size={20} color="#1e293b" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <AppText style={styles.headerTitle} numberOfLines={1}>
            {lesson.title || 'บทเรียน'}
          </AppText>
        </View>
        <View style={styles.headerRight} />
      </View>

      {/* Lesson Summary */}
      <View style={styles.summary}>
        <View style={styles.summaryItem}>
          <FontAwesome5 name="play-circle" size={18} color="#6366f1" />
          <AppText style={styles.summaryText}>{videos.length} ตอน</AppText>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <FontAwesome5 name="clock" size={18} color="#6366f1" />
          <AppText style={styles.summaryText}>
            {totalMinutes > 0 ? `${totalMinutes}นาที` : `${totalSeconds}วินาที`}
          </AppText>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <FontAwesome5 name="calendar-alt" size={18} color="#6366f1" />
          <AppText style={styles.summaryText}>
            {lesson.createdAt?.toLocaleDateString?.('th-TH') || ''}
          </AppText>
        </View>
      </View>

      {/* Episode List */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      ) : videos.length === 0 ? (
        <View style={styles.empty}>
          <FontAwesome5 name="video-slash" size={40} color="#cbd5e1" />
          <AppText style={styles.emptyTitle}>ไม่มีวิดีโอในบทเรียนนี้</AppText>
          <AppText style={styles.emptySubtitle}>
            บทเรียนนี้ยังไม่มีวิดีโอที่สร้างเสร็จสมบูรณ์
          </AppText>
        </View>
      ) : (
        <FlatList
          ref={flatListRef}
          data={videos}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          renderItem={({ item, index }) => (
            <EpisodeCard 
              episode={item} 
              episodeNumber={index + 1}
              onPress={handlePressEpisode}
            />
          )}
          ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
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
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    marginTop: '10%',
  },
  backBtn: {
    padding: 4,
    width: 40,
  },
  headerCenter: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
  },
  headerRight: {
    width: 40,
  },
  summary: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff',
    marginHorizontal: 16,
    marginBottom: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  summaryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  summaryText: {
    fontSize: 13,
    color: '#475569',
    fontWeight: '500',
  },
  summaryDivider: {
    width: 1,
    height: 20,
    backgroundColor: '#e2e8f0',
    marginHorizontal: 16,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    padding: 16,
    paddingTop: 4,
    paddingBottom: 30,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginTop: 8,
  },
  emptySubtitle: {
    fontSize: 13,
    color: '#94a3b8',
    textAlign: 'center',
  },
});

const cardStyles = StyleSheet.create({
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  numberBadge: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#f1f5f9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  numberText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#64748b',
  },
  info: {
    flex: 1,
    gap: 3,
  },
  title: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1e293b',
    lineHeight: 19,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  meta: {
    fontSize: 11,
    color: '#94a3b8',
  },
});

export default VideoLessonDetailScreen;