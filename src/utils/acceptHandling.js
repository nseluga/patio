import { useEffect } from "react";

// Auto-save bets to localStorage whenever they change
export const useAutoSaveBets = (bets, storageKey) => {
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(bets));
  }, [bets, storageKey]);
};

// Remove a bet from the list by index
export const removeBetByIndex = (indexToRemove, setBets) => {
  setBets((prevBets) =>
    prevBets.filter((_, index) => index !== indexToRemove)
  );
};

// Accept a CPU bet: do NOT remove from the list, just add to ongoing
export const acceptBetForCPU = (indexToAccept, setBets, addOngoingBet, userPlayerId) => {
  let acceptedBet = null;

  setBets((prevBets) => {
    const bet = prevBets[indexToAccept];
    acceptedBet = { ...bet, accepterId: userPlayerId };

    // Hide the bet from this user only
    const updated = prevBets.map((b, i) =>
      i === indexToAccept
        ? { ...b, hiddenFrom: [...(b.hiddenFrom || []), userPlayerId] }
        : b
    );
    return updated;
  });

  setTimeout(() => {
    addOngoingBet(acceptedBet);
  }, 0);
};

// Accept a bet: adds it to ongoingBets if not already there, then removes it
export const acceptBetWithOngoing = (indexToAccept, setBets, addOngoingBet, userPlayerId) => {
  let acceptedBet = null;

  setBets((prevBets) => {
    const bet = prevBets[indexToAccept];
    acceptedBet = { ...bet, accepterId: userPlayerId }; // inject accepter ID
    return prevBets.filter((_, index) => index !== indexToAccept);
  });

  // Delay to next tick so it doesn’t run during render
  setTimeout(() => {
    addOngoingBet(acceptedBet);
  }, 0);
};
