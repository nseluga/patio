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
    setBets((prevBets) => {
      const acceptedBet = prevBets[indexToAccept];
  
      // Call passed-in addOngoingBet instead of writing to localStorage
      addOngoingBet(acceptedBet);
  
      return prevBets.filter((_, index) => index !== indexToAccept);
    });
  };