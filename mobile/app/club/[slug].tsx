import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useEffect, useState } from 'react';
import { Image, Pressable, ScrollView, Text, View } from 'react-native';
import EventCard from '../../components/EventCard';
import { api } from '../../services/api';

/** Detalji kluba — tabovi: Eventi | Info. */
export default function ClubDetail() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const navigation = useNavigation();
  const [club, setClub] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [tab, setTab] = useState<'events' | 'info'>('events');

  useEffect(() => {
    api.get(`/api/clubs/${slug}`).then(async (res) => {
      setClub(res.data);
      navigation.setOptions({ title: res.data.name });
      const ev = await api.get(`/api/events?club_id=${res.data._id}`);
      setEvents(ev.data.events);
    }).catch(() => {});
  }, [slug]);

  if (!club) return <View className="flex-1 bg-bgDark" />;

  return (
    <ScrollView className="flex-1 bg-bgDark">
      {club.cover_image && (
        <Image source={{ uri: club.cover_image }} className="w-full h-52" resizeMode="cover" />
      )}
      <View className="px-4 pt-4">
        <Text className="text-textLight text-2xl font-extrabold">{club.name}</Text>
        <Text className="text-textMuted mt-1">
          {club.location?.address ? `${club.location.address}, ` : ''}{club.location?.city}
        </Text>

        <View className="flex-row mt-4 bg-bgCard rounded-xl p-1 border border-accent3">
          {(['events', 'info'] as const).map((t) => (
            <Pressable
              key={t}
              className={`flex-1 py-2.5 rounded-lg items-center ${tab === t ? 'bg-accent1' : ''}`}
              onPress={() => setTab(t)}
            >
              <Text className={tab === t ? 'text-white font-bold' : 'text-textMuted'}>
                {t === 'events' ? 'Eventi' : 'Info'}
              </Text>
            </Pressable>
          ))}
        </View>

        <View className="mt-4 mb-10">
          {tab === 'events' ? (
            events.length ? events.map((e) => <EventCard key={e._id} event={e} />) : (
              <Text className="text-textMuted text-center mt-6">Nema nadolazećih evenata.</Text>
            )
          ) : (
            <View className="bg-bgCard rounded-xl p-4 border border-accent3">
              {club.description ? (
                <Text className="text-textLight leading-5 mb-3">{club.description}</Text>
              ) : null}
              <InfoRow label="Kapacitet" value={club.capacity ? `${club.capacity} ljudi` : null} />
              <InfoRow label="Radno vrijeme" value={club.working_hours} />
              <InfoRow label="Dress code" value={club.dress_code} />
              <InfoRow label="Dobna granica" value={club.age_limit ? `${club.age_limit}+` : null} />
              {(club.amenities ?? []).length > 0 && (
                <InfoRow label="Sadržaji" value={club.amenities.join(', ')} />
              )}
              {club.social_links?.instagram && (
                <InfoRow label="Instagram" value={club.social_links.instagram} />
              )}
            </View>
          )}
        </View>
      </View>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <View className="flex-row justify-between py-2 border-b border-accent3/50">
      <Text className="text-textMuted">{label}</Text>
      <Text className="text-textLight font-semibold flex-1 text-right ml-4">{value}</Text>
    </View>
  );
}
