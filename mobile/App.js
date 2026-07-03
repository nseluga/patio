import { useState, useEffect } from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import * as SecureStore from 'expo-secure-store';
import { Swords, Home, Clock, Trophy, User } from 'lucide-react-native';

import UserContext from './src/UserContext';
import api from './src/api';

import Login from './src/screens/Login';
import Register from './src/screens/Register';
import PvP from './src/screens/PvP';
import CPU from './src/screens/CPU';
import Ongoing from './src/screens/Ongoing';
import Leaderboard from './src/screens/Leaderboard';
import Profile from './src/screens/Profile';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={Login} />
      <Stack.Screen name="Register" component={Register} />
    </Stack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: '#1a1a1a',
        tabBarInactiveTintColor: '#999',
        tabBarIcon: ({ color, size }) => {
          if (route.name === 'BOARD') return <Trophy color={color} size={size} />;
          if (route.name === 'PvP') return <Swords color={color} size={size} />;
          if (route.name === 'HOUSE') return <Home color={color} size={size} />;
          if (route.name === 'LIVE') return <Clock color={color} size={size} />;
          if (route.name === 'ME') return <User color={color} size={size} />;
          return null;
        },
      })}
    >
      <Tab.Screen name="BOARD" component={Leaderboard} />
      <Tab.Screen name="PvP" component={PvP} />
      <Tab.Screen name="HOUSE" component={CPU} />
      <Tab.Screen name="LIVE" component={Ongoing} />
      <Tab.Screen name="ME" component={Profile} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      try {
        const token = await SecureStore.getItemAsync('token');
        if (!token) {
          setLoading(false);
          return;
        }

        const res = await api.get('/me');
        const userObj = {
          ...res.data,
          playerId: res.data.id,
          token,
        };
        setUser(userObj);
      } catch {
        await SecureStore.deleteItemAsync('token');
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    bootstrap();
  }, []);

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#1a1a1a" />
      </View>
    );
  }

  return (
    <UserContext.Provider value={{ user, setUser }}>
      <NavigationContainer>
        {user ? <MainTabs /> : <AuthStack />}
      </NavigationContainer>
    </UserContext.Provider>
  );
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
});
