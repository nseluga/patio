// Create a standard bet object with the provided parameters
export function createStandardBet({
    id,
    poster,
    posterId,
    timePosted,
    matchup,
    amount,
    lineType,
    lineNumber,
    gameType,
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
      time: timePosted,
      matchup,
      amount,
      lineType,
      lineNumber,
      gameType,
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
  