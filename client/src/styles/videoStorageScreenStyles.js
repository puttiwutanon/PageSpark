import { StyleSheet } from 'react-native';

const videoStorageScreenStyle = StyleSheet.create({
    videoStorageScreenContainer: {
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
    },
    
    // NEW WRAPPER STYLE
    videoListWrapper: {
        width: '90%',
        height: '70%', // Change this number to exactly how tall you want the box to be
        marginTop: 20,
        backgroundColor: 'rgba(128, 128, 128, 0.27)',
        borderRadius: 16,
        overflow: 'hidden', // CRITICAL: This stops the ScrollView from bleeding outside the rounded corners
    },
});

export { videoStorageScreenStyle };