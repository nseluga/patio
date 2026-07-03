import { View, Text, StyleSheet } from 'react-native';

export default function CPU() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>House</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  text: {
    fontSize: 24,
    fontWeight: 'bold',
  },
});
