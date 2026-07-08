import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';
import { cardShadow, scrim } from '../constants/theme';
import PressableScale from './ui/PressableScale';

export default function EventCard({ event }: { event: any }) {
  const router = useRouter();
  const date = new Date(event.date);
  const prices = (event.ticket_types ?? []).map((t: any) => t.price).filter((p: number) => p > 0);
  const minPrice = prices.length ? Math.min(...prices) : null;

  return (
    <PressableScale
      className="mb-4 rounded-3xl overflow-hidden bg-surface"
      style={cardShadow}
      onPress={() => router.push(`/event/${event._id}`)}
    >
      <View className="h-64 justify-end">
        {event.cover_image ? (
          <Image source={{ uri: event.cover_image }} style={StyleSheet.absoluteFill} resizeMode="cover" />
        ) : (
          <View style={StyleSheet.absoluteFill} className="bg-surfaceHi items-center justify-center">
            <Text className="text-neon font-display text-6xl opacity-40">{event.name?.[0]}</Text>
          </View>
        )}
        <LinearGradient colors={scrim as any} style={StyleSheet.absoluteFill} />

        <View className="p-5">
          <Text className="text-neon font-bodySb text-[11px] uppercase" style={{ letterSpacing: 2 }}>
            {date.toLocaleDateString('hr-HR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </Text>
          <Text className="text-white font-display text-2xl uppercase mt-1.5" numberOfLines={2} style={{ letterSpacing: 0.3 }}>
            {event.name}
          </Text>
          <View className="flex-row items-center justify-between mt-3">
            <Text className="text-muted font-body flex-1" numberOfLines={1}>
              {event.club?.name}
              {event.club?.location?.city ? `  ·  ${event.club.location.city}` : ''}
            </Text>
            {minPrice != null && (
              <View className="ml-3 px-3 py-1 rounded-full border border-neon/60 bg-neon/10">
                <Text className="text-white font-bodySb text-xs">od {minPrice} €</Text>
              </View>
            )}
          </View>
        </View>
      </View>
    </PressableScale>
  );
}
