import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Image, ScrollView, StyleSheet, Text, View } from 'react-native';
import EventCard from '../../components/EventCard';
import PressableScale from '../../components/ui/PressableScale';
import { scrim } from '../../constants/theme';
import { api } from '../../services/api';

/** Detalji kluba — tabovi: Eventi | Info. */
export default function ClubDetail() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [club, setClub] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [tab, setTab] = useState<'events' | 'info'>('events');

  useEffect(() => {
    api.get(`/api/clubs/${slug}`).then(async (res) => {
      setClub(res.data);
      const ev = await api.get(`/api/events?club_id=${res.data._id}`);
      setEvents(ev.data.events);
    }).catch(() => {});
  }, [slug]);

  if (!club) return <View className="flex-1 bg-ink" />;

  return (
    <ScrollView className="flex-1 bg-ink" showsVerticalScrollIndicator={false}>
      {/* Hero */}
      <View className="h-[340px] justify-end">
        {club.cover_image ? (
          <Image source={{ uri: club.cover_image }} style={StyleSheet.absoluteFill} resizeMode="cover" />
        ) : (
          <View style={StyleSheet.absoluteFill} className="bg-surfaceHi" />
        )}
        <LinearGradient colors={scrim as any} style={StyleSheet.absoluteFill} />
        <View className="px-5 pb-6">
          <Text className="text-white font-display text-[34px] leading-[38px] uppercase" style={{ letterSpacing: 0.4 }}>
            {club.name}
          </Text>
          <Text className="text-muted font-body mt-2">
            {club.location?.address ? `${club.location.address}, ` : ''}{club.location?.city}
          </Text>
        </View>
      </View>

      <View className="px-5 pt-5">
        <View className="flex-row bg-surface rounded-2xl p-1 border border-line">
          {(['events', 'info'] as const).map((t) => (
            <PressableScale
              key={t}
              className={`flex-1 py-2.5 rounded-xl items-center ${tab === t ? 'bg-neon' : ''}`}
              onPress={() => setTab(t)}
            >
              <Text className={tab === t ? 'text-white font-bodyBd' : 'text-muted font-bodyMd'}>
                {t === 'events' ? 'Eventi' : 'Info'}
              </Text>
            </PressableScale>
          ))}
        </View>

        <View className="mt-5 mb-12">
          {tab === 'events' ? (
            events.length ? events.map((e) => <EventCard key={e._id} event={e} />) : (
              <Text className="text-muted font-body text-center mt-8">Nema nadolazećih evenata.</Text>
            )
          ) : (
            <View className="bg-surface rounded-2xl p-5 border border-line">
              {club.description ? (
                <Text className="text-text font-body leading-6 mb-3">{club.description}</Text>
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
    <View className="flex-row justify-between py-3 border-b border-line">
      <Text className="text-muted font-body">{label}</Text>
      <Text className="text-white font-bodySb flex-1 text-right ml-4">{value}</Text>
    </View>
  );
}
