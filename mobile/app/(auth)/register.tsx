import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Text, TextInput, View,
} from 'react-native';
import PressableScale from '../../components/ui/PressableScale';
import { Colors } from '../../constants/colors';
import { glow } from '../../constants/theme';
import { useAuth } from '../../hooks/useAuth';

const INPUT = 'bg-surface text-text font-body rounded-2xl px-4 py-4 mb-3 border border-line';

export default function Register() {
  const router = useRouter();
  const { register, loading } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function submit() {
    setError('');
    try {
      await register(name.trim(), email.trim(), password, phone.trim() || undefined);
      router.replace('/(tabs)');
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      className="flex-1 bg-ink justify-center px-7"
    >
      <Text className="text-neon font-bodySb text-xs uppercase mb-2" style={{ letterSpacing: 3 }}>Dobrodošao</Text>
      <Text className="text-white font-display text-4xl uppercase mb-8" style={{ letterSpacing: 0.5 }}>Kreiraj račun</Text>

      <TextInput
        className={INPUT}
        placeholder="Ime i prezime" placeholderTextColor={Colors.muted}
        value={name} onChangeText={setName}
      />
      <TextInput
        className={INPUT}
        placeholder="Email" placeholderTextColor={Colors.muted}
        autoCapitalize="none" keyboardType="email-address"
        value={email} onChangeText={setEmail}
      />
      <TextInput
        className={INPUT}
        placeholder="Mobitel (opcionalno)" placeholderTextColor={Colors.muted}
        keyboardType="phone-pad"
        value={phone} onChangeText={setPhone}
      />
      <TextInput
        className={INPUT}
        placeholder="Lozinka (min. 6 znakova)" placeholderTextColor={Colors.muted}
        secureTextEntry
        value={password} onChangeText={setPassword}
      />

      {error ? <Text className="text-error font-body mb-3">{error}</Text> : null}

      <PressableScale className="bg-neon rounded-2xl py-4 items-center mt-1" style={glow} onPress={submit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-bodyBd text-base">Registriraj se</Text>}
      </PressableScale>

      <View className="flex-row justify-center mt-7">
        <Text className="text-muted font-body">Već imaš račun? </Text>
        <Link href="/(auth)/login" className="text-neon font-bodyBd">Prijavi se</Link>
      </View>
    </KeyboardAvoidingView>
  );
}
