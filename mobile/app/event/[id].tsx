import { useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Image, Pressable, ScrollView, Text, View } from 'react-native';
import PaymentSheet from '../../components/PaymentSheet';
import { api, errorMessage } from '../../services/api';

/** Detalji eventa: lineup, tipovi karata (kupnja), ulaz u rezervaciju stola. */
export default function EventDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const navigation = useNavigation();
  const [event, setEvent] = useState<any>(null);
  const [purchase, setPurchase] = useState<{ clientSecret: string; ticketId: string; pi?: string } | null>(null);
  const [buying, setBuying] = useState<string | null>(null);

  function load() {
    api.get(`/api/events/${id}`).then((res) => {
      setEvent(res.data);
      navigation.setOptions({ title: res.data.name });
    }).catch(() => {});
  }

  useEffect(load, [id]);

  async function buyTicket(ticketTypeId: string) {
    setBuying(ticketTypeId);
    try {
      const res = await api.post('/api/tickets/purchase', {
        event_id: id, ticket_type_id: ticketTypeId,
      });
      setPurchase({ clientSecret: res.data.client_secret, ticketId: res.data.ticket_id });
    } catch (err: any) {
      Alert.alert('Kupnja nije moguća', errorMessage(err));
    } finally {
      setBuying(null);
    }
  }

  if (!event) return <View className="flex-1 bg-bgDark" />;

  const date = new Date(event.date);

  return (
    <ScrollView className="flex-1 bg-bgDark">
      {event.cover_image && (
        <Image source={{ uri: event.cover_image }} className="w-full h-56" resizeMode="cover" />
      )}
      <View className="px-4 pt-4 pb-12">
        <Text className="text-accent1 font-semibold uppercase text-xs">
          {date.toLocaleDateString('hr-HR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </Text>
        <Text className="text-textLight text-3xl font-extrabold mt-1">{event.name}</Text>
        <Text className="text-textMuted mt-1">
          {event.club?.name} · {event.club?.location?.city}
          {event.doors_open ? ` · vrata: ${event.doors_open}` : ''}
        </Text>

        {event.description ? (
          <Text className="text-textLight leading-5 mt-4">{event.description}</Text>
        ) : null}

        {(event.lineup ?? []).length > 0 && (
          <>
            <Text className="text-textLight text-lg font-bold mt-6 mb-2">Lineup</Text>
            {event.lineup.map((a: any, i: number) => (
              <View key={i} className="flex-row justify-between bg-bgCard rounded-xl p-3 mb-2 border border-accent3">
                <Text className="text-textLight font-semibold">{a.artist_name}</Text>
                {a.stage_time ? <Text className="text-textMuted">{a.stage_time}</Text> : null}
              </View>
            ))}
          </>
        )}

        <Text className="text-textLight text-lg font-bold mt-6 mb-2">Ulaznice</Text>
        {(event.ticket_types ?? []).filter((t: any) => t.is_active !== false).map((t: any) => {
          const soldOut = t.sold_quantity >= t.total_quantity;
          return (
            <View key={t.id} className="bg-bgCard rounded-xl p-4 mb-2 border border-accent3 flex-row items-center">
              <View className="flex-1">
                <Text className="text-textLight font-semibold">{t.name}</Text>
                <Text className="text-textMuted text-xs mt-0.5">
                  {soldOut ? 'Rasprodano' : `${t.total_quantity - t.sold_quantity} preostalo`}
                </Text>
              </View>
              <Text className="text-textLight font-bold mr-4">{t.price} €</Text>
              <Pressable
                className={`px-4 py-2.5 rounded-full ${soldOut ? 'bg-accent3' : 'bg-accent1'}`}
                disabled={soldOut || buying === t.id}
                onPress={() => buyTicket(t.id)}
              >
                <Text className="text-white font-bold">
                  {buying === t.id ? '…' : soldOut ? '—' : 'Kupi'}
                </Text>
              </Pressable>
            </View>
          );
        })}

        {purchase && (
          <View className="mt-3">
            <PaymentSheet
              clientSecret={purchase.clientSecret}
              label="Plati karticom / Apple Pay / Google Pay"
              onSuccess={() => {
                setPurchase(null);
                Alert.alert('Uspjeh', 'Karta je kupljena! Nalazi se pod „Moje karte".');
                // Fallback potvrda za lokalni razvoj bez webhooka
                const pi = purchase.clientSecret.split('_secret')[0];
                api.post('/api/tickets/confirm', { payment_intent_id: pi }).catch(() => {});
                load();
              }}
              onError={(msg) => Alert.alert('Plaćanje nije uspjelo', msg)}
            />
          </View>
        )}

        <Pressable
          className="bg-accent2 rounded-xl py-4 items-center mt-6"
          onPress={() => router.push(`/reservation/map/${id}`)}
        >
          <Text className="text-white font-bold text-base">Rezerviraj stol</Text>
        </Pressable>

        {(event.age_limit || event.dress_code) && (
          <Text className="text-textMuted text-xs mt-4 text-center">
            {event.age_limit ? `${event.age_limit}+` : ''}
            {event.age_limit && event.dress_code ? ' · ' : ''}
            {event.dress_code ?? ''}
          </Text>
        )}
      </View>
    </ScrollView>
  );
}
