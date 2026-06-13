import { StyleSheet } from 'react-native';

const authStyle = StyleSheet.create({
    loginPage: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#ffdce5', 
    },
    authform: {
        alignItems: 'center',
        justifyContent: 'center',
        borderColor: '#808080',
        borderWidth: 1,
        borderRadius: 16,
        padding: 32,
        width: '85%', 
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        
        // Box Shadow for iOS
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.16,
        shadowRadius: 36,
        // Box Shadow for Android
        elevation: 5,
    },
    title: {
        fontSize: 24,
        marginBottom: 20,
        color: '#0F172A',
    },
    authformEmail: {
        width: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottomWidth: 1,
        borderBottomColor: '#808080',
        paddingBottom: 20,
    },
    textInputContainer: {
        width: '100%',
        flexDirection: 'column',
        marginBottom: 16,
    },
    label: {
        fontSize: 14,
        marginBottom: 8,
        color: '#333',
        fontWeight: '600',
    },
    input: {
        width: '100%',
        padding: 12,
        borderWidth: 1,
        borderColor: '#ccc',
        borderRadius: 8,
        backgroundColor: '#fff',
        fontSize: 16,
    },
    button: {
        paddingVertical: 12,
        paddingHorizontal: 24,
        marginTop: 16,
        borderRadius: 12,
        width: 150,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#92d0ff',
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
    },
    errorText: {
        color: '#F43F5E', // PageSpark error color
        marginTop: 16,
        textAlign: 'center',
    },
    link: {
        color: '#92d0ff', 
        marginTop: 16,
    }
});

export { authStyle };