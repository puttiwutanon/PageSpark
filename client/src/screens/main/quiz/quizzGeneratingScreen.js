/**
 * screens/Quizz/QuizzGeneratingScreen.jsx
 *
 * 1. User picks topics + questions-per-topic
 * 2. POST to /api/generate-quiz
 * 3. Save result to Firestore via saveQuizToFirestore()
 * 4. Navigate BACK to QuizzScreen (which reloads on focus)
 *    — NOT directly to the quiz player
 */

import React, { useState } from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';
import axios from 'axios';
import { saveQuizToFirestore } from '../../../firebase/quizFirestore'; // adjust path

// ── Constants ─────────────────────────────────────────────────────────────────

const PHYSICS_TOPICS = [
  { id: 'mechanics_1',          name: 'กลศาสตร์ 1 (การเคลื่อนที่แนวตรง, นิวตัน, สมดุลกล)' },
  { id: 'mechanics_2',          name: 'กลศาสตร์ 2 (งานและพลังงาน, โมเมนตัม, การเคลื่อนที่แนวโค้ง)' },
  { id: 'waves_light_sound',    name: 'คลื่น เสียง และแสง' },
  { id: 'electricity_magnetism',name: 'ไฟฟ้าสถิต, ไฟฟ้ากระแส, และแม่เหล็ก' },
  { id: 'thermal_matter',       name: 'ความร้อน แก๊ส และของไหล' },
  { id: 'modern_physics',       name: 'ฟิสิกส์อะตอม, นิวเคลียร์ และฟิสิกส์อนุภาค' },
];

const COUNT_OPTIONS = [5, 10, 15, 20, 25, 30];

const API_BASE = 'https://pagespark-api-663555450350.asia-southeast1.run.app';

// ── Main Component ────────────────────────────────────────────────────────────

