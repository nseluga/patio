import { useContext } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ImageBackground,
  Image,
  ScrollView,
  Alert,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import UserContext from '../UserContext';
import api from '../api';

const back1 = require('../assets/images/back1.png');
const defaultProfile = require('../assets/images/defaultProfile.png');

export default function Profile() {
  const { user, setUser } = useContext(UserContext);

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('token');
    await SecureStore.deleteItemAsync('playerId');
    await SecureStore.deleteItemAsync('username');
    setUser(null);
    // App.js re-renders automatically to AuthStack
  };

  const handleCleanupBets = async () => {
    try {
      await api.post('/cleanup_bets');
      Alert.alert('Success', '✅ Expired bets cleaned up!');
    } catch (err) {
      console.error('Cleanup failed:', err);
      Alert.alert('Error', '❌ Cleanup failed. Try again.');
    }
  };

  if (!user) return null;

  return (
    <ImageBackground source={back1} style={styles.bg} resizeMode="cover">
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>PROFILE</Text>
          <Pressable onPress={handleLogout} style={styles.logoutBtn}>
            <Text style={styles.logoutText}>Log Out</Text>
          </Pressable>
        </View>

        <Image source={defaultProfile} style={styles.avatar} />
        <Text style={styles.username}>{user.username}</Text>

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{user.caps_balance ?? 0}</Text>
            <Text style={styles.statLabel}>caps</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{user.pvp_bets_won ?? 0}</Text>
            <Text style={styles.statLabel}>bets won</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{user.pvp_bets_played ?? 0}</Text>
            <Text style={styles.statLabel}>bets played</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Recent Bets</Text>
        {(user.recent_bets || []).map((bet, i) => (
          <View key={i} style={styles.betCard}>
            <Text style={styles.betType}>{bet.gameType}</Text>
            <Text style={styles.betStatus}>
              {bet.status} · {bet.amount} caps
            </Text>
          </View>
        ))}

        <Pressable onPress={handleCleanupBets} style={styles.cleanupBtn}>
          <Text style={styles.cleanupText}>🧹 Clean Up Expired Bets</Text>
        </Pressable>
      </ScrollView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  container: {
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 40,
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    letterSpacing: 2,
    color: '#1a1a1a',
  },
  logoutBtn: {
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  logoutText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginBottom: 12,
    backgroundColor: '#eee',
  },
  username: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: 24,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius: 12,
    paddingVertical: 16,
    marginBottom: 24,
  },
  stat: { alignItems: 'center' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#1a1a1a' },
  statLabel: { fontSize: 12, color: '#666', marginTop: 4 },
  sectionTitle: {
    alignSelf: 'flex-start',
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: 12,
  },
  betCard: {
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  betType: { fontSize: 15, fontWeight: '600', color: '#1a1a1a' },
  betStatus: { fontSize: 13, color: '#666', marginTop: 4 },
  cleanupBtn: {
    marginTop: 24,
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
  },
  cleanupText: { color: '#fff', fontSize: 15, fontWeight: '600' },
});
