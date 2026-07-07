/**
 * screens/VideoLesson/VideoPlayerScreen.jsx
 * 
 * Simple video player that opens videos in the device's native player.
 * No expo-av required - uses React Native's Linking API.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Dimensions,
  StatusBar,
  ActivityIndicator,
  ScrollView,
  Linking,
  Alert,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';

const { width, height } = Dimensions.get('window');

// ── Video Player Screen ──────────────────────────────────────────────────────

const VideoPlayerScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { allEpisodes, initialIndex = 0 } = route.params || {};
  
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [isOpening, setIsOpening] = useState(false);

  const episodes = allEpisodes || [];
  const totalEpisodes = episodes.length;
  const currentEpisode = episodes[currentIndex] || null;

  // Open video in external player
  const openVideo = async (videoUrl) => {
    try {
      setIsOpening(true);
      const supported = await Linking.canOpenURL(videoUrl);
      if (supported) {
        await Linking.openURL(videoUrl);
      } else {
        Alert.alert('ไม่สามารถเปิดวิดีโอได้', 'กรุณาติดตั้งแอปที่รองรับการเล่นวิดีโอ');
      }
    } catch (error) {
      console.error('Error opening video:', error);
      Alert.alert('ข้อผิดพลาด', 'ไม่สามารถเปิดวิดีโอได้');
    } finally {
      setIsOpening(false);
    }
  };

  // Auto-open first video when screen loads
  useEffect(() => {
    if (currentEpisode?.videoUrl) {
      openVideo(currentEpisode.videoUrl);
    }
  }, []);

  // Navigate back
  const goBack = () => {
    navigation.goBack();
  };

  // Go to next episode
  const goToNext = () => {
    if (currentIndex < totalEpisodes - 1) {
      const nextIndex = currentIndex + 1;
      setCurrentIndex(nextIndex);
      if (episodes[nextIndex]?.videoUrl) {
        openVideo(episodes[nextIndex].videoUrl);
      }
    } else {
      Alert.alert('สิ้นสุด', 'คุณดูวิดีโอทั้งหมดในบทเรียนนี้แล้ว');
    }
  };

  // Go to previous episode
  const goToPrevious = () => {
    if (currentIndex > 0) {
      const prevIndex = currentIndex - 1;
      setCurrentIndex(prevIndex);
      if (episodes[prevIndex]?.videoUrl) {
        openVideo(episodes[prevIndex].videoUrl);
      }
    }
  };

  const duration = currentEpisode?.videoDuration || 0;
  const durationMinutes = Math.floor(duration / 60);
  const durationSeconds = Math.floor(duration % 60);
  const durationStr = durationMinutes > 0 
    ? `${durationMinutes}:${durationSeconds.toString().padStart(2, '0')}`
    : `${durationSeconds}s`;

  // ── Render ──────────────────────────────────────────────────────────────────

  if (totalEpisodes === 0) {
    return (
      <SafeAreaView style={styles.errorContainer}>
        <FontAwesome5 name="video-slash" size={48} color="#94a3b8" />
        <AppText style={styles.errorText}>ไม่พบวิดีโอ</AppText>
        <TouchableOpacity style={styles.backButton} onPress={goBack}>
          <AppText style={styles.backButtonText}>กลับ</AppText>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Back Button */}
      <TouchableOpacity style={styles.backBtn} onPress={goBack}>
        <FontAwesome5 name="arrow-left" size={22} color="#ffffff" />
      </TouchableOpacity>
      
      {/* Episode Counter */}
      <View style={styles.counterContainer}>
        <AppText style={styles.counterText}>
          {currentIndex + 1} / {totalEpisodes}
        </AppText>
      </View>

      {/* Main Content */}
      <View style={styles.contentContainer}>
        {/* Video Info Card */}
        <View style={styles.videoInfoCard}>
          <View style={styles.iconContainer}>
            <FontAwesome5 name="play-circle" size={48} color="#818cf8" />
          </View>
          
          <AppText style={styles.episodeNumber}>
            ตอนที่ {currentIndex + 1}
          </AppText>
          
          <AppText style={styles.videoTitle} numberOfLines={3}>
            {currentEpisode?.title || `ตอนที่ ${currentIndex + 1}`}
          </AppText>
          
          {currentEpisode?.questionTitle && (
            <View style={styles.questionContainer}>
              <FontAwesome5 name="question-circle" size={14} color="#a5b4fc" />
              <AppText style={styles.questionText} numberOfLines={2}>
                {currentEpisode.questionTitle}
              </AppText>
            </View>
          )}
          
          <View style={styles.metaContainer}>
            <View style={styles.metaItem}>
              <FontAwesome5 name="clock" size={14} color="#94a3b8" />
              <AppText style={styles.metaText}>{durationStr}</AppText>
            </View>
            <View style={styles.metaDivider} />
            <View style={styles.metaItem}>
              <FontAwesome5 name="video" size={14} color="#94a3b8" />
              <AppText style={styles.metaText}>ตอนที่ {currentIndex + 1}</AppText>
            </View>
          </View>

          {/* Play Button */}
          <TouchableOpacity 
            style={styles.playButton}
            onPress={() => {
              if (currentEpisode?.videoUrl) {
                openVideo(currentEpisode.videoUrl);
              }
            }}
            disabled={isOpening}
          >
            {isOpening ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <>
                <FontAwesome5 name="play" size={18} color="#ffffff" />
                <AppText style={styles.playButtonText}>เปิดดูวิดีโอ</AppText>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Navigation Buttons */}
        <View style={styles.navContainer}>
          <TouchableOpacity 
            style={[styles.navBtn, currentIndex === 0 && styles.navBtnDisabled]}
            onPress={goToPrevious}
            disabled={currentIndex === 0}
          >
            <FontAwesome5 name="chevron-up" size={18} color={currentIndex > 0 ? "#ffffff" : "rgba(255,255,255,0.3)"} />
            <AppText style={[styles.navText, currentIndex === 0 && styles.navTextDisabled]}>
              ก่อนหน้า
            </AppText>
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.navBtn, currentIndex === totalEpisodes - 1 && styles.navBtnDisabled]}
            onPress={goToNext}
            disabled={currentIndex === totalEpisodes - 1}
          >
            <AppText style={[styles.navText, currentIndex === totalEpisodes - 1 && styles.navTextDisabled]}>
              ถัดไป
            </AppText>
            <FontAwesome5 name="chevron-down" size={18} color={currentIndex < totalEpisodes - 1 ? "#ffffff" : "rgba(255,255,255,0.3)"} />
          </TouchableOpacity>
        </View>

        {/* Episode List at bottom */}
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false}
          style={styles.episodeList}
          contentContainerStyle={styles.episodeListContent}
        >
          {episodes.map((ep, index) => (
            <TouchableOpacity
              key={ep.id}
              style={[
                styles.episodeDot,
                index === currentIndex && styles.episodeDotActive
              ]}
              onPress={() => {
                if (index !== currentIndex) {
                  setCurrentIndex(index);
                  if (ep.videoUrl) {
                    openVideo(ep.videoUrl);
                  }
                }
              }}
            >
              <AppText style={[
                styles.episodeDotText,
                index === currentIndex && styles.episodeDotTextActive
              ]}>
                {index + 1}
              </AppText>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)',
  },
  backBtn: {
    position: 'absolute',
    top: 50,
    left: 16,
    zIndex: 100,
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 22,
  },
  counterContainer: {
    position: 'absolute',
    top: 50,
    right: 16,
    zIndex: 100,
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  counterText: {
    fontSize: 13,
    color: '#ffffff',
    fontWeight: '500',
  },
  contentContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 100,
    paddingBottom: 40,
  },
  videoInfoCard: {
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
    borderRadius: 20,
    padding: 32,
    width: '100%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(129, 140, 248, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  episodeNumber: {
    fontSize: 14,
    color: '#a5b4fc',
    fontWeight: '500',
    marginBottom: 8,
  },
  videoTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 8,
    lineHeight: 30,
  },
  questionContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginTop: 4,
    marginBottom: 12,
  },
  questionText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    flex: 1,
    textAlign: 'center',
    lineHeight: 20,
  },
  metaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 13,
    color: '#94a3b8',
  },
  metaDivider: {
    width: 1,
    height: 16,
    backgroundColor: 'rgba(255,255,255,0.1)',
    marginHorizontal: 12,
  },
  playButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: '#818cf8',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 14,
    width: '100%',
  },
  playButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  navContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginTop: 16,
    gap: 12,
  },
  navBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
    flex: 1,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  navBtnDisabled: {
    opacity: 0.3,
  },
  navText: {
    fontSize: 13,
    color: '#ffffff',
  },
  navTextDisabled: {
    color: 'rgba(255,255,255,0.3)',
  },
  episodeList: {
    marginTop: 16,
    maxHeight: 50,
  },
  episodeListContent: {
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 8,
  },
  episodeDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  episodeDotActive: {
    backgroundColor: '#818cf8',
    borderColor: '#818cf8',
  },
  episodeDotText: {
    fontSize: 12,
    color: '#94a3b8',
    fontWeight: '500',
  },
  episodeDotTextActive: {
    color: '#ffffff',
  },
  errorContainer: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    gap: 16,
  },
  errorText: {
    fontSize: 18,
    color: '#94a3b8',
  },
  backButton: {
    backgroundColor: '#818cf8',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '500',
  },
});

export default VideoPlayerScreen;