// styles/accountScreenStyles.js

import { StyleSheet } from 'react-native';

export const accountScreenStyle = StyleSheet.create({
    profileContainer: {
        flex: 1,
        experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)',
        alignItems: 'center',
    },
    profileHeader: {
        alignItems: 'center',
        marginTop: '15%',
        gap: 8,
    },
    welcomeText: {
        fontSize: 18,
        color: '#334155',
        letterSpacing: 1,
    },
    accountInfoContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        width: '100%',
        marginTop: 16,
        gap: 12,
    },
    routeToFunction: {
        flex: 1,
        backgroundColor: 'rgba(15, 23, 42, 0.5)',
        borderRadius: 12,
        padding: 14,
        alignItems: 'center',
        gap: 4,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.05)',
    },
    logoutContainer: {
        position: 'absolute',
        bottom: 40,
        width: '90%',
        marginBottom: 70,
    },
    logoutButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        backgroundColor: 'rgba(15, 23, 42, 0.5)',
        paddingVertical: 14,
        borderRadius: 12,
    },
});