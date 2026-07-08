import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { Colors } from '../../constants/colors';

type IoniconName = keyof typeof Ionicons.glyphMap;

function icon(focused: string, unfocused: string) {
  return ({ color, focused: isFocused }: { color: string; focused: boolean }) => (
    <Ionicons name={(isFocused ? focused : unfocused) as IoniconName} size={22} color={color} />
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.inkSoft,
          borderTopColor: Colors.line,
          borderTopWidth: 1,
          height: 62,
          paddingTop: 6,
          paddingBottom: 8,
        },
        tabBarLabelStyle: { fontFamily: 'Inter_500Medium', fontSize: 11 },
        tabBarActiveTintColor: Colors.neon,
        tabBarInactiveTintColor: Colors.muted,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Početna', tabBarIcon: icon('home', 'home-outline') }}
      />
      <Tabs.Screen
        name="explore"
        options={{ title: 'Pretraži', tabBarIcon: icon('compass', 'compass-outline') }}
      />
      <Tabs.Screen
        name="tickets"
        options={{ title: 'Karte', tabBarIcon: icon('ticket', 'ticket-outline') }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: 'Profil', tabBarIcon: icon('person', 'person-outline') }}
      />
    </Tabs>
  );
}
