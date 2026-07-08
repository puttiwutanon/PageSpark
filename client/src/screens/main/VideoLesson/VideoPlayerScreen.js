/**
 * screens/VideoLesson/VideoPlayerScreen.jsx
 * 
 * TikTok/Shorts-style video player using expo-video with single player.
 * Features:
 *   - Vertical swipe to go to next/previous episode
 *   - Auto-play when visible
 *   - Pause when not visible
 *   - Episode info overlay (title, question, episode number)
 *   - Video fills entire screen
 *   - Hardware back button support
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Dimensions,
  FlatList,
  StatusBar,
  BackHandler,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { VideoView, useVideoPlayer } from 'expo-video';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';

const { width, height } = Dimensions.get('window');

// ── Main Screen ──────────────────────────────────────────────────────────────

const VideoPlayerScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { allEpisodes, initialIndex = 0 } = route.params || {};
  
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [isPlaying, setIsPlaying] = useState(true);
  const flatListRef = useRef(null);

  const episodes = allEpisodes || [];
  const totalEpisodes = episodes.length;
  const currentEpisode = episodes[currentIndex] || null;

  // ── Single player instance ─────────────────────────────────────────────────
  const player = useVideoPlayer(
    currentEpisode?.videoUrl || '',
    player => {
      player.loop = false;
      player.volume = 1.0;
      if (currentEpisode) {
        player.play();
        setIsPlaying(true);
      }
    }
  );

  // ── Handle video changes ──────────────────────────────────────────────────
  useEffect(() => {
    if (currentEpisode && player) {
      // Replace the current video source
      player.replace(currentEpisode.videoUrl);
      player.play();
      setIsPlaying(true);
    }
  }, [currentIndex, player]);

  // ── Handle hardware back button ───────────────────────────────────────────
  useEffect(() => {
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      navigation.goBack();
      return true;
    });

    return () => backHandler.remove();
  }, [navigation]);

  // ── Handle viewable items change ──────────────────────────────────────────
  const onViewableItemsChanged = useCallback(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      const visibleItem = viewableItems[0];
      const newIndex = visibleItem.index;
      
      if (newIndex !== currentIndex && newIndex !== undefined && newIndex < totalEpisodes) {
        setCurrentIndex(newIndex);
      }
    }
  }, [currentIndex, totalEpisodes]);

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 60,
  };

  // Navigate back
  const goBack = () => {
    navigation.goBack();
  };

  // Toggle play/pause
  const togglePlay = () => {
    if (isPlaying) {
      player.pause();
      setIsPlaying(false);
    } else {
      player.play();
      setIsPlaying(true);
    }
  };

  // Go to next episode
  const goToNext = () => {
    if (currentIndex < totalEpisodes - 1) {
      flatListRef.current?.scrollToIndex({
        index: currentIndex + 1,
        animated: true,
      });
    }
  };

  // Go to previous episode
  const goToPrevious = () => {
    if (currentIndex > 0) {
      flatListRef.current?.scrollToIndex({
        index: currentIndex - 1,
        animated: true,
      });
    }
  };

  // Render each video item (just a placeholder - video is rendered once)
  const renderItem = useCallback(({ item, index }) => {
    const isActive = index === currentIndex;
    const duration = item.videoDuration || 0;
    const durationMinutes = Math.floor(duration / 60);
    const durationSeconds = Math.floor(duration % 60);
    const durationStr = durationMinutes > 0 
      ? `${durationMinutes}:${durationSeconds.toString().padStart(2, '0')}`
      : `${durationSeconds}s`;

    return (
      <View style={styles.videoContainer}>
        {/* Only show the video player on the active index */}
        {isActive && (
          <VideoView
            player={player}
            style={styles.video}
            contentFit="cover"
            nativeControls={false}
          />
        )}
        
        {/* Overlay Info */}
        <View style={styles.overlay}>
          <View style={styles.overlayGradient} />
          
          <View style={styles.infoContainer}>
            {/* Episode badge */}
            <View style={styles.episodeBadge}>
              <FontAwesome5 name="play-circle" size={14} color="#ffffff" />
              <AppText style={styles.episodeBadgeText}>
                ตอนที่ {index + 1}
              </AppText>
              <View style={styles.dot} />
              <AppText style={styles.episodeBadgeText}>{durationStr}</AppText>
            </View>
            
            {/* Title */}
            <AppText style={styles.videoTitle} numberOfLines={2}>
              {item.title || `ตอนที่ ${index + 1}`}
            </AppText>
            
            {/* Question title if available */}
            {item.questionTitle && (
              <View style={styles.questionContainer}>
                <FontAwesome5 name="question-circle" size={14} color="#a5b4fc" />
                <AppText style={styles.questionText} numberOfLines={2}>
                  {item.questionTitle}
                </AppText>
              </View>
            )}
          </View>
        </View>
      </View>
    );
  }, [currentIndex, player]);

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
      <StatusBar hidden />
      
      {/* Play/Pause Overlay - positioned absolutely over everything */}
      <TouchableOpacity 
        style={styles.playOverlay} 
        onPress={togglePlay}
        activeOpacity={0.9}
      >
        {!isPlaying && (
          <View style={styles.playIconContainer}>
            <FontAwesome5 name="play" size={40} color="rgba(255,255,255,0.8)" />
          </View>
        )}
      </TouchableOpacity>
      
      {/* Back Button */}
      <TouchableOpacity style={styles.backBtn} onPress={goBack}>
        <FontAwesome5 name="arrow-left" size={22} color="#ffffff" />
      </TouchableOpacity>
      
      {/* Episode Counter */}
      {totalEpisodes > 1 && (
        <View style={styles.counterContainer}>
          <AppText style={styles.counterText}>
            {currentIndex + 1} / {totalEpisodes}
          </AppText>
        </View>
      )}

      {/* Navigation Arrows */}
      {totalEpisodes > 1 && (
        <>
          {currentIndex > 0 && (
            <TouchableOpacity style={styles.prevBtn} onPress={goToPrevious}>
              <FontAwesome5 name="chevron-up" size={24} color="rgba(255,255,255,0.5)" />
            </TouchableOpacity>
          )}
          {currentIndex < totalEpisodes - 1 && (
            <TouchableOpacity style={styles.nextBtn} onPress={goToNext}>
              <FontAwesome5 name="chevron-down" size={24} color="rgba(255,255,255,0.5)" />
            </TouchableOpacity>
          )}
        </>
      )}

      {/* FlatList for vertical swiping */}
      <FlatList
        ref={flatListRef}
        data={episodes}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        snapToInterval={height}
        snapToAlignment="start"
        decelerationRate="fast"
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
        initialScrollIndex={initialIndex}
        getItemLayout={(data, index) => ({
          length: height,
          offset: height * index,
          index,
        })}
        onScrollToIndexFailed={(info) => {
          setTimeout(() => {
            flatListRef.current?.scrollToIndex({
              index: info.index,
              animated: true,
            });
          }, 100);
        }}
      />
      
      {/* Swipe Hint */}
      {totalEpisodes > 1 && (
        <View style={styles.swipeHint}>
          <View style={styles.swipeIndicator}>
            <FontAwesome5 name="chevron-down" size={16} color="rgba(255,255,255,0.3)" />
          </View>
        </View>
      )}
    </SafeAreaView>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  videoContainer: {
    width: width,
    height: height,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  video: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: width,
    height: height,
    backgroundColor: '#000000',
  },
  touchOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 20,
  },
  playIconContainer: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    justifyContent: 'flex-end',
    zIndex: 10,
  },
  overlayGradient: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    opacity: 0.5,
  },
  infoContainer: {
    padding: 20,
    paddingBottom: 40,
  },
  episodeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  episodeBadgeText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.4)',
    marginHorizontal: 4,
  },
  videoTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 6,
    lineHeight: 28,
  },
  questionContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginTop: 4,
  },
  questionText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    flex: 1,
    lineHeight: 20,
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
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 22,
  },
  counterContainer: {
    position: 'absolute',
    top: 50,
    right: 16,
    zIndex: 100,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  counterText: {
    fontSize: 13,
    color: '#ffffff',
    fontWeight: '500',
  },
  swipeHint: {
    position: 'absolute',
    bottom: 120,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 50,
  },
  swipeIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
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
    backgroundColor: '#6366f1',
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