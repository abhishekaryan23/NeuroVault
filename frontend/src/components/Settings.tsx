import { useState, useEffect } from 'react';
import { useSettingsStore } from '../stores/settingsStore';
import { GlobeAltIcon, UserCircleIcon, TrashIcon, CheckCircleIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

const TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Australia/Sydney",
    "Pacific/Auckland",
];

interface SettingsProps {
    onBack?: () => void;
}

export const Settings = ({ onBack }: SettingsProps) => {
    const { timezone, username, setTimezone, setUsername } = useSettingsStore();
    const [nameInput, setNameInput] = useState(username);
    const [saved, setSaved] = useState(false);

    // Sync input if store changes externally
    useEffect(() => {
        setNameInput(username);
    }, [username]);

    const handleSave = () => {
        setUsername(nameInput);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    };

    const handleDataWipe = () => {
        if (window.confirm("CRITICAL WARNING: This will delete ALL local settings and cache. Are you sure? (Note: API data is persistent on backend)")) {
            localStorage.clear();
            window.location.reload();
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center gap-4 border-b border-white/5 pb-6">
                {onBack && (
                    <button
                        onClick={onBack}
                        className="p-2 -ml-2 hover:bg-white/5 rounded-full text-ash-gray hover:text-white transition-colors"
                        title="Go Back"
                    >
                        <ArrowLeftIcon className="w-6 h-6" />
                    </button>
                )}
                <div>
                    <h2 className="text-2xl font-bold text-white mb-1">Settings</h2>
                    <p className="text-ash-gray text-sm">Configure your local environment.</p>
                </div>
            </div>

            {/* Profile Section */}
            <section className="space-y-4">
                <div className="flex items-center gap-2 text-banana font-bold uppercase tracking-wider text-xs">
                    <UserCircleIcon className="w-4 h-4" />
                    Profile
                </div>
                <div className="bg-graphite p-6 rounded-2xl border border-white/5">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Display Name</label>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={nameInput}
                            onChange={(e) => setNameInput(e.target.value)}
                            className="flex-1 bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-banana/50 transition-colors"
                            placeholder="Enter your name"
                        />
                        <button
                            onClick={handleSave}
                            className="bg-white/5 hover:bg-banana/10 text-white hover:text-banana px-6 py-2 rounded-lg font-bold transition-all border border-white/5 hover:border-banana/30"
                        >
                            {saved ? (
                                <span className="flex items-center gap-1 text-mint">
                                    <CheckCircleIcon className="w-4 h-4" /> Saved
                                </span>
                            ) : "Save"}
                        </button>
                    </div>
                    <p className="text-xs text-ash-gray mt-2 opacity-60">This name is used for local personalization only.</p>
                </div>
            </section>

            {/* Regional Settings */}
            <section className="space-y-4">
                <div className="flex items-center gap-2 text-banana font-bold uppercase tracking-wider text-xs">
                    <GlobeAltIcon className="w-4 h-4" />
                    Region & Time
                </div>
                <div className="bg-graphite p-6 rounded-2xl border border-white/5 space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Timezone</label>
                        <select
                            value={timezone}
                            onChange={(e) => setTimezone(e.target.value)}
                            className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-banana/50 appearance-none cursor-pointer"
                        >
                            {TIMEZONES.map(tz => (
                                <option key={tz} value={tz} className="bg-graphite">{tz}</option>
                            ))}
                            {!TIMEZONES.includes(timezone) && <option value={timezone} className="bg-graphite">{timezone} (Detected)</option>}
                        </select>
                        <p className="text-xs text-ash-gray mt-2 pt-2 border-t border-white/5 flex justify-between">
                            <span>Current Local Time:</span>
                            <span className="font-mono text-banana">
                                {new Date().toLocaleTimeString('en-US', { timeZone: timezone })}
                            </span>
                        </p>
                    </div>
                </div>
            </section>

            {/* Data Management */}
            <section className="space-y-4 pt-4">
                <div className="bg-red-500/5 p-6 rounded-2xl border border-red-500/20">
                    <h3 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                        <TrashIcon className="w-4 h-4" />
                        Danger Zone
                    </h3>
                    <p className="text-sm text-ash-gray mb-4">
                        Clear all local settings and cached data. This will not delete your actual notes from the database, but will reset your preferences.
                    </p>
                    <button
                        onClick={handleDataWipe}
                        className="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 px-4 py-2 rounded-lg font-bold transition-colors border border-red-500/20"
                    >
                        Reset Local Data
                    </button>
                </div>
            </section>
        </div>
    );
};
