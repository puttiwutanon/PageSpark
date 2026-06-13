import React from 'react';
import { Text, StyleSheet } from 'react-native';

const AppText = ({ style, children, ...props }) => {
  return (
    <Text style={[styles.defaultFont, style]} {...props}>
      {children}
    </Text>
  );
};

const styles = StyleSheet.create({
  defaultFont: {
    fontFamily: 'Kanit', // This applies Kanit to every instance
  },
});

export default AppText;