import AsyncStorage from '@react-native-async-storage/async-storage';

// In RN: Ongoing fetches from server, so this hook is a no-op parity shim
export const useAutoSaveBets = (bets, storageKey) => {
  // no-op
};

// Remove a bet from the list by index
export const removeBetByIndex = (indexToRemove, setBets) => {
  setBets((prev) => prev.filter((_, i) => i !== indexToRemove));
};

// Accept a CPU bet: do NOT remove from the list, just hide it and add to ongoing cache
export const acceptBetForCPU = async (indexToAccept, setBets, addOngoingBet, userPlayerId) => {
  let acceptedBet = null;
  setBets((prev) => {
    const bet = prev[indexToAccept];
    acceptedBet = { ...bet, accepterId: userPlayerId };
    return prev.map((b, i) =>
      i === indexToAccept
        ? { ...b, hiddenFrom: [...(b.hiddenFrom || []), userPlayerId] }
        : b
    );
  });
  if (acceptedBet) await addOngoingBet(acceptedBet);
};

// Accept a PvP bet: remove from the list, then add to ongoing cache
export const acceptBetWithOngoing = async (indexToAccept, setBets, addOngoingBet, userPlayerId) => {
  let acceptedBet = null;
  setBets((prev) => {
    const bet = prev[indexToAccept];
    acceptedBet = { ...bet, accepterId: userPlayerId };
    return prev.filter((_, i) => i !== indexToAccept);
  });
  if (acceptedBet) await addOngoingBet(acceptedBet);
};
