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

// Accept a bet: adds it to ongoingBets if not already there, then removes it
export const acceptBetWithOngoing = (indexToAccept, setBets, addOngoingBet) => {
  let acceptedBet = null;

  setBets((prevBets) => {
    acceptedBet = prevBets[indexToAccept];
    return prevBets.filter((_, index) => index !== indexToAccept);
  });

  // Delay to next tick so it doesn’t run during render
  setTimeout(() => {
    addOngoingBet(acceptedBet);
  }, 0);
};
