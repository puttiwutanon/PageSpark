/**
 * services/quizFirestore.js
 *
 * Firestore service for the quiz feature.
 * Collection structure:
 *   quizzes/
 *     {quizId}/
 *       title: string
 *       topics: string[]
 *       questionsPerTopic: number
 *       totalQuestions: number
 *       createdAt: Timestamp
 *       questions: QuizItemSchema[]   ← full JSON array from the API
 */

import { db } from "./firebaseConfig"; // adjust path to your firebase init file
import {
  collection,
  addDoc,
  getDocs,
  getDoc,
  doc,
  serverTimestamp,
  query,
  orderBy,
  deleteDoc,
} from 'firebase/firestore';

const QUIZZES_COLLECTION = 'quizzes';

/**
 * Save a newly generated quiz to Firestore.
 * @param {string[]} topics       - array of topic IDs selected by the user
 * @param {number}   questionsPerTopic
 * @param {object[]} questions    - the `quizzes` array from the API response
 * @param {string[]} topicNames   - human-readable Thai names for the topics
 * @returns {string} the new Firestore document ID
 */
export async function saveQuizToFirestore(topics, questionsPerTopic, questions, topicNames) {
  const title = topicNames.length === 1
    ? topicNames[0]
    : `${topicNames[0]} +${topicNames.length - 1} หัวข้อ`;

  const docRef = await addDoc(collection(db, QUIZZES_COLLECTION), {
    title,
    topics,
    topicNames,
    questionsPerTopic,
    totalQuestions: questions.length,
    questions,               // full array — one doc keeps it simple
    createdAt: serverTimestamp(),
  });

  return docRef.id;
}

/**
 * Fetch all saved quizzes (ordered newest first).
 * @returns {{ id: string, title: string, totalQuestions: number, createdAt: Timestamp }[]}
 */
export async function fetchAllQuizzes() {
  const q = query(
    collection(db, QUIZZES_COLLECTION),
    orderBy('createdAt', 'desc'),
  );
  const snap = await getDocs(q);
  return snap.docs.map((d) => ({ id: d.id, ...d.data() }));
}

/**
 * Fetch a single quiz with all its questions.
 * @param {string} quizId
 */
export async function fetchQuizById(quizId) {
  const snap = await getDoc(doc(db, QUIZZES_COLLECTION, quizId));
  if (!snap.exists()) throw new Error(`Quiz ${quizId} not found`);
  return { id: snap.id, ...snap.data() };
}

/**
 * Delete a quiz.
 */
export async function deleteQuiz(quizId) {
  await deleteDoc(doc(db, QUIZZES_COLLECTION, quizId));
}