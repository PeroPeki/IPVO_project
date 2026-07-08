import { Ionicons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import { FlatList, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import EventCard from '../../components/EventCard';
import FadeIn from '../../components/ui/FadeIn';
import PressableScale from '../../components/ui/PressableScale';
import ScreenHeader from '../../components/ui/ScreenHeader';
import { Colors } from '../../constants/colors';
import { glowSoft } from '../../constants/theme';
import { api } from '../../services/api';

/** Pretraga evenata po gradu. */
export default function Explore() {
  const [city, setCity] = useState('');
  const [activeCity, setActiveCity] = useState('');
  const [events, setEvents] = useState<any[]>([]);
  const [cities, setCities] = useState<string[]>([]);

  useEffect(() => {
    api.get('/api/clubs')
      .then((res) => {
        const unique = [...new Set(
          res.data.clubs.map((c: any) => c.location?.city).filter(Boolean),
        )] as string[];
        setCities(unique);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const params = activeCity ? `?city=${encodeURIComponent(activeCity)}` : '';
    api.get(`/api/events${params}`)
      .then((res) => setEvents(res.data.events))
      .catch(() => {});
  }, [activeCity]);

  const chips = ['', ...cities];

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
        ListHeaderComponent={
          <View>
            <ScreenHeader eyebrow="Pronađi svoju noć" title="Pretraži" />

            <View className="flex-row items-center bg-surface rounded-2xl px-4 border border-line">
              <Ionicons name="search" size={18} color={Colors.muted} />
              <TextInput
                className="flex-1 text-text font-body py-3.5 ml-2"
                placeholder="Pretraži po gradu…"
                placeholderTextColor={Colors.muted}
                value={city}
                onChangeText={setCity}
                onSubmitEditing={() => setActiveCity(city.trim())}
                returnKeyType="search"
              />
            </View>

            <View className="flex-row flex-wrap gap-2 mt-4 mb-5">
              {chips.map((c) => {
                const active = activeCity === c;
                return (
                  <PressableScale
                    key={c || 'all'}
                    className={`px-4 py-2 rounded-full ${active ? 'bg-neon' : 'bg-surface border border-line'}`}
                    style={active ? glowSoft : undefined}
                    onPress={() => { setActiveCity(c); setCity(c); }}
                  >
                    <Text className={active ? 'text-white font-bodySb text-xs' : 'text-muted font-bodyMd text-xs'}>
                      {c || 'Svi gradovi'}
                    </Text>
                  </PressableScale>
                );
              })}
            </View>
          </View>
        }
        ListEmptyComponent={
          <Text className="text-muted font-body text-center mt-10">
            Nema evenata za odabrani filter.
          </Text>
        }
        ListFooterComponent={<View className="h-10" />}
      />
    </SafeAreaView>
  );
}
