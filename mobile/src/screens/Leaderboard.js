import { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, SafeAreaView } from 'react-native';
import api from '../api';

export default function Leaderboard() {
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    api
      .get('/leaderboard')
      .then((res) => setPlayers(res.data.slice(0, 5)))
      .catch((err) => console.error('Failed to fetch leaderboard:', err));
  }, []);

  const renderPlayer = ({ item, index }) => {
    const medal = ['🥇', '🥈', '🥉'][index] ?? `#${index + 1}`;
    return (
      <View style={styles.row}>
        <Text style={[styles.rank, index < 3 && styles.medal]}>{medal}</Text>
        <Text style={styles.username}>{item.username}</Text>
        <Text style={styles.caps}>{item.caps_balance} caps</Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>LEADERBOARD</Text>
      <FlatList
        data={players}
        keyExtractor={(_, i) => String(i)}
        renderItem={renderPlayer}
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 24,
    marginBottom: 16,
    letterSpacing: 2,
  },
  list: { paddingHorizontal: 24 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: '#eee',
  },
  rank: { width: 40, fontSize: 16, fontWeight: '600', color: '#555' },
  medal: { fontSize: 20 },
  username: { flex: 1, fontSize: 16, color: '#1a1a1a' },
  caps: { fontSize: 14, color: '#666' },
});
