import { useCallback, useEffect, useState } from 'react';
import { FlatList, RefreshControl, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import ClubCard from '../../components/ClubCard';
import EventCard from '../../components/EventCard';
import FadeIn from '../../components/ui/FadeIn';
import ScreenHeader from '../../components/ui/ScreenHeader';
import { Colors } from '../../constants/colors';
import { api } from '../../services/api';

/** Home: nadolazeći eventi + istaknuti klubovi. */
export default function Home() {
  const [events, setEvents] = useState<any[]>([]);
  const [clubs, setClubs] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [eventsRes, clubsRes] = await Promise.all([
        api.get('/api/events/upcoming?limit=10'),
        api.get('/api/clubs'),
      ]);
      setEvents(eventsRes.data.events);
      setClubs(clubsRes.data.clubs.slice(0, 5));
    } catch {
      // offline / backend nedostupan — ostavi zadnje stanje
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-ink">
      <FlatList
        className="px-5"
        showsVerticalScrollIndicator={false}
        data={events}
        keyExtractor={(e) => e._id}
        renderItem={({ item, index }) => (
          <FadeIn delay={Math.min(index, 6) * 60}>
            <EventCard event={item} />
          </FadeIn>
        )}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={Colors.neon} />
        }
        ListHeaderComponent={<ScreenHeader eyebrow="Novalja · Zrće" title="Nadolazeći eventi" />}
        ListEmptyComponent={
          <Text className="text-muted font-body text-center mt-10">
            Trenutno nema objavljenih evenata.
          </Text>
        }
        ListFooterComponent={
          <View className="mb-10">
            <Text className="text-white font-display text-[26px] uppercase mt-8 mb-4" style={{ letterSpacing: 0.5 }}>
              Klubovi
            </Text>
            {clubs.map((c, i) => (
              <FadeIn key={c._id} delay={Math.min(i, 5) * 60}>
                <ClubCard club={c} />
              </FadeIn>
            ))}
          </View>
        }
      />
    </SafeAreaView>
  );
}
