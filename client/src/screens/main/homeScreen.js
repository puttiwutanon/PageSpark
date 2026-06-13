import React, { useState } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    KeyboardAvoidingView, 
    Platform,
    SafeAreaView
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AppText from '../../components/appText';        
import AppTextInput from '../../components/appTextInput';
import { homeScreenStyle } from '../../styles/homeScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';

const HomeScreen = () => {
  const navigation = useNavigation();

  return (
    <SafeAreaView style={homeScreenStyle.homeContainer}>
        <View style={homeScreenStyle.welcomeContainer}>
            <AppText style={homeScreenStyle.welcomeText}>ยินดีต้อนรับสู่ PageSpark👋</AppText>
            <AppText style={homeScreenStyle.subText}>เลือกสิ่งที่คุณต้องการ</AppText>
        </View>

        <View style={homeScreenStyle.routeToFunctionContainer}>
            <TouchableOpacity style={homeScreenStyle.routeToFunction} onPress={() => navigation.navigate('camera')}>
                <AppText style={{ fontSize: 16, color: 'white' }}>สรุปบทเรียน</AppText>
                <FontAwesome5 name="chalkboard-teacher" size={24} color="white" />
            </TouchableOpacity>

            <TouchableOpacity style={homeScreenStyle.routeToFunction} onPress={() => navigation.navigate('SignUp')}>
                <AppText style={{ fontSize: 16, color: 'white' }}>ทำแบบทดสอบ</AppText>
                <FontAwesome5 name="book" size={24} color="white" />
            </TouchableOpacity>
        </View>

        <View style={homeScreenStyle.recentActivityContainer}>
            <View style={homeScreenStyle.recentActivityHeader}>
                <AppText style={homeScreenStyle.welcomeText}>กิจกรรมล่าสุด</AppText>

                <AppText style={homeScreenStyle.subText} onPress={() => navigation.navigate('videoStorage')}>
                    ดูทั้งหมด
                </AppText>
            </View>
            <SafeAreaView style={{ marginTop: 10 }}>
                
            </SafeAreaView>
        </View>
    </SafeAreaView>
  );
};

export default HomeScreen