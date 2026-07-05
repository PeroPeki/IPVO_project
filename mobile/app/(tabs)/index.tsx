import { useCallback, useEffect, useState } from 'react';
import { FlatList, RefreshControl, Text, View } from 'react-native';
import ClubCard from '../../components/ClubCard';
import EventCard from '../../components/EventCard';
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

  useEffect(() => {
    load();
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  return (
    <FlatList
      className="flex-1 bg-bgDark px-4"
      data={events}
      keyExtractor={(e) => e._id}
      renderItem={({ item }) => <EventCard event={item} />}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={Colors.accent1} />
      }
      ListHeaderComponent={
        <Text className="text-textLight text-2xl font-extrabold mt-4 mb-3">
          Nadolazeći eventi
        </Text>
      }
      ListEmptyComponent={
        <Text className="text-textMuted text-center mt-10">
          Trenutno nema objavljenih evenata.
        </Text>
      }
      ListFooterComponent={
        <View className="mb-8">
          <Text className="text-textLight text-2xl font-extrabold mt-6 mb-3">Klubovi</Text>
          {clubs.map((c) => <ClubCard key={c._id} club={c} />)}
        </View>
      }
    />
  );
}
