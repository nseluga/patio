// Create a standard bet object with the provided parameters
export function createStandardBet({
    id,
    poster,
    timePosted,
    matchup,
    amount,
    lineType,
    lineNumber,
    gameType,
  }) {
    return {
      id,
      poster,
      timePosted,
      matchup,
      amount,
      lineType,
      lineNumber,
      gameType,
  
      // Score-specific
      // Your inputs
      yourPlayerA: "",
      yourPlayerB: "",
      yourStatsA: "",
      yourStatsB: "",

      // Opponnent inputs
      oppPlayerA: "",
      oppPlayerB: "",
      oppStatsA: "",
      oppStatsB: "",
  
      // Shots Made-specific
      // Your inputs
      yourPlayer: "",
      yourStats: "",

      // Opponent inputs
      oppPlayer: "",
      oppStats: "",

      // Other specific
      yourInfo: "",
      oppInfo: "",
    };
  }
  