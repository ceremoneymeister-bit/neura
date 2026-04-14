import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ru.ceremoneymeister.neura',
  appName: 'Neura',
  webDir: 'dist',
  server: {
    url: 'https://app.ceremoneymeister.ru',
    cleartext: false,
  },
  ios: {
    scheme: 'Neura',
    contentInset: 'always',
  },
};

export default config;
