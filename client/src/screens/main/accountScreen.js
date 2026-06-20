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
import { accountScreenStyle } from '../../styles/accountScreenStyles';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';
import FontAwesome from '@expo/vector-icons/FontAwesome';
import { PieChart } from "react-native-gifted-charts";
import { signOut } from 'firebase/auth';
import { auth } from '../../firebase/firebaseConfig';
import { Alert } from 'react-native';

const AccountScreen = () => {

    const navigation = useNavigation();

    const placeholderData = [
        { value: 70, color: '#eed0fb', text: '70%' }, // Bright Teal for Correct answers
        { value: 30, color: '#fff' }              // Dark slate for remaining
    ];

    const handleLogout = async () => {
        try {
            await signOut(auth);
            // On successful signout, purge stack and swap back to Login view
            navigation.replace('Login');
        } catch (error) {
            console.error("Firebase Signout Error:", error.message);
            Alert.alert(
                "เกิดข้อผิดพลาด",
                "ไม่สามารถออกจากระบบได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง",
                [{ text: "ตกลง" }]
            );
        }
    };
    
  return (
    <SafeAreaView style={accountScreenStyle.profileContainer}>
        <View style={accountScreenStyle.profileHeader}>
            <FontAwesome5 name="user-alt" size={100} color="#334155" />
            <AppText style={accountScreenStyle.welcomeText}>USER PROFILE</AppText>
        </View>

        <View style={{ width: '90%', alignItems: 'center', marginTop: '5%', backgroundColor: 'rgba(128, 128, 128, 0.27)', padding: 20, borderRadius: 16 }}>
            <View style={{ alignItems: 'center', marginVertical: 2 }}>
                <AppText style={{ fontSize: 18, marginBottom: 15, color: '#FFF' }}>
                    สถิติการทำแบบทดสอบหลังเรียน
                </AppText>
                
                <PieChart
                    data={placeholderData}
                    donut
                    radius={90}
                    innerRadius={60}
                    innerCircleColor={'#0F172A'} // Matches your PageSpark Deep Navy background
                    centerLabelComponent={() => {
                        return (
                            <View style={{ justifyContent: 'center', alignItems: 'center' }}>
                                <AppText style={{ fontSize: 22, color: 'white', fontWeight: 'bold' }}>70%</AppText>
                                <AppText style={{ fontSize: 12, color: '#64748B' }}>ถูกต้องเฉลี่ย</AppText>
                            </View>
                        );
                    }}
                />
            </View>

            <View style={accountScreenStyle.accountInfoContainer}>
                <View style={accountScreenStyle.routeToFunction} >
                    <AppText style={{ fontSize: 12, color: '#ffff', textAlign: 'center' }}>คลิปที่สร้างไปแล้ว</AppText>
                    <AppText style={{ fontSize: 14, color: '#ffff' }}>n</AppText>
                </View>

                <View style={accountScreenStyle.routeToFunction}>
                    <AppText style={{ fontSize: 12, color: '#FFFFFF', textAlign: 'center' }}>ทำแบบทดสอบไปแล้ว</AppText>
                    <AppText style={{ fontSize: 14, color: '#ffff' }}>n</AppText>
                </View>

            </View>
        </View>

        <View style={accountScreenStyle.logoutContainer}>
            <TouchableOpacity style={accountScreenStyle.logoutButton} onPress={handleLogout}>
                <FontAwesome name="sign-out" size={24} color="white" />
                <AppText style={{ fontSize: 16, color: 'white' }}>ออกจากระบบ</AppText>
            </TouchableOpacity>
        </View>
    </SafeAreaView>
  )
}

export default AccountScreen