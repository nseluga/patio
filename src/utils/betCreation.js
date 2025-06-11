// Create a standard bet object with the provided parameters
export function createStandardBet({
  id,
  poster,
  posterId,
  accepterId = null,
  timePosted,
  matchup,
  amount,
  lineType,
  lineNumber,
  gameType,
  gamePlayed,
  hiddenFrom = [],

  // Score-specific
  gameSize,
  yourTeamA,
  yourTeamB,
  oppTeamA,
  oppTeamB,
  yourScoreA,
  yourScoreB,
  oppScoreA,
  oppScoreB,

  // Shots Made
  yourPlayer,
  yourShots,
  oppPlayer,
  oppShots,

  // Other
  yourOutcome,
  oppOutcome
}) {
  const base = {
    id,
    poster,
    posterId,
    accepterId,
    timePosted,
    matchup,
    amount: parseInt(amount),
    lineType,
    lineNumber: parseFloat(lineNumber),
    gameType,
    gamePlayed,
    hiddenFrom,
  };

  if (gameType === "Score") {
    return {
      ...base,
      gameSize,
      yourTeamA,
      yourTeamB,
      oppTeamA,
      oppTeamB,
      yourScoreA,
      yourScoreB,
      oppScoreA,
      oppScoreB,
    };
  } else if (gameType === "Shots Made") {
    return {
      ...base,
      yourPlayer,
      yourShots,
      oppPlayer,
      oppShots,
    };
  } else if (gameType === "Other") {
    return {
      ...base,
      yourPlayer,
      yourOutcome,
      oppPlayer,
      oppOutcome,
    };
  }

  return base;
}
