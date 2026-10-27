import { useState } from 'react';
import { getGroqKey, setGroqKey } from '../lib/api';

/** Optional own Groq key. Saved in this browser only and sent as the X-Groq-Api-Key header. */
export default function GroqKeyField() {
  const [value, setValue] = useState(getGroqKey());

  return (
    <div>
      <label className="label">Your Groq API key (optional)</label>
      <input
        className="input"
        type="password"
        autoComplete="off"
        placeholder="gsk_…  (uses the server's key if empty)"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setGroqKey(e.target.value);
        }}
      />
      <p className="text-xs text-slate-500 mt-1">
        Free at console.groq.com/keys. Stored only in this browser, never in our database.
      </p>
    </div>
  );
}
