import { StyleSheet } from 'react-native';

const accountScreenStyle = StyleSheet.create({
    profileContainer: {
        width: '100%',
        flex: 1,
        alignItems: 'center',
        experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)'
    },
    profileHeader: {
        width: '100%',
        alignItems: 'center',
        marginTop: '20%',
    },
    welcomeText: {
        fontSize: 24,
        color: '#334155',
    },
    subText: {
        fontSize: 16,
        marginTop: 10,
    },
    accountInfoContainer: {
        width: '90%',
        marginTop: '10%',
        display: 'flex',
        flexDirection: 'row',
        justifyContent: 'center',
    },
    routeToFunction: {
        backgroundColor: 'rgba(128, 128, 128, 0.27)',
        padding: 10,
        margin: 10,
        borderRadius: 16,
        width: '50%',
        height: 100,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        fontSize: 16,
    },
    logoutContainer: {
        width: '100%',
        alignItems: 'center',
        marginTop: '10%',
        marginBottom: '10%',
    },
    logoutButton: {
        backgroundColor: '#FF3B30',
        padding: 10,
        margin: 10,
        borderRadius: 16,
        width: '40%',
        height: 50,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'row',
    },
});

export { accountScreenStyle };