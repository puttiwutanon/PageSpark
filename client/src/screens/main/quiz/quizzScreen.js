/**
 * screens/Quizz/QuizzScreen.jsx
 *
 * The landing page for the quiz feature.
 * Shows a list of all saved quizzes fetched from Firestore.
 * From here the user can:
 *   - Tap a quiz to play it  →  QuizzPlayScreen
 *   - Press "สร้างแบบทดสอบ"  →  QuizzGeneratingScreen
 *   - Swipe-delete a quiz from Firestore
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
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';
import { fetchAllQuizzes, deleteQuiz } from '../../../firebase/quizFirestore'; // adjust path

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(timestamp) {
  if (!timestamp) return '';
  const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
  return date.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ── Sub-component: single quiz card ──────────────────────────────────────────

function QuizCard({ quiz, onPlay, onDelete }) {
  return (
    <TouchableOpacity style={cardStyles.card} onPress={() => onPlay(quiz)} activeOpacity={0.85}>
      <View style={cardStyles.left}>
        <View style={cardStyles.iconBox}>
          <FontAwesome5 name="clipboard-list" size={20} color="#fff" />
        </View>
        <View style={cardStyles.info}>
          <AppText style={cardStyles.title} numberOfLines={2}>{quiz.title}</AppText>
          <AppText style={cardStyles.meta}>
            {quiz.totalQuestions} ข้อ · {formatDate(quiz.createdAt)}
          </AppText>
        </View>
      </View>

      <TouchableOpacity
        style={cardStyles.deleteBtn}
        onPress={() => onDelete(quiz)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <FontAwesome5 name="trash-alt" size={16} color="#f87171" />
      </TouchableOpacity>
    </TouchableOpacity>
  );
}

// ── Main Screen ───────────────────────────────────────────────────────────────

const QuizzScreen = () => {
  const navigation = useNavigation();
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Reload every time screen comes into focus (e.g. after generating a new quiz)
  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);

      fetchAllQuizzes()
        .then((data) => { if (active) setQuizzes(data); })
        .catch((err) => {
          console.error('fetchAllQuizzes error:', err);
          Alert.alert('ข้อผิดพลาด', 'ไม่สามารถโหลดรายการแบบทดสอบได้');
        })
        .finally(() => { if (active) setLoading(false); });

      return () => { active = false; };
    }, []),
  );

  const handlePlay = (quiz) => {
    navigation.navigate('quizzPlay', { quiz });
  };

  const handleDelete = (quiz) => {
    Alert.alert(
      'ลบแบบทดสอบ',
      `คุณต้องการลบ "${quiz.title}" ใช่หรือไม่?`,
      [
        { text: 'ยกเลิก', style: 'cancel' },
        {
          text: 'ลบ',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteQuiz(quiz.id);
              setQuizzes((prev) => prev.filter((q) => q.id !== quiz.id));
            } catch (e) {
              Alert.alert('ข้อผิดพลาด', 'ไม่สามารถลบแบบทดสอบได้');
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
        <AppText style={styles.headerTitle}>แบบทดสอบ</AppText>
        <TouchableOpacity
          style={styles.createBtn}
          onPress={() => navigation.navigate('quizzGenerator')}
          activeOpacity={0.85}
        >
          <FontAwesome5 name="plus" size={14} color="white" />
          <AppText style={styles.createBtnText}>สร้างใหม่</AppText>
        </TouchableOpacity>
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#c6cdfc" />
        </View>
      ) : quizzes.length === 0 ? (
        <View style={styles.empty}>
          <FontAwesome5 name="book-open" size={48} color="#3d3f5a" />
          <AppText style={styles.emptyTitle}>ยังไม่มีแบบทดสอบ</AppText>
          <AppText style={styles.emptySubtitle}>
            กดปุ่ม "สร้างใหม่" เพื่อให้ AI สร้างชุดข้อสอบฟิสิกส์สำหรับคุณ
          </AppText>
          <TouchableOpacity
            style={styles.emptyBtn}
            onPress={() => navigation.navigate('quizzGenerator')}
          >
            <FontAwesome5 name="magic" size={16} color="white" />
            <AppText style={styles.emptyBtnText}>สร้างแบบทดสอบแรก</AppText>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={quizzes}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <QuizCard quiz={item} onPlay={handlePlay} onDelete={handleDelete} />
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
    experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)'
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    marginTop: '10%'
  },
  headerTitle: {
    fontSize: 26,
    color: '#334155',
  },
  createBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
  },
  createBtnText: {
    color: 'white',
    fontSize: 14,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    padding: 16,
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
    color: '#e2e8f0',
    marginTop: 12,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#888',
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
  },
});

const cardStyles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
    color: '#334155',
    lineHeight: 20,
  },
  meta: {
    fontSize: 12,
    color: '#888',
  },
  deleteBtn: {
    padding: 6,
    marginLeft: 8,
  },
});

export default QuizzScreen;