export default {
  name: "Patio",
  slug: "patio",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  ios: {
    // TODO(10.3): placeholder — confirm the real reverse-DNS bundle ID before
    // creating the App ID in Apple Developer / running the first EAS build.
    bundleIdentifier: "com.nseluga.patio",
    supportsTablet: true,
  },
  android: {
    package: "com.nseluga.patio",
    adaptiveIcon: {
      backgroundColor: "#E6F4FE",
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundImage: "./assets/android-icon-background.png",
      monochromeImage: "./assets/android-icon-monochrome.png",
    },
  },
  web: {
    favicon: "./assets/favicon.png",
  },
  plugins: ["expo-secure-store"],
  extra: {
    apiUrl: process.env.EXPO_PUBLIC_API_URL || "http://localhost:5001",
  },
};
