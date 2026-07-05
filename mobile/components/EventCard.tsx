import { useRouter } from 'expo-router';
import { Image, Pressable, Text, View } from 'react-native';

export default function EventCard({ event }: { event: any }) {
  const router = useRouter();
  const date = new Date(event.date);
  const minPrice = Math.min(
    ...(event.ticket_types ?? []).map((t: any) => t.price).filter((p: number) => p > 0),
  );

  return (
    <Pressable
      className="bg-bgCard rounded-2xl overflow-hidden mb-4 border border-accent3"
      onPress={() => router.push(`/event/${event._id}`)}
    >
      {event.cover_image && (
        <Image source={{ uri: event.cover_image }} className="w-full h-44" resizeMode="cover" />
      )}
      <View className="p-4">
        <Text className="text-accent1 font-semibold text-xs uppercase">
          {date.toLocaleDateString('hr-HR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </Text>
        <Text className="text-textLight text-lg font-bold mt-1">{event.name}</Text>
        <Text className="text-textMuted mt-1">
          {event.club?.name}
          {event.club?.location?.city ? ` · ${event.club.location.city}` : ''}
        </Text>
        <View className="flex-row justify-between items-center mt-3">
          {event.genre ? (
            <Text className="text-textMuted text-xs bg-accent3/40 px-2 py-1 rounded-full">
              {event.genre}
            </Text>
          ) : <View />}
          {Number.isFinite(minPrice) && (
            <Text className="text-textLight font-bold">od {minPrice} €</Text>
          )}
        </View>
      </View>
    </Pressable>
  );
}
