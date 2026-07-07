// firebase/lessonFirestore.js
import { db } from './firebaseConfig';
import { 
  collection, 
  doc, 
  getDocs, 
  getDoc, 
  addDoc, 
  updateDoc, 
  deleteDoc, 
  query, 
  where, 
  orderBy, 
  limit 
} from 'firebase/firestore';

const LESSONS_COLLECTION = 'lessons';
const VIDEOS_COLLECTION = 'videos';

// ── Get all lessons for a user ──────────────────────────────────────────────

// firebase/lessonFirestore.js

// ── Get all lessons for a user ──────────────────────────────────────────────

export async function fetchUserLessons(uid) {
  try {
    const lessonsRef = collection(db, LESSONS_COLLECTION);
    // Simple query without orderBy
    const q = query(
      lessonsRef, 
      where('uid', '==', uid)
    );
    const snapshot = await getDocs(q);
    
    const lessons = [];
    for (const docSnap of snapshot.docs) {
      const data = docSnap.data();
      const episodeCount = data.episodeCount || 0;
      
      lessons.push({
        id: docSnap.id,
        ...data,
        episodeCount,
        createdAt: data.createdAt?.toDate?.() || data.createdAt || new Date(),
        updatedAt: data.updatedAt?.toDate?.() || data.updatedAt || new Date(),
      });
    }
    
    // Sort manually by createdAt descending
    lessons.sort((a, b) => b.createdAt - a.createdAt);
    
    return lessons;
  } catch (error) {
    console.error('Error fetching lessons:', error);
    throw error;
  }
}

// ── Get all videos for a lesson ─────────────────────────────────────────────

export async function fetchLessonVideos(lessonId) {
  try {
    const videosRef = collection(db, VIDEOS_COLLECTION);
    // Simple query without orderBy
    const q = query(
      videosRef,
      where('lessonId', '==', lessonId)
    );
    const snapshot = await getDocs(q);
    
    const videos = [];
    for (const docSnap of snapshot.docs) {
      const data = docSnap.data();
      videos.push({
        id: docSnap.id,
        ...data,
        createdAt: data.createdAt?.toDate?.() || data.createdAt || new Date(),
        renderedAt: data.renderedAt?.toDate?.() || data.renderedAt || new Date(),
      });
    }
    
    // Sort manually by episodeNumber ascending
    videos.sort((a, b) => (a.episodeNumber || 0) - (b.episodeNumber || 0));
    
    return videos;
  } catch (error) {
    console.error('Error fetching lesson videos:', error);
    throw error;
  }
}

// ── Delete a lesson and all its videos ─────────────────────────────────────

export async function deleteLesson(lessonId) {
  try {
    // First, delete all videos in this lesson
    const videos = await fetchLessonVideos(lessonId);
    const videosRef = collection(db, VIDEOS_COLLECTION);
    
    for (const video of videos) {
      await deleteDoc(doc(videosRef, video.id));
    }
    
    // Then delete the lesson itself
    const lessonRef = doc(db, LESSONS_COLLECTION, lessonId);
    await deleteDoc(lessonRef);
    
    return true;
  } catch (error) {
    console.error('Error deleting lesson:', error);
    throw error;
  }
}

// ── Update lesson title ─────────────────────────────────────────────────────

export async function updateLessonTitle(lessonId, newTitle) {
  try {
    const lessonRef = doc(db, LESSONS_COLLECTION, lessonId);
    await updateDoc(lessonRef, {
      title: newTitle,
      updatedAt: new Date(),
    });
    return true;
  } catch (error) {
    console.error('Error updating lesson title:', error);
    throw error;
  }
}