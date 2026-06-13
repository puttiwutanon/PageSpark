import { StyleSheet } from 'react-native';

const navbarStyle = StyleSheet.create({
  navbar:{
    height: 95,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'Kanit',
    paddingTop: 15,
    fontSize: 20,
  },
   tabBarItemStyle: {
     borderRadius: 40,
     overflow: 'hidden',
   },
});

export { navbarStyle };