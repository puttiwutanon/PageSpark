import React from 'react';
import { TextInput, StyleSheet } from 'react-native';

const AppTextInput = ({ style, ...props }) => {
  return (
    <TextInput 
      style={[styles.input, style]} 
      {...props} 
    />
  );
};

const styles = StyleSheet.create({
  input: {
    fontFamily: 'Kanit', // Your global font here
  },
});

export default AppTextInput;