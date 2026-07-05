import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, Text, TextInput,
} from 'react-native';
import { Colors } from '../../constants/colors';
import { useAuth } from '../../hooks/useAuth';

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
      className="flex-1 bg-bgDark justify-center px-6"
    >
      <Text className="text-textLight text-2xl font-extrabold mb-8">Kreiraj račun</Text>

      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Ime i prezime" placeholderTextColor={Colors.textMuted}
        value={name} onChangeText={setName}
      />
      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Email" placeholderTextColor={Colors.textMuted}
        autoCapitalize="none" keyboardType="email-address"
        value={email} onChangeText={setEmail}
      />
      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Mobitel (opcionalno)" placeholderTextColor={Colors.textMuted}
        keyboardType="phone-pad"
        value={phone} onChangeText={setPhone}
      />
      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
        placeholder="Lozinka (min. 6 znakova)" placeholderTextColor={Colors.textMuted}
        secureTextEntry
        value={password} onChangeText={setPassword}
      />

      {error ? <Text className="text-error mb-3">{error}</Text> : null}

      <Pressable className="bg-accent1 rounded-xl py-4 items-center" onPress={submit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-bold text-base">Registriraj se</Text>}
      </Pressable>

      <Link href="/(auth)/login" className="text-textMuted text-center mt-6">
        Već imaš račun? <Text className="text-accent1 font-bold">Prijavi se</Text>
      </Link>
    </KeyboardAvoidingView>
  );
}
