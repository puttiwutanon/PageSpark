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

import { doSignInWithEmailAndPassword } from '../../firebase/auth';
import { onAuthStateChanged } from 'firebase/auth';

export default function LoginScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    // useNavigate becomes useNavigation in React Native
    const navigation = useNavigation();

    const handleLogin = async () => {
        if (!email || !password) {
            setError('กรุณากรอกข้อมูลให้ครบถ้วน');
            return;
        }

        setError('');
        setLoading(true);

        try {
            const userCredential = await doSignInWithEmailAndPassword(email, password);
            console.log('Logged in user:', userCredential.user);
            
            navigation.replace('MainApp'); 
        } catch (err) {
            console.error(err);
            setError('อีเมลหรือรหัสผ่านไม่ถูกต้อง');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
        if (user) {
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
                <AppText style={authStyle.title}>เข้าสู่ระบบ</AppText>

                <View style={authStyle.authformEmail}>
                    
                    {/* Email Input */}
                    <View style={authStyle.textInputContainer}>
                        <AppText style={authStyle.label}>อีเมล</AppText>
                        <AppTextInput
                            style={authStyle.input}
                            value={email}
                            onChangeText={setEmail} // onChange -> onChangeText
                            keyboardType="email-address"
                            autoCapitalize="none"
                            autoComplete="email"
                        />
                    </View>

                    {/* Password Input */}
                    <View style={authStyle.textInputContainer}>
                        <AppText style={authStyle.label}>รหัสผ่าน</AppText>
                        <AppTextInput
                            style={authStyle.input}
                            value={password}
                            onChangeText={setPassword}
                            secureTextEntry={true} // Replaces type="password"
                        />
                    </View>

                    {/* Submit Button */}
                    <TouchableOpacity 
                        style={authStyle.button} 
                        onPress={handleLogin}
                        disabled={loading}
                        activeOpacity={0.7} // Gives a nice tap feedback instead of :hover
                    >
                        <AppText style={authStyle.buttonText}>
                            {loading ? 'กำลังเข้าสู่ระบบ...' : 'เข้าสู่ระบบ'}
                        </AppText>
                    </TouchableOpacity>
                </View>

                <AppText style={authStyle.link} onPress={() => navigation.navigate('SignUp')}>ยังไม่มีบัญชี? สมัครสมาชิก</AppText>

                {error ? <AppText style={authStyle.errorText}>{error}</AppText> : null}
            </View>
        </KeyboardAvoidingView>
    );
}

