import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View,
} from 'react-native';
import { Colors } from '../../constants/colors';
import { useAuth } from '../../hooks/useAuth';

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
      className="flex-1 bg-bgDark justify-center px-6"
    >
      <Text className="text-accent1 text-4xl font-extrabold text-center">NIGHTCLUB</Text>
      <Text className="text-textLight text-xl font-bold text-center mb-10">MANAGER</Text>

      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Email"
        placeholderTextColor={Colors.textMuted}
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Lozinka"
        placeholderTextColor={Colors.textMuted}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text className="text-error mb-3">{error}</Text> : null}

      <Pressable className="bg-accent1 rounded-xl py-4 items-center" onPress={submit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-bold text-base">Prijavi se</Text>}
      </Pressable>

      <Link href="/(auth)/oauth" asChild>
        <Pressable className="bg-bgCard border border-accent3 rounded-xl py-4 items-center mt-3">
          <Text className="text-textLight font-semibold">Nastavi s Google / Facebook</Text>
        </Pressable>
      </Link>

      <View className="flex-row justify-center mt-6">
        <Text className="text-textMuted">Nemaš račun? </Text>
        <Link href="/(auth)/register" className="text-accent1 font-bold">Registriraj se</Link>
      </View>

      <Link href="/staff/hostess" className="text-textMuted text-center mt-10 text-xs">
        Prijava za osoblje →
      </Link>
    </KeyboardAvoidingView>
  );
}
