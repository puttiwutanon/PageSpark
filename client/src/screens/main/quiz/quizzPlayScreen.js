/**
 * screens/Quizz/QuizzPlayScreen.jsx
 *
 * Receives a `quiz` object via React Navigation params.
 * Phases:
 *   PLAYING  → one question at a time, reveal answer + mini-explanation after answering
 *   RESULTS  → score card + full review of every Q with correct answer highlighted
 *
 * Math: all question/option/explanation text is rendered through <MathText>
 * so that LaTeX ($...$) renders correctly via KaTeX in a WebView.
 */

import React, { useState } from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Animated,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import AppText from '../../../components/appText';
import MathText from '../../../components/mathText'; // adjust path

// ─────────────────────────────────────────────────────────────────────────────
// Option button — shows correct/wrong highlight after answering
// ─────────────────────────────────────────────────────────────────────────────

function OptionButton({ option, isAnswered, isSelected, isCorrect, onPress }) {
  let bg = '#1e2035';
  let border = '#2a2d4a';
  let textColor = '#ccc';

  if (isAnswered) {
    if (isCorrect) {
      bg = '#14532d';
      border = '#22c55e';
      textColor = '#86efac';
    } else if (isSelected) {
      bg = '#4c0519';
      border = '#f87171';
      textColor = '#fca5a5';
    }
  } else if (isSelected) {
    bg = '#2a2d4a';
    border = '#c6cdfc';
    textColor = '#e2e8f0';
  }

  return (
    <TouchableOpacity
      style={[styles.option, { backgroundColor: bg, borderColor: border }]}
      onPress={onPress}
      disabled={isAnswered}
      activeOpacity={0.8}
    >
      {isAnswered && isCorrect && (
        <FontAwesome5 name="check" size={13} color="#22c55e" style={{ marginRight: 6, marginTop: 2 }} />
      )}
      {isAnswered && isSelected && !isCorrect && (
        <FontAwesome5 name="times" size={13} color="#f87171" style={{ marginRight: 6, marginTop: 2 }} />
      )}
      <MathText style={[styles.optionText, { color: textColor }]}>{option}</MathText>
    </TouchableOpacity>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Results screen — full review of all questions
// ─────────────────────────────────────────────────────────────────────────────

function ResultsScreen({ questions, answers, score, onRetry, onExit }) {
  return (
    <SafeAreaView style={styles.container}>
      {/* Score banner */}
      <View style={styles.scoreBanner}>
        <AppText style={styles.scoreLabel}>คะแนนของคุณ</AppText>
        <AppText style={styles.scoreBig}>
          {score} / {questions.length}
        </AppText>
        <AppText style={styles.scorePercent}>
          {Math.round((score / questions.length) * 100)}%
        </AppText>
        <View style={styles.scoreBtns}>
          <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
            <FontAwesome5 name="redo" size={14} color="#c6cdfc" />
            <AppText style={styles.retryBtnText}>ทำอีกครั้ง</AppText>
          </TouchableOpacity>
          <TouchableOpacity style={styles.exitBtn} onPress={onExit}>
            <FontAwesome5 name="home" size={14} color="#888" />
            <AppText style={styles.exitBtnText}>กลับหน้าหลัก</AppText>
          </TouchableOpacity>
        </View>
      </View>

      {/* Full review */}
      <ScrollView contentContainerStyle={styles.reviewList}>
        <AppText style={styles.reviewTitle}>เฉลยทั้งหมด</AppText>
        {questions.map((q, idx) => {
          const userAnswer = answers[idx];
          const correct = userAnswer === q.correct_answer;
          return (
            <View key={idx} style={[styles.reviewCard, correct ? styles.reviewCorrect : styles.reviewWrong]}>
              {/* Q number + result icon */}
              <View style={styles.reviewHeader}>
                <View style={[styles.reviewNumBadge, correct ? styles.badgeCorrect : styles.badgeWrong]}>
                  <AppText style={styles.reviewNum}>{idx + 1}</AppText>
                </View>
                <FontAwesome5
                  name={correct ? 'check-circle' : 'times-circle'}
                  size={18}
                  color={correct ? '#22c55e' : '#f87171'}
                />
              </View>

              {/* Question */}
              <MathText style={styles.reviewQuestion}>{q.question}</MathText>

              {/* Options */}
              {q.options.map((opt, oi) => {
                const isCorrectOpt = opt === q.correct_answer;
                const isUserOpt    = opt === userAnswer;
                let optColor = '#555';
                if (isCorrectOpt) optColor = '#22c55e';
                else if (isUserOpt && !correct) optColor = '#f87171';

                return (
                  <View key={oi} style={styles.reviewOption}>
                    {isCorrectOpt && <FontAwesome5 name="check" size={11} color="#22c55e" style={{ marginRight: 4 }} />}
                    {isUserOpt && !correct && <FontAwesome5 name="times" size={11} color="#f87171" style={{ marginRight: 4 }} />}
                    {!isCorrectOpt && !isUserOpt && <View style={{ width: 15 }} />}
                    <MathText style={[styles.reviewOptionText, { color: optColor }]}>{opt}</MathText>
                  </View>
                );
              })}

              {/* Explanation */}
              <View style={styles.explanationBox}>
                <AppText style={styles.explanationLabel}>เฉลยและวิธีทำ:</AppText>
                <MathText style={styles.explanationText}>{q.step_by_step_solution}</MathText>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

const QuizzPlayScreen = () => {
  const navigation = useNavigation();
  const route      = useRoute();
  const { quiz }   = route.params;       // { id, title, questions, ... }

  const questions = quiz.questions ?? [];

  const [phase, setPhase]           = useState('PLAYING');  // 'PLAYING' | 'RESULTS'
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedOpt, setSelectedOpt] = useState(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [score, setScore]           = useState(0);
  const [answers, setAnswers]       = useState([]);         // record per-Q answer

  // ── Answer handling ─────────────────────────────────────────────────────────

  const handleSelectOption = (opt) => {
    if (isAnswered) return;
    setSelectedOpt(opt);
    setIsAnswered(true);
    if (opt === questions[currentIdx].correct_answer) {
      setScore((s) => s + 1);
    }
  };

  const handleNext = () => {
    const newAnswers = [...answers, selectedOpt];
    setAnswers(newAnswers);

    if (currentIdx < questions.length - 1) {
      setCurrentIdx((i) => i + 1);
      setSelectedOpt(null);
      setIsAnswered(false);
    } else {
      setPhase('RESULTS');
    }
  };

  // ── Retry ───────────────────────────────────────────────────────────────────

  const handleRetry = () => {
    setPhase('PLAYING');
    setCurrentIdx(0);
    setSelectedOpt(null);
    setIsAnswered(false);
    setScore(0);
    setAnswers([]);
  };

  // ── Results phase ───────────────────────────────────────────────────────────

  if (phase === 'RESULTS') {
    return (
      <ResultsScreen
        questions={questions}
        answers={answers}
        score={score}
        onRetry={handleRetry}
        onExit={() => navigation.goBack()}
      />
    );
  }

  // ── Playing phase ───────────────────────────────────────────────────────────

  const q         = questions[currentIdx];
  const progress  = ((currentIdx + 1) / questions.length) * 100;

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.playHeader}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <FontAwesome5 name="times" size={18} color="#888" />
        </TouchableOpacity>
        <View style={styles.progressInfo}>
          <AppText style={styles.progressText}>
            ข้อที่ {currentIdx + 1} / {questions.length}
          </AppText>
          <AppText style={styles.scoreChip}>คะแนน: {score}</AppText>
        </View>
      </View>

      {/* Progress bar */}
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${progress}%` }]} />
      </View>

      <ScrollView contentContainerStyle={styles.playContent}>
        {/* Question card */}
        <View style={styles.questionCard}>
          <MathText style={styles.questionText}>{q.question}</MathText>
        </View>

        {/* Options */}
        <View style={styles.options}>
          {q.options.map((opt, i) => (
            <OptionButton
              key={i}
              option={opt}
              isAnswered={isAnswered}
              isSelected={selectedOpt === opt}
              isCorrect={opt === q.correct_answer}
              onPress={() => handleSelectOption(opt)}
            />
          ))}
        </View>

        {/* Mini explanation shown immediately after answering */}
        {isAnswered && (
          <View style={styles.miniExplanation}>
            <View style={styles.miniExHeader}>
              <FontAwesome5
                name={selectedOpt === q.correct_answer ? 'check-circle' : 'times-circle'}
                size={18}
                color={selectedOpt === q.correct_answer ? '#22c55e' : '#f87171'}
              />
              <AppText
                style={[
                  styles.miniExResult,
                  { color: selectedOpt === q.correct_answer ? '#22c55e' : '#f87171' },
                ]}
              >
                {selectedOpt === q.correct_answer ? 'ถูกต้อง!' : 'ผิด'}
              </AppText>
            </View>

            <AppText style={styles.miniExLabel}>วิธีทำโดยย่อ:</AppText>
            <MathText style={styles.miniExText}>{q.step_by_step_solution}</MathText>

            <TouchableOpacity style={styles.nextBtn} onPress={handleNext}>
              <AppText style={styles.nextBtnText}>
                {currentIdx === questions.length - 1 ? 'ดูสรุปคะแนน' : 'ข้อถัดไป'}
              </AppText>
              <FontAwesome5 name="arrow-right" size={14} color="white" />
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </ScrollView>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#12131e',
  },

  // Play header
  playHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    gap: 12,
  },
  backBtn: { padding: 4 },
  progressInfo: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressText: { fontSize: 14, color: '#888' },
  scoreChip: {
    fontSize: 13,
    color: '#c6cdfc',
    backgroundColor: '#1e2035',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },

  // Progress bar
  progressBar: {
    height: 3,
    backgroundColor: '#1e2035',
    marginHorizontal: 16,
    borderRadius: 2,
    marginBottom: 4,
  },
  progressFill: {
    height: 3,
    backgroundColor: '#5b63c4',
    borderRadius: 2,
  },

  // Play content
  playContent: {
    padding: 16,
    paddingBottom: 40,
    gap: 12,
  },
  questionCard: {
    backgroundColor: '#1e2035',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#2a2d4a',
  },
  questionText: {
    fontSize: 16,
    color: '#e2e8f0',
    lineHeight: 26,
  },
  options: { gap: 10 },
  option: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
  },
  optionText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
  },

  // Mini explanation
  miniExplanation: {
    backgroundColor: '#151628',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2a2d4a',
    gap: 8,
  },
  miniExHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  miniExResult: {
    fontSize: 16,
    fontWeight: '700',
  },
  miniExLabel: {
    fontSize: 13,
    color: '#f0c040',
    fontWeight: '600',
  },
  miniExText: {
    fontSize: 14,
    color: '#bbb',
    lineHeight: 22,
  },
  nextBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#5b63c4',
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 4,
  },
  nextBtnText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 15,
  },

  // Results
  scoreBanner: {
    alignItems: 'center',
    backgroundColor: '#1e2035',
    paddingVertical: 28,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2d4a',
    gap: 6,
  },
  scoreLabel: { fontSize: 13, color: '#888', textTransform: 'uppercase', letterSpacing: 1 },
  scoreBig:   { fontSize: 52, fontWeight: '800', color: '#c6cdfc' },
  scorePercent: { fontSize: 16, color: '#888' },
  scoreBtns: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 12,
  },
  retryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#2a2d4a',
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 20,
  },
  retryBtnText: { color: '#c6cdfc', fontSize: 14, fontWeight: '600' },
  exitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#1a1b2e',
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#2a2d4a',
  },
  exitBtnText: { color: '#888', fontSize: 14 },

  reviewList: { padding: 16, gap: 16, paddingBottom: 48 },
  reviewTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#e2e8f0',
    marginBottom: 4,
  },
  reviewCard: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    gap: 10,
  },
  reviewCorrect: {
    backgroundColor: '#0f2218',
    borderColor: '#1a4731',
  },
  reviewWrong: {
    backgroundColor: '#1e0f16',
    borderColor: '#4c1528',
  },
  reviewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  reviewNumBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeCorrect: { backgroundColor: '#14532d' },
  badgeWrong:   { backgroundColor: '#4c0519' },
  reviewNum: { color: 'white', fontSize: 12, fontWeight: '700' },
  reviewQuestion: {
    fontSize: 14,
    color: '#e2e8f0',
    lineHeight: 22,
    fontWeight: '600',
  },
  reviewOption: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 4,
  },
  reviewOptionText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 20,
  },
  explanationBox: {
    backgroundColor: '#0a0b14',
    borderRadius: 10,
    padding: 12,
    gap: 6,
    marginTop: 4,
    borderLeftWidth: 3,
    borderLeftColor: '#f0c040',
  },
  explanationLabel: {
    fontSize: 12,
    color: '#f0c040',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  explanationText: {
    fontSize: 13,
    color: '#aaa',
    lineHeight: 22,
  },
});

export default QuizzPlayScreen;