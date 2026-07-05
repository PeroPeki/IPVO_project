import * as Google from 'expo-auth-session/providers/google';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useAuth } from '../../hooks/useAuth';

WebBrowser.maybeCompleteAuthSession();

const GOOGLE_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID ?? '';

export default function OAuth() {
  const router = useRouter();
  const { oauthLogin } = useAuth();
  const [error, setError] = useState('');

  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: GOOGLE_CLIENT_ID,
  });

  useEffect(() => {
    if (response?.type === 'success' && response.params.id_token) {
      oauthLogin('google', response.params.id_token)
        .then(() => router.replace('/(tabs)'))
        .catch((e) => setError(e.message));
    }
  }, [response]);

  return (
    <View className="flex-1 bg-bgDark justify-center px-6">
      <Text className="text-textLight text-2xl font-extrabold mb-8 text-center">
        Prijava putem servisa
      </Text>

      <Pressable
        className="bg-bgCard border border-accent3 rounded-xl py-4 items-center mb-3"
        disabled={!request}
        onPress={() => promptAsync()}
      >
        <Text className="text-textLight font-semibold">Nastavi s Googleom</Text>
      </Pressable>

      <Pressable
        className="bg-bgCard border border-accent3 rounded-xl py-4 items-center opacity-60"
        onPress={() => setError('Facebook prijava zahtijeva konfiguriran Facebook App ID.')}
      >
        <Text className="text-textLight font-semibold">Nastavi s Facebookom</Text>
      </Pressable>

      {!GOOGLE_CLIENT_ID && (
        <Text className="text-textMuted text-xs text-center mt-4">
          Postavi EXPO_PUBLIC_GOOGLE_CLIENT_ID u .env za Google prijavu.
        </Text>
      )}
      {error ? <Text className="text-error text-center mt-4">{error}</Text> : null}

      <Pressable className="mt-8" onPress={() => router.back()}>
        <Text className="text-accent1 text-center font-semibold">← Natrag</Text>
      </Pressable>
    </View>
  );
}
