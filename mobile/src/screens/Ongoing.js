import { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  Modal,
  FlatList,
  ScrollView,
  ImageBackground,
  SafeAreaView,
} from 'react-native';
import { formatTimeAgo } from '../utils/timeUtils';
import UserContext from '../UserContext';
import api from '../api';

const back1 = require('../assets/images/back1.png');

function getNumPlayers(gameSize) {
  if (!gameSize) return 2;
  const [a] = gameSize.split('v').map(Number);
  return isNaN(a) ? 2 : a;
}

const flipLineType = (type) => (type === 'Over' ? 'Under' : 'Over');

export default function Ongoing() {
  const { user } = useContext(UserContext);
  const [bets, setBets] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [activeBetId, setActiveBetId] = useState(null);
  const [popupMessage, setPopupMessage] = useState('');

  // Score bets
  const [yourTeamA, setYourTeamA] = useState([]);
  const [yourScoreA, setYourScoreA] = useState('');
  const [yourTeamB, setYourTeamB] = useState([]);
  const [yourScoreB, setYourScoreB] = useState('');

  // Shots Made
  const [yourPlayer, setYourPlayer] = useState('');
  const [yourShots, setYourShots] = useState('');

  // Other
  const [yourOutcome, setYourOutcome] = useState('');

  const fetchBets = async () => {
    try {
      const res = await api.get('/ongoing_bets');
      setBets(res.data);
    } catch (err) {
      console.error('Failed to fetch bets from DB:', err);
    }
  };

  useEffect(() => {
    if (user?.token) fetchBets();
  }, [user?.token]);

  const isCPUAdmin = user?.playerId === 0;

  const uniqueVisibleBets = [
    ...new Map(
      bets
        .filter((b) => {
          if (!b || !b.id) return false;
          if (isCPUAdmin) return b.posterId === 0;
          return true;
        })
        .map((bet) => [bet.id, bet])
    ).values(),
  ];

  const getGameType = () => {
    const bet = bets.find((b) => b.id === activeBetId);
    return bet?.gameType || 'Shots Made';
  };

  const openStatsModal = (bet) => {
    setActiveBetId(bet.id);
    const numPlayers = getNumPlayers(bet.gameSize || '2v2');
    setYourTeamA(Array.from({ length: numPlayers }, () => ({ name: '', score: '' })));
    setYourTeamB(Array.from({ length: numPlayers }, () => ({ name: '', score: '' })));
    setYourScoreA('');
    setYourScoreB('');
    setYourPlayer('');
    setYourShots('');
    setYourOutcome('');
    setShowModal(true);
  };

  const resetForm = () => {
    setShowModal(false);
    setActiveBetId(null);
    setYourTeamA([]);
    setYourTeamB([]);
    setYourScoreA('');
    setYourScoreB('');
    setYourPlayer('');
    setYourShots('');
    setYourOutcome('');
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const res = await api.post(`/submit_stats/${activeBetId}`, {
        playerId: user.playerId,
        gameType: getGameType(),
        yourTeamA: yourTeamA.map((p) => p.name),
        yourTeamB: yourTeamB.map((p) => p.name),
        yourScoreA,
        yourScoreB,
        yourPlayer,
        yourShots,
        yourOutcome,
      });

      if (res.data.match) {
        setPopupMessage('✅ Match confirmed!');
        setTimeout(() => setPopupMessage(''), 3000);
      }

      await fetchBets();
    } catch (err) {
      console.error('Error submitting stats:', err);
    } finally {
      setSubmitting(false);
      resetForm();
    }
  };

  const updateTeamName = (team, setTeam, index, value) => {
    const next = [...team];
    next[index] = { ...next[index], name: value };
    setTeam(next);
  };

  const renderBet = ({ item: bet }) => (
    <View style={styles.betCard}>
      <View style={styles.betTop}>
        <Text style={styles.posterTime}>
          {bet.poster} · {formatTimeAgo(bet.timePosted)}
        </Text>
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
      {bet.status_message ? <Text style={styles.statusText}>{bet.status_message}</Text> : null}
      <Pressable style={styles.acceptBtn} onPress={() => openStatsModal(bet)}>
        <Text style={styles.acceptText}>Enter Stats</Text>
      </Pressable>
    </View>
  );

  const gameType = getGameType();

  return (
    <ImageBackground source={back1} style={styles.bg} resizeMode="cover">
      <SafeAreaView style={styles.container}>
        {popupMessage ? (
          <View style={styles.popup}>
            <Text style={styles.popupText}>{popupMessage}</Text>
          </View>
        ) : null}

        <View style={styles.header}>
          <Text style={styles.title}>ONGOING BETS</Text>
          <Pressable style={styles.helpBtn} onPress={() => setShowHelp(true)}>
            <Text style={styles.helpText}>?</Text>
          </Pressable>
        </View>

        <FlatList
          data={uniqueVisibleBets}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderBet}
          contentContainerStyle={styles.list}
        />

        {/* Help modal */}
        <Modal visible={showHelp} transparent animationType="slide">
          <View style={styles.modalOverlay}>
            <View style={styles.modal}>
              <ScrollView>
                <Text style={styles.modalTitle}>How to Enter Stats</Text>
                <Text style={styles.helpPara}>
                  While entering player stats, please follow these guidelines:
                </Text>
                <Text style={styles.helpPara}>
                  Enter each player's real name with the first letter capitalized.
                </Text>
                <Text style={styles.helpPara}>ie: "Nate", "Mike", "Stryker"</Text>
                <Text style={styles.helpPara}>
                  For Score bets, enter each side's total points at end of game.
                </Text>
                <Text style={styles.helpPara}>
                  For Shots Made, enter the number of successful shots made by the player.
                </Text>
                <Text style={styles.helpPara}>
                  For Other, enter the stat value relevant to the custom line.
                </Text>
                <Text style={styles.helpPara}>
                  Entering stats and player names accurately is crucial for confirming matches and
                  tracking stats.
                </Text>
                <Text style={styles.helpPara}>
                  In order for a match to be confirmed both players must have matching players and
                  stats.
                </Text>
                <Text style={styles.helpPara}>
                  If you have a disagreement on stats, please communicate with the other player.
                </Text>
                <Text style={styles.helpPara}>
                  If a disagreement persists feel free to reach out to the developers.
                </Text>
              </ScrollView>
              <Pressable style={styles.confirmBtn} onPress={() => setShowHelp(false)}>
                <Text style={styles.confirmText}>Close</Text>
              </Pressable>
            </View>
          </View>
        </Modal>

        {/* Enter stats modal */}
        <Modal visible={showModal} transparent animationType="slide">
          <View style={styles.modalOverlay}>
            <View style={styles.modal}>
              <ScrollView>
                <Text style={styles.modalTitle}>Enter Stats</Text>

                {gameType === 'Shots Made' && (
                  <>
                    <TextInput
                      style={styles.input}
                      placeholder="Your Player"
                      placeholderTextColor="#999"
                      value={yourPlayer}
                      onChangeText={setYourPlayer}
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Shots Made"
                      placeholderTextColor="#999"
                      keyboardType="numeric"
                      value={yourShots}
                      onChangeText={setYourShots}
                    />
                  </>
                )}

                {gameType === 'Score' && (
                  <>
                    <Text style={styles.subhead}>Your Team A</Text>
                    {yourTeamA.map((player, i) => (
                      <TextInput
                        key={`teamA-${i}`}
                        style={styles.input}
                        placeholder={`Player ${i + 1} Name`}
                        placeholderTextColor="#999"
                        value={player.name}
                        onChangeText={(v) => updateTeamName(yourTeamA, setYourTeamA, i, v)}
                      />
                    ))}
                    <TextInput
                      style={styles.input}
                      placeholder="Total Score for Team A"
                      placeholderTextColor="#999"
                      keyboardType="numeric"
                      value={String(yourScoreA)}
                      onChangeText={setYourScoreA}
                    />

                    <Text style={styles.subhead}>Your Team B</Text>
                    {yourTeamB.map((player, i) => (
                      <TextInput
                        key={`teamB-${i}`}
                        style={styles.input}
                        placeholder={`Player ${i + 2} Name`}
                        placeholderTextColor="#999"
                        value={player.name}
                        onChangeText={(v) => updateTeamName(yourTeamB, setYourTeamB, i, v)}
                      />
                    ))}
                    <TextInput
                      style={styles.input}
                      placeholder="Total Score for Team B"
                      placeholderTextColor="#999"
                      keyboardType="numeric"
                      value={String(yourScoreB)}
                      onChangeText={setYourScoreB}
                    />
                  </>
                )}

                {gameType === 'Other' && (
                  <TextInput
                    style={styles.input}
                    placeholder="Describe Outcome"
                    placeholderTextColor="#999"
                    keyboardType="numeric"
                    value={yourOutcome}
                    onChangeText={setYourOutcome}
                  />
                )}

                <View style={styles.modalActions}>
                  <Pressable style={styles.cancelBtn} onPress={resetForm}>
                    <Text style={styles.cancelText}>Cancel</Text>
                  </Pressable>
                  <Pressable
                    style={[styles.confirmBtn, styles.flexBtn, submitting && styles.disabled]}
                    onPress={handleSubmit}
                    disabled={submitting}
                  >
                    <Text style={styles.confirmText}>Submit</Text>
                  </Pressable>
                </View>
              </ScrollView>
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
  helpBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  helpText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  list: { paddingBottom: 40 },
  betCard: {
    backgroundColor: 'rgba(255,255,255,0.94)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  betTop: { marginBottom: 8 },
  posterTime: { fontSize: 13, color: '#666' },
  subject: { fontSize: 18, fontWeight: 'bold', color: '#1a1a1a', marginBottom: 4 },
  meta: { fontSize: 13, color: '#555' },
  betBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 8,
  },
  amount: { fontSize: 15, fontWeight: '600', color: '#1a1a1a' },
  line: { fontSize: 15, fontWeight: '600', color: '#1a1a1a' },
  statusText: { fontSize: 13, color: '#1a7a3a', marginBottom: 10, fontStyle: 'italic' },
  acceptBtn: {
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  acceptText: { color: '#fff', fontWeight: 'bold', letterSpacing: 1 },
  popup: { backgroundColor: '#1a7a3a', borderRadius: 8, padding: 12, marginBottom: 12 },
  popupText: { color: '#fff', textAlign: 'center', fontWeight: '600' },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  modal: { backgroundColor: '#fff', borderRadius: 16, padding: 20, maxHeight: '85%' },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 16,
    color: '#1a1a1a',
  },
  subhead: { fontSize: 15, fontWeight: '600', color: '#1a1a1a', marginBottom: 8, marginTop: 4 },
  helpPara: { fontSize: 14, color: '#444', marginBottom: 8, lineHeight: 20 },
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
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
  },
  flexBtn: { flex: 1, marginLeft: 8 },
  disabled: { opacity: 0.5 },
  confirmText: { color: '#fff', fontWeight: '600' },
});
