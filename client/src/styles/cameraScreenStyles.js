import { StyleSheet } from 'react-native';

const cameraScreenStyle = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#ffdce5', // PageSpark Deep Navy
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 15,
        marginTop: 30,
    },
    headerTitle: {
        color: '#F8FAFC',
        fontSize: 24,
    },
    cameraContainer: {
        flex: 1,
        borderRadius: 20,
        overflow: 'hidden',
        marginHorizontal: 15,
        marginBottom: 20,
    },
    camera: {
        flex: 1,
    },
    controlsContainer: {
        flexDirection: 'row',
        justifyContent: 'space-evenly',
        alignItems: 'center',
        paddingBottom: 40,
        paddingTop: 10,
    },
    shutterButton: {
        width: 70,
        height: 70,
        borderRadius: 35,
        backgroundColor: '#F8FAFC',
        justifyContent: 'center',
        alignItems: 'center',
    },
    shutterInner: {
        width: 60,
        height: 60,
        borderRadius: 30,
        borderWidth: 2,
        borderColor: '#0F172A',
    },
    iconButton: {
        alignItems: 'center',
        justifyContent: 'center',
        width: 80,
    },
    iconText: {
        color: '#F8FAFC',
        marginTop: 8,
        fontSize: 12,
    },
    text: {
        color: '#F8FAFC',
        textAlign: 'center',
        marginBottom: 20,
    },
    primaryButton: {
        backgroundColor: '#7C3AED', // Electric Violet
        padding: 15,
        borderRadius: 10,
        alignSelf: 'center',
    },
    buttonText: {
        color: 'white',
        fontWeight: 'bold',
    }
});

export { cameraScreenStyle };