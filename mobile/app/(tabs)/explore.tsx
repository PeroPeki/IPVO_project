import { useEffect, useState } from 'react';
import { FlatList, Pressable, Text, TextInput, View } from 'react-native';
import EventCard from '../../components/EventCard';
import { Colors } from '../../constants/colors';
import { api } from '../../services/api';

/** Pretraga evenata po gradu. */
export default function Explore() {
  const [city, setCity] = useState('');
  const [activeCity, setActiveCity] = useState('');
  const [events, setEvents] = useState<any[]>([]);
  const [cities, setCities] = useState<string[]>([]);

  useEffect(() => {
    // Popis gradova iz klubova
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

  return (
    <View className="flex-1 bg-bgDark px-4">
      <TextInput
        className="bg-bgCard text-textLight rounded-xl px-4 py-3 mt-4 border border-accent3"
        placeholder="Pretraži po gradu…"
        placeholderTextColor={Colors.textMuted}
        value={city}
        onChangeText={setCity}
        onSubmitEditing={() => setActiveCity(city.trim())}
        returnKeyType="search"
      />

      <View className="flex-row flex-wrap gap-2 mt-3">
        <Pressable
          className={`px-3 py-1.5 rounded-full ${!activeCity ? 'bg-accent1' : 'bg-bgCard border border-accent3'}`}
          onPress={() => { setActiveCity(''); setCity(''); }}
        >
          <Text className={!activeCity ? 'text-white font-bold' : 'text-textMuted'}>Svi</Text>
        </Pressable>
        {cities.map((c) => (
          <Pressable
            key={c}
            className={`px-3 py-1.5 rounded-full ${activeCity === c ? 'bg-accent1' : 'bg-bgCard border border-accent3'}`}
            onPress={() => { setActiveCity(c); setCity(c); }}
          >
            <Text className={activeCity === c ? 'text-white font-bold' : 'text-textMuted'}>{c}</Text>
          </Pressable>
        ))}
      </View>

      <FlatList
        className="mt-4"
        data={events}
        keyExtractor={(e) => e._id}
        renderItem={({ item }) => <EventCard event={item} />}
        ListEmptyComponent={
          <Text className="text-textMuted text-center mt-10">Nema evenata za odabrani filter.</Text>
        }
      />
    </View>
  );
}