const QuizzGeneratingScreen = () => {
  const navigation = useNavigation();

  const [selectedTopics, setSelectedTopics]       = useState([]);
  const [questionsPerTopic, setQuestionsPerTopic] = useState(5);
  const [isLoading, setIsLoading]                 = useState(false);
  const [loadingStep, setLoadingStep]             = useState('');   // status string for UX

  // ── Topic toggle ────────────────────────────────────────────────────────────

  const handleSelectTopic = (id) => {
    setSelectedTopics((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    );
  };

  // ── Generate + save ─────────────────────────────────────────────────────────

  const handleGenerateQuiz = async () => {
    if (selectedTopics.length === 0) {
      Alert.alert('กรุณาเลือกหัวข้อ', 'เลือกหัวข้ออย่างน้อย 1 หัวข้อก่อนสร้างข้อสอบ');
      return;
    }

    setIsLoading(true);
    setLoadingStep('กำลังสร้างข้อสอบด้วย AI...');

    try {
      // Step 1 — Call the API
      const response = await axios.post(`${API_BASE}/api/generate-quiz`, {
        topics: selectedTopics,
        questions_per_topic: questionsPerTopic,
      });

      if (!response.data?.quizzes?.length) {
        throw new Error('API returned no questions');
      }

      // Step 2 — Save to Firestore
      setLoadingStep('กำลังบันทึกไปยัง Firestore...');
      const topicNames = selectedTopics.map(
        (id) => PHYSICS_TOPICS.find((t) => t.id === id)?.name ?? id,
      );

      await saveQuizToFirestore(
        selectedTopics,
        questionsPerTopic,
        response.data.quizzes,
        topicNames,
      );

      // Step 3 — Navigate BACK to QuizzScreen (which will reload its list)
      navigation.goBack();

    } catch (error) {
      console.error('Quiz generation error:', error.response?.data ?? error);
      Alert.alert(
        'เกิดข้อผิดพลาด',
        'ไม่สามารถสร้างแบบทดสอบได้ กรุณาลองใหม่อีกครั้ง',
      );
    } finally {
      setIsLoading(false);
      setLoadingStep('');
    }
  };

  // ── Loading screen ───────────────────────────────────────────────────────────

  if (isLoading) {
    const total = selectedTopics.length * questionsPerTopic;
    return (
      <SafeAreaView style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color="#c6cdfc" />
        <AppText style={styles.loadingPrimary}>
          กำลังสร้างข้อสอบ {total} ข้อ...
        </AppText>
        <AppText style={styles.loadingSecondary}>{loadingStep}</AppText>
      </SafeAreaView>
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={styles.container}>
      {/* Nav header */}
      <View style={styles.navHeader}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <FontAwesome5 name="arrow-left" size={18} color="#fff" />
        </TouchableOpacity>
        <AppText style={styles.navTitle}>สร้างแบบทดสอบ</AppText>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView contentContainerStyle={styles.form}>
        <AppText style={styles.sectionLabel}>จำนวนข้อต่อหัวข้อ</AppText>

        {/* Pill selector */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.pillRow}
        >
          {COUNT_OPTIONS.map((num) => {
            const active = questionsPerTopic === num;
            return (
              <TouchableOpacity
                key={num}
                style={[styles.pill, active && styles.pillActive]}
                onPress={() => setQuestionsPerTopic(num)}
              >
                <AppText style={[styles.pillText, active && styles.pillTextActive]}>
                  {num} ข้อ
                </AppText>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        <AppText style={[styles.sectionLabel, { marginTop: 24 }]}>เลือกหัวข้อ</AppText>
        <AppText style={styles.hint}>
          เลือกได้หลายหัวข้อ · รวมทั้งหมด{' '}
          <AppText style={{ color: '#c6cdfc', fontWeight: '700' }}>
            {selectedTopics.length * questionsPerTopic}
          </AppText>{' '}
          ข้อ
        </AppText>

        {/* Topic list */}
        <View style={styles.topicList}>
          {PHYSICS_TOPICS.map((topic) => {
            const sel = selectedTopics.includes(topic.id);
            return (
              <TouchableOpacity
                key={topic.id}
                style={[styles.topicItem, sel && styles.topicItemSel]}
                onPress={() => handleSelectTopic(topic.id)}
                activeOpacity={0.8}
              >
                <FontAwesome5
                  name={sel ? 'check-square' : 'square'}
                  size={20}
                  color={sel ? '#fff' : '#fff'}
                />
                <AppText style={[styles.topicName, sel && styles.topicNameSel]}>
                  {topic.name}
                </AppText>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Submit */}
        <TouchableOpacity
          style={[
            styles.submitBtn,
            selectedTopics.length === 0 && styles.submitBtnDisabled,
          ]}
          onPress={handleGenerateQuiz}
          disabled={selectedTopics.length === 0}
          activeOpacity={0.85}
        >
          <FontAwesome5 name="magic" size={18} color="white" />
          <AppText style={styles.submitBtnText}>เริ่มสร้างชุดข้อสอบ</AppText>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)'
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },

  // Nav
  navHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    marginTop: '10%'
  },
  backBtn: {
    padding: 6,
  },
  navTitle: {
    fontSize: 18,
    color: '#fff',
  },

  // Form
  form: {
    padding: 20,
    paddingBottom: 48,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 10,
  },

  // Pills
  pillRow: {
    gap: 8,
    paddingRight: 20,
  },
  pill: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
  },
  pillActive: {
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
  },
  pillText: {
    color: '#888',
    fontSize: 14,
  },
  pillTextActive: {
    color: 'white',
  },

  hint: {
    fontSize: 13,
    color: '#666',
    marginBottom: 12,
  },

  // Topics
  topicList: {
    gap: 8,
  },
  topicItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
  },
  topicItemSel: {
    backgroundColor: '#c6cdfc',
  },
  topicName: {
    flex: 1,
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  topicNameSel: {
    color: '#e2e8f0',
  },

  // Submit
  submitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: '#c6cdfc',
    paddingVertical: 16,
    borderRadius: 16,
    marginTop: 28,
  },
  submitBtnDisabled: {
    opacity: 0.4,
  },
  submitBtnText: {
    color: 'white',
    fontSize: 16,
  },

  // Loading
  loadingPrimary: {
    fontSize: 18,
    fontWeight: '700',
    color: '#e2e8f0',
    marginTop: 16,
  },
  loadingSecondary: {
    fontSize: 13,
    color: '#888',
    marginTop: 4,
  },
});

export default QuizzGeneratingScreen;