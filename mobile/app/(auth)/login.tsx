import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View,
} from 'react-native';
import PressableScale from '../../components/ui/PressableScale';
import { Colors } from '../../constants/colors';
import { glow } from '../../constants/theme';
import { useAuth } from '../../hooks/useAuth';

const INPUT = 'bg-surface text-text font-body rounded-2xl px-4 py-4 mb-3 border border-line';

export default function Login() {
  const router = useRouter();
  const { login, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function submit() {
    setError('');
    try {
      await login(email.trim(), password);
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
      <View className="items-center mb-12">
        <Text
          className="text-white font-display text-5xl uppercase"
          style={{ letterSpacing: 2, textShadowColor: Colors.neon, textShadowRadius: 20, textShadowOffset: { width: 0, height: 0 } }}
        >
          Nightclub
        </Text>
        <Text className="text-neon font-sub text-sm uppercase mt-1" style={{ letterSpacing: 6 }}>
          Manager
        </Text>
      </View>

      <TextInput
        className={INPUT}
        placeholder="Email"
        placeholderTextColor={Colors.muted}
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        className={INPUT}
        placeholder="Lozinka"
        placeholderTextColor={Colors.muted}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text className="text-error font-body mb-3">{error}</Text> : null}

      <PressableScale className="bg-neon rounded-2xl py-4 items-center mt-1" style={glow} onPress={submit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-bodyBd text-base">Prijavi se</Text>}
      </PressableScale>

      <Link href="/(auth)/oauth" asChild>
        <Pressable className="bg-surface border border-line rounded-2xl py-4 items-center mt-3">
          <Text className="text-text font-bodySb">Nastavi s Google / Facebook</Text>
        </Pressable>
      </Link>

      <View className="flex-row justify-center mt-7">
        <Text className="text-muted font-body">Nemaš račun? </Text>
        <Link href="/(auth)/register" className="text-neon font-bodyBd">Registriraj se</Link>
      </View>
    </KeyboardAvoidingView>
  );
}
