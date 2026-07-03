import { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  Modal,
  FlatList,
  ImageBackground,
  Alert,
  SafeAreaView,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { removeBetByIndex } from '../utils/acceptHandling';
import { formatTimeAgo } from '../utils/timeUtils';
import UserContext from '../UserContext';
import api from '../api';

const back1 = require('../assets/images/back1.png');

const flipLineType = (type) => (type === 'Over' ? 'Under' : 'Over');

// Append an accepted bet to the local AsyncStorage cache (Ongoing refetches from server anyway)
async function addOngoingBet(bet) {
  try {
    const raw = await AsyncStorage.getItem('ongoingBets');
    const list = raw ? JSON.parse(raw) : [];
    if (!list.some((b) => b.id === bet.id)) {
      list.push(bet);
      await AsyncStorage.setItem('ongoingBets', JSON.stringify(list));
    }
  } catch (err) {
    console.error('Failed to cache ongoing bet:', err);
  }
}

export default function PvP() {
  const { user } = useContext(UserContext);
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState('Shots Made');
  const [lineType, setLineType] = useState('Over');
  const [bets, setBets] = useState([]);
  const [matchup, setMatchup] = useState('');
  const [amount, setAmount] = useState('');
  const [lineNumber, setLineNumber] = useState('');
  const [gamePlayed, setGamePlayed] = useState('Caps');
  const [gameSize, setGameSize] = useState('2v2');
  const [popupMessage, setPopupMessage] = useState('');

  // Show the caps refreshed message once
  useEffect(() => {
    (async () => {
      const wasRefreshed = await SecureStore.getItemAsync('capsRefreshed');
      if (wasRefreshed === 'true') {
        setPopupMessage('✅ +100 caps added for the week!');
        setTimeout(() => setPopupMessage(''), 3000);
        await SecureStore.deleteItemAsync('capsRefreshed');
      }
    })();
  }, []);

  // Fetch PvP bets from backend
  useEffect(() => {
    if (!user?.playerId) return;
    const fetchBets = async () => {
      try {
        const res = await api.get('/pvp_bets', {
          params: { playerId: user.playerId },
        });
        setBets(res.data);
      } catch (err) {
        console.error('Error fetching PvP bets:', err);
      }
    };
    fetchBets();
  }, [user?.playerId]);

  const acceptBet = async (betId) => {
    try {
      const bet = bets.find((b) => b.id === betId);
      if (!bet) return;
      const accepterLineType = flipLineType(bet.lineType);
      const res = await api.post(`/accept_bet/${betId}`, { accepterLineType });
      if (res.status === 200) {
        setBets((prev) => prev.filter((b) => b.id !== betId));
        await addOngoingBet({ ...bet, accepterId: user.playerId });
      }
    } catch (err) {
      console.error('Request failed:', err);
    }
  };

  const handlePost = async () => {
    if (!matchup.trim() || !amount.trim() || !lineType.trim() || !lineNumber.trim()) {
      Alert.alert('', 'Please fill out all fields before posting.');
      return;
    }

    const newBet = {
      id: Date.now().toString(), // temp local key; server assigns real id
      poster: user?.username,
      posterId: user?.playerId,
      timePosted: new Date().toISOString(),
      matchup,
      amount: parseInt(amount),
      lineType,
      lineNumber: parseFloat(lineNumber),
      gameType,
      gamePlayed,
      gameSize: ['Shots Made', 'Score'].includes(gameType) ? gameSize : null,
    };

    try {
      const response = await api.post('/create_bet', newBet);
      if (response.status !== 201) {
        Alert.alert('', response.data?.error || 'Failed to post bet.');
        return;
      }
      setPopupMessage('✅ Bet posted!');
      setTimeout(() => setPopupMessage(''), 3000);
      setShowModal(false);
      setMatchup('');
      setAmount('');
      setLineNumber('');
      setLineType('Over');
      setGameType('Shots Made');
    } catch (err) {
      console.error('Network error:', err);
    }
  };

  const renderBet = ({ item: bet, index }) => (
    <View style={styles.betCard}>
      <View style={styles.betTop}>
        <Text style={styles.posterTime}>
          {bet.poster} · {formatTimeAgo(bet.timePosted)}
        </Text>
        <Pressable onPress={() => removeBetByIndex(index, setBets)}>
          <Text style={styles.dismiss}>×</Text>
        </Pressable>
      </View>
      <Text style={styles.subject}>{bet.matchup}</Text>
      <Text style={styles.meta}>Game: {bet.gamePlayed}</Text>
      <Text style={styles.meta}>Type: {bet.gameType}</Text>
      <View style={styles.betBottom}>
        <Text style={styles.amount}>{bet.amount} caps</Text>
        <Text style={styles.line}>
          {user?.playerId === bet.posterId
            ? `${bet.lineType} ${bet.lineNumber}`
            : `${flipLineType(bet.lineType)} ${bet.lineNumber}`}
        </Text>
      </View>
      <Pressable style={styles.acceptBtn} onPress={() => acceptBet(bet.id)}>
        <Text style={styles.acceptText}>ACCEPT</Text>
      </Pressable>
    </View>
  );

  return (
    <ImageBackground source={back1} style={styles.bg} resizeMode="cover">
      <SafeAreaView style={styles.container}>
        {popupMessage ? (
          <View style={styles.popup}>
            <Text style={styles.popupText}>{popupMessage}</Text>
          </View>
        ) : null}

        <View style={styles.header}>
          <Text style={styles.title}>PvP BETS</Text>
          <Pressable style={styles.createBtn} onPress={() => setShowModal(true)}>
            <Text style={styles.createBtnText}>+ Create</Text>
          </Pressable>
        </View>

        <FlatList
          data={bets}
          keyExtractor={(item, i) => String(item.id ?? i)}
          renderItem={renderBet}
          contentContainerStyle={styles.list}
        />

        <Modal visible={showModal} transparent animationType="slide">
          <View style={styles.modalOverlay}>
            <View style={styles.modal}>
              <Text style={styles.modalTitle}>CREATE A BET!</Text>

              <TextInput
                style={styles.input}
                placeholder="Matchup"
                placeholderTextColor="#999"
                value={matchup}
                onChangeText={setMatchup}
              />
              <TextInput
                style={styles.input}
                placeholder="Amount (caps)"
                placeholderTextColor="#999"
                keyboardType="numeric"
                value={amount}
                onChangeText={setAmount}
              />

              <View style={styles.toggleRow}>
                <Pressable
                  style={[styles.toggle, lineType === 'Over' && styles.toggleActive]}
                  onPress={() => setLineType('Over')}
                >
                  <Text style={[styles.toggleText, lineType === 'Over' && styles.toggleTextActive]}>
                    Over
                  </Text>
                </Pressable>
                <Pressable
                  style={[styles.toggle, lineType === 'Under' && styles.toggleActive]}
                  onPress={() => setLineType('Under')}
                >
                  <Text style={[styles.toggleText, lineType === 'Under' && styles.toggleTextActive]}>
                    Under
                  </Text>
                </Pressable>
              </View>

              <TextInput
                style={styles.input}
                placeholder="Line"
                placeholderTextColor="#999"
                keyboardType="numeric"
                value={lineNumber}
                onChangeText={setLineNumber}
              />

              <View style={styles.pickerWrap}>
                <Picker selectedValue={gameType} onValueChange={setGameType}>
                  <Picker.Item label="Shots Made" value="Shots Made" />
                  <Picker.Item label="Score" value="Score" />
                  <Picker.Item label="Other" value="Other" />
                </Picker>
              </View>

              <View style={styles.pickerWrap}>
                <Picker selectedValue={gamePlayed} onValueChange={setGamePlayed}>
                  <Picker.Item label="Caps" value="Caps" />
                  <Picker.Item label="Pong" value="Pong" />
                  <Picker.Item label="Beerball" value="Beerball" />
                  <Picker.Item label="Campus Golf" value="Campus Golf" />
                  <Picker.Item label="Other" value="Other" />
                </Picker>
              </View>

              {['Score', 'Shots Made'].includes(gameType) && (
                <View style={styles.pickerWrap}>
                  <Picker selectedValue={gameSize} onValueChange={setGameSize}>
                    <Picker.Item label="1v1" value="1v1" />
                    <Picker.Item label="2v2" value="2v2" />
                    <Picker.Item label="3v3" value="3v3" />
                  </Picker>
                </View>
              )}

              <View style={styles.modalActions}>
                <Pressable style={styles.cancelBtn} onPress={() => setShowModal(false)}>
                  <Text style={styles.cancelText}>Cancel</Text>
                </Pressable>
                <Pressable style={styles.confirmBtn} onPress={handlePost}>
                  <Text style={styles.confirmText}>Post</Text>
                </Pressable>
              </View>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  container: { flex: 1, paddingHorizontal: 16, paddingTop: 50 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  title: { fontSize: 24, fontWeight: 'bold', letterSpacing: 1, color: '#1a1a1a' },
  createBtn: {
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  createBtnText: { color: '#fff', fontWeight: '600' },
  list: { paddingBottom: 40 },
  betCard: {
    backgroundColor: 'rgba(255,255,255,0.94)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  betTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  posterTime: { fontSize: 13, color: '#666' },
  dismiss: { fontSize: 22, color: '#999', paddingHorizontal: 6 },
  subject: { fontSize: 18, fontWeight: 'bold', color: '#1a1a1a', marginBottom: 4 },
  meta: { fontSize: 13, color: '#555' },
  betBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 12,
  },
  amount: { fontSize: 15, fontWeight: '600', color: '#1a1a1a' },
  line: { fontSize: 15, fontWeight: '600', color: '#1a1a1a' },
  acceptBtn: {
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  acceptText: { color: '#fff', fontWeight: 'bold', letterSpacing: 1 },
  popup: {
    backgroundColor: '#1a7a3a',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  popupText: { color: '#fff', textAlign: 'center', fontWeight: '600' },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  modal: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 16,
    color: '#1a1a1a',
  },
  input: {
    height: 46,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 14,
    marginBottom: 12,
    fontSize: 15,
    color: '#1a1a1a',
    backgroundColor: '#fafafa',
  },
  toggleRow: { flexDirection: 'row', marginBottom: 12, gap: 12 },
  toggle: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ccc',
    alignItems: 'center',
  },
  toggleActive: { backgroundColor: '#1a1a1a', borderColor: '#1a1a1a' },
  toggleText: { color: '#1a1a1a', fontWeight: '600' },
  toggleTextActive: { color: '#fff' },
  pickerWrap: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    marginBottom: 12,
    overflow: 'hidden',
  },
  modalActions: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  cancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ccc',
    alignItems: 'center',
    marginRight: 8,
  },
  cancelText: { color: '#1a1a1a', fontWeight: '600' },
  confirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    marginLeft: 8,
  },
  confirmText: { color: '#fff', fontWeight: '600' },
});
