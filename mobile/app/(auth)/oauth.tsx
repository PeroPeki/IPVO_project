import * as Google from 'expo-auth-session/providers/google';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import PressableScale from '../../components/ui/PressableScale';
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
    <View className="flex-1 bg-ink justify-center px-7">
      <Text className="text-neon font-bodySb text-xs uppercase mb-2 text-center" style={{ letterSpacing: 3 }}>Brza prijava</Text>
      <Text className="text-white font-display text-3xl uppercase mb-8 text-center" style={{ letterSpacing: 0.5 }}>
        Nastavi putem servisa
      </Text>

      <PressableScale
        className="bg-surface border border-line rounded-2xl py-4 items-center mb-3"
        disabled={!request}
        onPress={() => promptAsync()}
      >
        <Text className="text-text font-bodySb">Nastavi s Googleom</Text>
      </PressableScale>

      <Pressable
        className="bg-surface border border-line rounded-2xl py-4 items-center opacity-50"
        onPress={() => setError('Facebook prijava zahtijeva konfiguriran Facebook App ID.')}
      >
        <Text className="text-text font-bodySb">Nastavi s Facebookom</Text>
      </Pressable>

      {!GOOGLE_CLIENT_ID && (
        <Text className="text-muted font-body text-xs text-center mt-4">
          Postavi EXPO_PUBLIC_GOOGLE_CLIENT_ID u .env za Google prijavu.
        </Text>
      )}
      {error ? <Text className="text-error font-body text-center mt-4">{error}</Text> : null}

      <Pressable className="mt-8" onPress={() => router.back()}>
        <Text className="text-neon font-bodySb text-center">← Natrag</Text>
      </Pressable>
    </View>
  );
}
