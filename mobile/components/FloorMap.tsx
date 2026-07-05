import { useCallback, useEffect, useState } from 'react';
import { Modal, Pressable, Text, View } from 'react-native';
import Svg, { Image as SvgImage } from 'react-native-svg';
import { useSocketEvent } from '../hooks/useSocket';
import { joinEventRoom, leaveEventRoom } from '../services/socket';
import TableMarker, { FloorTable } from './TableMarker';

/**
 * SVG mapa stolova:
 * - slika tlocrta kao pozadina, stolovi pozicionirani u % koordinatama
 * - slobodan stol: zeleni rub → modal s detaljima i gumbom "Rezerviraj"
 * - rezerviran stol: crveni rub, neklikabilan
 * - real-time: Socket.IO `table_updated` ažurira dostupnost bez refresha
 */
export default function FloorMap({
  map, eventId, onReserve,
}: {
  map: any;
  eventId: string;
  onReserve: (table: FloorTable) => void;
}) {
  const [tables, setTables] = useState<FloorTable[]>(map.tables ?? []);
  const [selected, setSelected] = useState<FloorTable | null>(null);

  useEffect(() => {
    setTables(map.tables ?? []);
  }, [map]);

  useEffect(() => {
    joinEventRoom(eventId);
    return () => leaveEventRoom(eventId);
  }, [eventId]);

  const onTableUpdate = useCallback((data: any) => {
    if (String(data.event_id) !== String(eventId)) return;
    setTables((prev) =>
      prev.map((t) =>
        t.id === data.table_id
          ? { ...t, is_available: data.status === 'free', reservation_status: data.status === 'free' ? null : data.status }
          : t),
    );
  }, [eventId]);

  useSocketEvent('table_updated', onTableUpdate);

  return (
    <View>
      <Svg
        viewBox="0 0 100 70"
        style={{ width: '100%', aspectRatio: 100 / 70, backgroundColor: '#0A0010', borderRadius: 12 }}
      >
        {map.background_image_url && (
          <SvgImage
            href={{ uri: map.background_image_url }}
            x="0" y="0" width="100" height="70"
            preserveAspectRatio="xMidYMid slice"
            opacity={0.45}
          />
        )}
        {tables.map((t) => (
          <TableMarker key={t.id} table={t} onPress={setSelected} />
        ))}
      </Svg>

      <View className="flex-row gap-4 mt-3">
        <View className="flex-row items-center gap-1">
          <View className="w-3 h-3 rounded-sm border-2 border-success bg-accent3" />
          <Text className="text-textMuted text-xs">Slobodno</Text>
        </View>
        <View className="flex-row items-center gap-1">
          <View className="w-3 h-3 rounded-sm border-2 border-error bg-accent3/40" />
          <Text className="text-textMuted text-xs">Rezervirano</Text>
        </View>
      </View>

      <Modal visible={!!selected} transparent animationType="slide" onRequestClose={() => setSelected(null)}>
        <Pressable className="flex-1 bg-black/70 justify-end" onPress={() => setSelected(null)}>
          <Pressable className="bg-bgCard rounded-t-3xl p-6" onPress={() => {}}>
            {selected && (
              <>
                <Text className="text-textLight text-2xl font-extrabold">
                  {selected.type === 'vip_separe' ? 'VIP separé' : 'Stol'} {selected.label}
                </Text>
                <Text className="text-textMuted mt-2">Kapacitet: do {selected.capacity} osoba</Text>
                {selected.min_spend > 0 && (
                  <Text className="text-textMuted mt-1">Minimalna potrošnja: {selected.min_spend} €</Text>
                )}
                {selected.type === 'vip_separe' && selected.deposit > 0 && (
                  <Text className="text-warning mt-1">
                    Depozit: {selected.deposit} € (pretvara se u kupon za piće)
                  </Text>
                )}
                {selected.description ? (
                  <Text className="text-textMuted mt-2">{selected.description}</Text>
                ) : null}
                <Pressable
                  className="bg-accent1 rounded-xl py-4 items-center mt-6"
                  onPress={() => { const t = selected; setSelected(null); onReserve(t); }}
                >
                  <Text className="text-white font-bold text-base">Rezerviraj</Text>
                </Pressable>
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}
