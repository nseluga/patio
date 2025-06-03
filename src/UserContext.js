// Import createContext from React to create a new context
import { createContext } from 'react';

// Create a context to hold user information globally across the app
// The default value is 'null', meaning no user is logged in by default
const UserContext = createContext(null);

// Export the context so it can be used in other components (e.g., App.js, Login.js, Profile.js)
export default UserContext;
