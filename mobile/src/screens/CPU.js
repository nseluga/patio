import { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Modal,
  FlatList,
  ImageBackground,
  Alert,
  SafeAreaView,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { removeBetByIndex } from '../utils/acceptHandling';
import { formatTimeAgo } from '../utils/timeUtils';
import UserContext from '../UserContext';
import api from '../api';

const back1 = require('../assets/images/back1.png');

const BET_TYPE_ENDPOINTS = {
  'Caps - Shots Made': '/cpu/create_caps_shots_bet',
  'Beerball - Shots Made': '/cpu/create_beerball_shots_bet',
  'Pong - Shots Made': '/cpu/create_pong_shots_bet',
  'Caps - Score': '/cpu/create_caps_score_bet',
  'Beerball - Score': '/cpu/create_beerball_score_bet',
  'Pong - Score': '/cpu/create_pong_score_bet',
};

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

export default function CPU() {
  const { user } = useContext(UserContext);
  const [bets, setBets] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedBetType, setSelectedBetType] = useState('');
  const [gameSize, setGameSize] = useState('1v1');
  const [popupMessage, setPopupMessage] = useState('');

  const isCPUAdmin = user?.playerId === 0;

  const fetchBets = async () => {
    try {
      const res = await api.get('/cpu_bets');
      setBets(res.data);
    } catch (err) {
      console.error('Error fetching CPU bets:', err);
    }
  };

  useEffect(() => {
    if (!user?.token) return;
    fetchBets();
  }, [user?.token]);

  const visibleBets = isCPUAdmin ? [] : bets;

  const acceptBet = async (bet, index) => {
    try {
      const res = await api.post(`/accept_cpu_bet/${bet.id}`, null);
      if (res.status === 200) {
        setBets((prev) => {
          const updated = [...prev];
          updated.splice(index, 1);
          return updated;
        });
        await addOngoingBet(bet);
      }
    } catch (err) {
      console.error('CPU bet accept error:', err);
    }
  };

  const handleGenerate = async () => {
    const endpoint = BET_TYPE_ENDPOINTS[selectedBetType];
    if (!endpoint) {
      Alert.alert('', 'Please select a valid bet type.');
      return;
    }
    try {
      await api.post(endpoint, { gameSize });
      setPopupMessage('✅ CPU bet created!');
      setTimeout(() => setPopupMessage(''), 3000);
      setShowModal(false);
      await fetchBets();
    } catch (err) {
      Alert.alert('', '❌ ' + (err.response?.data?.error || 'Unknown error'));
    }
  };

  const renderBet = ({ item: bet, index }) => {
    const flipped = bet.lineType === 'Over' ? 'Under' : 'Over';
    return (
      <View style={styles.betCard}>
        <View style={styles.betTop}>
          <Text style={styles.posterTime}>CPU · {formatTimeAgo(bet.timePosted)}</Text>
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
            {flipped} {bet.lineNumber}
          </Text>
        </View>
        <Pressable style={styles.acceptBtn} onPress={() => acceptBet(bet, index)}>
          <Text style={styles.acceptText}>ACCEPT</Text>
        </Pressable>
      </View>
    );
  };

  return (
    <ImageBackground source={back1} style={styles.bg} resizeMode="cover">
      <SafeAreaView style={styles.container}>
        {popupMessage ? (
          <View style={styles.popup}>
            <Text style={styles.popupText}>{popupMessage}</Text>
          </View>
        ) : null}

        <View style={styles.header}>
          <Text style={styles.title}>HOUSE BETS</Text>
          {isCPUAdmin && (
            <Pressable style={styles.createBtn} onPress={() => setShowModal(true)}>
              <Text style={styles.createBtnText}>+ Generate</Text>
            </Pressable>
          )}
        </View>

        <FlatList
          data={visibleBets}
          keyExtractor={(item, i) => String(item.id ?? i)}
          renderItem={renderBet}
          contentContainerStyle={styles.list}
        />

        <Modal visible={showModal} transparent animationType="slide">
          <View style={styles.modalOverlay}>
            <View style={styles.modal}>
              <Text style={styles.modalTitle}>Generate CPU Bet</Text>

              <View style={styles.pickerWrap}>
                <Picker selectedValue={selectedBetType} onValueChange={setSelectedBetType}>
                  <Picker.Item label="Select Bet Type" value="" />
                  {Object.keys(BET_TYPE_ENDPOINTS).map((t) => (
                    <Picker.Item key={t} label={t} value={t} />
                  ))}
                </Picker>
              </View>

              <View style={styles.pickerWrap}>
                <Picker selectedValue={gameSize} onValueChange={setGameSize}>
                  <Picker.Item label="1v1" value="1v1" />
                  <Picker.Item label="2v2" value="2v2" />
                  <Picker.Item label="3v3" value="3v3" />
                </Picker>
              </View>

              <View style={styles.modalActions}>
                <Pressable style={styles.cancelBtn} onPress={() => setShowModal(false)}>
                  <Text style={styles.cancelText}>Cancel</Text>
                </Pressable>
                <Pressable style={styles.confirmBtn} onPress={handleGenerate}>
                  <Text style={styles.confirmText}>Generate</Text>
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
  modal: { backgroundColor: '#fff', borderRadius: 16, padding: 20 },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 16,
    color: '#1a1a1a',
  },
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
