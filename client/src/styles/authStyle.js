import { StyleSheet } from 'react-native';

const authStyle = StyleSheet.create({
    loginPage: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)' 
    },
    authform: {
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 20,
        padding: 32,
        width: '85%', 
        experimental_backgroundImage: 'linear-gradient(180deg, #6d748673, #0a0d1326,  #0a0d1326, #6d748673)' 
        
    },
    title: {
        fontSize: 24,
        marginBottom: 20,
        color: '#fff',
    },
    authformEmail: {
        width: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottomWidth: 1,
        borderBottomColor: '#fff',
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
        color: '#fff',
        fontWeight: '600',
    },
    input: {
        width: '100%',
        paddingVertical: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#fff', // White underline
        color: '#fff',
        fontSize: 16,
        // Removed border, backgroundColor, and borderRadius to match the design
    },
    button: {
        paddingVertical: 12,
        paddingHorizontal: 24,
        marginTop: 16,
        borderRadius: 12,
        width: 180,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#eed0fb',
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
        alignSelf: 'center',
    },
    errorText: {
        color: '#F43F5E', // PageSpark error color
        marginTop: 16,
        textAlign: 'center',
    },
    link: {
        color: '#fff', 
        marginTop: 16,
    }
});

export { authStyle };