import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Colors } from '../constants/colors';
import { getAccessToken } from '../services/api';

/** Ulazna točka — preusmjerava na tabove ako postoji token, inače na login. */
export default function Index() {
  const [target, setTarget] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken().then((token) => setTarget(token ? '/(tabs)' : '/(auth)/login'));
  }, []);

  if (!target) {
    return (
      <View className="flex-1 bg-ink items-center justify-center">
        <ActivityIndicator color={Colors.neon} size="large" />
      </View>
    );
  }
  return <Redirect href={target as any} />;
}
