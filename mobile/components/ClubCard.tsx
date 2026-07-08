import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';
import { cardShadow, scrim } from '../constants/theme';
import PressableScale from './ui/PressableScale';

export default function ClubCard({ club }: { club: any }) {
  const router = useRouter();
  return (
    <PressableScale
      className="mb-4 rounded-3xl overflow-hidden bg-surface"
      style={cardShadow}
      onPress={() => router.push(`/club/${club.slug}`)}
    >
      <View className="h-48 justify-end">
        {club.cover_image ? (
          <Image source={{ uri: club.cover_image }} style={StyleSheet.absoluteFill} resizeMode="cover" />
        ) : (
          <View style={StyleSheet.absoluteFill} className="bg-surfaceHi items-center justify-center">
            <Text className="text-neon font-display text-6xl opacity-40">{club.name?.[0]}</Text>
          </View>
        )}
        <LinearGradient colors={scrim as any} style={StyleSheet.absoluteFill} />

        <View className="p-5">
          <Text className="text-white font-heading text-xl uppercase" style={{ letterSpacing: 0.3 }}>
            {club.name}
          </Text>
          <View className="flex-row items-center justify-between mt-1.5">
            <Text className="text-muted font-body flex-1" numberOfLines={1}>
              {club.location?.city}
              {club.location?.address ? `  ·  ${club.location.address}` : ''}
            </Text>
            {club.upcoming_event_count > 0 && (
              <Text className="text-neon font-bodySb text-xs ml-3">
                {club.upcoming_event_count} eventa
              </Text>
            )}
          </View>
        </View>
      </View>
    </PressableScale>
  );
}
