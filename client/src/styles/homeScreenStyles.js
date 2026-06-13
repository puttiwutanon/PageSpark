import { StyleSheet } from 'react-native';

const homeScreenStyle = StyleSheet.create({
    homeContainer: {
        width: '100%',
        flex: 1,
        alignItems: 'center',
    },
    routeToFunctionContainer: {
        width: '100%',
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: '5%',
    },
    routeToFunction: {
        backgroundColor: '#92d0ff',
        padding: 10,
        margin: 10,
        borderRadius: 16,
        width: '40%',
        height: 100,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        fontSize: 16,
    },
    welcomeContainer: {
        marginTop: '20%',
        alignItems: 'flex-start',
        alignSelf: 'flex-start',
        marginLeft: '10%',
    },
    welcomeText: {
        fontSize: 24,
        color: '#334155',
    },
    subText: {
        fontSize: 16,
        marginTop: 10,
        color: '#334155',
    },
    recentActivityContainer: {
        width: '90%',
        marginTop: '10%',   
    },
    recentActivityHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
});

export { homeScreenStyle };