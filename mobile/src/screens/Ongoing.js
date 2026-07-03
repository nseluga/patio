import { View, Text, StyleSheet } from 'react-native';

export default function Ongoing() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Ongoing</Text>
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
