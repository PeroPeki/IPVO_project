import { useEffect, useState } from 'react';
import {
  Alert, FlatList, Pressable, Text, TextInput, View,
} from 'react-native';
import { Colors } from '../../constants/colors';
import { useAuth } from '../../hooks/useAuth';
import { api, errorMessage } from '../../services/api';

/** Hostesa: prijava PIN-om, odabir eventa, pretraga gostiju, check-in. */
export default function HostessScreen() {
  const { staff, role, staffLogin, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');

  const [events, setEvents] = useState<any[]>([]);
  const [eventId, setEventId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [guests, setGuests] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  const loggedIn = role === 'hostess' && staff;

  useEffect(() => {
    if (!loggedIn) return;
    api.get(`/api/events?club_id=${staff.club_id}`)
      .then((r) => setEvents(r.data.events))
      .catch(() => {});
  }, [loggedIn]);

  useEffect(() => {
    if (!eventId) return;
    loadGuests();
    const interval = setInterval(loadStats, 15000);
    loadStats();
    return () => clearInterval(interval);
  }, [eventId, search]);

  function loadGuests() {
    api.get(`/api/hostess/event/${eventId}/guests?search=${encodeURIComponent(search)}`)
      .then((r) => setGuests(r.data.guests))
      .catch(() => {});
  }

  function loadStats() {
    api.get(`/api/hostess/event/${eventId}/stats`).then((r) => setStats(r.data)).catch(() => {});
  }

  async function login() {
    setError('');
    try {
      await staffLogin(email.trim(), pin);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function checkin(guest: any) {
    const path = guest.type === 'ticket'
      ? `/api/hostess/checkin/ticket/${guest.id}`
      : `/api/hostess/checkin/reservation/${guest.id}`;
    try {
      const res = await api.post(path);
      Alert.alert('✓ Ulaz potvrđen', res.data.guest_name ?? guest.name);
      loadGuests();
      loadStats();
    } catch (err: any) {
      Alert.alert('Odbijeno', errorMessage(err));
    }
  }

  if (!loggedIn) {
    return (
      <View className="flex-1 bg-bgDark justify-center px-6">
        <Text className="text-textLight text-2xl font-extrabold mb-6">Prijava osoblja</Text>
        <TextInput
          className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
          placeholder="Email" placeholderTextColor={Colors.textMuted}
          autoCapitalize="none" value={email} onChangeText={setEmail}
        />
        <TextInput
          className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3 text-center text-2xl tracking-widest"
          placeholder="PIN" placeholderTextColor={Colors.textMuted}
          keyboardType="number-pad" maxLength={4} secureTextEntry
          value={pin} onChangeText={setPin}
        />
        {error ? <Text className="text-error mb-3">{error}</Text> : null}
        <Pressable className="bg-accent1 rounded-xl py-4 items-center" onPress={login} disabled={loading}>
          <Text className="text-white font-bold">Prijava</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-bgDark px-4 pt-4">
      {!eventId ? (
        <>
          <Text className="text-textLight text-xl font-extrabold mb-3">Odaberi event</Text>
          <FlatList
            data={events}
            keyExtractor={(e) => e._id}
            renderItem={({ item }) => (
              <Pressable
                className="bg-bgCard rounded-xl p-4 mb-2 border border-accent3"
                onPress={() => setEventId(item._id)}
              >
                <Text className="text-textLight font-bold">{item.name}</Text>
                <Text className="text-textMuted text-xs">
                  {new Date(item.date).toLocaleString('hr-HR')}
                </Text>
              </Pressable>
            )}
          />
        </>
      ) : (
        <>
          {stats && (
            <View className="flex-row gap-2 mb-3">
              <View className="flex-1 bg-bgCard rounded-xl p-3 border border-accent3 items-center">
                <Text className="text-accent1 text-xl font-extrabold">{stats.total_inside}</Text>
                <Text className="text-textMuted text-xs">Unutra</Text>
              </View>
              <View className="flex-1 bg-bgCard rounded-xl p-3 border border-accent3 items-center">
                <Text className="text-textLight text-xl font-extrabold">{stats.tickets_sold}</Text>
                <Text className="text-textMuted text-xs">Karata</Text>
              </View>
              <View className="flex-1 bg-bgCard rounded-xl p-3 border border-accent3 items-center">
                <Text className="text-textLight text-xl font-extrabold">{stats.reservations_confirmed}</Text>
                <Text className="text-textMuted text-xs">Rezervacija</Text>
              </View>
            </View>
          )}

          <TextInput
            className="bg-bgCard text-textLight rounded-xl px-4 py-3 mb-3 border border-accent3"
            placeholder="Pretraga po imenu/prezimenu…" placeholderTextColor={Colors.textMuted}
            value={search} onChangeText={setSearch}
          />

          <FlatList
            data={guests}
            keyExtractor={(g) => `${g.type}-${g.id}`}
            renderItem={({ item }) => {
              const inside = item.status === 'checked_in';
              return (
                <View className="bg-bgCard rounded-xl p-4 mb-2 border border-accent3 flex-row items-center">
                  <View className="flex-1">
                    <Text className="text-textLight font-semibold">{item.name}</Text>
                    <Text className="text-textMuted text-xs">{item.detail}</Text>
                  </View>
                  {inside ? (
                    <Text className="text-success font-bold">✓ Unutra</Text>
                  ) : (
                    <Pressable
                      className="bg-accent1 px-4 py-2.5 rounded-full"
                      onPress={() => checkin(item)}
                    >
                      <Text className="text-white font-bold">Check-in</Text>
                    </Pressable>
                  )}
                </View>
              );
            }}
            ListEmptyComponent={
              <Text className="text-textMuted text-center mt-8">Nema gostiju za prikaz.</Text>
            }
          />

          <Pressable className="py-3 items-center" onPress={() => setEventId(null)}>
            <Text className="text-accent1">← Promijeni event</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}
