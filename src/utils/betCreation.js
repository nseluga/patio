// Create a standard bet object with the provided parameters
export function createStandardBet({
    id,
    poster,
    posterId,
    accepterId,
    timePosted,
    matchup,
    amount,
    lineType,
    lineNumber,
    gameType,
    gamePlayed,
    yourPlayerA,
    yourPlayerB,
    yourStatsA,
    yourStatsB,
    yourPlayer,
    yourStats,
    yourInfo,
    oppPlayerA,
    oppPlayerB,
    oppStatsA,
    oppStatsB,
    oppPlayer,
    oppStats,
    oppInfo,
  }) {
    const base = {
      id,
      poster,
      posterId,
      accepterId,
      time: timePosted,
      matchup,
      amount,
      lineType,
      lineNumber,
      gameType,
      gamePlayed,
    };
  
    if (gameType === "Score") {
      return {
        ...base,
        yourPlayerA,
        yourPlayerB,
        yourStatsA,
        yourStatsB,
        oppPlayerA,
        oppPlayerB,
        oppStatsA,
        oppStatsB,
      };
    } else if (gameType === "Shots Made") {
      return {
        ...base,
        yourPlayer,
        yourStats,
        oppPlayer,
        oppStats,
      };
    } else if (gameType === "Other") {
      return {
        ...base,
        yourInfo,
        oppInfo,
      };
    }
  
    return base;
  }
  