import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, ScrollView, Text, View } from 'react-native';
import FloorMap from '../../../components/FloorMap';
import { FloorTable } from '../../../components/TableMarker';
import { api, errorMessage } from '../../../services/api';

/** SVG mapa stolova s real-time dostupnošću — odabir i kreiranje rezervacije. */
export default function ReservationMap() {
  const { event_id } = useLocalSearchParams<{ event_id: string }>();
  const router = useRouter();
  const [map, setMap] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/api/floor-maps/event/${event_id}`)
      .then((res) => setMap(res.data))
      .catch((err) => setError(errorMessage(err)));
  }, [event_id]);

  async function reserve(table: FloorTable) {
    try {
      const res = await api.post('/api/reservations', {
        event_id, table_id: table.id, guests_count: table.capacity,
      });
      router.replace(`/reservation/confirm/${res.data.reservation_id}`);
    } catch (err: any) {
      Alert.alert('Rezervacija nije moguća', errorMessage(err));
    }
  }

  return (
    <ScrollView className="flex-1 bg-ink px-5 pt-5" showsVerticalScrollIndicator={false}>
      <Text className="text-white font-display text-[26px] uppercase" style={{ letterSpacing: 0.5 }}>Odaberi stol</Text>
      <Text className="text-muted font-body mt-1 mb-4">
        Dodirni slobodan (zeleni) stol za detalje i rezervaciju.
      </Text>
      {error ? <Text className="text-error font-body">{error}</Text> : null}
      {map && (
        <FloorMap map={map} eventId={String(event_id)} onReserve={reserve} />
      )}
      {map?.sections?.length > 0 && (
        <View className="mt-5 mb-10">
          <Text className="text-neon font-bodySb text-[11px] uppercase mb-2" style={{ letterSpacing: 2 }}>Sekcije</Text>
          {map.sections.map((s: any) => (
            <View key={s.id} className="flex-row items-center gap-2 mb-1.5">
              <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: s.color }} />
              <Text className="text-muted font-body">{s.name}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}
