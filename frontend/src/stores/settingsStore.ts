import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
    timezone: string;
    username: string;
    theme: 'nano-dark' | 'light'; // keeping it future proof, though currently enforcing nano-dark

    setTimezone: (timezone: string) => void;
    setUsername: (name: string) => void;
    setTheme: (theme: 'nano-dark' | 'light') => void;
}

export const useSettingsStore = create<SettingsState>()(
    persist(
        (set) => ({
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, // Default to system
            username: 'Traveler',
            theme: 'nano-dark',

            setTimezone: (timezone) => set({ timezone }),
            setUsername: (username) => set({ username }),
            setTheme: (theme) => set({ theme }),
        }),
        {
            name: 'open-gdr-settings', // unique name for local storage
        }
    )
);
