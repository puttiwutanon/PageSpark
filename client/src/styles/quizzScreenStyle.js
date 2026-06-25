import { StyleSheet } from 'react-native';

const quizzScreenStyle = StyleSheet.create({
    quizzScreenContainer: {
        width: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        flex: 1,
        // Reminder: This experimental_backgroundImage won't work in production.
        // You'll need expo-linear-gradient to see the actual background.
        experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)'
    },
    welcomeContainer: {
        marginTop: '20%',
        width: '100%',
        flex: 1, 
        alignItems: 'center',
        justifyContent: 'flex-start', 
    },
    welcomeText: {
        fontSize: 24,
        color: '#334155',
        alignSelf: 'flex-start',
        marginLeft: '10%',
        marginTop: '10%'
    },
    welcomeText_1: {
        fontSize: 24,
        color: '#334155',
        alignSelf: 'flex-start',
        marginLeft: '10%',
    },
    
    // NEW WRAPPER STYLE
    quizzGeneratorButton: {
        width: '90%',
        height: '10%', // Change this number to exactly how tall you want the box to be
        marginTop: 20,
        backgroundColor: 'rgba(128, 128, 128, 0.27)',
        borderRadius: 16,
        overflow: 'hidden', // CRITICAL: This stops the ScrollView from bleeding outside the rounded corners
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        
    },

    quizzGenerator: {
        width: '90%',
        height: '80%', // Change this number to exactly how tall you want the box to be
        marginTop: 20,
        backgroundColor: 'rgba(128, 128, 128, 0.27)',
        borderRadius: 16,
        overflow: 'hidden', // CRITICAL: This stops the ScrollView from bleeding outside the rounded corners
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'row',
        
    },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  formContainer: { padding: 20 },
  subtitleText: { fontSize: 14, color: '#666', marginBottom: 20, marginTop: 5 },
  listWrapper: { marginBottom: 30 },
  topicItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#f8f9fa',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e9ecef'
  },
  topicItemSelected: { backgroundColor: '#f1f0ff', borderColor: '#c6cdfc', fontFamily: 'Kanit' },
  topicName: { marginLeft: 12, fontSize: 15, color: '#888', flex: 1 },
  topicNameSelected: { color: '#c6cdfc', fontWeight: 'bold' },
  submitButton: {
    backgroundColor: '#c6cdfc',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 10,
    fontFamily: 'Kanit',
    marginBottom: '10%'
  },
  submitButtonText: { color: 'white', fontSize: 18 },
  loadingText: { marginTop: 15, fontSize: 16, color: '#555', textAlign: 'center' },
  quizHeader: { flexDirection: 'row', justifyContent: 'space-between', padding: 20 },
  progressText: { fontSize: 16, fontWeight: 'bold' },
  scoreText: { fontSize: 16, color: '#2e7d32', fontWeight: 'bold' },
  questionCard: { padding: 20, backgroundColor: '#f5f5f5', borderRadius: 12, marginHorizontal: 20, marginBottom: 20 },
  questionText: { fontSize: 18, lineHeight: 26, fontWeight: '600' },
  optionsContainer: { paddingHorizontal: 20 },
  optionButton: { padding: 16, borderRadius: 10, backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#ddd', marginBottom: 12 },
  selectedButton: { borderColor: '#c6cdfc', backgroundColor: '#f1f0ff' },
  correctButton: { borderColor: '#2e7d32', backgroundColor: '#e8f5e9' },
  wrongButton: { borderColor: '#c62828', backgroundColor: '#ffebee' },
  optionText: { fontSize: 16 },
  explanationBox: { padding: 20, backgroundColor: '#fff8e1', borderTopWidth: 1, borderColor: '#ffe082' },
  explanationTitle: { fontSize: 15, fontWeight: 'bold', color: '#b78103', marginBottom: 5 },
  explanationText: { fontSize: 14, color: '#555', lineHeight: 20, marginBottom: 15 },
  nextButton: { backgroundColor: '#333', flexDirection: 'row', padding: 14, borderRadius: 8, justifyContent: 'center', alignItems: 'center', gap: 8 },
  nextButtonText: { color: 'white', fontWeight: 'bold' },
    counterRow: { marginBottom: 10, paddingHorizontal: 5 },
  counterLabel: { fontSize: 16,  color: '#334155' },
  pillContainer: { paddingHorizontal: 5, marginBottom: 25, paddingBottom: 5 },
  countPill: { paddingVertical: 8, paddingHorizontal: 16, backgroundColor: '#fff', borderRadius: 20, borderWidth: 1, borderColor: '#ddd', marginRight: 10 },
  countPillActive: { backgroundColor: '#f1f0ff', borderColor: '#c6cdfc' },
  countPillText: { fontSize: 14, color: '#666', fontWeight: '500' },
  countPillTextActive: { color: '#c6cdfc', fontWeight: 'bold' },
});

export { quizzScreenStyle };