import { useRouter } from 'expo-router';
import { Image, Pressable, Text, View } from 'react-native';

export default function ClubCard({ club }: { club: any }) {
  const router = useRouter();
  return (
    <Pressable
      className="bg-bgCard rounded-2xl overflow-hidden mb-4 border border-accent3"
      onPress={() => router.push(`/club/${club.slug}`)}
    >
      {club.cover_image ? (
        <Image source={{ uri: club.cover_image }} className="w-full h-36" resizeMode="cover" />
      ) : (
        <View className="w-full h-36 bg-accent3 items-center justify-center">
          <Text className="text-accent1 text-4xl font-extrabold">{club.name?.[0]}</Text>
        </View>
      )}
      <View className="p-4">
        <Text className="text-textLight text-lg font-bold">{club.name}</Text>
        <Text className="text-textMuted mt-1">
          {club.location?.city}
          {club.location?.address ? ` · ${club.location.address}` : ''}
        </Text>
        {club.upcoming_event_count > 0 && (
          <Text className="text-accent1 mt-2 font-semibold">
            {club.upcoming_event_count} nadolazećih evenata
          </Text>
        )}
      </View>
    </Pressable>
  );
}
