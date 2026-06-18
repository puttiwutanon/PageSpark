import React, { useState, useEffect } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    KeyboardAvoidingView, 
    Platform 
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { authStyle } from '../../styles';
import { auth } from '../../firebase/firebaseConfig';
import AppText from '../../components/appText';        
import AppTextInput from '../../components/appTextInput';
import { getFirestore, doc, setDoc } from "firebase/firestore";
import { doCreateUserWithEmailAndPassword } from '../../firebase/auth';
import { onAuthStateChanged } from 'firebase/auth'; 

export default function SignUpScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const navigation = useNavigation();

    const handleSignUp = async () => {
        // Basic Validation
        if (!email || !password || !confirmPassword) {
            setError('กรุณากรอกข้อมูลให้ครบถ้วน');
            return;
        }
        if (password !== confirmPassword) {
            setError('รหัสผ่านไม่ตรงกัน');
            return;
        }

        setError('');
        setLoading(true);

        try {
            // The `const userCredential =` part is the line that matters here --
            // without it, `userCredential` below is undefined and throws.
            const userCredential = await doCreateUserWithEmailAndPassword(email, password);
            const uid = userCredential.user.uid;

            // Use the uid as the document ID so users/{uid} is always the lookup path.
            // No query needed later -- just doc(db, "users", auth.currentUser.uid).
            await setDoc(doc(getFirestore(), "users", uid), {
                uid: uid,
                email: email,
                createdAt: new Date(),
            });

            console.log('Account created successfully');
            
            // Navigate to Home or Login after successful registration
            navigation.replace('MainApp'); 
        } catch (err) {
            console.error(err);
            setError('ไม่สามารถสร้างบัญชีได้ โปรดลองใหม่อีกครั้ง');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
        if (user) {
        // Use the exact name you gave the screen in your Navigator
        // Example: If your <Stack.Screen name="Home" ... />
        navigation.replace('MainApp'); 
        }
    });

    return () => unsubscribe();
    }, []);

    return (
        <KeyboardAvoidingView 
            style={authStyle.loginPage} 
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={authStyle.authform}>
                <AppText style={authStyle.title}>สมัครสมาชิก</AppText>

                <View style={authStyle.authformEmail}>
                    {/* Email Input */}
                    <View style={authStyle.textInputContainer}>
                        <AppText style={authStyle.label}>อีเมล</AppText>
                        <AppTextInput 
                            style={authStyle.input}
                            placeholder="กรุณาใส่อีเมล"
                            placeholderTextColor="#A0A0A0"
                            value={email}
                            onChangeText={setEmail}
                            keyboardType="email-address"
                            autoCapitalize="none"
                        />
                    </View>

                    {/* Password Input */}
                    <View style={authStyle.textInputContainer}>
                        <AppText style={authStyle.label}>รหัสผ่าน</AppText>
                        <AppTextInput 
                            style={authStyle.input}
                            placeholder="กรุณาใส่รหัสผ่าน"
                            placeholderTextColor="#A0A0A0"
                            value={password}
                            onChangeText={setPassword}
                            secureTextEntry={true}
                        />
                    </View>

                    {/* Confirm Password Input */}
                    <View style={authStyle.textInputContainer}>
                        <AppText style={authStyle.label}>ยืนยันรหัสผ่าน</AppText>
                        <AppTextInput 
                            style={authStyle.input}
                            placeholder="กรุณายืนยันรหัสผ่าน"
                            placeholderTextColor="#A0A0A0"
                            value={confirmPassword}
                            onChangeText={setConfirmPassword}
                            secureTextEntry={true}
                        />
                    </View>

                    {/* Submit Button */}
                    <TouchableOpacity 
                        style={authStyle.button} 
                        onPress={handleSignUp}
                        disabled={loading}
                        activeOpacity={0.7}
                    >
                        <AppText style={authStyle.buttonText}>
                            {loading ? 'กำลังสมัครสมาชิก...' : 'สมัครสมาชิก'}
                        </AppText>
                    </TouchableOpacity>
                </View>

                <AppText style={authStyle.link} onPress={() => navigation.navigate('Login')}>มีบัญชีแล้ว? ลงชื่อเข้าใช้</AppText>

                {error ? <AppText style={authStyle.errorText}>{error}</AppText> : null}
            </View>
        </KeyboardAvoidingView>
    );
}